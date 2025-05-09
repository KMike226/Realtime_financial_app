#!/usr/bin/env python3
"""
Snowflake Integration Script MVP
Connects Spark streaming jobs to Snowflake data pipeline
"""

import json
import boto3
from datetime import datetime
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SnowflakeIntegration:
    """MVP Integration between Spark jobs and Snowflake"""
    
    def __init__(self, s3_bucket: str):
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3')
    
    def process_spark_output(self, spark_output_path: str) -> bool:
        """Process Spark job output and prepare for Snowflake"""
        try:
            # Read Spark output from S3
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=spark_output_path
            )
            
            data = json.loads(response['Body'].read())
            
            # Process price data if present
            if 'price_data' in data:
                self._upload_price_data(data['price_data'])
            
            # Process technical indicators if present
            if 'technical_indicators' in data:
                self._upload_technical_indicators(data['technical_indicators'])
            
            logger.info(f"Successfully processed Spark output: {spark_output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process Spark output: {e}")
            return False
    
    def _upload_price_data(self, price_data: list):
        """Upload price data to Snowflake staging area"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"price_data_{timestamp}.json"
        
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=f"processed/{filename}",
            Body=json.dumps(price_data),
            ContentType='application/json'
        )
        
        logger.info(f"Uploaded price data: {filename}")
    
    def _upload_technical_indicators(self, indicators: list):
        """Upload technical indicators to Snowflake staging area"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"technical_indicators_{timestamp}.json"
        
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=f"processed/{filename}",
            Body=json.dumps(indicators),
            ContentType='application/json'
        )
        
        logger.info(f"Uploaded technical indicators: {filename}")

def main():
    """Example integration usage"""
    integration = SnowflakeIntegration("your-financial-data-bucket")
    
    # Example: Process Spark job output
    spark_output_path = "spark-output/2025/05/15/price_data.json"
    success = integration.process_spark_output(spark_output_path)
    
    if success:
        logger.info("Integration completed successfully")
    else:
        logger.error("Integration failed")

if __name__ == "__main__":
    main()
