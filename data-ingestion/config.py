"""
Configuration module for data ingestion
=======================================

Gère la configuration centralisée pour tous les connecteurs de données.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()


@dataclass
class S3Config:
    """Configuration pour le stockage S3"""
    bucket_name: str = os.getenv('DATA_LAKE_BUCKET', 'realtime-financial-data-lake')
    region: str = os.getenv('AWS_REGION', 'us-east-1')
    access_key_id: Optional[str] = os.getenv('AWS_ACCESS_KEY_ID')
    secret_access_key: Optional[str] = os.getenv('AWS_SECRET_ACCESS_KEY')


@dataclass
class AlphaVantageConfig:
    """Configuration pour Alpha Vantage API"""
    api_key: str = os.getenv('ALPHA_VANTAGE_API_KEY', '')
    base_url: str = "https://www.alphavantage.co/query"
    requests_per_minute: int = int(os.getenv('ALPHA_VANTAGE_RPM', '5'))
    timeout: int = int(os.getenv('ALPHA_VANTAGE_TIMEOUT', '30'))
    max_retries: int = int(os.getenv('ALPHA_VANTAGE_MAX_RETRIES', '3'))
    retry_delay: int = int(os.getenv('ALPHA_VANTAGE_RETRY_DELAY', '60'))


@dataclass
class KinesisConfig:
    """Configuration pour AWS Kinesis"""
    stream_name: str = os.getenv('KINESIS_STREAM_NAME', 'financial-data-stream')
    region: str = os.getenv('AWS_REGION', 'us-east-1')
    shard_count: int = int(os.getenv('KINESIS_SHARD_COUNT', '2'))


@dataclass
class ApplicationConfig:
    """Configuration générale de l'application"""
    environment: str = os.getenv('ENVIRONMENT', 'development')
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    batch_size: int = int(os.getenv('BATCH_SIZE', '100'))
    processing_interval: int = int(os.getenv('PROCESSING_INTERVAL', '60'))
    
    # Configuration des données
    symbols_file: str = os.getenv('SYMBOLS_FILE', 'config/symbols.json')
    max_symbols_per_request: int = int(os.getenv('MAX_SYMBOLS_PER_REQUEST', '10'))


# Configuration globale
config = ApplicationConfig()
s3_config = S3Config()
alpha_vantage_config = AlphaVantageConfig()
kinesis_config = KinesisConfig()


def validate_config():
    """Valide que toutes les configurations requises sont présentes"""
    errors = []
    
    if not alpha_vantage_config.api_key:
        errors.append("ALPHA_VANTAGE_API_KEY est requis")
    
    if not s3_config.bucket_name:
        errors.append("DATA_LAKE_BUCKET est requis")
    
    if errors:
        raise ValueError("Erreurs de configuration: " + ", ".join(errors))
    
    return True
