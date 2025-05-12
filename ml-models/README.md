# ML Models - Financial Analytics

This directory contains machine learning models for the real-time financial application, including anomaly detection and price prediction capabilities.

## Overview

The ML models system provides two main capabilities:

### 1. Anomaly Detection
The anomaly detection system is designed to identify unusual patterns in financial data such as:
- Unusual price movements
- Volume spikes
- Volatility anomalies
- Market manipulation patterns

### 2. Price Prediction
The price prediction system provides forecasts for future price movements:
- Multi-horizon predictions (1, 5, 10, 20 days)
- Technical indicators integration
- Ensemble modeling approach
- Confidence scoring

## Features (MVP)

### Anomaly Detection
- **Statistical Methods**: Z-score and IQR-based detection
- **Machine Learning**: Isolation Forest algorithm
- **Real-time Processing**: Designed for streaming data
- **Configurable Thresholds**: Easy customization of detection parameters
- **Multi-asset Support**: Works with stocks, crypto, and forex data

### Price Prediction
- **Multiple Models**: Linear regression, Ridge regression, Moving averages
- **Technical Indicators**: RSI, MACD, Bollinger Bands, Moving averages
- **Ensemble Approach**: Combines multiple models for better accuracy
- **Multi-horizon**: Predictions for 1, 5, 10, and 20 days ahead
- **Confidence Scoring**: Provides confidence levels for predictions

### Detection Methods

1. **Statistical Methods**
   - Z-score based detection (configurable threshold)
   - Interquartile Range (IQR) based detection
   - Rolling window statistics

2. **Machine Learning Methods**
   - Isolation Forest for unsupervised anomaly detection
   - Feature engineering for financial data
   - Cross-validation for model stability

## File Structure

```
ml-models/
├── anomaly_detection.py      # Anomaly detection model
├── price_prediction.py       # Price prediction model
├── config.py                 # Anomaly detection configuration
├── prediction_config.py      # Price prediction configuration
├── train_model.py           # Anomaly detection training
├── train_prediction_model.py # Price prediction training
├── pipeline_integration.py   # Anomaly detection pipeline
├── prediction_pipeline.py   # Price prediction pipeline
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Price Prediction Usage

```python
from price_prediction import PricePredictor, create_sample_data

# Create sample data
data = create_sample_data(1000)

# Initialize predictor
predictor = PricePredictor()

# Prepare data
prepared_data = predictor.prepare_features(data)
prepared_data = predictor.create_prediction_targets(prepared_data)

# Train models
training_results = predictor.train_models(prepared_data)

# Make predictions
predictions = predictor.predict(data, horizon=5)
summary = predictor.get_prediction_summary(predictions)
print(f"Predicted change: {summary['best_prediction']['predicted_change_pct']:.2f}%")
```

### Training a Model

```python
from train_model import ModelTrainer

# Initialize trainer
trainer = ModelTrainer()

# Split data
train_data, val_data = trainer.prepare_training_data(data)

# Train and validate
training_results = trainer.train_model(train_data)
validation_results = trainer.validate_model(val_data)
```

## Configuration

The system supports different configurations for various asset types and timeframes:

```python
from config import get_config

# Get configuration for crypto data
crypto_config = get_config('crypto', 'intraday')

# Get configuration for stocks
stocks_config = get_config('stocks', 'daily')
```

### Configuration Parameters

- `z_score_threshold`: Threshold for Z-score based detection (default: 3.0)
- `iqr_multiplier`: Multiplier for IQR based detection (default: 1.5)
- `isolation_forest_contamination`: Expected proportion of anomalies (default: 0.1)
- `window_size`: Rolling window size for calculations (default: 20)
- `min_samples_for_training`: Minimum samples required for training (default: 100)

## Performance Metrics

The system tracks several performance metrics:

- **Anomaly Rate**: Percentage of data points flagged as anomalies
- **Detection Accuracy**: Accuracy of anomaly detection
- **False Positive Rate**: Rate of false anomaly detections
- **Cross-validation Stability**: Consistency across different data splits

## Integration with Main Application

The anomaly detection model integrates with the main financial application through:

1. **Data Ingestion**: Receives real-time data from Kinesis streams
2. **Processing**: Analyzes data using trained models
3. **Alerting**: Triggers alerts for detected anomalies
4. **Storage**: Stores results in S3 and Snowflake

## Model Persistence

Trained models can be saved and loaded:

```python
# Save model
detector.save_model('path/to/model.json')

# Load model
detector.load_model('path/to/model.json')
```

## Testing

Run the training pipeline to test the system:

```bash
python train_model.py
```

This will:
1. Generate sample financial data
2. Train the anomaly detection model
3. Validate the model performance
4. Save results and visualizations

## Future Enhancements

Planned improvements for future versions:

- **Deep Learning Models**: LSTM and Transformer-based anomaly detection
- **Ensemble Methods**: Combining multiple detection algorithms
- **Real-time Learning**: Online learning capabilities
- **Advanced Features**: Technical indicators integration
- **Performance Optimization**: GPU acceleration support

## Dependencies

- Python 3.8+
- NumPy >= 1.21.0
- Pandas >= 1.3.0
- Scikit-learn >= 1.0.0
- Matplotlib >= 3.5.0
- Seaborn >= 0.11.0

## Contributing

When contributing to the ML models:

1. Follow the existing code structure
2. Add comprehensive tests
3. Update documentation
4. Ensure backward compatibility
5. Validate performance metrics

## License

This project is part of the real-time financial application and follows the same licensing terms.
