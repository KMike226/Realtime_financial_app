"""
Integration Script for Anomaly Detection Model
==============================================

This script integrates the anomaly detection model with the existing data pipeline,
including Kinesis streams, S3 storage, and alerting systems.
"""

import json
import logging
import boto3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from io import StringIO

from anomaly_detection import FinancialAnomalyDetector
from config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnomalyDetectionPipeline:
    """
    Pipeline for integrating anomaly detection with the existing data infrastructure.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the anomaly detection pipeline.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or get_config()
        self.detector = FinancialAnomalyDetector(self.config)
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3')
        self.kinesis_client = boto3.client('kinesis')
        self.sns_client = boto3.client('sns')
        
        # Configuration from environment
        self.s3_bucket = os.getenv('S3_BUCKET', 'financial-data-lake')
        self.kinesis_stream = os.getenv('KINESIS_STREAM', 'financial-data-stream')
        self.sns_topic = os.getenv('SNS_TOPIC', 'anomaly-alerts')
        
    def process_kinesis_data(self, batch_size: int = 100) -> Dict:
        """
        Process data from Kinesis stream for anomaly detection.
        
        Args:
            batch_size: Number of records to process in each batch
            
        Returns:
            Processing results dictionary
        """
        logger.info(f"Processing Kinesis data with batch size {batch_size}")
        
        try:
            # Get records from Kinesis
            response = self.kinesis_client.get_records(
                ShardIterator=self._get_shard_iterator(),
                Limit=batch_size
            )
            
            records = response['Records']
            if not records:
                logger.info("No records available in Kinesis stream")
                return {'processed': 0, 'anomalies': 0}
            
            # Parse records
            data_points = []
            for record in records:
                try:
                    data = json.loads(record['Data'].decode('utf-8'))
                    data_points.append(data)
                except Exception as e:
                    logger.warning(f"Failed to parse record: {e}")
                    continue
            
            if not data_points:
                logger.warning("No valid data points found in batch")
                return {'processed': 0, 'anomalies': 0}
            
            # Convert to DataFrame
            df = pd.DataFrame(data_points)
            
            # Detect anomalies
            results = self.detector.detect_anomalies(df, train_model=False)
            
            # Process results
            anomalies = results[results['is_anomaly']]
            anomaly_count = len(anomalies)
            
            # Store results in S3
            self._store_results_in_s3(results)
            
            # Send alerts for anomalies
            if anomaly_count > 0:
                self._send_anomaly_alerts(anomalies)
            
            logger.info(f"Processed {len(data_points)} records, found {anomaly_count} anomalies")
            
            return {
                'processed': len(data_points),
                'anomalies': anomaly_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing Kinesis data: {e}")
            return {'error': str(e), 'processed': 0, 'anomalies': 0}
    
    def _get_shard_iterator(self) -> str:
        """
        Get shard iterator for Kinesis stream.
        
        Returns:
            Shard iterator string
        """
        try:
            response = self.kinesis_client.describe_stream(StreamName=self.kinesis_stream)
            shard_id = response['StreamDescription']['Shards'][0]['ShardId']
            
            response = self.kinesis_client.get_shard_iterator(
                StreamName=self.kinesis_stream,
                ShardId=shard_id,
                ShardIteratorType='LATEST'
            )
            
            return response['ShardIterator']
            
        except Exception as e:
            logger.error(f"Error getting shard iterator: {e}")
            raise
    
    def _store_results_in_s3(self, results: pd.DataFrame) -> None:
        """
        Store anomaly detection results in S3.
        
        Args:
            results: DataFrame with detection results
        """
        try:
            # Create timestamp-based key
            timestamp = datetime.now().strftime('%Y/%m/%d/%H')
            key = f"anomaly-detection/{timestamp}/results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Convert DataFrame to JSON
            json_data = results.to_json(orient='records', date_format='iso')
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json_data,
                ContentType='application/json'
            )
            
            logger.info(f"Results stored in S3: s3://{self.s3_bucket}/{key}")
            
        except Exception as e:
            logger.error(f"Error storing results in S3: {e}")
    
    def _send_anomaly_alerts(self, anomalies: pd.DataFrame) -> None:
        """
        Send alerts for detected anomalies.
        
        Args:
            anomalies: DataFrame containing anomaly records
        """
        try:
            for _, anomaly in anomalies.iterrows():
                alert_message = {
                    'timestamp': anomaly['timestamp'].isoformat() if hasattr(anomaly['timestamp'], 'isoformat') else str(anomaly['timestamp']),
                    'symbol': anomaly.get('symbol', 'Unknown'),
                    'anomaly_score': float(anomaly['anomaly_score']),
                    'anomaly_type': 'financial_anomaly',
                    'details': {
                        'price': float(anomaly.get('price', 0)),
                        'volume': float(anomaly.get('volume', 0)),
                        'price_change': float(anomaly.get('price_change', 0)),
                        'volume_change': float(anomaly.get('volume_change', 0))
                    }
                }
                
                # Send SNS notification
                self.sns_client.publish(
                    TopicArn=self.sns_topic,
                    Message=json.dumps(alert_message),
                    Subject=f"Financial Anomaly Detected: {anomaly.get('symbol', 'Unknown')}"
                )
                
            logger.info(f"Sent {len(anomalies)} anomaly alerts")
            
        except Exception as e:
            logger.error(f"Error sending anomaly alerts: {e}")
    
    def train_model_from_s3(self, s3_prefix: str, days_back: int = 30) -> Dict:
        """
        Train the anomaly detection model using historical data from S3.
        
        Args:
            s3_prefix: S3 prefix for training data
            days_back: Number of days of historical data to use
            
        Returns:
            Training results dictionary
        """
        logger.info(f"Training model from S3 data: {s3_prefix}")
        
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
            logger.info(f"Training model with {len(df)} data points")
            
            # Train the model
            results = self.detector.detect_anomalies(df, train_model=True)
            
            # Save trained model
            model_key = f"models/anomaly_detection_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.detector.save_model(f"s3://{self.s3_bucket}/{model_key}")
            
            # Get training summary
            summary = self.detector.get_anomaly_summary(results)
            
            logger.info(f"Model training completed. Anomaly rate: {summary['anomaly_rate']:.2%}")
            
            return {
                'training_samples': len(df),
                'anomaly_rate': summary['anomaly_rate'],
                'model_saved_to': f"s3://{self.s3_bucket}/{model_key}",
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error training model from S3: {e}")
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
            
            # Load model into detector
            self.detector.config = model_data['config']
            self.detector.feature_names = model_data['feature_names']
            
            # Restore scaler
            from sklearn.preprocessing import StandardScaler
            self.detector.scaler = StandardScaler()
            self.detector.scaler.mean_ = np.array(model_data['scaler_mean'])
            self.detector.scaler.scale_ = np.array(model_data['scaler_scale'])
            
            # Restore Isolation Forest
            from sklearn.ensemble import IsolationForest
            self.detector.isolation_forest = IsolationForest(**model_data['isolation_forest_params'])
            self.detector.isolation_forest.fit(np.zeros((1, len(self.detector.feature_names))))
            
            self.detector.is_trained = True
            
            logger.info(f"Model loaded successfully from S3: {model_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model from S3: {e}")
            return False
    
    def get_anomaly_statistics(self, days_back: int = 7) -> Dict:
        """
        Get statistics about detected anomalies from S3.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Statistics dictionary
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            total_anomalies = 0
            anomalies_by_symbol = {}
            
            # Iterate through date range
            current_date = start_date
            while current_date <= end_date:
                date_prefix = f"anomaly-detection/{current_date.strftime('%Y/%m/%d')}"
                
                try:
                    response = self.s3_client.list_objects_v2(
                        Bucket=self.s3_bucket,
                        Prefix=date_prefix
                    )
                    
                    for obj in response.get('Contents', []):
                        # Download and parse anomaly data
                        data_obj = self.s3_client.get_object(
                            Bucket=self.s3_bucket,
                            Key=obj['Key']
                        )
                        
                        data = json.loads(data_obj['Body'].read().decode('utf-8'))
                        
                        for record in data:
                            if record.get('is_anomaly', False):
                                total_anomalies += 1
                                symbol = record.get('symbol', 'Unknown')
                                anomalies_by_symbol[symbol] = anomalies_by_symbol.get(symbol, 0) + 1
                                
                except Exception as e:
                    logger.warning(f"Error processing anomaly data for {date_prefix}: {e}")
                
                current_date += timedelta(days=1)
            
            return {
                'total_anomalies': total_anomalies,
                'anomalies_by_symbol': anomalies_by_symbol,
                'period_days': days_back,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting anomaly statistics: {e}")
            return {'error': str(e)}


def main():
    """
    Main function for running the anomaly detection pipeline.
    """
    print("Anomaly Detection Pipeline")
    print("=" * 30)
    
    # Initialize pipeline
    pipeline = AnomalyDetectionPipeline()
    
    # Check if model exists in S3, otherwise train one
    model_key = "models/latest_anomaly_detection_model.json"
    if not pipeline.load_model_from_s3(model_key):
        print("No trained model found. Training new model...")
        training_results = pipeline.train_model_from_s3("raw-data", days_back=30)
        print(f"Training completed: {training_results}")
    
    # Process real-time data
    print("\nProcessing real-time data...")
    processing_results = pipeline.process_kinesis_data(batch_size=50)
    print(f"Processing results: {processing_results}")
    
    # Get anomaly statistics
    print("\nGetting anomaly statistics...")
    stats = pipeline.get_anomaly_statistics(days_back=7)
    print(f"Anomaly statistics: {stats}")
    
    print("\nPipeline execution completed!")


if __name__ == "__main__":
    main()
