"""
Anomaly Detection Model for Financial Data
==========================================

This module implements anomaly detection algorithms specifically designed for financial data.
It includes both statistical and machine learning-based approaches for detecting unusual patterns
in price movements, volume, and other financial indicators.

MVP Features:
- Statistical anomaly detection (Z-score, IQR)
- Machine learning-based detection (Isolation Forest)
- Real-time anomaly scoring
- Configurable thresholds and parameters
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import logging
import json
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialAnomalyDetector:
    """
    Main class for detecting anomalies in financial data.
    
    This class provides multiple anomaly detection methods suitable for different
    types of financial data patterns and use cases.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the anomaly detector with configuration.
        
        Args:
            config: Configuration dictionary with detection parameters
        """
        self.config = config or self._get_default_config()
        self.scaler = StandardScaler()
        self.isolation_forest = None
        self.is_trained = False
        self.feature_names = []
        
    def _get_default_config(self) -> Dict:
        """Get default configuration for anomaly detection."""
        return {
            'z_score_threshold': 3.0,
            'iqr_multiplier': 1.5,
            'isolation_forest_contamination': 0.1,
            'isolation_forest_n_estimators': 100,
            'min_samples_for_training': 100,
            'features': ['price', 'volume', 'price_change', 'volume_change'],
            'window_size': 20
        }
    
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for anomaly detection.
        
        Args:
            data: DataFrame with financial data
            
        Returns:
            DataFrame with engineered features
        """
        df = data.copy()
        
        # Ensure we have required columns
        required_cols = ['timestamp', 'symbol', 'price', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Calculate price changes
        df['price_change'] = df['price'].pct_change()
        df['price_change_abs'] = df['price_change'].abs()
        
        # Calculate volume changes
        df['volume_change'] = df['volume'].pct_change()
        df['volume_change_abs'] = df['volume_change'].abs()
        
        # Calculate rolling statistics
        window = self.config['window_size']
        df['price_ma'] = df['price'].rolling(window=window).mean()
        df['price_std'] = df['price'].rolling(window=window).std()
        df['volume_ma'] = df['volume'].rolling(window=window).mean()
        df['volume_std'] = df['volume'].rolling(window=window).std()
        
        # Calculate volatility
        df['volatility'] = df['price'].rolling(window=window).std() / df['price'].rolling(window=window).mean()
        
        # Calculate price-to-volume ratio
        df['price_volume_ratio'] = df['price'] / df['volume']
        
        # Remove rows with NaN values
        df = df.dropna().reset_index(drop=True)
        
        return df
    
    def detect_statistical_anomalies(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Detect anomalies using statistical methods (Z-score and IQR).
        
        Args:
            data: DataFrame with prepared features
            
        Returns:
            DataFrame with anomaly scores and flags
        """
        df = data.copy()
        
        # Z-score based anomaly detection
        numeric_features = ['price', 'volume', 'price_change', 'volume_change', 'volatility']
        
        for feature in numeric_features:
            if feature in df.columns:
                # Calculate Z-score
                df[f'{feature}_zscore'] = np.abs(
                    (df[feature] - df[feature].mean()) / df[feature].std()
                )
                
                # Flag anomalies based on Z-score threshold
                df[f'{feature}_anomaly_zscore'] = df[f'{feature}_zscore'] > self.config['z_score_threshold']
        
        # IQR based anomaly detection
        for feature in numeric_features:
            if feature in df.columns:
                Q1 = df[feature].quantile(0.25)
                Q3 = df[feature].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - self.config['iqr_multiplier'] * IQR
                upper_bound = Q3 + self.config['iqr_multiplier'] * IQR
                
                df[f'{feature}_anomaly_iqr'] = (df[feature] < lower_bound) | (df[feature] > upper_bound)
        
        # Overall anomaly flag (any method detects anomaly)
        anomaly_cols = [col for col in df.columns if col.endswith('_anomaly_zscore') or col.endswith('_anomaly_iqr')]
        df['is_anomaly_statistical'] = df[anomaly_cols].any(axis=1)
        
        # Calculate overall anomaly score
        zscore_cols = [col for col in df.columns if col.endswith('_zscore')]
        df['anomaly_score_statistical'] = df[zscore_cols].max(axis=1)
        
        return df
    
    def train_ml_model(self, data: pd.DataFrame) -> None:
        """
        Train the machine learning model for anomaly detection.
        
        Args:
            data: DataFrame with prepared features for training
        """
        if len(data) < self.config['min_samples_for_training']:
            logger.warning(f"Insufficient data for training. Need at least {self.config['min_samples_for_training']} samples.")
            return
        
        # Select features for ML model
        feature_cols = [col for col in self.config['features'] if col in data.columns]
        if not feature_cols:
            raise ValueError("No valid features found for ML model training")
        
        self.feature_names = feature_cols
        X = data[feature_cols].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        self.isolation_forest = IsolationForest(
            contamination=self.config['isolation_forest_contamination'],
            n_estimators=self.config['isolation_forest_n_estimators'],
            random_state=42
        )
        
        self.isolation_forest.fit(X_scaled)
        self.is_trained = True
        
        logger.info(f"ML model trained successfully with {len(data)} samples and {len(feature_cols)} features")
    
    def detect_ml_anomalies(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Detect anomalies using the trained machine learning model.
        
        Args:
            data: DataFrame with prepared features
            
        Returns:
            DataFrame with ML-based anomaly scores and flags
        """
        if not self.is_trained:
            logger.warning("ML model not trained. Skipping ML-based anomaly detection.")
            return data
        
        df = data.copy()
        
        # Select features
        X = df[self.feature_names].values
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict anomalies
        anomaly_scores = self.isolation_forest.decision_function(X_scaled)
        anomaly_predictions = self.isolation_forest.predict(X_scaled)
        
        # Convert predictions to boolean (1 = normal, -1 = anomaly)
        df['is_anomaly_ml'] = anomaly_predictions == -1
        df['anomaly_score_ml'] = -anomaly_scores  # Higher scores = more anomalous
        
        return df
    
    def detect_anomalies(self, data: pd.DataFrame, train_model: bool = True) -> pd.DataFrame:
        """
        Main method to detect anomalies using all available methods.
        
        Args:
            data: DataFrame with financial data
            train_model: Whether to train the ML model on this data
            
        Returns:
            DataFrame with anomaly detection results
        """
        logger.info("Starting anomaly detection process...")
        
        # Prepare features
        df = self.prepare_features(data)
        logger.info(f"Prepared features for {len(df)} data points")
        
        # Statistical anomaly detection
        df = self.detect_statistical_anomalies(df)
        logger.info("Completed statistical anomaly detection")
        
        # Train ML model if requested and not already trained
        if train_model and not self.is_trained:
            self.train_ml_model(df)
        
        # ML-based anomaly detection
        df = self.detect_ml_anomalies(df)
        logger.info("Completed ML-based anomaly detection")
        
        # Combine results
        df['is_anomaly'] = df['is_anomaly_statistical'] | df.get('is_anomaly_ml', False)
        df['anomaly_score'] = np.maximum(
            df['anomaly_score_statistical'],
            df.get('anomaly_score_ml', 0)
        )
        
        # Add metadata
        df['detection_timestamp'] = datetime.now()
        df['detection_method'] = 'combined'
        
        logger.info(f"Anomaly detection completed. Found {df['is_anomaly'].sum()} anomalies out of {len(df)} data points")
        
        return df
    
    def get_anomaly_summary(self, data: pd.DataFrame) -> Dict:
        """
        Get a summary of detected anomalies.
        
        Args:
            data: DataFrame with anomaly detection results
            
        Returns:
            Dictionary with anomaly summary statistics
        """
        if 'is_anomaly' not in data.columns:
            raise ValueError("Data must contain anomaly detection results")
        
        total_points = len(data)
        anomaly_count = data['is_anomaly'].sum()
        anomaly_rate = anomaly_count / total_points if total_points > 0 else 0
        
        summary = {
            'total_data_points': total_points,
            'anomaly_count': anomaly_count,
            'anomaly_rate': anomaly_rate,
            'detection_timestamp': datetime.now().isoformat(),
            'config': self.config
        }
        
        # Add per-symbol statistics if symbol column exists
        if 'symbol' in data.columns:
            symbol_stats = data.groupby('symbol')['is_anomaly'].agg(['count', 'sum']).reset_index()
            symbol_stats['anomaly_rate'] = symbol_stats['sum'] / symbol_stats['count']
            summary['per_symbol_stats'] = symbol_stats.to_dict('records')
        
        return summary
    
    def save_model(self, filepath: str) -> None:
        """
        Save the trained model to disk.
        
        Args:
            filepath: Path to save the model
        """
        if not self.is_trained:
            logger.warning("No trained model to save")
            return
        
        model_data = {
            'config': self.config,
            'feature_names': self.feature_names,
            'scaler_mean': self.scaler.mean_.tolist(),
            'scaler_scale': self.scaler.scale_.tolist(),
            'isolation_forest_params': self.isolation_forest.get_params(),
            'trained_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(model_data, f, indent=2)
        
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """
        Load a trained model from disk.
        
        Args:
            filepath: Path to the saved model
        """
        with open(filepath, 'r') as f:
            model_data = json.load(f)
        
        self.config = model_data['config']
        self.feature_names = model_data['feature_names']
        
        # Restore scaler
        self.scaler.mean_ = np.array(model_data['scaler_mean'])
        self.scaler.scale_ = np.array(model_data['scaler_scale'])
        
        # Restore Isolation Forest
        self.isolation_forest = IsolationForest(**model_data['isolation_forest_params'])
        self.isolation_forest.fit(np.zeros((1, len(self.feature_names))))  # Dummy fit
        
        self.is_trained = True
        logger.info(f"Model loaded from {filepath}")


def create_sample_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    Create sample financial data for testing.
    
    Args:
        n_samples: Number of samples to generate
        
    Returns:
        DataFrame with sample financial data
    """
    np.random.seed(42)
    
    # Generate timestamps
    start_time = datetime.now() - timedelta(days=30)
    timestamps = [start_time + timedelta(minutes=i*5) for i in range(n_samples)]
    
    # Generate sample data
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
    data = []
    
    for i, timestamp in enumerate(timestamps):
        symbol = symbols[i % len(symbols)]
        
        # Generate realistic price data with some anomalies
        base_price = 100 + np.random.normal(0, 10)
        if i % 50 == 0:  # Create artificial anomalies
            price = base_price * (1 + np.random.normal(0, 0.5))  # Large price movement
        else:
            price = base_price * (1 + np.random.normal(0, 0.02))  # Normal price movement
        
        # Generate volume data
        base_volume = 1000000 + np.random.normal(0, 100000)
        if i % 30 == 0:  # Create volume anomalies
            volume = base_volume * (1 + np.random.normal(0, 2))  # Large volume spike
        else:
            volume = base_volume * (1 + np.random.normal(0, 0.1))  # Normal volume
        
        data.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'price': max(price, 0.01),  # Ensure positive price
            'volume': max(volume, 1)    # Ensure positive volume
        })
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # Example usage
    print("Financial Anomaly Detection Model - MVP Implementation")
    print("=" * 60)
    
    # Create sample data
    print("Creating sample financial data...")
    sample_data = create_sample_data(500)
    print(f"Generated {len(sample_data)} data points")
    
    # Initialize detector
    print("\nInitializing anomaly detector...")
    detector = FinancialAnomalyDetector()
    
    # Detect anomalies
    print("\nDetecting anomalies...")
    results = detector.detect_anomalies(sample_data)
    
    # Get summary
    print("\nAnomaly Detection Summary:")
    print("-" * 30)
    summary = detector.get_anomaly_summary(results)
    print(f"Total data points: {summary['total_data_points']}")
    print(f"Anomalies detected: {summary['anomaly_count']}")
    print(f"Anomaly rate: {summary['anomaly_rate']:.2%}")
    
    # Show some examples
    print("\nSample anomalies:")
    anomalies = results[results['is_anomaly']].head(5)
    if len(anomalies) > 0:
        print(anomalies[['timestamp', 'symbol', 'price', 'volume', 'anomaly_score']].to_string())
    else:
        print("No anomalies detected in sample data")
    
    print("\nAnomaly detection model ready for production use!")
