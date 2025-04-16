#!/usr/bin/env python3
"""
Multi-Source Data Ingestion Connectors
Connecteurs pour IEX Cloud, CoinGecko, et Binance
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import boto3
from dataclasses import dataclass
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Structure pour les données de marché"""
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str
    market: str

class BaseConnector:
    """Classe de base pour tous les connecteurs"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FinancialPipeline/1.0'
        })
        
    def _make_request(self, url: str, params: Dict = None, max_retries: int = 3) -> Dict:
        """Effectue une requête HTTP avec retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Tentative {attempt + 1} échouée: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Backoff exponentiel
                else:
                    raise e

class IEXCloudConnector(BaseConnector):
    """Connecteur pour IEX Cloud API"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://cloud.iexapis.com/stable"
        
    def get_stock_data(self, symbol: str, timeframe: str = "1d") -> List[MarketData]:
        """Récupère les données d'actions depuis IEX Cloud"""
        logger.info(f"Récupération des données IEX Cloud pour {symbol}")
        
        url = f"{self.base_url}/stock/{symbol}/chart/{timeframe}"
        params = {
            'token': self.api_key,
            'chartCloseOnly': 'false'
        }
        
        try:
            data = self._make_request(url, params)
            
            market_data = []
            for item in data:
                market_data.append(MarketData(
                    symbol=symbol,
                    timestamp=item['date'] + ' ' + item.get('minute', '00:00'),
                    open=item['open'],
                    high=item['high'],
                    low=item['low'],
                    close=item['close'],
                    volume=item['volume'],
                    source='iex_cloud',
                    market='stocks'
                ))
            
            logger.info(f"Récupéré {len(market_data)} points de données pour {symbol}")
            return market_data
            
        except Exception as e:
            logger.error(f"Erreur IEX Cloud pour {symbol}: {e}")
            return []
    
    def get_market_data(self, symbols: List[str]) -> List[MarketData]:
        """Récupère les données pour plusieurs symboles"""
        all_data = []
        
        for symbol in symbols:
            data = self.get_stock_data(symbol)
            all_data.extend(data)
            time.sleep(0.1)  # Rate limiting
        
        return all_data

