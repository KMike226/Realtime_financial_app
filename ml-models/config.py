"""
Configuration file for Anomaly Detection Model
==============================================

This file contains configuration parameters for the financial anomaly detection system.
It allows easy customization of detection thresholds and methods without modifying the main code.
"""

# Default configuration for anomaly detection
DEFAULT_CONFIG = {
    # Statistical detection parameters
    'z_score_threshold': 3.0,  # Threshold for Z-score based detection
    'iqr_multiplier': 1.5,     # Multiplier for IQR based detection
    
    # Machine Learning parameters
    'isolation_forest_contamination': 0.1,  # Expected proportion of anomalies
    'isolation_forest_n_estimators': 100,   # Number of trees in the forest
    'isolation_forest_random_state': 42,    # Random state for reproducibility
    
    # Training parameters
    'min_samples_for_training': 100,        # Minimum samples required for training
    'window_size': 20,                      # Rolling window size for calculations
    
    # Features to use for anomaly detection
    'features': [
        'price',
        'volume', 
        'price_change',
        'volume_change',
        'volatility',
        'price_volume_ratio'
    ],
    
    # Detection methods to use
    'methods': {
        'statistical': True,   # Enable statistical methods (Z-score, IQR)
        'ml': True            # Enable machine learning methods (Isolation Forest)
    },
    
    # Output parameters
    'save_predictions': True,           # Save prediction results
    'save_model': True,                 # Save trained model
    'log_level': 'INFO',                # Logging level
    'output_format': 'json'             # Output format for results
}

# Configuration for different asset types
ASSET_TYPE_CONFIGS = {
    'stocks': {
        'z_score_threshold': 3.0,
        'iqr_multiplier': 1.5,
        'isolation_forest_contamination': 0.1,
        'window_size': 20
    },
    'crypto': {
        'z_score_threshold': 2.5,  # Crypto is more volatile
        'iqr_multiplier': 1.2,
        'isolation_forest_contamination': 0.15,
        'window_size': 15
    },
    'forex': {
        'z_score_threshold': 3.5,  # Forex is less volatile
        'iqr_multiplier': 2.0,
        'isolation_forest_contamination': 0.05,
        'window_size': 30
    }
}

# Configuration for different timeframes
TIMEFRAME_CONFIGS = {
    'intraday': {
        'window_size': 10,
        'z_score_threshold': 2.5,
        'min_samples_for_training': 50
    },
    'daily': {
        'window_size': 20,
        'z_score_threshold': 3.0,
        'min_samples_for_training': 100
    },
    'weekly': {
        'window_size': 12,
        'z_score_threshold': 3.5,
        'min_samples_for_training': 200
    }
}

# Alert thresholds
ALERT_THRESHOLDS = {
    'low': {
        'anomaly_score_threshold': 2.0,
        'consecutive_anomalies': 1,
        'notification_enabled': True
    },
    'medium': {
        'anomaly_score_threshold': 3.0,
        'consecutive_anomalies': 2,
        'notification_enabled': True
    },
    'high': {
        'anomaly_score_threshold': 4.0,
        'consecutive_anomalies': 1,
        'notification_enabled': True
    }
}

# Model performance thresholds
PERFORMANCE_THRESHOLDS = {
    'min_accuracy': 0.85,        # Minimum accuracy for model validation
    'max_false_positive_rate': 0.1,  # Maximum acceptable false positive rate
    'min_precision': 0.8,        # Minimum precision for anomaly detection
    'min_recall': 0.7           # Minimum recall for anomaly detection
}

def get_config(asset_type: str = 'stocks', timeframe: str = 'daily') -> dict:
    """
    Get configuration for specific asset type and timeframe.
    
    Args:
        asset_type: Type of asset (stocks, crypto, forex)
        timeframe: Timeframe for analysis (intraday, daily, weekly)
        
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
        'z_score_threshold',
        'iqr_multiplier', 
        'isolation_forest_contamination',
        'min_samples_for_training',
        'window_size'
    ]
    
    # Check required keys
    for key in required_keys:
        if key not in config:
            print(f"Missing required configuration key: {key}")
            return False
    
    # Validate parameter ranges
    if config['z_score_threshold'] <= 0:
        print("z_score_threshold must be positive")
        return False
    
    if config['iqr_multiplier'] <= 0:
        print("iqr_multiplier must be positive")
        return False
    
    if not 0 < config['isolation_forest_contamination'] < 1:
        print("isolation_forest_contamination must be between 0 and 1")
        return False
    
    if config['min_samples_for_training'] < 10:
        print("min_samples_for_training must be at least 10")
        return False
    
    if config['window_size'] < 5:
        print("window_size must be at least 5")
        return False
    
    return True

if __name__ == "__main__":
    # Test configuration
    print("Anomaly Detection Configuration")
    print("=" * 40)
    
    # Test default config
    default_config = get_config()
    print(f"Default config valid: {validate_config(default_config)}")
    
    # Test asset-specific configs
    for asset_type in ['stocks', 'crypto', 'forex']:
        config = get_config(asset_type)
        print(f"{asset_type} config valid: {validate_config(config)}")
    
    # Test timeframe-specific configs
    for timeframe in ['intraday', 'daily', 'weekly']:
        config = get_config('stocks', timeframe)
        print(f"{timeframe} config valid: {validate_config(config)}")
    
    print("\nConfiguration validation completed!")
