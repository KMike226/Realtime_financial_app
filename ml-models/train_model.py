"""
Training and Validation Script for Anomaly Detection Model
==========================================================

This script provides functionality to train, validate, and test the anomaly detection model
using historical financial data. It includes cross-validation and performance metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
import json
import os
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns

from anomaly_detection import FinancialAnomalyDetector, create_sample_data
from config import get_config, validate_config, PERFORMANCE_THRESHOLDS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Class for training and validating the anomaly detection model.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the model trainer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or get_config()
        self.detector = FinancialAnomalyDetector(self.config)
        self.validation_results = {}
        
    def prepare_training_data(self, data: pd.DataFrame, 
                            train_ratio: float = 0.7) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split data into training and validation sets.
        
        Args:
            data: Full dataset
            train_ratio: Ratio of data to use for training
            
        Returns:
            Tuple of (training_data, validation_data)
        """
        # Sort by timestamp
        data = data.sort_values('timestamp').reset_index(drop=True)
        
        # Split chronologically
        split_idx = int(len(data) * train_ratio)
        train_data = data.iloc[:split_idx].copy()
        val_data = data.iloc[split_idx:].copy()
        
        logger.info(f"Split data: {len(train_data)} training samples, {len(val_data)} validation samples")
        
        return train_data, val_data
    
    def train_model(self, train_data: pd.DataFrame) -> Dict:
        """
        Train the anomaly detection model.
        
        Args:
            train_data: Training dataset
            
        Returns:
            Training results dictionary
        """
        logger.info("Starting model training...")
        
        # Prepare features
        train_processed = self.detector.prepare_features(train_data)
        
        # Train the model
        self.detector.train_ml_model(train_processed)
        
        # Get training results
        train_results = self.detector.detect_anomalies(train_processed, train_model=False)
        
        # Calculate training metrics
        training_metrics = self._calculate_metrics(train_results, 'training')
        
        logger.info(f"Model training completed. Training anomaly rate: {training_metrics['anomaly_rate']:.2%}")
        
        return {
            'training_metrics': training_metrics,
            'training_samples': len(train_data),
            'training_timestamp': datetime.now().isoformat()
        }
    
    def validate_model(self, val_data: pd.DataFrame) -> Dict:
        """
        Validate the trained model.
        
        Args:
            val_data: Validation dataset
            
        Returns:
            Validation results dictionary
        """
        if not self.detector.is_trained:
            raise ValueError("Model must be trained before validation")
        
        logger.info("Starting model validation...")
        
        # Prepare features
        val_processed = self.detector.prepare_features(val_data)
        
        # Detect anomalies
        val_results = self.detector.detect_anomalies(val_processed, train_model=False)
        
        # Calculate validation metrics
        validation_metrics = self._calculate_metrics(val_results, 'validation')
        
        # Cross-validation
        cv_results = self._cross_validate(val_processed)
        
        logger.info(f"Model validation completed. Validation anomaly rate: {validation_metrics['anomaly_rate']:.2%}")
        
        return {
            'validation_metrics': validation_metrics,
            'cross_validation': cv_results,
            'validation_samples': len(val_data),
            'validation_timestamp': datetime.now().isoformat()
        }
    
    def _calculate_metrics(self, results: pd.DataFrame, dataset_type: str) -> Dict:
        """
        Calculate performance metrics for the model.
        
        Args:
            results: DataFrame with detection results
            dataset_type: Type of dataset (training/validation)
            
        Returns:
            Dictionary with calculated metrics
        """
        total_samples = len(results)
        anomalies = results['is_anomaly'].sum()
        anomaly_rate = anomalies / total_samples if total_samples > 0 else 0
        
        # Calculate average anomaly scores
        avg_score = results['anomaly_score'].mean()
        max_score = results['anomaly_score'].max()
        min_score = results['anomaly_score'].min()
        
        metrics = {
            'dataset_type': dataset_type,
            'total_samples': total_samples,
            'anomaly_count': anomalies,
            'anomaly_rate': anomaly_rate,
            'avg_anomaly_score': avg_score,
            'max_anomaly_score': max_score,
            'min_anomaly_score': min_score
        }
        
        # Add per-symbol metrics if available
        if 'symbol' in results.columns:
            symbol_metrics = results.groupby('symbol').agg({
                'is_anomaly': ['count', 'sum', 'mean'],
                'anomaly_score': ['mean', 'max', 'min']
            }).round(4)
            
            metrics['per_symbol_metrics'] = symbol_metrics.to_dict()
        
        return metrics
    
    def _cross_validate(self, data: pd.DataFrame, n_splits: int = 5) -> Dict:
        """
        Perform time series cross-validation.
        
        Args:
            data: Dataset for cross-validation
            n_splits: Number of CV splits
            
        Returns:
            Cross-validation results
        """
        logger.info(f"Performing {n_splits}-fold time series cross-validation...")
        
        # Prepare features
        X = data[self.detector.feature_names].values
        y = data['is_anomaly'].values if 'is_anomaly' in data.columns else np.zeros(len(data))
        
        # Time series split
        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            # Train on fold
            fold_detector = FinancialAnomalyDetector(self.config)
            fold_detector.feature_names = self.detector.feature_names
            fold_detector.scaler.fit(X_train)
            
            # Create temporary model for this fold
            X_train_scaled = fold_detector.scaler.transform(X_train)
            fold_detector.isolation_forest = self.detector.isolation_forest.__class__(
                **self.detector.isolation_forest.get_params()
            )
            fold_detector.isolation_forest.fit(X_train_scaled)
            fold_detector.is_trained = True
            
            # Predict on validation set
            X_val_scaled = fold_detector.scaler.transform(X_val)
            predictions = fold_detector.isolation_forest.predict(X_val_scaled)
            scores = fold_detector.isolation_forest.decision_function(X_val_scaled)
            
            # Calculate fold metrics
            fold_anomaly_rate = (predictions == -1).mean()
            cv_scores.append(fold_anomaly_rate)
        
        return {
            'n_splits': n_splits,
            'cv_scores': cv_scores,
            'mean_cv_score': np.mean(cv_scores),
            'std_cv_score': np.std(cv_scores)
        }
    
    def evaluate_performance(self, results: Dict) -> Dict:
        """
        Evaluate model performance against thresholds.
        
        Args:
            results: Results from training/validation
            
        Returns:
            Performance evaluation results
        """
        evaluation = {
            'meets_thresholds': True,
            'thresholds_met': [],
            'thresholds_failed': [],
            'recommendations': []
        }
        
        # Check validation metrics
        if 'validation_metrics' in results:
            val_metrics = results['validation_metrics']
            
            # Check anomaly rate (should be reasonable)
            if val_metrics['anomaly_rate'] > 0.5:
                evaluation['thresholds_failed'].append('anomaly_rate_too_high')
                evaluation['recommendations'].append('Consider adjusting contamination parameter')
                evaluation['meets_thresholds'] = False
            else:
                evaluation['thresholds_met'].append('anomaly_rate_reasonable')
        
        # Check cross-validation stability
        if 'cross_validation' in results:
            cv_results = results['cross_validation']
            cv_std = cv_results['std_cv_score']
            
            if cv_std > 0.1:  # High variance across folds
                evaluation['thresholds_failed'].append('cv_high_variance')
                evaluation['recommendations'].append('Model shows high variance - consider more training data')
                evaluation['meets_thresholds'] = False
            else:
                evaluation['thresholds_met'].append('cv_stable')
        
        return evaluation
    
    def save_results(self, results: Dict, filepath: str) -> None:
        """
        Save training and validation results.
        
        Args:
            results: Results dictionary
            filepath: Path to save results
        """
        # Add configuration to results
        results['config'] = self.config
        results['model_info'] = {
            'feature_names': self.detector.feature_names,
            'is_trained': self.detector.is_trained,
            'trained_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filepath}")
    
    def plot_results(self, results: pd.DataFrame, save_path: Optional[str] = None) -> None:
        """
        Create visualization plots for the results.
        
        Args:
            results: DataFrame with detection results
            save_path: Optional path to save plots
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Anomaly Detection Results', fontsize=16)
        
        # Plot 1: Anomaly scores over time
        axes[0, 0].plot(results['timestamp'], results['anomaly_score'], alpha=0.7)
        axes[0, 0].scatter(
            results[results['is_anomaly']]['timestamp'],
            results[results['is_anomaly']]['anomaly_score'],
            color='red', alpha=0.8, s=20, label='Anomalies'
        )
        axes[0, 0].set_title('Anomaly Scores Over Time')
        axes[0, 0].set_xlabel('Time')
        axes[0, 0].set_ylabel('Anomaly Score')
        axes[0, 0].legend()
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # Plot 2: Price vs Volume with anomalies
        scatter = axes[0, 1].scatter(results['price'], results['volume'], 
                                   c=results['anomaly_score'], cmap='viridis', alpha=0.6)
        axes[0, 1].scatter(
            results[results['is_anomaly']]['price'],
            results[results['is_anomaly']]['volume'],
            color='red', s=50, alpha=0.8, label='Anomalies'
        )
        axes[0, 1].set_title('Price vs Volume (Anomalies Highlighted)')
        axes[0, 1].set_xlabel('Price')
        axes[0, 1].set_ylabel('Volume')
        axes[0, 1].legend()
        plt.colorbar(scatter, ax=axes[0, 1], label='Anomaly Score')
        
        # Plot 3: Anomaly score distribution
        axes[1, 0].hist(results['anomaly_score'], bins=50, alpha=0.7, edgecolor='black')
        axes[1, 0].axvline(results['anomaly_score'].mean(), color='red', linestyle='--', 
                          label=f'Mean: {results["anomaly_score"].mean():.2f}')
        axes[1, 0].set_title('Anomaly Score Distribution')
        axes[1, 0].set_xlabel('Anomaly Score')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].legend()
        
        # Plot 4: Anomalies by symbol (if available)
        if 'symbol' in results.columns:
            symbol_anomalies = results.groupby('symbol')['is_anomaly'].sum()
            axes[1, 1].bar(symbol_anomalies.index, symbol_anomalies.values)
            axes[1, 1].set_title('Anomalies by Symbol')
            axes[1, 1].set_xlabel('Symbol')
            axes[1, 1].set_ylabel('Number of Anomalies')
            axes[1, 1].tick_params(axis='x', rotation=45)
        else:
            axes[1, 1].text(0.5, 0.5, 'No symbol data available', 
                           ha='center', va='center', transform=axes[1, 1].transAxes)
            axes[1, 1].set_title('Anomalies by Symbol')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Plots saved to {save_path}")
        
        plt.show()


def main():
    """
    Main function to run training and validation pipeline.
    """
    print("Anomaly Detection Model Training and Validation")
    print("=" * 50)
    
    # Create sample data for demonstration
    print("Creating sample financial data...")
    sample_data = create_sample_data(1000)
    print(f"Generated {len(sample_data)} data points")
    
    # Initialize trainer
    print("\nInitializing model trainer...")
    trainer = ModelTrainer()
    
    # Split data
    print("\nSplitting data into training and validation sets...")
    train_data, val_data = trainer.prepare_training_data(sample_data)
    
    # Train model
    print("\nTraining model...")
    training_results = trainer.train_model(train_data)
    
    # Validate model
    print("\nValidating model...")
    validation_results = trainer.validate_model(val_data)
    
    # Combine results
    all_results = {**training_results, **validation_results}
    
    # Evaluate performance
    print("\nEvaluating model performance...")
    performance_eval = trainer.evaluate_performance(all_results)
    
    # Print results
    print("\nTraining Results:")
    print(f"  Training samples: {training_results['training_samples']}")
    print(f"  Training anomaly rate: {training_results['training_metrics']['anomaly_rate']:.2%}")
    
    print("\nValidation Results:")
    print(f"  Validation samples: {validation_results['validation_samples']}")
    print(f"  Validation anomaly rate: {validation_results['validation_metrics']['anomaly_rate']:.2%}")
    print(f"  CV mean score: {validation_results['cross_validation']['mean_cv_score']:.3f}")
    print(f"  CV std: {validation_results['cross_validation']['std_cv_score']:.3f}")
    
    print("\nPerformance Evaluation:")
    print(f"  Meets thresholds: {performance_eval['meets_thresholds']}")
    if performance_eval['recommendations']:
        print("  Recommendations:")
        for rec in performance_eval['recommendations']:
            print(f"    - {rec}")
    
    # Save results
    results_file = 'ml-models/training_results.json'
    trainer.save_results(all_results, results_file)
    
    # Create visualizations
    print("\nCreating visualizations...")
    val_results = trainer.detector.detect_anomalies(val_data, train_model=False)
    trainer.plot_results(val_results, 'ml-models/anomaly_detection_plots.png')
    
    # Save trained model
    model_file = 'ml-models/trained_anomaly_model.json'
    trainer.detector.save_model(model_file)
    
    print(f"\nTraining completed successfully!")
    print(f"Results saved to: {results_file}")
    print(f"Model saved to: {model_file}")
    print(f"Plots saved to: ml-models/anomaly_detection_plots.png")


if __name__ == "__main__":
    main()
