#!/usr/bin/env python3
"""
Alpha Vantage Connector for Real-time Financial Data
====================================================

This module provides a robust connector for fetching stock market data from Alpha Vantage API.
Features:
- Real-time stock quotes
- Historical data retrieval
- Technical indicators
- Error handling and retry logic
- Rate limiting compliance
- Data validation and quality checks

Author: Michée Project Team
Date: 2025-04-02
"""

import os
import time
import json
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
import pandas as pd
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataType(Enum):
    """Enumération des types de données supportés"""
    REAL_TIME_QUOTE = "real_time_quote"
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    TECHNICAL_INDICATORS = "technical_indicators"


@dataclass
class AlphaVantageConfig:
    """Configuration pour le connecteur Alpha Vantage"""
    api_key: str
    base_url: str = "https://www.alphavantage.co/query"
    requests_per_minute: int = 5  # Free tier limit
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 60


class AlphaVantageConnector:
    """
    Connecteur principal pour l'API Alpha Vantage
    
    Ce connecteur gère:
    - L'authentification avec l'API
    - Le respect des limites de taux
    - La gestion des erreurs et reprises
    - La validation des données
    - Le stockage en S3
    """
    
    def __init__(self, config: AlphaVantageConfig):
        self.config = config
        self.session = requests.Session()
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_reset_time = 0
        
        # Configuration S3 pour le stockage
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.getenv('DATA_LAKE_BUCKET', 'realtime-financial-data-lake')
        
        logger.info(f"Alpha Vantage Connector initialisé avec API key: {self.config.api_key[:8]}...")
    
    def _enforce_rate_limit(self):
        """Applique les limites de taux de l'API Alpha Vantage"""
        current_time = time.time()
        
        # Reset du compteur de requêtes chaque minute
        if current_time - self.rate_limit_reset_time >= 60:
            self.request_count = 0
            self.rate_limit_reset_time = current_time
        
        # Vérification de la limite de taux
        if self.request_count >= self.config.requests_per_minute:
            sleep_time = 60 - (current_time - self.rate_limit_reset_time)
            if sleep_time > 0:
                logger.info(f"Rate limit atteinte, attente de {sleep_time:.2f} secondes")
                time.sleep(sleep_time)
                self.request_count = 0
                self.rate_limit_reset_time = time.time()
        
        # Délai minimum entre les requêtes
        time_since_last_request = current_time - self.last_request_time
        min_delay = 60 / self.config.requests_per_minute
        
        if time_since_last_request < min_delay:
            sleep_time = min_delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _make_api_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Effectue une requête vers l'API Alpha Vantage avec gestion d'erreur
        
        Args:
            params: Paramètres de la requête
            
        Returns:
            Réponse JSON de l'API
            
        Raises:
            Exception: En cas d'échec après toutes les tentatives
        """
        params['apikey'] = self.config.api_key
        
        for attempt in range(self.config.max_retries):
            try:
                self._enforce_rate_limit()
                
                logger.info(f"Requête Alpha Vantage (tentative {attempt + 1}): {params.get('function', 'unknown')}")
                
                response = self.session.get(
                    self.config.base_url,
                    params=params,
                    timeout=self.config.timeout
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Vérification des erreurs de l'API
                if "Error Message" in data:
                    raise Exception(f"Erreur API Alpha Vantage: {data['Error Message']}")
                
                if "Note" in data:
                    logger.warning(f"Note Alpha Vantage: {data['Note']}")
                    if "API call frequency" in data["Note"]:
                        time.sleep(self.config.retry_delay)
                        continue
                
                logger.info("Requête Alpha Vantage réussie")
                return data
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur de requête (tentative {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    raise
                time.sleep(self.config.retry_delay * (attempt + 1))
            
            except Exception as e:
                logger.error(f"Erreur générale (tentative {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    raise
                time.sleep(self.config.retry_delay * (attempt + 1))
        
        raise Exception("Échec de toutes les tentatives de requête Alpha Vantage")
    
    def get_real_time_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Récupère la cotation en temps réel d'un symbole
        
        Args:
            symbol: Symbole boursier (ex: 'AAPL', 'GOOGL')
            
        Returns:
            Données de cotation en temps réel
        """
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol
        }
        
        data = self._make_api_request(params)
        quote_data = data.get('Global Quote', {})
        
        # Normalisation des données
        normalized_data = {
            'symbol': quote_data.get('01. symbol', symbol),
            'open': float(quote_data.get('02. open', 0)),
            'high': float(quote_data.get('03. high', 0)),
            'low': float(quote_data.get('04. low', 0)),
            'price': float(quote_data.get('05. price', 0)),
            'volume': int(quote_data.get('06. volume', 0)),
            'latest_trading_day': quote_data.get('07. latest trading day', ''),
            'previous_close': float(quote_data.get('08. previous close', 0)),
            'change': float(quote_data.get('09. change', 0)),
            'change_percent': quote_data.get('10. change percent', '').replace('%', ''),
            'timestamp': datetime.utcnow().isoformat(),
            'data_type': DataType.REAL_TIME_QUOTE.value
        }
        
        return normalized_data
    
    def get_intraday_data(self, symbol: str, interval: str = '1min') -> Dict[str, Any]:
        """
        Récupère les données intraday d'un symbole
        
        Args:
            symbol: Symbole boursier
            interval: Intervalle ('1min', '5min', '15min', '30min', '60min')
            
        Returns:
            Données intraday structurées
        """
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': symbol,
            'interval': interval,
            'outputsize': 'compact'
        }
        
        data = self._make_api_request(params)
        meta_data = data.get('Meta Data', {})
        time_series_key = f'Time Series ({interval})'
        time_series = data.get(time_series_key, {})
        
        # Conversion en format standardisé
        normalized_data = {
            'symbol': symbol,
            'interval': interval,
            'last_refreshed': meta_data.get('3. Last Refreshed', ''),
            'timezone': meta_data.get('6. Time Zone', 'US/Eastern'),
            'data_type': DataType.INTRADAY.value,
            'timestamp': datetime.utcnow().isoformat(),
            'data_points': []
        }
        
        for timestamp, values in time_series.items():
            data_point = {
                'timestamp': timestamp,
                'open': float(values.get('1. open', 0)),
                'high': float(values.get('2. high', 0)),
                'low': float(values.get('3. low', 0)),
                'close': float(values.get('4. close', 0)),
                'volume': int(values.get('5. volume', 0))
            }
            normalized_data['data_points'].append(data_point)
        
        return normalized_data
    
    def get_daily_data(self, symbol: str, outputsize: str = 'compact') -> Dict[str, Any]:
        """
        Récupère les données quotidiennes d'un symbole
        
        Args:
            symbol: Symbole boursier
            outputsize: 'compact' (100 derniers jours) ou 'full' (20+ ans)
            
        Returns:
            Données quotidiennes structurées
        """
        params = {
            'function': 'TIME_SERIES_DAILY_ADJUSTED',
            'symbol': symbol,
            'outputsize': outputsize
        }
        
        data = self._make_api_request(params)
        meta_data = data.get('Meta Data', {})
        time_series = data.get('Time Series (Daily)', {})
        
        normalized_data = {
            'symbol': symbol,
            'last_refreshed': meta_data.get('3. Last Refreshed', ''),
            'timezone': meta_data.get('5. Time Zone', 'US/Eastern'),
            'data_type': DataType.DAILY.value,
            'timestamp': datetime.utcnow().isoformat(),
            'data_points': []
        }
        
        for date, values in time_series.items():
            data_point = {
                'date': date,
                'open': float(values.get('1. open', 0)),
                'high': float(values.get('2. high', 0)),
                'low': float(values.get('3. low', 0)),
                'close': float(values.get('4. close', 0)),
                'adjusted_close': float(values.get('5. adjusted close', 0)),
                'volume': int(values.get('6. volume', 0)),
                'dividend_amount': float(values.get('7. dividend amount', 0)),
                'split_coefficient': float(values.get('8. split coefficient', 1))
            }
            normalized_data['data_points'].append(data_point)
        
        return normalized_data
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Valide la qualité des données reçues
        
        Args:
            data: Données à valider
            
        Returns:
            True si les données sont valides
        """
        if not data:
            logger.error("Données vides reçues")
            return False
        
        # Vérifications de base selon le type de données
        data_type = data.get('data_type')
        
        if data_type == DataType.REAL_TIME_QUOTE.value:
            required_fields = ['symbol', 'price', 'volume']
            for field in required_fields:
                if field not in data or data[field] is None:
                    logger.error(f"Champ requis manquant: {field}")
                    return False
                    
            # Vérification des valeurs aberrantes
            if data['price'] <= 0:
                logger.error(f"Prix invalide: {data['price']}")
                return False
        
        elif data_type in [DataType.INTRADAY.value, DataType.DAILY.value]:
            if not data.get('data_points'):
                logger.error("Aucun point de données trouvé")
                return False
        
        logger.info("Validation des données réussie")
        return True
    
    def store_to_s3(self, data: Dict[str, Any], symbol: str) -> str:
        """
        Stocke les données dans S3 avec partitioning intelligent
        
        Args:
            data: Données à stocker
            symbol: Symbole boursier
            
        Returns:
            Clé S3 du fichier stocké
        """
        try:
            # Génération de la clé S3 avec partitioning
            now = datetime.utcnow()
            data_type = data.get('data_type', 'unknown')
            
            s3_key = (
                f"alpha-vantage/"
                f"data_type={data_type}/"
                f"symbol={symbol}/"
                f"year={now.year}/"
                f"month={now.month:02d}/"
                f"day={now.day:02d}/"
                f"hour={now.hour:02d}/"
                f"{symbol}_{data_type}_{now.strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            # Ajout de métadonnées
            data_with_metadata = {
                **data,
                'ingestion_timestamp': now.isoformat(),
                'source': 'alpha_vantage',
                'version': '1.0'
            }
            
            # Upload vers S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(data_with_metadata, indent=2),
                ContentType='application/json',
                Metadata={
                    'symbol': symbol,
                    'data_type': data_type,
                    'timestamp': now.isoformat()
                }
            )
            
            logger.info(f"Données stockées avec succès: s3://{self.bucket_name}/{s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Erreur lors du stockage S3: {e}")
            raise
    
    def fetch_and_store_data(self, symbols: List[str], data_types: List[DataType] = None) -> Dict[str, List[str]]:
        """
        Récupère et stocke les données pour une liste de symboles
        
        Args:
            symbols: Liste des symboles à traiter
            data_types: Types de données à récupérer (par défaut: real-time quotes)
            
        Returns:
            Dictionnaire des clés S3 créées par symbole
        """
        if data_types is None:
            data_types = [DataType.REAL_TIME_QUOTE]
        
        results = {}
        
        for symbol in symbols:
            symbol_results = []
            
            for data_type in data_types:
                try:
                    logger.info(f"Traitement de {symbol} - {data_type.value}")
                    
                    # Récupération des données selon le type
                    if data_type == DataType.REAL_TIME_QUOTE:
                        data = self.get_real_time_quote(symbol)
                    elif data_type == DataType.INTRADAY:
                        data = self.get_intraday_data(symbol)
                    elif data_type == DataType.DAILY:
                        data = self.get_daily_data(symbol)
                    else:
                        logger.warning(f"Type de données non supporté: {data_type}")
                        continue
                    
                    # Validation et stockage
                    if self._validate_data(data):
                        s3_key = self.store_to_s3(data, symbol)
                        symbol_results.append(s3_key)
                    else:
                        logger.error(f"Validation échouée pour {symbol} - {data_type.value}")
                
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de {symbol} - {data_type.value}: {e}")
                    continue
            
            results[symbol] = symbol_results
        
        return results
    
    def get_top_symbols(self) -> List[str]:
        """
        Retourne une liste des symboles les plus populaires pour les tests
        
        Returns:
            Liste des symboles boursiers populaires
        """
        return [
            'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA',
            'META', 'NVDA', 'NFLX', 'ORCL', 'CRM',
            'IBM', 'INTC', 'AMD', 'UBER', 'SNAP'
        ]


def main():
    """
    Fonction principale pour tester le connecteur Alpha Vantage
    """
    # Configuration depuis les variables d'environnement
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        logger.error("ALPHA_VANTAGE_API_KEY non définie dans les variables d'environnement")
        return
    
    config = AlphaVantageConfig(api_key=api_key)
    connector = AlphaVantageConnector(config)
    
    # Test avec quelques symboles populaires
    test_symbols = ['AAPL', 'GOOGL', 'MSFT']
    
    try:
        logger.info("Démarrage du test du connecteur Alpha Vantage")
        
        # Test des quotes en temps réel
        results = connector.fetch_and_store_data(
            symbols=test_symbols,
            data_types=[DataType.REAL_TIME_QUOTE]
        )
        
        logger.info(f"Résultats du test: {results}")
        
        # Statistiques
        total_files = sum(len(files) for files in results.values())
        logger.info(f"Total de {total_files} fichiers créés en S3")
        
    except Exception as e:
        logger.error(f"Erreur lors du test: {e}")
        raise


if __name__ == "__main__":
    main()
