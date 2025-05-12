"""
Configuration file for Price Prediction Model
=============================================

This file contains configuration parameters for the price prediction system.
It allows easy customization of prediction horizons, features, and model parameters.
"""

# Default configuration for price prediction
DEFAULT_CONFIG = {
    # Prediction horizons (days ahead)
    'prediction_horizons': [1, 5, 10, 20],
    
    # Feature engineering parameters
    'lookback_window': 30,
    'min_samples_for_training': 50,
    'validation_split': 0.2,
    
    # Features to use for prediction
    'features': [
        'price', 'volume', 'price_change', 'volume_change',
        'sma_5', 'sma_20', 'ema_12', 'ema_26',
        'rsi', 'macd', 'bollinger_upper', 'bollinger_lower',
        'volatility', 'momentum_5', 'momentum_10'
    ],
    
    # Model types to use
    'model_types': ['linear', 'ridge', 'moving_average'],
    
    # Model-specific parameters
    'linear_regression': {
        'fit_intercept': True,
        'normalize': False
    },
    
    'ridge_regression': {
        'alpha': 1.0,
        'fit_intercept': True,
        'normalize': False
    },
    
    'moving_average': {
        'default_window': 20,
        'adaptive_window': True
    },
    
    # Technical indicators parameters
    'technical_indicators': {
        'rsi_period': 14,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'bollinger_period': 20,
        'bollinger_std': 2,
        'sma_periods': [5, 20],
        'ema_periods': [12, 26]
    },
    
    # Prediction confidence thresholds
    'confidence_thresholds': {
        'high': 0.8,
        'medium': 0.6,
        'low': 0.4
    },
    
    # Performance evaluation thresholds
    'performance_thresholds': {
        'min_r2_score': 0.1,
        'min_direction_accuracy': 0.55,
        'max_mae_percentage': 10.0
    }
}

# Configuration for different asset types
ASSET_TYPE_CONFIGS = {
    'stocks': {
        'prediction_horizons': [1, 5, 10, 20],
        'lookback_window': 30,
        'ridge_regression': {'alpha': 1.0},
        'technical_indicators': {
            'rsi_period': 14,
            'bollinger_period': 20
        }
    },
    'crypto': {
        'prediction_horizons': [1, 3, 7, 14],
        'lookback_window': 20,
        'ridge_regression': {'alpha': 0.5},  # Less regularization for crypto
        'technical_indicators': {
            'rsi_period': 14,
            'bollinger_period': 20
        }
    },
    'forex': {
        'prediction_horizons': [1, 5, 10, 30],
        'lookback_window': 50,
        'ridge_regression': {'alpha': 2.0},  # More regularization for forex
        'technical_indicators': {
            'rsi_period': 14,
            'bollinger_period': 20
        }
    }
}

# Configuration for different timeframes
TIMEFRAME_CONFIGS = {
    'intraday': {
        'prediction_horizons': [1, 2, 4, 8],  # Hours ahead
        'lookback_window': 20,
        'min_samples_for_training': 30,
        'technical_indicators': {
            'rsi_period': 14,
            'sma_periods': [5, 10],
            'ema_periods': [8, 16]
        }
    },
    'daily': {
        'prediction_horizons': [1, 5, 10, 20],
        'lookback_window': 30,
        'min_samples_for_training': 50,
        'technical_indicators': {
            'rsi_period': 14,
            'sma_periods': [5, 20],
            'ema_periods': [12, 26]
        }
    },
    'weekly': {
        'prediction_horizons': [1, 2, 4, 8],  # Weeks ahead
        'lookback_window': 12,
        'min_samples_for_training': 20,
        'technical_indicators': {
            'rsi_period': 14,
            'sma_periods': [4, 12],
            'ema_periods': [8, 20]
        }
    }
}

# Model ensemble weights
ENSEMBLE_WEIGHTS = {
    'linear': 0.4,
    'ridge': 0.4,
    'moving_average': 0.2
}

# Prediction risk levels
RISK_LEVELS = {
    'conservative': {
        'max_prediction_horizon': 5,
        'confidence_threshold': 0.7,
        'model_types': ['linear', 'ridge']
    },
    'moderate': {
        'max_prediction_horizon': 10,
        'confidence_threshold': 0.6,
        'model_types': ['linear', 'ridge', 'moving_average']
    },
    'aggressive': {
        'max_prediction_horizon': 20,
        'confidence_threshold': 0.5,
        'model_types': ['linear', 'ridge', 'moving_average']
    }
}

