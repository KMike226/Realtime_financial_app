"""
Training and Evaluation Script for Price Prediction Model
=========================================================

This script provides functionality to train, validate, and evaluate the price prediction model
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
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns

from price_prediction import PricePredictor, create_sample_data
from prediction_config import get_config, validate_config, RISK_LEVELS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionTrainer:
    """
    Class for training and evaluating the price prediction model.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the prediction trainer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or get_config()
        self.predictor = PricePredictor(self.config)
        self.evaluation_results = {}
        
    def prepare_training_data(self, data: pd.DataFrame, 
                            train_ratio: float = 0.8) -> Tuple[pd.DataFrame, pd.DataFrame]:
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
        Train the price prediction model.
        
        Args:
            train_data: Training dataset
            
        Returns:
            Training results dictionary
        """
        logger.info("Starting model training...")
        
        # Prepare features and targets
        train_processed = self.predictor.prepare_features(train_data)
        train_processed = self.predictor.create_prediction_targets(train_processed)
        
        # Train the model
        training_results = self.predictor.train_models(train_processed)
        
        logger.info(f"Model training completed for {len(training_results)} horizons")
        
        return {
            'training_results': training_results,
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
        if not self.predictor.is_trained:
            raise ValueError("Model must be trained before validation")
        
        logger.info("Starting model validation...")
        
        # Prepare features and targets
        val_processed = self.predictor.prepare_features(val_data)
        val_processed = self.predictor.create_prediction_targets(val_processed)
        
        validation_results = {}
        
        # Evaluate each horizon
        for horizon in self.config['prediction_horizons']:
            evaluation = self.predictor.evaluate_model(val_processed, horizon)
            if evaluation:
                validation_results[horizon] = evaluation
        
        logger.info(f"Model validation completed for {len(validation_results)} horizons")
        
        return {
            'validation_results': validation_results,
            'validation_samples': len(val_data),
            'validation_timestamp': datetime.now().isoformat()
        }
    
    def cross_validate(self, data: pd.DataFrame, n_splits: int = 5) -> Dict:
        """
        Perform time series cross-validation.
        
        Args:
            data: Dataset for cross-validation
            n_splits: Number of CV splits
            
        Returns:
            Cross-validation results
        """
        logger.info(f"Performing {n_splits}-fold time series cross-validation...")
        
        # Prepare data
        df = self.predictor.prepare_features(data)
        df = self.predictor.create_prediction_targets(df)
        
        cv_results = {}
        
        # Cross-validate each horizon
        for horizon in self.config['prediction_horizons']:
            target_col = f'price_change_{horizon}d'
            if target_col not in df.columns:
                continue
            
            # Prepare features and targets
            feature_cols = [col for col in self.config['features'] if col in df.columns]
            X = df[feature_cols].values
            y = df[target_col].dropna().values
            
            if len(y) < 20:
                continue
            
            # Time series split
            tscv = TimeSeriesSplit(n_splits=n_splits)
            cv_scores = {'r2': [], 'mae': [], 'direction_accuracy': []}
            
            for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                
                if len(y_train) < 10 or len(y_val) < 5:
                    continue
                
                # Train simple model for this fold
                from sklearn.linear_model import LinearRegression
                model = LinearRegression()
                model.fit(X_train, y_train)
                
                # Predict
                y_pred = model.predict(X_val)
                
                # Calculate metrics
                r2 = r2_score(y_val, y_pred)
                mae = mean_absolute_error(y_val, y_pred)
                direction_acc = np.mean((y_pred > 0) == (y_val > 0))
                
                cv_scores['r2'].append(r2)
                cv_scores['mae'].append(mae)
                cv_scores['direction_accuracy'].append(direction_acc)
            
            if cv_scores['r2']:
                cv_results[horizon] = {
                    'r2_mean': np.mean(cv_scores['r2']),
                    'r2_std': np.std(cv_scores['r2']),
                    'mae_mean': np.mean(cv_scores['mae']),
                    'mae_std': np.std(cv_scores['mae']),
                    'direction_accuracy_mean': np.mean(cv_scores['direction_accuracy']),
                    'direction_accuracy_std': np.std(cv_scores['direction_accuracy']),
                    'n_splits': len(cv_scores['r2'])
                }
        
        return cv_results
    
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
        
        # Check validation results
        if 'validation_results' in results:
            val_results = results['validation_results']
            
            for horizon, horizon_results in val_results.items():
                for model_name, metrics in horizon_results.items():
                    # Check R² score
                    if metrics['r2'] < self.config['performance_thresholds']['min_r2_score']:
                        evaluation['thresholds_failed'].append(f'r2_score_low_{horizon}d_{model_name}')
                        evaluation['recommendations'].append(f'Improve R² score for {horizon}d {model_name} model')
                        evaluation['meets_thresholds'] = False
                    else:
                        evaluation['thresholds_met'].append(f'r2_score_good_{horizon}d_{model_name}')
                    
                    # Check direction accuracy
                    if metrics['direction_accuracy'] < self.config['performance_thresholds']['min_direction_accuracy']:
                        evaluation['thresholds_failed'].append(f'direction_accuracy_low_{horizon}d_{model_name}')
                        evaluation['recommendations'].append(f'Improve direction accuracy for {horizon}d {model_name} model')
                        evaluation['meets_thresholds'] = False
                    else:
                        evaluation['thresholds_met'].append(f'direction_accuracy_good_{horizon}d_{model_name}')
        
        return evaluation
    
    def generate_predictions_report(self, data: pd.DataFrame) -> Dict:
        """
        Generate a comprehensive predictions report.
        
        Args:
            data: Dataset for generating predictions
            
        Returns:
            Predictions report dictionary
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'predictions': {},
            'summary': {}
        }
        
        # Generate predictions for each horizon
        for horizon in self.config['prediction_horizons']:
            predictions = self.predictor.predict(data, horizon)
            if predictions:
                summary = self.predictor.get_prediction_summary(predictions)
                report['predictions'][horizon] = summary
        
        # Generate overall summary
        if report['predictions']:
            all_predictions = []
            for horizon_data in report['predictions'].values():
                if 'best_prediction' in horizon_data:
                    all_predictions.append(horizon_data['best_prediction']['predicted_change_pct'])
            
            if all_predictions:
                report['summary'] = {
                    'avg_predicted_change': np.mean(all_predictions),
                    'max_predicted_change': np.max(all_predictions),
                    'min_predicted_change': np.min(all_predictions),
                    'prediction_consistency': 1 - np.std(all_predictions) / (np.mean(np.abs(all_predictions)) + 1e-6)
                }
        
        return report
    
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
            'feature_names': self.predictor.feature_names,
            'is_trained': self.predictor.is_trained,
            'trained_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filepath}")
    
    def plot_results(self, data: pd.DataFrame, save_path: Optional[str] = None) -> None:
        """
        Create visualization plots for the results.
        
        Args:
            data: DataFrame with historical data
            save_path: Optional path to save plots
        """
        # Prepare data
        df = self.predictor.prepare_features(data)
        df = self.predictor.create_prediction_targets(df)
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Price Prediction Model Results', fontsize=16)
        
        # Plot 1: Price over time
        axes[0, 0].plot(df['timestamp'], df['price'], alpha=0.7)
        axes[0, 0].set_title('Price Over Time')
        axes[0, 0].set_xlabel('Time')
        axes[0, 0].set_ylabel('Price')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # Plot 2: Price changes distribution
        price_changes = df['price_change'].dropna()
        axes[0, 1].hist(price_changes, bins=50, alpha=0.7, edgecolor='black')
        axes[0, 1].axvline(price_changes.mean(), color='red', linestyle='--', 
                          label=f'Mean: {price_changes.mean():.3f}')
        axes[0, 1].set_title('Price Changes Distribution')
        axes[0, 1].set_xlabel('Price Change')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].legend()
        
        # Plot 3: Technical indicators
        if 'rsi' in df.columns:
            axes[1, 0].plot(df['timestamp'], df['rsi'], alpha=0.7, label='RSI')
            axes[1, 0].axhline(y=70, color='r', linestyle='--', alpha=0.5, label='Overbought')
            axes[1, 0].axhline(y=30, color='g', linestyle='--', alpha=0.5, label='Oversold')
            axes[1, 0].set_title('RSI Indicator')
            axes[1, 0].set_xlabel('Time')
            axes[1, 0].set_ylabel('RSI')
            axes[1, 0].legend()
            axes[1, 0].tick_params(axis='x', rotation=45)
        
        # Plot 4: Moving averages
        if 'sma_5' in df.columns and 'sma_20' in df.columns:
            axes[1, 1].plot(df['timestamp'], df['price'], alpha=0.5, label='Price')
            axes[1, 1].plot(df['timestamp'], df['sma_5'], alpha=0.8, label='SMA 5')
            axes[1, 1].plot(df['timestamp'], df['sma_20'], alpha=0.8, label='SMA 20')
            axes[1, 1].set_title('Price and Moving Averages')
            axes[1, 1].set_xlabel('Time')
            axes[1, 1].set_ylabel('Price')
            axes[1, 1].legend()
            axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Plots saved to {save_path}")
        
        plt.show()


