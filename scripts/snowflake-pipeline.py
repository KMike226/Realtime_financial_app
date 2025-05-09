#!/usr/bin/env python3
"""
Snowflake Data Pipeline MVP
Simple script to format financial data for Snowflake ingestion
"""

import json
import boto3
from datetime import datetime
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SnowflakeDataPipeline:
    """MVP Data pipeline for Snowflake ingestion"""
    
    def __init__(self, s3_bucket: str, s3_prefix: str = "processed/"):
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.s3_client = boto3.client('s3')
    
    def format_price_data(self, symbol: str, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format price data for Snowflake ingestion"""
        return {
            "SYMBOL": symbol,
            "TIMESTAMP": datetime.utcnow().isoformat(),
            "OPEN_PRICE": float(price_data.get('open', 0)),
            "HIGH_PRICE": float(price_data.get('high', 0)),
            "LOW_PRICE": float(price_data.get('low', 0)),
            "CLOSE_PRICE": float(price_data.get('close', 0)),
            "VOLUME": int(price_data.get('volume', 0)),
            "SOURCE": price_data.get('source', 'unknown')
        }
    
    def format_technical_indicators(self, symbol: str, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Format technical indicators for Snowflake ingestion"""
        return {
            "SYMBOL": symbol,
            "TIMESTAMP": datetime.utcnow().isoformat(),
            "RSI": float(indicators.get('rsi', 0)),
            "MACD": float(indicators.get('macd', 0)),
            "MACD_SIGNAL": float(indicators.get('macd_signal', 0)),
            "MACD_HISTOGRAM": float(indicators.get('macd_histogram', 0)),
            "SMA_20": float(indicators.get('sma_20', 0)),
            "SMA_50": float(indicators.get('sma_50', 0))
        }
    
    def upload_to_s3(self, data: List[Dict], data_type: str) -> bool:
        """Upload formatted data to S3 for Snowflake ingestion"""
        try:
            # Create filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{data_type}_{timestamp}.json"
            s3_key = f"{self.s3_prefix}{filename}"
            
            # Convert to JSON
            json_data = json.dumps(data, indent=2)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=json_data,
                ContentType='application/json'
            )
            
            logger.info(f"Uploaded {len(data)} records to s3://{self.s3_bucket}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload data to S3: {e}")
            return False
    
    def process_price_data(self, price_records: List[Dict[str, Any]]) -> bool:
        """Process and upload price data"""
        formatted_data = []
        
        for record in price_records:
            symbol = record.get('symbol', 'UNKNOWN')
            formatted_record = self.format_price_data(symbol, record)
            formatted_data.append(formatted_record)
        
        return self.upload_to_s3(formatted_data, "price_data")
    
    def process_technical_indicators(self, indicator_records: List[Dict[str, Any]]) -> bool:
        """Process and upload technical indicators"""
        formatted_data = []
        
        for record in indicator_records:
            symbol = record.get('symbol', 'UNKNOWN')
            formatted_record = self.format_technical_indicators(symbol, record)
            formatted_data.append(formatted_record)
        
        return self.upload_to_s3(formatted_data, "technical_indicators")

def main():
    """Example usage of the Snowflake data pipeline"""
    
    # Initialize pipeline
    pipeline = SnowflakeDataPipeline("your-financial-data-bucket")
    
    # Example price data
    sample_price_data = [
        {
            "symbol": "AAPL",
            "open": 150.25,
            "high": 152.10,
            "low": 149.80,
            "close": 151.50,
            "volume": 1000000,
            "source": "alpha_vantage"
        },
        {
            "symbol": "GOOGL",
            "open": 2800.00,
            "high": 2825.50,
            "low": 2795.25,
            "close": 2810.75,
            "volume": 500000,
            "source": "alpha_vantage"
        }
    ]
    
    # Example technical indicators
    sample_indicators = [
        {
            "symbol": "AAPL",
            "rsi": 65.5,
            "macd": 2.15,
            "macd_signal": 1.85,
            "macd_histogram": 0.30,
            "sma_20": 150.25,
            "sma_50": 148.90
        }
    ]
    
    # Process data
    price_success = pipeline.process_price_data(sample_price_data)
    indicator_success = pipeline.process_technical_indicators(sample_indicators)
    
    if price_success and indicator_success:
        logger.info("Data pipeline completed successfully")
    else:
        logger.error("Data pipeline failed")

if __name__ == "__main__":
    main()
