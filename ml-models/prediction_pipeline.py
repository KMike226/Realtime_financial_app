"""
Integration Script for Price Prediction Model
=============================================

This script integrates the price prediction model with the existing data pipeline,
including real-time predictions, S3 storage, and alerting systems.
"""

import json
import logging
import boto3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from io import StringIO

from price_prediction import PricePredictor
from prediction_config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionPipeline:
    """
    Pipeline for integrating price prediction with the existing data infrastructure.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the prediction pipeline.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or get_config()
        self.predictor = PricePredictor(self.config)
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3')
        self.kinesis_client = boto3.client('kinesis')
        self.sns_client = boto3.client('sns')
        
        # Configuration from environment
        self.s3_bucket = os.getenv('S3_BUCKET', 'financial-data-lake')
        self.kinesis_stream = os.getenv('KINESIS_STREAM', 'financial-data-stream')
        self.sns_topic = os.getenv('SNS_TOPIC', 'prediction-alerts')
        
    def process_realtime_predictions(self, data: pd.DataFrame) -> Dict:
        """
        Process real-time data for price predictions.
        
        Args:
            data: DataFrame with recent financial data
            
        Returns:
            Prediction results dictionary
        """
        logger.info("Processing real-time predictions...")
        
        try:
            # Ensure we have enough data
            if len(data) < self.config['min_samples_for_training']:
                logger.warning("Insufficient data for predictions")
                return {'error': 'Insufficient data'}
            
            # Generate predictions for all horizons
            all_predictions = {}
            
            for horizon in self.config['prediction_horizons']:
                predictions = self.predictor.predict(data, horizon)
                if predictions:
                    summary = self.predictor.get_prediction_summary(predictions)
                    all_predictions[horizon] = summary
            
            if not all_predictions:
                logger.warning("No predictions generated")
                return {'error': 'No predictions generated'}
            
            # Store predictions in S3
            self._store_predictions_in_s3(all_predictions)
            
            # Check for significant predictions and send alerts
            self._check_prediction_alerts(all_predictions)
            
            logger.info(f"Generated predictions for {len(all_predictions)} horizons")
            
            return {
                'predictions': all_predictions,
                'timestamp': datetime.now().isoformat(),
                'horizons': list(all_predictions.keys())
            }
            
        except Exception as e:
            logger.error(f"Error processing predictions: {e}")
            return {'error': str(e)}
    
    def _store_predictions_in_s3(self, predictions: Dict) -> None:
        """
        Store prediction results in S3.
        
        Args:
            predictions: Dictionary with prediction results
        """
        try:
            # Create timestamp-based key
            timestamp = datetime.now().strftime('%Y/%m/%d/%H')
            key = f"predictions/{timestamp}/predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Convert predictions to JSON
            json_data = json.dumps(predictions, default=str, indent=2)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json_data,
                ContentType='application/json'
            )
            
            logger.info(f"Predictions stored in S3: s3://{self.s3_bucket}/{key}")
            
        except Exception as e:
            logger.error(f"Error storing predictions in S3: {e}")
    
    def _check_prediction_alerts(self, predictions: Dict) -> None:
        """
        Check for significant predictions and send alerts.
        
        Args:
            predictions: Dictionary with prediction results
        """
        try:
            alert_threshold = 5.0  # 5% change threshold for alerts
            high_confidence_threshold = 0.7
            
            alerts_sent = 0
            
            for horizon, prediction_data in predictions.items():
                if 'best_prediction' not in prediction_data:
                    continue
                
                best_pred = prediction_data['best_prediction']
                predicted_change = abs(best_pred['predicted_change_pct'])
                confidence = best_pred['confidence']
                
                # Send alert for significant predictions with high confidence
                if predicted_change > alert_threshold and confidence > high_confidence_threshold:
                    alert_message = {
                        'timestamp': datetime.now().isoformat(),
                        'horizon_days': horizon,
                        'predicted_change_pct': best_pred['predicted_change_pct'],
                        'predicted_price': best_pred['predicted_price'],
                        'current_price': prediction_data['current_price'],
                        'confidence': confidence,
                        'model': prediction_data['best_model'],
                        'alert_type': 'significant_prediction'
                    }
                    
                    # Send SNS notification
                    self.sns_client.publish(
                        TopicArn=self.sns_topic,
                        Message=json.dumps(alert_message),
                        Subject=f"Significant Price Prediction: {best_pred['predicted_change_pct']:.2f}% change in {horizon} days"
                    )
                    
                    alerts_sent += 1
            
            if alerts_sent > 0:
                logger.info(f"Sent {alerts_sent} prediction alerts")
            
        except Exception as e:
            logger.error(f"Error sending prediction alerts: {e}")
    
    def train_model_from_s3(self, s3_prefix: str, days_back: int = 60) -> Dict:
        """
        Train the prediction model using historical data from S3.
        
        Args:
            s3_prefix: S3 prefix for training data
            days_back: Number of days of historical data to use
            
        Returns:
            Training results dictionary
        """
        logger.info(f"Training prediction model from S3 data: {s3_prefix}")
        
        try:
            # Get list of objects from S3
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            training_data = []
            
            # Iterate through date range
            current_date = start_date
            while current_date <= end_date:
                date_prefix = f"{s3_prefix}/{current_date.strftime('%Y/%m/%d')}"
                
                try:
                    response = self.s3_client.list_objects_v2(
                        Bucket=self.s3_bucket,
                        Prefix=date_prefix
                    )
                    
                    for obj in response.get('Contents', []):
                        # Download and parse data
                        data_obj = self.s3_client.get_object(
                            Bucket=self.s3_bucket,
                            Key=obj['Key']
                        )
                        
                        data = json.loads(data_obj['Body'].read().decode('utf-8'))
                        if isinstance(data, list):
                            training_data.extend(data)
                        else:
                            training_data.append(data)
                            
                except Exception as e:
                    logger.warning(f"Error processing data for {date_prefix}: {e}")
                
                current_date += timedelta(days=1)
            
            if not training_data:
                logger.warning("No training data found in S3")
                return {'error': 'No training data found'}
            
            # Convert to DataFrame and train
            df = pd.DataFrame(training_data)
            logger.info(f"Training prediction model with {len(df)} data points")
            
            # Prepare data for training
            prepared_data = self.predictor.prepare_features(df)
            prepared_data = self.predictor.create_prediction_targets(prepared_data)
            
            # Train the model
            training_results = self.predictor.train_models(prepared_data)
            
            # Save trained model
            model_key = f"models/price_prediction_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.predictor.save_model(f"s3://{self.s3_bucket}/{model_key}")
            
            logger.info(f"Prediction model training completed. Horizons: {len(training_results)}")
            
            return {
                'training_samples': len(df),
                'horizons_trained': len(training_results),
                'model_saved_to': f"s3://{self.s3_bucket}/{model_key}",
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error training prediction model from S3: {e}")
            return {'error': str(e)}
    
    def load_model_from_s3(self, model_key: str) -> bool:
        """
        Load a trained model from S3.
        
        Args:
            model_key: S3 key for the model file
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            # Download model from S3
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=model_key
            )
            
            model_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Load model into predictor
            self.predictor.config = model_data['config']
            self.predictor.feature_names = model_data['feature_names']
            
            # Restore scaler
            from sklearn.preprocessing import StandardScaler
            import numpy as np
            self.predictor.scaler = StandardScaler()
            self.predictor.scaler.mean_ = np.array(model_data['scaler_mean'])
            self.predictor.scaler.scale_ = np.array(model_data['scaler_scale'])
            
            # Restore models (simplified for MVP)
            self.predictor.models = model_data['models']
            self.predictor.is_trained = True
            
            logger.info(f"Prediction model loaded successfully from S3: {model_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading prediction model from S3: {e}")
            return False
    
    def get_prediction_statistics(self, days_back: int = 7) -> Dict:
        """
        Get statistics about predictions from S3.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Statistics dictionary
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            total_predictions = 0
            predictions_by_horizon = {}
            significant_predictions = 0
            
            # Iterate through date range
            current_date = start_date
            while current_date <= end_date:
                date_prefix = f"predictions/{current_date.strftime('%Y/%m/%d')}"
                
                try:
                    response = self.s3_client.list_objects_v2(
                        Bucket=self.s3_bucket,
                        Prefix=date_prefix
                    )
                    
                    for obj in response.get('Contents', []):
                        # Download and parse prediction data
                        data_obj = self.s3_client.get_object(
                            Bucket=self.s3_bucket,
                            Key=obj['Key']
                        )
                        
                        data = json.loads(data_obj['Body'].read().decode('utf-8'))
                        
                        for horizon, prediction_data in data.items():
                            if isinstance(horizon, str) and horizon.isdigit():
                                horizon_int = int(horizon)
                                predictions_by_horizon[horizon_int] = predictions_by_horizon.get(horizon_int, 0) + 1
                                total_predictions += 1
                                
                                # Check for significant predictions
                                if 'best_prediction' in prediction_data:
                                    pred_change = abs(prediction_data['best_prediction']['predicted_change_pct'])
                                    if pred_change > 5.0:  # 5% threshold
                                        significant_predictions += 1
                                        
                except Exception as e:
                    logger.warning(f"Error processing prediction data for {date_prefix}: {e}")
                
                current_date += timedelta(days=1)
            
            return {
                'total_predictions': total_predictions,
                'predictions_by_horizon': predictions_by_horizon,
                'significant_predictions': significant_predictions,
                'period_days': days_back,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting prediction statistics: {e}")
            return {'error': str(e)}
    
    def generate_prediction_report(self, data: pd.DataFrame) -> Dict:
        """
        Generate a comprehensive prediction report.
        
        Args:
            data: DataFrame with recent data
            
        Returns:
            Prediction report dictionary
        """
        try:
            # Generate predictions
            predictions_result = self.process_realtime_predictions(data)
            
            if 'error' in predictions_result:
                return predictions_result
            
            # Analyze predictions
            report = {
                'timestamp': datetime.now().isoformat(),
                'data_points': len(data),
                'predictions': predictions_result['predictions'],
                'analysis': {}
            }
            
            # Analyze prediction consistency
            all_changes = []
            all_confidences = []
            
            for horizon, pred_data in predictions_result['predictions'].items():
                if 'best_prediction' in pred_data:
                    all_changes.append(pred_data['best_prediction']['predicted_change_pct'])
                    all_confidences.append(pred_data['best_prediction']['confidence'])
            
            if all_changes:
                report['analysis'] = {
                    'avg_predicted_change': np.mean(all_changes),
                    'max_predicted_change': np.max(all_changes),
                    'min_predicted_change': np.min(all_changes),
                    'avg_confidence': np.mean(all_confidences),
                    'prediction_consistency': 1 - np.std(all_changes) / (np.mean(np.abs(all_changes)) + 1e-6),
                    'trend_direction': 'bullish' if np.mean(all_changes) > 0 else 'bearish'
                }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating prediction report: {e}")
            return {'error': str(e)}


def main():
    """
    Main function for running the prediction pipeline.
    """
    print("Price Prediction Pipeline")
    print("=" * 30)
    
    # Initialize pipeline
    pipeline = PredictionPipeline()
    
    # Check if model exists in S3, otherwise train one
    model_key = "models/latest_price_prediction_model.json"
    if not pipeline.load_model_from_s3(model_key):
        print("No trained model found. Training new model...")
        training_results = pipeline.train_model_from_s3("raw-data", days_back=60)
        print(f"Training completed: {training_results}")
    
    # Create sample data for demonstration
    from price_prediction import create_sample_data
    sample_data = create_sample_data(200)
    
    # Process real-time predictions
    print("\nProcessing real-time predictions...")
    predictions_result = pipeline.process_realtime_predictions(sample_data)
    print(f"Predictions result: {predictions_result}")
    
    # Generate prediction report
    print("\nGenerating prediction report...")
    report = pipeline.generate_prediction_report(sample_data)
    print(f"Prediction report: {report}")
    
    # Get prediction statistics
    print("\nGetting prediction statistics...")
    stats = pipeline.get_prediction_statistics(days_back=7)
    print(f"Prediction statistics: {stats}")
    
    print("\nPrediction pipeline execution completed!")


if __name__ == "__main__":
    main()
