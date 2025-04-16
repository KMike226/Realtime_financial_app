#!/usr/bin/env python3
"""
Configuration pour Multi-Source Data Ingestion
"""

import os
from typing import Dict, List

class MultiSourceConfig:
    """Configuration pour l'ingestion multi-sources"""
    
    # Configuration S3
    S3_BUCKET = os.getenv('S3_BUCKET', 'financial-pipeline-dev-data-lake')
    S3_PREFIX = 'raw-data'
    
    # Configuration IEX Cloud
    IEX_CLOUD_API_KEY = os.getenv('IEX_CLOUD_API_KEY')
    IEX_CLOUD_BASE_URL = 'https://cloud.iexapis.com/stable'
    
    # Configuration CoinGecko
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
    COINGECKO_BASE_URL = 'https://api.coingecko.com/api/v3'
    
    # Configuration Binance
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    BINANCE_BASE_URL = 'https://api.binance.com/api/v3'
    
    # Symboles par défaut
    DEFAULT_STOCK_SYMBOLS = [
        'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA',
        'META', 'NVDA', 'NFLX', 'ADBE', 'CRM'
    ]
    
    DEFAULT_CRYPTO_SYMBOLS = [
        'bitcoin', 'ethereum', 'binancecoin', 'cardano', 'solana',
        'polkadot', 'chainlink', 'litecoin', 'bitcoin-cash', 'stellar'
    ]
    
    # Configuration des requêtes
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    RATE_LIMIT_DELAY = 0.1
    
    # Configuration des données
    DEFAULT_TIMEFRAME = '1d'
    DEFAULT_INTERVAL = '1h'
    DEFAULT_LIMIT = 100
    
    @classmethod
    def get_api_keys_status(cls) -> Dict[str, bool]:
        """Retourne le statut des clés API"""
        return {
            'iex_cloud': bool(cls.IEX_CLOUD_API_KEY),
            'coingecko': bool(cls.COINGECKO_API_KEY),
            'binance': bool(cls.BINANCE_API_KEY and cls.BINANCE_SECRET_KEY)
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Valide la configuration"""
        status = cls.get_api_keys_status()
        
        if not any(status.values()):
            print("⚠️ Aucune clé API configurée")
            return False
        
        print("🔑 Statut des clés API:")
        for service, available in status.items():
            status_icon = "✅" if available else "❌"
            print(f"  {status_icon} {service}")
        
        return True