def main():
    """
    Main function to run training and validation pipeline.
    """
    print("Price Prediction Model Training and Validation")
    print("=" * 50)
    
    # Create sample data for demonstration
    print("Creating sample financial data...")
    sample_data = create_sample_data(800)
    print(f"Generated {len(sample_data)} data points")
    
    # Initialize trainer
    print("\nInitializing prediction trainer...")
    trainer = PredictionTrainer()
    
    # Split data
    print("\nSplitting data into training and validation sets...")
    train_data, val_data = trainer.prepare_training_data(sample_data)
    
    # Train model
    print("\nTraining model...")
    training_results = trainer.train_model(train_data)
    
    # Validate model
    print("\nValidating model...")
    validation_results = trainer.validate_model(val_data)
    
    # Cross-validation
    print("\nPerforming cross-validation...")
    cv_results = trainer.cross_validate(sample_data)
    
    # Combine results
    all_results = {
        **training_results, 
        **validation_results,
        'cross_validation': cv_results
    }
    
    # Evaluate performance
    print("\nEvaluating model performance...")
    performance_eval = trainer.evaluate_performance(all_results)
    
    # Generate predictions report
    print("\nGenerating predictions report...")
    predictions_report = trainer.generate_predictions_report(val_data)
    
    # Print results
    print("\nTraining Results:")
    print(f"  Training samples: {training_results['training_samples']}")
    print(f"  Horizons trained: {len(training_results['training_results'])}")
    
    print("\nValidation Results:")
    print(f"  Validation samples: {validation_results['validation_samples']}")
    print(f"  Horizons validated: {len(validation_results['validation_results'])}")
    
    print("\nCross-Validation Results:")
    for horizon, metrics in cv_results.items():
        print(f"  {horizon}d horizon: R² = {metrics['r2_mean']:.3f} ± {metrics['r2_std']:.3f}")
    
    print("\nPerformance Evaluation:")
    print(f"  Meets thresholds: {performance_eval['meets_thresholds']}")
    if performance_eval['recommendations']:
        print("  Recommendations:")
        for rec in performance_eval['recommendations']:
            print(f"    - {rec}")
    
    print("\nPredictions Summary:")
    if predictions_report['summary']:
        summary = predictions_report['summary']
        print(f"  Average predicted change: {summary['avg_predicted_change']:.2f}%")
        print(f"  Prediction consistency: {summary['prediction_consistency']:.3f}")
    
    # Save results
    results_file = 'ml-models/prediction_training_results.json'
    trainer.save_results(all_results, results_file)
    
    # Create visualizations
    print("\nCreating visualizations...")
    trainer.plot_results(sample_data, 'ml-models/price_prediction_plots.png')
    
    # Save trained model
    model_file = 'ml-models/trained_prediction_model.json'
    trainer.predictor.save_model(model_file)
    
    print(f"\nTraining completed successfully!")
    print(f"Results saved to: {results_file}")
    print(f"Model saved to: {model_file}")
    print(f"Plots saved to: ml-models/price_prediction_plots.png")


if __name__ == "__main__":
    main()
