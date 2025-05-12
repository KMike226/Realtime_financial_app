"""
Price Prediction Algorithm for Financial Data
============================================

This module implements price prediction algorithms specifically designed for financial data.
It includes both traditional statistical methods and machine learning approaches for predicting
future price movements and trends.

MVP Features:
- Linear regression models
- Moving average predictions
- Technical indicators integration
- Simple trend analysis
- Real-time prediction capabilities
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import logging
import json
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PricePredictor:
    """
    Main class for predicting future price movements in financial data.
    
    This class provides multiple prediction methods suitable for different
    prediction horizons and market conditions.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the price predictor with configuration.
        
        Args:
            config: Configuration dictionary with prediction parameters
        """
        self.config = config or self._get_default_config()
        self.scaler = StandardScaler()
        self.models = {}
        self.is_trained = False
        self.feature_names = []
        
    def _get_default_config(self) -> Dict:
        """Get default configuration for price prediction."""
        return {
            'prediction_horizons': [1, 5, 10, 20],  # Days ahead to predict
            'lookback_window': 30,                   # Days of historical data to use
            'features': [
                'price', 'volume', 'price_change', 'volume_change',
                'sma_5', 'sma_20', 'ema_12', 'ema_26',
                'rsi', 'macd', 'bollinger_upper', 'bollinger_lower'
            ],
            'model_types': ['linear', 'ridge', 'moving_average'],
            'min_samples_for_training': 50,
            'validation_split': 0.2
        }
    
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for price prediction.
        
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
        
        # Calculate basic price changes
        df['price_change'] = df['price'].pct_change()
        df['volume_change'] = df['volume'].pct_change()
        
        # Calculate moving averages
        df['sma_5'] = df['price'].rolling(window=5).mean()
        df['sma_20'] = df['price'].rolling(window=20).mean()
        df['ema_12'] = df['price'].ewm(span=12).mean()
        df['ema_26'] = df['price'].ewm(span=26).mean()
        
        # Calculate RSI
        df['rsi'] = self._calculate_rsi(df['price'])
        
        # Calculate MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Calculate Bollinger Bands
        df['bollinger_middle'] = df['price'].rolling(window=20).mean()
        df['bollinger_std'] = df['price'].rolling(window=20).std()
        df['bollinger_upper'] = df['bollinger_middle'] + (df['bollinger_std'] * 2)
        df['bollinger_lower'] = df['bollinger_middle'] - (df['bollinger_std'] * 2)
        
        # Calculate volatility
        df['volatility'] = df['price'].rolling(window=20).std() / df['price'].rolling(window=20).mean()
        
        # Calculate price momentum
        df['momentum_5'] = df['price'] / df['price'].shift(5) - 1
        df['momentum_10'] = df['price'] / df['price'].shift(10) - 1
        
        # Remove rows with NaN values
        df = df.dropna().reset_index(drop=True)
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            prices: Price series
            window: RSI window period
            
        Returns:
            RSI series
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def create_prediction_targets(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Create prediction targets for different horizons.
        
        Args:
            data: DataFrame with prepared features
            
        Returns:
            DataFrame with prediction targets
        """
        df = data.copy()
        
        # Create targets for different prediction horizons
        for horizon in self.config['prediction_horizons']:
            df[f'price_target_{horizon}d'] = df['price'].shift(-horizon)
            df[f'price_change_{horizon}d'] = (df[f'price_target_{horizon}d'] / df['price'] - 1) * 100
            df[f'direction_{horizon}d'] = (df[f'price_change_{horizon}d'] > 0).astype(int)
        
        return df
    
    def train_models(self, data: pd.DataFrame) -> Dict:
        """
        Train prediction models for different horizons.
        
        Args:
            data: DataFrame with prepared features and targets
            
        Returns:
            Training results dictionary
        """
        if len(data) < self.config['min_samples_for_training']:
            logger.warning(f"Insufficient data for training. Need at least {self.config['min_samples_for_training']} samples.")
            return {}
        
        logger.info("Starting model training...")
        
        # Select features
        feature_cols = [col for col in self.config['features'] if col in data.columns]
        if not feature_cols:
            raise ValueError("No valid features found for model training")
        
        self.feature_names = feature_cols
        X = data[feature_cols].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        training_results = {}
        
        # Train models for each prediction horizon
        for horizon in self.config['prediction_horizons']:
            target_col = f'price_change_{horizon}d'
            if target_col not in data.columns:
                continue
            
            y = data[target_col].dropna()
            valid_indices = y.index
            X_horizon = X_scaled[valid_indices]
            
            if len(X_horizon) < 10:
                logger.warning(f"Insufficient data for {horizon}d prediction")
                continue
            
            horizon_models = {}
            
            # Train Linear Regression
            if 'linear' in self.config['model_types']:
                lr_model = LinearRegression()
                lr_model.fit(X_horizon, y)
                horizon_models['linear'] = lr_model
            
            # Train Ridge Regression
            if 'ridge' in self.config['model_types']:
                ridge_model = Ridge(alpha=1.0)
                ridge_model.fit(X_horizon, y)
                horizon_models['ridge'] = ridge_model
            
            # Moving Average baseline
            if 'moving_average' in self.config['model_types']:
                ma_model = self._create_moving_average_model(data, horizon)
                horizon_models['moving_average'] = ma_model
            
            self.models[horizon] = horizon_models
            
            # Calculate training metrics
            predictions = {}
            for model_name, model in horizon_models.items():
                if model_name == 'moving_average':
                    pred = model.predict(data.iloc[valid_indices])
                else:
                    pred = model.predict(X_horizon)
                
                predictions[model_name] = pred
            
            training_results[horizon] = {
                'models_trained': list(horizon_models.keys()),
                'training_samples': len(X_horizon),
                'predictions': predictions
            }
        
        self.is_trained = True
        logger.info(f"Model training completed for {len(self.models)} horizons")
        
        return training_results
    
    def _create_moving_average_model(self, data: pd.DataFrame, horizon: int) -> Dict:
        """
        Create a simple moving average prediction model.
        
        Args:
            data: DataFrame with price data
            horizon: Prediction horizon
            
        Returns:
            Moving average model dictionary
        """
        return {
            'type': 'moving_average',
            'window': min(20, horizon * 2),
            'predict': lambda df: df['price'].rolling(window=min(20, horizon * 2)).mean().iloc[-1]
        }
    
    def predict(self, data: pd.DataFrame, horizon: int = 1) -> Dict:
        """
        Make predictions for a specific horizon.
        
        Args:
            data: DataFrame with prepared features
            horizon: Prediction horizon in days
            
        Returns:
            Prediction results dictionary
        """
        if not self.is_trained:
            logger.warning("Models not trained. Cannot make predictions.")
            return {}
        
        if horizon not in self.models:
            logger.warning(f"No model trained for {horizon}d horizon")
            return {}
        
        # Prepare features for prediction
        df = self.prepare_features(data)
        
        if len(df) == 0:
            logger.warning("No data available for prediction")
            return {}
        
        # Get latest data point
        latest_data = df.iloc[-1:]
        X = latest_data[self.feature_names].values
        X_scaled = self.scaler.transform(X)
        
        predictions = {}
        current_price = latest_data['price'].iloc[0]
        
        # Make predictions with each model
        for model_name, model in self.models[horizon].items():
            if model_name == 'moving_average':
                # Simple moving average prediction
                window = model['window']
                if len(df) >= window:
                    ma_value = df['price'].rolling(window=window).mean().iloc[-1]
                    predicted_change = (ma_value / current_price - 1) * 100
                else:
                    predicted_change = 0
            else:
                # ML model prediction
                predicted_change = model.predict(X_scaled)[0]
            
            predicted_price = current_price * (1 + predicted_change / 100)
            
            predictions[model_name] = {
                'predicted_price': predicted_price,
                'predicted_change_pct': predicted_change,
                'confidence': self._calculate_confidence(model_name, predicted_change)
            }
        
        # Ensemble prediction (average of all models)
        if len(predictions) > 1:
            avg_change = np.mean([pred['predicted_change_pct'] for pred in predictions.values()])
            avg_price = current_price * (1 + avg_change / 100)
            
            predictions['ensemble'] = {
                'predicted_price': avg_price,
                'predicted_change_pct': avg_change,
                'confidence': np.mean([pred['confidence'] for pred in predictions.values()])
            }
        
        return {
            'horizon': horizon,
            'current_price': current_price,
            'timestamp': datetime.now().isoformat(),
            'predictions': predictions
        }
    
    def _calculate_confidence(self, model_name: str, predicted_change: float) -> float:
        """
        Calculate confidence score for prediction.
        
        Args:
            model_name: Name of the model
            predicted_change: Predicted price change percentage
            
        Returns:
            Confidence score between 0 and 1
        """
        # Simple confidence calculation based on prediction magnitude
        # Smaller changes are generally more confident
        base_confidence = 0.7
        
        if abs(predicted_change) < 1:
            confidence = base_confidence + 0.2
        elif abs(predicted_change) < 5:
            confidence = base_confidence
        else:
            confidence = base_confidence - 0.2
        
        return max(0.1, min(1.0, confidence))
    
    def evaluate_model(self, data: pd.DataFrame, horizon: int = 1) -> Dict:
        """
        Evaluate model performance on historical data.
        
        Args:
            data: DataFrame with historical data
            horizon: Prediction horizon
            
        Returns:
            Evaluation results dictionary
        """
        if not self.is_trained or horizon not in self.models:
            return {}
        
        # Prepare data
        df = self.prepare_features(data)
        df = self.create_prediction_targets(df)
        
        # Remove rows without targets
        target_col = f'price_change_{horizon}d'
        df = df.dropna(subset=[target_col])
        
        if len(df) < 10:
            return {}
        
        X = df[self.feature_names].values
        X_scaled = self.scaler.transform(X)
        y_true = df[target_col].values
        
        evaluation_results = {}
        
        # Evaluate each model
        for model_name, model in self.models[horizon].items():
            if model_name == 'moving_average':
                # Moving average evaluation
                window = model['window']
                y_pred = []
                for i in range(len(df)):
                    if i >= window:
                        ma_value = df['price'].iloc[i-window:i].mean()
                        pred_change = (ma_value / df['price'].iloc[i] - 1) * 100
                        y_pred.append(pred_change)
                    else:
                        y_pred.append(0)
                y_pred = np.array(y_pred)
            else:
                y_pred = model.predict(X_scaled)
            
            # Calculate metrics
            mse = mean_squared_error(y_true, y_pred)
            mae = mean_absolute_error(y_true, y_pred)
            r2 = r2_score(y_true, y_pred)
            
            # Direction accuracy (up/down prediction)
            direction_accuracy = np.mean(
                (y_pred > 0) == (y_true > 0)
            )
            
            evaluation_results[model_name] = {
                'mse': mse,
                'mae': mae,
                'r2': r2,
                'direction_accuracy': direction_accuracy,
                'samples': len(y_true)
            }
        
        return evaluation_results
    
    def get_prediction_summary(self, predictions: Dict) -> Dict:
        """
        Get a summary of predictions.
        
        Args:
            predictions: Prediction results dictionary
            
        Returns:
            Summary dictionary
        """
        if not predictions or 'predictions' not in predictions:
            return {}
        
        pred_data = predictions['predictions']
        
        # Calculate ensemble if not present
        if 'ensemble' not in pred_data and len(pred_data) > 1:
            avg_change = np.mean([pred['predicted_change_pct'] for pred in pred_data.values()])
            avg_confidence = np.mean([pred['confidence'] for pred in pred_data.values()])
            
            pred_data['ensemble'] = {
                'predicted_change_pct': avg_change,
                'confidence': avg_confidence
            }
        
        # Find best prediction (highest confidence)
        best_model = max(pred_data.keys(), key=lambda k: pred_data[k]['confidence'])
        
        return {
            'horizon': predictions['horizon'],
            'current_price': predictions['current_price'],
            'best_model': best_model,
            'best_prediction': pred_data[best_model],
            'all_predictions': pred_data,
            'timestamp': predictions['timestamp']
        }
    
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
            'models': {},
            'trained_timestamp': datetime.now().isoformat()
        }
        
        # Save model parameters (not the actual sklearn objects for simplicity)
        for horizon, horizon_models in self.models.items():
            model_data['models'][str(horizon)] = {}
            for model_name, model in horizon_models.items():
                if model_name == 'moving_average':
                    model_data['models'][str(horizon)][model_name] = model
                else:
                    model_data['models'][str(horizon)][model_name] = {
                        'type': 'sklearn_model',
                        'params': model.get_params(),
                        'coef': model.coef_.tolist() if hasattr(model, 'coef_') else None,
                        'intercept': model.intercept_ if hasattr(model, 'intercept_') else None
                    }
        
        with open(filepath, 'w') as f:
            json.dump(model_data, f, indent=2)
        
        logger.info(f"Model saved to {filepath}")


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
    start_time = datetime.now() - timedelta(days=60)
    timestamps = [start_time + timedelta(hours=i) for i in range(n_samples)]
    
    # Generate sample data with trend
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
    data = []
    
    base_price = 100
    for i, timestamp in enumerate(timestamps):
        symbol = symbols[i % len(symbols)]
        
        # Generate price with trend and noise
        trend = 0.001 * i  # Slight upward trend
        noise = np.random.normal(0, 0.02)
        price = base_price * (1 + trend + noise)
        
        # Generate volume
        volume = 1000000 + np.random.normal(0, 100000)
        
        data.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'price': max(price, 0.01),
            'volume': max(volume, 1)
        })
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # Example usage
    print("Price Prediction Algorithm - MVP Implementation")
    print("=" * 50)
    
    # Create sample data
    print("Creating sample financial data...")
    sample_data = create_sample_data(500)
    print(f"Generated {len(sample_data)} data points")
    
    # Initialize predictor
    print("\nInitializing price predictor...")
    predictor = PricePredictor()
    
    # Prepare features and targets
    print("\nPreparing features and targets...")
    prepared_data = predictor.prepare_features(sample_data)
    prepared_data = predictor.create_prediction_targets(prepared_data)
    print(f"Prepared data with {len(prepared_data)} samples")
    
    # Train models
    print("\nTraining prediction models...")
    training_results = predictor.train_models(prepared_data)
    print(f"Trained models for {len(training_results)} horizons")
    
    # Make predictions
    print("\nMaking predictions...")
    predictions = predictor.predict(sample_data, horizon=1)
    if predictions:
        summary = predictor.get_prediction_summary(predictions)
        print(f"Best prediction: {summary['best_model']} model")
        print(f"Predicted change: {summary['best_prediction']['predicted_change_pct']:.2f}%")
        print(f"Confidence: {summary['best_prediction']['confidence']:.2f}")
    
    # Evaluate model
    print("\nEvaluating model performance...")
    evaluation = predictor.evaluate_model(sample_data, horizon=1)
    if evaluation:
        for model_name, metrics in evaluation.items():
            print(f"{model_name}: R² = {metrics['r2']:.3f}, Direction Accuracy = {metrics['direction_accuracy']:.3f}")
    
    print("\nPrice prediction model ready for production use!")
