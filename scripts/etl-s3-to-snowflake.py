#!/usr/bin/env python3
"""
ETL Pipeline: S3 to Snowflake MVP
Extract, Transform, and Load financial data from S3 to Snowflake
"""

import json
import boto3
import pandas as pd
import snowflake.connector
from datetime import datetime, timedelta
import logging
import os
from typing import Dict, List, Any, Optional
import gzip
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class S3ToSnowflakeETL:
    """MVP ETL Pipeline for S3 to Snowflake data transfer"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.s3_client = boto3.client('s3')
        self.snowflake_conn = None
        
        # Initialize connections
        self._init_snowflake_connection()
    
    def _init_snowflake_connection(self):
        """Initialize Snowflake connection"""
        try:
            self.snowflake_conn = snowflake.connector.connect(
                user=self.config['snowflake']['username'],
                password=self.config['snowflake']['password'],
                account=self.config['snowflake']['account'],
                warehouse=self.config['snowflake']['warehouse'],
                database=self.config['snowflake']['database'],
                schema=self.config['snowflake']['schema'],
                role=self.config['snowflake']['role']
            )
            logger.info("Snowflake connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise
    
    def extract_from_s3(self, bucket: str, prefix: str, hours_back: int = 1) -> List[Dict[str, Any]]:
        """Extract data from S3 bucket"""
        logger.info(f"Extracting data from S3: {bucket}/{prefix}")
        
        try:
            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours_back)
            
            # List objects in S3
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            extracted_data = []
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Check if object is within time range
                    if obj['LastModified'].replace(tzinfo=None) >= start_time:
                        data = self._read_s3_object(bucket, obj['Key'])
                        if data:
                            extracted_data.extend(data)
            
            logger.info(f"Extracted {len(extracted_data)} records from S3")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Failed to extract data from S3: {e}")
            return []
    
    def _read_s3_object(self, bucket: str, key: str) -> Optional[List[Dict[str, Any]]]:
        """Read and parse S3 object"""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            
            # Handle compressed files
            if key.endswith('.gz'):
                content = gzip.decompress(response['Body'].read())
            else:
                content = response['Body'].read()
            
            # Parse JSON data
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            data = json.loads(content)
            
            # Handle different data formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                logger.warning(f"Unexpected data format in {key}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to read S3 object {key}: {e}")
            return None
    
    def transform_data(self, raw_data: List[Dict[str, Any]], data_type: str) -> pd.DataFrame:
        """Transform raw data into structured format"""
        logger.info(f"Transforming {len(raw_data)} records of type: {data_type}")
        
        if data_type == 'price_data':
            return self._transform_price_data(raw_data)
        elif data_type == 'technical_indicators':
            return self._transform_technical_indicators(raw_data)
        else:
            logger.warning(f"Unknown data type: {data_type}")
            return pd.DataFrame()
    
    def _transform_price_data(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transform price data"""
        transformed_records = []
        
        for record in data:
            try:
                transformed_record = {
                    'SYMBOL': record.get('symbol', ''),
                    'TIMESTAMP': pd.to_datetime(record.get('timestamp', datetime.utcnow())),
                    'OPEN_PRICE': float(record.get('open', 0)),
                    'HIGH_PRICE': float(record.get('high', 0)),
                    'LOW_PRICE': float(record.get('low', 0)),
                    'CLOSE_PRICE': float(record.get('close', 0)),
                    'VOLUME': int(record.get('volume', 0)),
                    'SOURCE': record.get('source', 'unknown')
                }
                transformed_records.append(transformed_record)
            except Exception as e:
                logger.warning(f"Failed to transform price record: {e}")
                continue
        
        return pd.DataFrame(transformed_records)
    
    def _transform_technical_indicators(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transform technical indicators data"""
        transformed_records = []
        
        for record in data:
            try:
                transformed_record = {
                    'SYMBOL': record.get('symbol', ''),
                    'TIMESTAMP': pd.to_datetime(record.get('timestamp', datetime.utcnow())),
                    'RSI': float(record.get('rsi', 0)),
                    'MACD': float(record.get('macd', 0)),
                    'MACD_SIGNAL': float(record.get('macd_signal', 0)),
                    'MACD_HISTOGRAM': float(record.get('macd_histogram', 0)),
                    'SMA_20': float(record.get('sma_20', 0)),
                    'SMA_50': float(record.get('sma_50', 0))
                }
                transformed_records.append(transformed_record)
            except Exception as e:
                logger.warning(f"Failed to transform technical indicators record: {e}")
                continue
        
        return pd.DataFrame(transformed_records)
    
    def load_to_snowflake(self, df: pd.DataFrame, table_name: str) -> bool:
        """Load transformed data to Snowflake"""
        if df.empty:
            logger.warning(f"No data to load to {table_name}")
            return True
        
        logger.info(f"Loading {len(df)} records to Snowflake table: {table_name}")
        
        try:
            cursor = self.snowflake_conn.cursor()
            
            # Create temporary table for staging
            temp_table = f"{table_name}_TEMP_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Convert DataFrame to SQL INSERT statements
            insert_sql = self._dataframe_to_insert_sql(df, table_name)
            
            # Execute insert
            cursor.execute(insert_sql)
            
            # Commit transaction
            self.snowflake_conn.commit()
            
            logger.info(f"Successfully loaded {len(df)} records to {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load data to Snowflake: {e}")
            self.snowflake_conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def _dataframe_to_insert_sql(self, df: pd.DataFrame, table_name: str) -> str:
        """Convert DataFrame to SQL INSERT statement"""
        columns = ', '.join(df.columns)
        values_list = []
        
        for _, row in df.iterrows():
            values = []
            for value in row:
                if pd.isna(value):
                    values.append('NULL')
                elif isinstance(value, str):
                    values.append(f"'{value.replace("'", "''")}'")
                elif isinstance(value, datetime):
                    values.append(f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'")
                else:
                    values.append(str(value))
            values_list.append(f"({', '.join(values)})")
        
        sql = f"INSERT INTO {table_name} ({columns}) VALUES {', '.join(values_list)}"
        return sql
    
    def run_etl_pipeline(self, data_sources: List[Dict[str, str]]) -> Dict[str, bool]:
        """Run complete ETL pipeline for multiple data sources"""
        results = {}
        
        logger.info("Starting ETL pipeline execution")
        
        for source in data_sources:
            source_name = source['name']
            logger.info(f"Processing data source: {source_name}")
            
            try:
                # Extract
                raw_data = self.extract_from_s3(
                    bucket=source['bucket'],
                    prefix=source['prefix'],
                    hours_back=source.get('hours_back', 1)
                )
                
                if not raw_data:
                    logger.warning(f"No data found for source: {source_name}")
                    results[source_name] = False
                    continue
                
                # Transform
                df = self.transform_data(raw_data, source['data_type'])
                
                if df.empty:
                    logger.warning(f"No valid data after transformation for: {source_name}")
                    results[source_name] = False
                    continue
                
                # Load
                success = self.load_to_snowflake(df, source['table_name'])
                results[source_name] = success
                
            except Exception as e:
                logger.error(f"ETL pipeline failed for {source_name}: {e}")
                results[source_name] = False
        
        logger.info(f"ETL pipeline completed. Results: {results}")
        return results
    
    def close_connections(self):
        """Close database connections"""
        if self.snowflake_conn:
            self.snowflake_conn.close()
            logger.info("Snowflake connection closed")

def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables or config file"""
    config = {
        'snowflake': {
            'username': os.getenv('SNOWFLAKE_USERNAME', 'your_username'),
            'password': os.getenv('SNOWFLAKE_PASSWORD', 'your_password'),
            'account': os.getenv('SNOWFLAKE_ACCOUNT', 'your_account'),
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'FINANCIAL_WAREHOUSE'),
            'database': os.getenv('SNOWFLAKE_DATABASE', 'FINANCIAL_DATA'),
            'schema': os.getenv('SNOWFLAKE_SCHEMA', 'MARKET_DATA'),
            'role': os.getenv('SNOWFLAKE_ROLE', 'your_role')
        },
        's3': {
            'bucket': os.getenv('S3_BUCKET', 'financial-platform-dev-data-lake')
        }
    }
    return config

def main():
    """Main ETL pipeline execution"""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize ETL pipeline
        etl = S3ToSnowflakeETL(config)
        
        # Define data sources
        data_sources = [
            {
                'name': 'price_data',
                'bucket': config['s3']['bucket'],
                'prefix': 'processed/price_data',
                'data_type': 'price_data',
                'table_name': 'FINANCIAL_DATA.MARKET_DATA.PRICE_DATA',
                'hours_back': 1
            },
            {
                'name': 'technical_indicators',
                'bucket': config['s3']['bucket'],
                'prefix': 'processed/technical_indicators',
                'data_type': 'technical_indicators',
                'table_name': 'FINANCIAL_DATA.ANALYTICS.TECHNICAL_INDICATORS',
                'hours_back': 1
            }
        ]
        
        # Run ETL pipeline
        results = etl.run_etl_pipeline(data_sources)
        
        # Log results
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        logger.info(f"ETL Pipeline Summary: {success_count}/{total_count} sources processed successfully")
        
        # Close connections
        etl.close_connections()
        
        return success_count == total_count
        
    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