def get_config(asset_type: str = 'stocks', timeframe: str = 'daily', risk_level: str = 'moderate') -> dict:
    """
    Get configuration for specific asset type, timeframe, and risk level.
    
    Args:
        asset_type: Type of asset (stocks, crypto, forex)
        timeframe: Timeframe for analysis (intraday, daily, weekly)
        risk_level: Risk level (conservative, moderate, aggressive)
        
    Returns:
        Configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()
    
    # Merge asset type specific config
    if asset_type in ASSET_TYPE_CONFIGS:
        config.update(ASSET_TYPE_CONFIGS[asset_type])
    
    # Merge timeframe specific config
    if timeframe in TIMEFRAME_CONFIGS:
        config.update(TIMEFRAME_CONFIGS[timeframe])
    
    # Apply risk level constraints
    if risk_level in RISK_LEVELS:
        risk_config = RISK_LEVELS[risk_level]
        
        # Filter prediction horizons
        config['prediction_horizons'] = [
            h for h in config['prediction_horizons'] 
            if h <= risk_config['max_prediction_horizon']
        ]
        
        # Set confidence threshold
        config['confidence_threshold'] = risk_config['confidence_threshold']
        
        # Filter model types
        config['model_types'] = [
            m for m in config['model_types'] 
            if m in risk_config['model_types']
        ]
    
    return config

def validate_config(config: dict) -> bool:
    """
    Validate configuration parameters.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid, False otherwise
    """
    required_keys = [
        'prediction_horizons',
        'lookback_window',
        'min_samples_for_training',
        'features',
        'model_types'
    ]
    
    # Check required keys
    for key in required_keys:
        if key not in config:
            print(f"Missing required configuration key: {key}")
            return False
    
    # Validate parameter ranges
    if not config['prediction_horizons'] or any(h <= 0 for h in config['prediction_horizons']):
        print("prediction_horizons must contain positive values")
        return False
    
    if config['lookback_window'] < 5:
        print("lookback_window must be at least 5")
        return False
    
    if config['min_samples_for_training'] < 10:
        print("min_samples_for_training must be at least 10")
        return False
    
    if not config['features']:
        print("features list cannot be empty")
        return False
    
    if not config['model_types']:
        print("model_types list cannot be empty")
        return False
    
    return True

def get_ensemble_weights(model_types: list) -> dict:
    """
    Get ensemble weights for given model types.
    
    Args:
        model_types: List of model types to use
        
    Returns:
        Dictionary with model weights
    """
    weights = {}
    total_weight = 0
    
    for model_type in model_types:
        if model_type in ENSEMBLE_WEIGHTS:
            weights[model_type] = ENSEMBLE_WEIGHTS[model_type]
            total_weight += ENSEMBLE_WEIGHTS[model_type]
    
    # Normalize weights
    if total_weight > 0:
        for model_type in weights:
            weights[model_type] /= total_weight
    
    return weights

if __name__ == "__main__":
    # Test configuration
    print("Price Prediction Configuration")
    print("=" * 40)
    
    # Test default config
    default_config = get_config()
    print(f"Default config valid: {validate_config(default_config)}")
    
    # Test asset-specific configs
    for asset_type in ['stocks', 'crypto', 'forex']:
        config = get_config(asset_type)
        print(f"{asset_type} config valid: {validate_config(config)}")
        print(f"  Horizons: {config['prediction_horizons']}")
        print(f"  Models: {config['model_types']}")
    
    # Test timeframe-specific configs
    for timeframe in ['intraday', 'daily', 'weekly']:
        config = get_config('stocks', timeframe)
        print(f"{timeframe} config valid: {validate_config(config)}")
        print(f"  Horizons: {config['prediction_horizons']}")
    
    # Test risk levels
    for risk_level in ['conservative', 'moderate', 'aggressive']:
        config = get_config('stocks', 'daily', risk_level)
        print(f"{risk_level} risk config valid: {validate_config(config)}")
        print(f"  Max horizon: {max(config['prediction_horizons'])}")
        print(f"  Confidence threshold: {config.get('confidence_threshold', 'N/A')}")
    
    print("\nConfiguration validation completed!")
