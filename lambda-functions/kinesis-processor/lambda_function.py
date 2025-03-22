#!/usr/bin/env python3
"""
Lambda Function: Kinesis Data Processor
=======================================

Cette fonction Lambda traite les données financières en temps réel
provenant des streams Kinesis et les transforme pour les diriger
vers différents systèmes de stockage et d'analyse.

Fonctionnalités:
- Traitement en temps réel des événements Kinesis
- Validation et nettoyage des données financières
- Calcul d'indicateurs techniques de base
- Détection d'anomalies simples
- Routage vers S3, DynamoDB et autres services
- Génération d'alertes pour événements critiques

Author: Michée Project Team
Date: 2025-03-22
"""

import json
import logging
import base64
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal, InvalidOperation
import uuid

# Configuration du logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clients AWS
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')

# Configuration depuis les variables d'environnement
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'realtime-financial')
S3_BUCKET = os.environ.get('S3_BUCKET', f'{PROJECT_NAME}-{ENVIRONMENT}-data-lake')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', f'{PROJECT_NAME}-{ENVIRONMENT}-processed-data')
SNS_ALERTS_TOPIC = os.environ.get('SNS_ALERTS_TOPIC', '')

# Seuils de détection d'anomalies
PRICE_CHANGE_THRESHOLD = 10.0  # 10% de changement
VOLUME_SPIKE_MULTIPLIER = 5.0   # 5x le volume normal