class CoinGeckoConnector(BaseConnector):
    """Connecteur pour CoinGecko API"""
    
    def __init__(self, api_key: str = None):
        super().__init__(api_key)
        self.base_url = "https://api.coingecko.com/api/v3"
        
    def get_crypto_data(self, coin_id: str, days: int = 1) -> List[MarketData]:
        """Récupère les données crypto depuis CoinGecko"""
        logger.info(f"Récupération des données CoinGecko pour {coin_id}")
        
        url = f"{self.base_url}/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'hourly' if days > 1 else 'minutely'
        }
        
        if self.api_key:
            params['x_cg_demo_api_key'] = self.api_key
        
        try:
            data = self._make_request(url, params)
            
            market_data = []
            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            
            for i, price_point in enumerate(prices):
                timestamp = datetime.fromtimestamp(price_point[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                price = price_point[1]
                volume = volumes[i][1] if i < len(volumes) else 0
                
                market_data.append(MarketData(
                    symbol=coin_id,
                    timestamp=timestamp,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=int(volume),
                    source='coingecko',
                    market='crypto'
                ))
            
            logger.info(f"Récupéré {len(market_data)} points de données pour {coin_id}")
            return market_data
            
        except Exception as e:
            logger.error(f"Erreur CoinGecko pour {coin_id}: {e}")
            return []
    
    def get_top_cryptos(self, limit: int = 10) -> List[str]:
        """Récupère la liste des cryptos les plus populaires"""
        url = f"{self.base_url}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1
        }
        
        if self.api_key:
            params['x_cg_demo_api_key'] = self.api_key
        
        try:
            data = self._make_request(url, params)
            return [coin['id'] for coin in data]
        except Exception as e:
            logger.error(f"Erreur récupération top cryptos: {e}")
            return ['bitcoin', 'ethereum', 'binancecoin']

class BinanceConnector(BaseConnector):
    """Connecteur pour Binance API"""
    
    def __init__(self, api_key: str = None, secret_key: str = None):
        super().__init__(api_key)
        self.secret_key = secret_key
        self.base_url = "https://api.binance.com/api/v3"
        
    def get_crypto_data(self, symbol: str, interval: str = "1h", limit: int = 100) -> List[MarketData]:
        """Récupère les données crypto depuis Binance"""
        logger.info(f"Récupération des données Binance pour {symbol}")
        
        url = f"{self.base_url}/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            data = self._make_request(url, params)
            
            market_data = []
            for item in data:
                timestamp = datetime.fromtimestamp(item[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                
                market_data.append(MarketData(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=int(float(item[5])),
                    source='binance',
                    market='crypto'
                ))
            
            logger.info(f"Récupéré {len(market_data)} points de données pour {symbol}")
            return market_data
            
        except Exception as e:
            logger.error(f"Erreur Binance pour {symbol}: {e}")
            return []
    
    def get_exchange_info(self) -> Dict:
        """Récupère les informations sur les symboles disponibles"""
        url = f"{self.base_url}/exchangeInfo"
        
        try:
            return self._make_request(url)
        except Exception as e:
            logger.error(f"Erreur récupération exchange info: {e}")
            return {}

class DataIngestionManager:
    """Gestionnaire principal pour l'ingestion multi-sources"""
    
    def __init__(self, s3_bucket: str = None):
        self.s3_bucket = s3_bucket or os.getenv('S3_BUCKET', 'financial-pipeline-dev-data-lake')
        self.s3_client = boto3.client('s3')
        
        # Initialisation des connecteurs
        self.iex_connector = IEXCloudConnector(os.getenv('IEX_CLOUD_API_KEY'))
        self.coingecko_connector = CoinGeckoConnector(os.getenv('COINGECKO_API_KEY'))
        self.binance_connector = BinanceConnector(
            os.getenv('BINANCE_API_KEY'),
            os.getenv('BINANCE_SECRET_KEY')
        )
        
        logger.info("DataIngestionManager initialisé")
    
    def ingest_stock_data(self, symbols: List[str]) -> List[MarketData]:
        """Ingestion des données d'actions"""
        logger.info(f"Ingestion des données d'actions pour {len(symbols)} symboles")
        
        all_data = []
        
        # IEX Cloud pour les actions US
        us_symbols = [s for s in symbols if not s.endswith('.TO')]  # Exclure les actions canadiennes
        if us_symbols:
            iex_data = self.iex_connector.get_market_data(us_symbols)
            all_data.extend(iex_data)
        
        return all_data
    
    def ingest_crypto_data(self, symbols: List[str] = None) -> List[MarketData]:
        """Ingestion des données crypto"""
        logger.info("Ingestion des données crypto")
        
        all_data = []
        
        # Si pas de symboles spécifiés, utiliser les top cryptos
        if not symbols:
            symbols = self.coingecko_connector.get_top_cryptos(10)
        
        # CoinGecko pour les données historiques
        for symbol in symbols:
            coingecko_data = self.coingecko_connector.get_crypto_data(symbol, days=1)
            all_data.extend(coingecko_data)
            time.sleep(0.1)  # Rate limiting
        
        # Binance pour les données temps réel (symboles avec USDT)
        binance_symbols = [f"{s.upper()}USDT" for s in symbols if s != 'bitcoin']
        for symbol in binance_symbols:
            try:
                binance_data = self.binance_connector.get_crypto_data(symbol, interval="1h", limit=24)
                all_data.extend(binance_data)
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.warning(f"Impossible de récupérer {symbol} depuis Binance: {e}")
        
        return all_data
    
    def save_to_s3(self, data: List[MarketData], prefix: str = "raw-data"):
        """Sauvegarde les données vers S3"""
        if not data:
            logger.warning("Aucune donnée à sauvegarder")
            return
        
        logger.info(f"Sauvegarde de {len(data)} points de données vers S3")
        
        # Conversion en JSON
        json_data = []
        for item in data:
            json_data.append({
                'symbol': item.symbol,
                'timestamp': item.timestamp,
                'open': item.open,
                'high': item.high,
                'low': item.low,
                'close': item.close,
                'volume': item.volume,
                'source': item.source,
                'market': item.market
            })
        
        # Sauvegarde par source et marché
        for source in set(item.source for item in data):
            for market in set(item.market for item in data):
                source_data = [item for item in json_data if item['source'] == source and item['market'] == market]
                
                if source_data:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    key = f"{prefix}/{source}/{market}/{timestamp}.json"
                    
                    try:
                        self.s3_client.put_object(
                            Bucket=self.s3_bucket,
                            Key=key,
                            Body=json.dumps(source_data, indent=2),
                            ContentType='application/json'
                        )
                        logger.info(f"Données sauvegardées: s3://{self.s3_bucket}/{key}")
                    except Exception as e:
                        logger.error(f"Erreur sauvegarde S3: {e}")
    
    def run_full_ingestion(self, stock_symbols: List[str] = None, crypto_symbols: List[str] = None):
        """Exécute l'ingestion complète multi-sources"""
        logger.info("🚀 Début de l'ingestion multi-sources")
        
        all_data = []
        
        # Ingestion des actions
        if stock_symbols:
            stock_data = self.ingest_stock_data(stock_symbols)
            all_data.extend(stock_data)
        
        # Ingestion des cryptos
        if crypto_symbols:
            crypto_data = self.ingest_crypto_data(crypto_symbols)
            all_data.extend(crypto_data)
        
        # Sauvegarde vers S3
        if all_data:
            self.save_to_s3(all_data)
            
            # Statistiques
            sources = {}
            markets = {}
            for item in all_data:
                sources[item.source] = sources.get(item.source, 0) + 1
                markets[item.market] = markets.get(item.market, 0) + 1
            
            logger.info("📊 Statistiques d'ingestion:")
            logger.info(f"  Total: {len(all_data)} points de données")
            logger.info(f"  Sources: {sources}")
            logger.info(f"  Marchés: {markets}")
        
        logger.info("✅ Ingestion multi-sources terminée")

def main():
    """Fonction principale"""
    logger.info("🚀 Démarrage de l'ingestion multi-sources")
    
    # Configuration par défaut
    stock_symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    crypto_symbols = ['bitcoin', 'ethereum', 'binancecoin', 'cardano', 'solana']
    
    # Arguments de ligne de commande
    if len(sys.argv) > 1:
        if sys.argv[1] == 'stocks':
            crypto_symbols = None
        elif sys.argv[1] == 'crypto':
            stock_symbols = None
        elif sys.argv[1] == 'all':
            pass  # Utiliser les valeurs par défaut
    
    try:
        # Initialisation du gestionnaire
        manager = DataIngestionManager()
        
        # Exécution de l'ingestion
        manager.run_full_ingestion(stock_symbols, crypto_symbols)
        
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}")
        sys.exit(1)
    
    logger.info("🎉 Ingestion multi-sources terminée")

if __name__ == "__main__":
    main()
