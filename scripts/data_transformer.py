#!/usr/bin/env python3
"""
Data Transformation Utilities for ETL Pipeline
Advanced data cleaning, validation, and transformation functions
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional, Tuple
import re

logger = logging.getLogger(__name__)

class DataTransformer:
    """Advanced data transformation utilities for financial data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_quality_rules = self._load_data_quality_rules()
    
    def _load_data_quality_rules(self) -> Dict[str, Any]:
        """Load data quality validation rules"""
        return {
            'price_data': {
                'min_price': self.config.get('MIN_PRICE_VALUE', 0.01),
                'max_price': self.config.get('MAX_PRICE_VALUE', 1000000),
                'min_volume': self.config.get('MIN_VOLUME_VALUE', 0),
                'required_fields': ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume'],
                'symbol_pattern': r'^[A-Z]{1,5}$'
            },
            'technical_indicators': {
                'min_rsi': self.config.get('MIN_RSI_VALUE', 0),
                'max_rsi': self.config.get('MAX_RSI_VALUE', 100),
                'required_fields': ['symbol', 'timestamp', 'rsi', 'macd', 'sma_20', 'sma_50'],
                'symbol_pattern': r'^[A-Z]{1,5}$'
            }
        }
    
    def validate_and_clean_price_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """Validate and clean price data"""
        logger.info(f"Validating {len(df)} price data records")
        
        validation_stats = {
            'total_records': len(df),
            'valid_records': 0,
            'invalid_records': 0,
            'duplicate_records': 0,
            'missing_values': 0
        }
        
        if df.empty:
            return df, validation_stats
        
        # Remove duplicates
        initial_count = len(df)
        df = df.drop_duplicates(subset=['symbol', 'timestamp'])
        validation_stats['duplicate_records'] = initial_count - len(df)
        
        # Validate required fields
        required_fields = self.data_quality_rules['price_data']['required_fields']
        missing_fields = [field for field in required_fields if field not in df.columns]
        
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return pd.DataFrame(), validation_stats
        
        # Clean and validate data
        cleaned_records = []
        
        for idx, row in df.iterrows():
            try:
                cleaned_record = self._clean_price_record(row)
                if cleaned_record:
                    cleaned_records.append(cleaned_record)
                    validation_stats['valid_records'] += 1
                else:
                    validation_stats['invalid_records'] += 1
            except Exception as e:
                logger.warning(f"Failed to clean record {idx}: {e}")
                validation_stats['invalid_records'] += 1
        
        cleaned_df = pd.DataFrame(cleaned_records)
        validation_stats['missing_values'] = df.isnull().sum().sum()
        
        logger.info(f"Validation complete: {validation_stats['valid_records']} valid, {validation_stats['invalid_records']} invalid")
        return cleaned_df, validation_stats
    
    def _clean_price_record(self, record: pd.Series) -> Optional[Dict[str, Any]]:
        """Clean individual price record"""
        rules = self.data_quality_rules['price_data']
        
        # Validate symbol
        symbol = str(record['symbol']).upper().strip()
        if not re.match(rules['symbol_pattern'], symbol):
            return None
        
        # Validate timestamp
        try:
            timestamp = pd.to_datetime(record['timestamp'])
            if timestamp > datetime.utcnow() + timedelta(days=1):
                return None
        except:
            return None
        
        # Validate prices
        prices = ['open', 'high', 'low', 'close']
        price_values = {}
        
        for price_field in prices:
            try:
                value = float(record[price_field])
                if not (rules['min_price'] <= value <= rules['max_price']):
                    return None
                price_values[price_field] = value
            except:
                return None
        
        # Validate OHLC relationships
        if not (price_values['low'] <= price_values['open'] <= price_values['high'] and
                price_values['low'] <= price_values['close'] <= price_values['high']):
            return None
        
        # Validate volume
        try:
            volume = int(record['volume'])
            if volume < rules['min_volume']:
                return None
        except:
            return None
        
        # Clean source field
        source = str(record.get('source', 'unknown')).strip()
        
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'open': price_values['open'],
            'high': price_values['high'],
            'low': price_values['low'],
            'close': price_values['close'],
            'volume': volume,
            'source': source
        }
    
    def validate_and_clean_technical_indicators(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """Validate and clean technical indicators data"""
        logger.info(f"Validating {len(df)} technical indicators records")
        
        validation_stats = {
            'total_records': len(df),
            'valid_records': 0,
            'invalid_records': 0,
            'duplicate_records': 0,
            'missing_values': 0
        }
        
        if df.empty:
            return df, validation_stats
        
        # Remove duplicates
        initial_count = len(df)
        df = df.drop_duplicates(subset=['symbol', 'timestamp'])
        validation_stats['duplicate_records'] = initial_count - len(df)
        
        # Validate required fields
        required_fields = self.data_quality_rules['technical_indicators']['required_fields']
        missing_fields = [field for field in required_fields if field not in df.columns]
        
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return pd.DataFrame(), validation_stats
        
        # Clean and validate data
        cleaned_records = []
        
        for idx, row in df.iterrows():
            try:
                cleaned_record = self._clean_technical_indicators_record(row)
                if cleaned_record:
                    cleaned_records.append(cleaned_record)
                    validation_stats['valid_records'] += 1
                else:
                    validation_stats['invalid_records'] += 1
            except Exception as e:
                logger.warning(f"Failed to clean record {idx}: {e}")
                validation_stats['invalid_records'] += 1
        
        cleaned_df = pd.DataFrame(cleaned_records)
        validation_stats['missing_values'] = df.isnull().sum().sum()
        
        logger.info(f"Validation complete: {validation_stats['valid_records']} valid, {validation_stats['invalid_records']} invalid")
        return cleaned_df, validation_stats
    
    def _clean_technical_indicators_record(self, record: pd.Series) -> Optional[Dict[str, Any]]:
        """Clean individual technical indicators record"""
        rules = self.data_quality_rules['technical_indicators']
        
        # Validate symbol
        symbol = str(record['symbol']).upper().strip()
        if not re.match(rules['symbol_pattern'], symbol):
            return None
        
        # Validate timestamp
        try:
            timestamp = pd.to_datetime(record['timestamp'])
            if timestamp > datetime.utcnow() + timedelta(days=1):
                return None
        except:
            return None
        
        # Validate RSI
        try:
            rsi = float(record['rsi'])
            if not (rules['min_rsi'] <= rsi <= rules['max_rsi']):
                return None
        except:
            return None
        
        # Validate MACD values
        try:
            macd = float(record['macd'])
            macd_signal = float(record['macd_signal'])
            macd_histogram = float(record['macd_histogram'])
        except:
            return None
        
        # Validate SMA values
        try:
            sma_20 = float(record['sma_20'])
            sma_50 = float(record['sma_50'])
            if sma_20 <= 0 or sma_50 <= 0:
                return None
        except:
            return None
        
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal,
            'macd_histogram': macd_histogram,
            'sma_20': sma_20,
            'sma_50': sma_50
        }
    
    def enrich_data(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Enrich data with additional calculated fields"""
        if df.empty:
            return df
        
        logger.info(f"Enriching {len(df)} {data_type} records")
        
        if data_type == 'price_data':
            return self._enrich_price_data(df)
        elif data_type == 'technical_indicators':
            return self._enrich_technical_indicators(df)
        else:
            return df
    
    def _enrich_price_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich price data with calculated fields"""
        enriched_df = df.copy()
        
        # Calculate price change
        enriched_df['price_change'] = enriched_df['close'] - enriched_df['open']
        enriched_df['price_change_percent'] = (enriched_df['price_change'] / enriched_df['open']) * 100
        
        # Calculate price range
        enriched_df['price_range'] = enriched_df['high'] - enriched_df['low']
        enriched_df['price_range_percent'] = (enriched_df['price_range'] / enriched_df['open']) * 100
        
        # Calculate typical price
        enriched_df['typical_price'] = (enriched_df['high'] + enriched_df['low'] + enriched_df['close']) / 3
        
        # Add processing timestamp
        enriched_df['processed_at'] = datetime.utcnow()
        
        return enriched_df
    
    def _enrich_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich technical indicators with calculated fields"""
        enriched_df = df.copy()
        
        # Calculate RSI signal
        enriched_df['rsi_signal'] = enriched_df['rsi'].apply(
            lambda x: 'oversold' if x < 30 else 'overbought' if x > 70 else 'neutral'
        )
        
        # Calculate MACD signal
        enriched_df['macd_signal_type'] = enriched_df['macd_histogram'].apply(
            lambda x: 'bullish' if x > 0 else 'bearish'
        )
        
        # Calculate SMA trend
        enriched_df['sma_trend'] = enriched_df.apply(
            lambda row: 'bullish' if row['sma_20'] > row['sma_50'] else 'bearish', axis=1
        )
        
        # Add processing timestamp
        enriched_df['processed_at'] = datetime.utcnow()
        
        return enriched_df
    
    def detect_anomalies(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Detect anomalies in the data"""
        if df.empty:
            return pd.DataFrame()
        
        logger.info(f"Detecting anomalies in {len(df)} {data_type} records")
        
        anomalies = []
        
        if data_type == 'price_data':
            anomalies = self._detect_price_anomalies(df)
        elif data_type == 'technical_indicators':
            anomalies = self._detect_technical_anomalies(df)
        
        return pd.DataFrame(anomalies)
    
    def _detect_price_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect price anomalies"""
        anomalies = []
        
        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol].sort_values('timestamp')
            
            if len(symbol_data) < 2:
                continue
            
            # Detect extreme price movements
            price_changes = symbol_data['price_change_percent'].abs()
            threshold = price_changes.quantile(0.95)  # Top 5% as threshold
            
            extreme_moves = symbol_data[price_changes > threshold]
            
            for _, row in extreme_moves.iterrows():
                anomalies.append({
                    'symbol': row['symbol'],
                    'timestamp': row['timestamp'],
                    'anomaly_type': 'extreme_price_movement',
                    'severity': 'high' if price_changes.loc[row.name] > threshold * 2 else 'medium',
                    'value': row['price_change_percent'],
                    'threshold': threshold,
                    'description': f"Price change of {row['price_change_percent']:.2f}% exceeds threshold"
                })
        
        return anomalies
    
    def _detect_technical_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect technical indicators anomalies"""
        anomalies = []
        
        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol].sort_values('timestamp')
            
            if len(symbol_data) < 2:
                continue
            
            # Detect RSI anomalies
            extreme_rsi = symbol_data[(symbol_data['rsi'] < 10) | (symbol_data['rsi'] > 90)]
            
            for _, row in extreme_rsi.iterrows():
                anomalies.append({
                    'symbol': row['symbol'],
                    'timestamp': row['timestamp'],
                    'anomaly_type': 'extreme_rsi',
                    'severity': 'high',
                    'value': row['rsi'],
                    'threshold': 10 if row['rsi'] < 10 else 90,
                    'description': f"RSI value {row['rsi']:.2f} is extremely {'low' if row['rsi'] < 10 else 'high'}"
                })
        
        return anomalies

def create_transformer(config: Dict[str, Any]) -> DataTransformer:
    """Factory function to create DataTransformer instance"""
    return DataTransformer(config)