class DataProcessor:
    """Processeur principal pour les données financières"""
    
    def __init__(self):
        """Initialise le processeur avec les clients AWS"""
        self.s3_bucket = S3_BUCKET
        self.dynamodb_table = dynamodb.Table(DYNAMODB_TABLE) if DYNAMODB_TABLE else None
        self.sns_topic_arn = SNS_ALERTS_TOPIC
        
        # Cache pour les données de référence
        self.reference_cache = {}
        
        logger.info(f"Processeur initialisé - Env: {ENVIRONMENT}, Bucket: {self.s3_bucket}")
    
    def process_kinesis_records(self, kinesis_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Traite les enregistrements Kinesis reçus
        
        Args:
            kinesis_records: Liste des enregistrements Kinesis
            
        Returns:
            Résultats du traitement
        """
        results = {
            'total_records': len(kinesis_records),
            'processed_successfully': 0,
            'processing_errors': 0,
            'anomalies_detected': 0,
            'alerts_sent': 0,
            'records_stored': 0
        }
        
        logger.info(f"Traitement de {len(kinesis_records)} enregistrements Kinesis")
        
        for record in kinesis_records:
            try:
                # Décodage des données Kinesis
                encoded_data = record['kinesis']['data']
                decoded_data = base64.b64decode(encoded_data)
                financial_data = json.loads(decoded_data.decode('utf-8'))
                
                # Traitement des données
                processed_result = self._process_financial_record(financial_data)
                
                if processed_result['success']:
                    results['processed_successfully'] += 1
                    
                    # Stockage des données traitées
                    if processed_result.get('store_s3', True):
                        self._store_to_s3(processed_result['processed_data'])
                        results['records_stored'] += 1
                    
                    # Stockage en DynamoDB pour accès rapide
                    if processed_result.get('store_dynamodb', True):
                        self._store_to_dynamodb(processed_result['processed_data'])
                    
                    # Détection d'anomalies
                    if processed_result.get('anomaly_detected', False):
                        results['anomalies_detected'] += 1
                        
                        # Envoi d'alerte si configuré
                        if self.sns_topic_arn:
                            self._send_anomaly_alert(processed_result['processed_data'])
                            results['alerts_sent'] += 1
                
                else:
                    results['processing_errors'] += 1
                    logger.error(f"Erreur traitement enregistrement: {processed_result.get('error', 'Unknown')}")
                    
            except Exception as e:
                results['processing_errors'] += 1
                logger.error(f"Erreur critique lors du traitement: {str(e)}")
        
        return results
    
    def _process_financial_record(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un enregistrement financier individuel
        
        Args:
            financial_data: Données financières brutes
            
        Returns:
            Résultat du traitement avec données enrichies
        """
        try:
            # Validation de base
            if not self._validate_financial_data(financial_data):
                return {
                    'success': False,
                    'error': 'Invalid financial data structure'
                }
            
            # Extraction des données de base
            symbol = financial_data.get('symbol', '').upper()
            data_type = financial_data.get('data_type', 'unknown')
            
            # Traitement selon le type de données
            if data_type == 'real_time_quote':
                processed_data = self._process_real_time_quote(financial_data)
            elif data_type == 'intraday':
                processed_data = self._process_intraday_data(financial_data)
            elif data_type == 'crypto_quote':
                processed_data = self._process_crypto_data(financial_data)
            else:
                processed_data = self._process_generic_data(financial_data)
            
            # Enrichissement avec métadonnées Lambda
            processed_data['lambda_processing'] = {
                'processed_at': datetime.utcnow().isoformat(),
                'processor_version': '1.0',
                'environment': ENVIRONMENT,
                'processing_id': str(uuid.uuid4())
            }
            
            # Détection d'anomalies
            anomaly_detected = self._detect_anomalies(processed_data)
            
            return {
                'success': True,
                'processed_data': processed_data,
                'anomaly_detected': anomaly_detected,
                'store_s3': True,
                'store_dynamodb': data_type == 'real_time_quote'  # Seulement les quotes temps réel en DynamoDB
            }
            
        except Exception as e:
            logger.error(f"Erreur traitement enregistrement financier: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_financial_data(self, data: Dict[str, Any]) -> bool:
        """Valide la structure des données financières"""
        required_fields = ['symbol', 'timestamp']
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Champ requis manquant: {field}")
                return False
        
        # Validation du symbole
        symbol = data.get('symbol', '')
        if not symbol or len(symbol) > 10:
            logger.warning(f"Symbole invalide: {symbol}")
            return False
        
        return True
    
    def _process_real_time_quote(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Traite une cotation en temps réel"""
        symbol = data.get('symbol', '').upper()
        current_price = float(data.get('price', 0))
        current_volume = int(data.get('volume', 0))
        
        # Calculs dérivés
        processed = {
            **data,
            'symbol': symbol,
            'price': current_price,
            'volume': current_volume,
            'derived_metrics': {}
        }
        
        # Récupération du prix précédent pour calculs
        previous_data = self._get_previous_quote(symbol)
        
        if previous_data and previous_data.get('price'):
            previous_price = float(previous_data['price'])
            price_change = current_price - previous_price
            price_change_percent = (price_change / previous_price) * 100 if previous_price > 0 else 0
            
            processed['derived_metrics'].update({
                'price_change': price_change,
                'price_change_percent': round(price_change_percent, 4),
                'previous_price': previous_price
            })
            
            # Volume comparé à la moyenne
            if previous_data.get('volume'):
                volume_ratio = current_volume / float(previous_data['volume'])
                processed['derived_metrics']['volume_ratio'] = round(volume_ratio, 2)
        
        # Classification de la volatilité
        if 'price_change_percent' in processed['derived_metrics']:
            volatility = abs(processed['derived_metrics']['price_change_percent'])
            if volatility > 5:
                processed['derived_metrics']['volatility_category'] = 'high'
            elif volatility > 2:
                processed['derived_metrics']['volatility_category'] = 'medium'
            else:
                processed['derived_metrics']['volatility_category'] = 'low'
        
        # Indicateurs techniques simples
        processed['technical_indicators'] = self._calculate_basic_indicators(symbol, current_price)
        
        return processed
    
    def _process_intraday_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Traite des données intraday"""
        symbol = data.get('symbol', '').upper()
        data_points = data.get('data_points', [])
        
        processed = {
            **data,
            'symbol': symbol,
            'analysis': {}
        }
        
        if data_points:
            # Calculs statistiques sur les points de données
            closes = [float(point.get('close', 0)) for point in data_points if point.get('close')]
            volumes = [int(point.get('volume', 0)) for point in data_points if point.get('volume')]
            
            if closes:
                processed['analysis'] = {
                    'price_statistics': {
                        'min_price': min(closes),
                        'max_price': max(closes),
                        'avg_price': round(sum(closes) / len(closes), 4),
                        'price_range': max(closes) - min(closes),
                        'data_points_count': len(closes)
                    }
                }
                
                if volumes:
                    processed['analysis']['volume_statistics'] = {
                        'total_volume': sum(volumes),
                        'avg_volume': round(sum(volumes) / len(volumes), 0),
                        'max_volume': max(volumes)
                    }
                
                # Calcul de la tendance
                if len(closes) >= 5:
                    trend = self._calculate_trend(closes)
                    processed['analysis']['trend'] = trend
        
        return processed
    
    def _process_crypto_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Traite des données crypto"""
        # Traitement similaire aux quotes mais avec des spécificités crypto
        processed = self._process_real_time_quote(data)
        
        # Ajout de métadonnées spécifiques crypto
        processed['asset_type'] = 'cryptocurrency'
        
        # Les cryptos sont plus volatiles - ajustement des seuils
        if 'derived_metrics' in processed:
            volatility_percent = abs(processed['derived_metrics'].get('price_change_percent', 0))
            if volatility_percent > 15:
                processed['derived_metrics']['crypto_volatility'] = 'extreme'
            elif volatility_percent > 8:
                processed['derived_metrics']['crypto_volatility'] = 'high'
            elif volatility_percent > 3:
                processed['derived_metrics']['crypto_volatility'] = 'normal'
            else:
                processed['derived_metrics']['crypto_volatility'] = 'low'
        
        return processed
    
    def _process_generic_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Traite des données génériques"""
        return {
            **data,
            'processed_as': 'generic_financial_data',
            'processing_note': 'Processed with minimal transformations'
        }
    
    def _calculate_basic_indicators(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Calcule des indicateurs techniques de base"""
        indicators = {}
        
        # Récupération de l'historique récent (simulé pour l'instant)
        # En production, ceci viendrait d'une base de données
        historical_prices = self._get_historical_prices(symbol, 20)
        
        if historical_prices and len(historical_prices) >= 10:
            prices = [float(p) for p in historical_prices] + [current_price]
            
            # SMA (Simple Moving Average)
            if len(prices) >= 10:
                sma_10 = sum(prices[-10:]) / 10
                indicators['sma_10'] = round(sma_10, 4)
                indicators['price_vs_sma10'] = round(((current_price - sma_10) / sma_10) * 100, 2)
            
            if len(prices) >= 20:
                sma_20 = sum(prices[-20:]) / 20
                indicators['sma_20'] = round(sma_20, 4)
                indicators['price_vs_sma20'] = round(((current_price - sma_20) / sma_20) * 100, 2)
        
        return indicators
    
    def _calculate_trend(self, prices: List[float]) -> str:
        """Calcule la tendance des prix"""
        if len(prices) < 3:
            return 'insufficient_data'
        
        # Comparaison simple du début vs fin
        start_avg = sum(prices[:3]) / 3
        end_avg = sum(prices[-3:]) / 3
        
        change_percent = ((end_avg - start_avg) / start_avg) * 100 if start_avg > 0 else 0
        
        if change_percent > 2:
            return 'uptrend'
        elif change_percent < -2:
            return 'downtrend'
        else:
            return 'sideways'
    
    def _detect_anomalies(self, processed_data: Dict[str, Any]) -> bool:
        """Détecte des anomalies dans les données traitées"""
        anomalies = []
        
        # Vérification changement de prix extrême
        price_change_percent = processed_data.get('derived_metrics', {}).get('price_change_percent', 0)
        if abs(price_change_percent) > PRICE_CHANGE_THRESHOLD:
            anomalies.append(f"extreme_price_change_{price_change_percent:.2f}%")
        
        # Vérification spike de volume
        volume_ratio = processed_data.get('derived_metrics', {}).get('volume_ratio', 1)
        if volume_ratio > VOLUME_SPIKE_MULTIPLIER:
            anomalies.append(f"volume_spike_{volume_ratio:.1f}x")
        
        # Vérification prix négatif ou zéro
        price = processed_data.get('price', 1)
        if price <= 0:
            anomalies.append("invalid_price")
        
        # Ajout des anomalies détectées aux données
        if anomalies:
            processed_data['anomalies_detected'] = anomalies
            logger.warning(f"Anomalies détectées pour {processed_data.get('symbol', 'unknown')}: {anomalies}")
            return True
        
        return False
    
    def _get_previous_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Récupère la cotation précédente (simulé pour l'instant)"""
        # En production, ceci viendrait de DynamoDB ou d'un cache
        # Pour l'instant, retourne des données simulées
        cache_key = f"previous_quote_{symbol}"
        
        if cache_key in self.reference_cache:
            return self.reference_cache[cache_key]
        
        # Simulation de données précédentes
        return {
            'price': 100.0,  # Prix simulé
            'volume': 1000000  # Volume simulé
        }
    
    def _get_historical_prices(self, symbol: str, count: int) -> List[float]:
        """Récupère l'historique des prix (simulé pour l'instant)"""
        # En production, ceci viendrait d'une base de données historique
        # Simulation de prix historiques
        base_price = 100.0
        return [base_price + (i * 0.5) for i in range(count)]
    
    def _store_to_s3(self, processed_data: Dict[str, Any]):
        """Stocke les données traitées en S3"""
        try:
            symbol = processed_data.get('symbol', 'unknown')
            timestamp = datetime.utcnow()
            data_type = processed_data.get('data_type', 'processed')
            
            # Génération de la clé S3 avec partitioning
            s3_key = (
                f"lambda-processed/"
                f"data_type={data_type}/"
                f"symbol={symbol}/"
                f"year={timestamp.year}/"
                f"month={timestamp.month:02d}/"
                f"day={timestamp.day:02d}/"
                f"hour={timestamp.hour:02d}/"
                f"{symbol}_{data_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            # Upload vers S3
            s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=json.dumps(processed_data, indent=2, default=str),
                ContentType='application/json',
                Metadata={
                    'symbol': symbol,
                    'data_type': data_type,
                    'processed_at': timestamp.isoformat(),
                    'processor': 'lambda'
                }
            )
            
            logger.debug(f"Données stockées en S3: {s3_key}")
            
        except Exception as e:
            logger.error(f"Erreur stockage S3: {str(e)}")
            raise
    
    def _store_to_dynamodb(self, processed_data: Dict[str, Any]):
        """Stocke les données en DynamoDB pour accès rapide"""
        if not self.dynamodb_table:
            return
        
        try:
            symbol = processed_data.get('symbol', 'unknown')
            timestamp = processed_data.get('timestamp', datetime.utcnow().isoformat())
            
            # Préparation de l'item DynamoDB
            dynamodb_item = {
                'symbol': symbol,
                'timestamp': timestamp,
                'price': Decimal(str(processed_data.get('price', 0))),
                'volume': processed_data.get('volume', 0),
                'data_type': processed_data.get('data_type', 'unknown'),
                'processed_at': datetime.utcnow().isoformat(),
                'ttl': int((datetime.utcnow() + timedelta(days=7)).timestamp())  # TTL de 7 jours
            }
            
            # Ajout des métriques dérivées si disponibles
            derived_metrics = processed_data.get('derived_metrics', {})
            if derived_metrics:
                for key, value in derived_metrics.items():
                    if isinstance(value, (int, float)):
                        dynamodb_item[f"metric_{key}"] = Decimal(str(value))
                    else:
                        dynamodb_item[f"metric_{key}"] = str(value)
            
            # Insertion en DynamoDB
            self.dynamodb_table.put_item(Item=dynamodb_item)
            
            logger.debug(f"Données stockées en DynamoDB: {symbol}")
            
        except Exception as e:
            logger.error(f"Erreur stockage DynamoDB: {str(e)}")
            # Ne pas faire échouer le traitement pour une erreur DynamoDB
    
    def _send_anomaly_alert(self, processed_data: Dict[str, Any]):
        """Envoie une alerte SNS pour les anomalies détectées"""
        try:
            symbol = processed_data.get('symbol', 'unknown')
            anomalies = processed_data.get('anomalies_detected', [])
            
            alert_message = {
                'alert_type': 'financial_anomaly',
                'symbol': symbol,
                'anomalies': anomalies,
                'current_data': {
                    'price': processed_data.get('price'),
                    'volume': processed_data.get('volume'),
                    'timestamp': processed_data.get('timestamp')
                },
                'derived_metrics': processed_data.get('derived_metrics', {}),
                'detected_at': datetime.utcnow().isoformat(),
                'environment': ENVIRONMENT
            }
            
            sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Message=json.dumps(alert_message, indent=2, default=str),
                Subject=f"Anomalie financière détectée: {symbol}",
                MessageAttributes={
                    'symbol': {
                        'DataType': 'String',
                        'StringValue': symbol
                    },
                    'anomaly_count': {
                        'DataType': 'Number',
                        'StringValue': str(len(anomalies))
                    }
                }
            )
            
            logger.info(f"Alerte SNS envoyée pour {symbol}: {anomalies}")
            
        except Exception as e:
            logger.error(f"Erreur envoi alerte SNS: {str(e)}")


def lambda_handler(event, context):
    """
    Handler principal de la fonction Lambda
    
    Args:
        event: Événement Kinesis contenant les enregistrements
        context: Contexte d'exécution Lambda
        
    Returns:
        Résultats du traitement
    """
    logger.info(f"Début traitement Lambda - Records: {len(event.get('Records', []))}")
    
    try:
        # Initialisation du processeur
        processor = DataProcessor()
        
        # Traitement des enregistrements Kinesis
        kinesis_records = event.get('Records', [])
        results = processor.process_kinesis_records(kinesis_records)
        
        # Logging des résultats
        logger.info(f"Traitement terminé: {results}")
        
        # Métriques CloudWatch (optionnel)
        if results['anomalies_detected'] > 0:
            logger.warning(f"⚠️ {results['anomalies_detected']} anomalies détectées dans ce batch")
        
        success_rate = (results['processed_successfully'] / results['total_records']) * 100 if results['total_records'] > 0 else 0
        logger.info(f"Taux de succès: {success_rate:.1f}%")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing completed successfully',
                'results': results,
                'success_rate': f"{success_rate:.1f}%"
            })
        }
        
    except Exception as e:
        logger.error(f"Erreur critique dans Lambda handler: {str(e)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Processing failed',
                'message': str(e)
            })
        }


# Pour les tests locaux
if __name__ == "__main__":
    # Simulation d'un événement Kinesis pour test
    test_event = {
        "Records": [
            {
                "kinesis": {
                    "data": base64.b64encode(json.dumps({
                        "symbol": "AAPL",
                        "price": 150.25,
                        "volume": 1000000,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data_type": "real_time_quote"
                    }).encode()).decode(),
                    "partitionKey": "symbol_AAPL",
                    "sequenceNumber": "12345"
                }
            }
        ]
    }
    
    # Test du handler
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
