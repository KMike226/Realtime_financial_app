"""
Fonction Lambda de transformation pour Kinesis Firehose
======================================================

Cette fonction Lambda traite les données en transit dans Kinesis Firehose
pour enrichir, valider et transformer les données financières avant stockage.

Transformations appliquées:
- Validation et nettoyage des données
- Enrichissement avec métadonnées
- Formatage uniforme JSON
- Détection d'anomalies de base

Author: Michée Project Team
"""

import json
import base64
import logging
import os
from datetime import datetime
from typing import Dict, List, Any

# Configuration du logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Variables d'environnement
PROJECT_NAME = os.environ.get('PROJECT_NAME', '${project_name}')
ENVIRONMENT = os.environ.get('ENVIRONMENT', '${environment}')


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Handler principal de la fonction Lambda
    
    Args:
        event: Événement Kinesis Firehose
        context: Contexte Lambda
        
    Returns:
        Réponse avec les enregistrements transformés
    """
    logger.info(f"Traitement de {len(event.get('records', []))} enregistrements")
    
    output_records = []
    
    for record in event.get('records', []):
        try:
            # Décodage des données
            payload = base64.b64decode(record['data'])
            data = json.loads(payload.decode('utf-8'))
            
            # Transformation des données
            transformed_data = transform_financial_data(data)
            
            # Validation des données transformées
            if validate_transformed_data(transformed_data):
                # Encodage des données transformées
                output_data = json.dumps(transformed_data, separators=(',', ':'))
                output_record = {
                    'recordId': record['recordId'],
                    'result': 'Ok',
                    'data': base64.b64encode(output_data.encode('utf-8')).decode('utf-8')
                }
            else:
                # Données invalides - marquage pour erreur
                logger.warning(f"Données invalides détectées: {record['recordId']}")
                output_record = {
                    'recordId': record['recordId'],
                    'result': 'ProcessingFailed'
                }
                
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'enregistrement {record['recordId']}: {str(e)}")
            output_record = {
                'recordId': record['recordId'],
                'result': 'ProcessingFailed'
            }
        
        output_records.append(output_record)
    
    logger.info(f"Transformation terminée: {len(output_records)} enregistrements traités")
    
    return {
        'records': output_records
    }


def transform_financial_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforme et enrichit les données financières
    
    Args:
        data: Données financières brutes
        
    Returns:
        Données transformées et enrichies
    """
    current_time = datetime.utcnow().isoformat()
    
    # Structure de base enrichie
    transformed = {
        # Métadonnées système
        'processing_timestamp': current_time,
        'processor': 'kinesis-firehose-lambda',
        'version': '1.0',
        'project': PROJECT_NAME,
        'environment': ENVIRONMENT,
        
        # Données originales préservées
        'original_data': data,
        
        # Données enrichies
        'enriched': {}
    }
    
    # Enrichissement selon le type de données
    data_type = data.get('data_type', 'unknown')
    
    if data_type == 'real_time_quote':
        transformed['enriched'] = enrich_real_time_quote(data)
    elif data_type == 'intraday':
        transformed['enriched'] = enrich_intraday_data(data)
    elif data_type == 'daily':
        transformed['enriched'] = enrich_daily_data(data)
    else:
        # Type de données non reconnu
        transformed['enriched'] = {
            'status': 'unknown_data_type',
            'warning': f"Type de données non reconnu: {data_type}"
        }
    
    return transformed


def enrich_real_time_quote(data: Dict[str, Any]) -> Dict[str, Any]:
    """Enrichit les données de cotation temps réel"""
    enriched = {
        'data_type': 'real_time_quote',
        'symbol': data.get('symbol', '').upper(),
        'market_data': {
            'price': float(data.get('price', 0)),
            'volume': int(data.get('volume', 0)),
            'change': float(data.get('change', 0)),
            'change_percent': parse_change_percent(data.get('change_percent', '0%'))
        }
    }
    
    # Calculs dérivés
    price = enriched['market_data']['price']
    change = enriched['market_data']['change']
    
    if price > 0:
        enriched['market_data']['previous_close'] = price - change
        enriched['derived_metrics'] = {
            'price_volatility_indicator': abs(change / price) * 100,
            'volume_normalized': enriched['market_data']['volume'] / 1000000,  # En millions
            'market_cap_tier': classify_market_cap_tier(price)
        }
    
    # Détection d'anomalies de base
    enriched['anomaly_flags'] = detect_quote_anomalies(enriched['market_data'])
    
    return enriched


def enrich_intraday_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Enrichit les données intraday"""
    enriched = {
        'data_type': 'intraday',
        'symbol': data.get('symbol', '').upper(),
        'interval': data.get('interval', 'unknown'),
        'data_points_count': len(data.get('data_points', []))
    }
    
    # Analyse des points de données
    data_points = data.get('data_points', [])
    if data_points:
        prices = [float(point.get('close', 0)) for point in data_points if point.get('close')]
        
        if prices:
            enriched['summary_statistics'] = {
                'min_price': min(prices),
                'max_price': max(prices),
                'avg_price': sum(prices) / len(prices),
                'price_range': max(prices) - min(prices),
                'total_volume': sum(int(point.get('volume', 0)) for point in data_points)
            }
    
    return enriched


def enrich_daily_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Enrichit les données quotidiennes"""
    enriched = {
        'data_type': 'daily',
        'symbol': data.get('symbol', '').upper(),
        'data_points_count': len(data.get('data_points', []))
    }
    
    # Analyse des données historiques
    data_points = data.get('data_points', [])
    if data_points:
        # Calcul de métriques techniques de base
        closes = [float(point.get('close', 0)) for point in data_points if point.get('close')]
        
        if len(closes) >= 20:  # Assez de données pour des calculs meaningfuls
            enriched['technical_indicators'] = {
                'sma_20': calculate_sma(closes, 20),
                'volatility': calculate_volatility(closes),
                'trend_direction': determine_trend(closes)
            }
    
    return enriched


def validate_transformed_data(data: Dict[str, Any]) -> bool:
    """
    Valide les données transformées
    
    Args:
        data: Données transformées
        
    Returns:
        True si les données sont valides
    """
    try:
        # Vérifications de base
        required_fields = ['processing_timestamp', 'processor', 'original_data', 'enriched']
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Champ requis manquant: {field}")
                return False
        
        # Validation des données originales
        original = data.get('original_data', {})
        if not original.get('symbol'):
            logger.warning("Symbole manquant dans les données originales")
            return False
        
        # Validation des données enrichies
        enriched = data.get('enriched', {})
        if not enriched:
            logger.warning("Données enrichies vides")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation: {str(e)}")
        return False


def parse_change_percent(change_percent_str: str) -> float:
    """Parse le pourcentage de changement"""
    try:
        return float(change_percent_str.replace('%', ''))
    except (ValueError, AttributeError):
        return 0.0


def classify_market_cap_tier(price: float) -> str:
    """Classifie grossièrement par taille de marché basé sur le prix"""
    if price < 10:
        return "small_cap_indicator"
    elif price < 100:
        return "mid_cap_indicator"
    else:
        return "large_cap_indicator"


def detect_quote_anomalies(market_data: Dict[str, Any]) -> List[str]:
    """Détecte des anomalies de base dans les cotations"""
    anomalies = []
    
    price = market_data.get('price', 0)
    volume = market_data.get('volume', 0)
    change_percent = market_data.get('change_percent', 0)
    
    # Détections d'anomalies simples
    if price <= 0:
        anomalies.append("negative_or_zero_price")
    
    if volume < 0:
        anomalies.append("negative_volume")
    
    if abs(change_percent) > 50:  # Changement de plus de 50%
        anomalies.append("extreme_price_movement")
    
    if volume == 0:
        anomalies.append("zero_volume")
    
    return anomalies


def calculate_sma(prices: List[float], period: int) -> float:
    """Calcule la moyenne mobile simple"""
    if len(prices) >= period:
        return sum(prices[-period:]) / period
    return 0.0


def calculate_volatility(prices: List[float]) -> float:
    """Calcule la volatilité des prix (écart-type)"""
    if len(prices) < 2:
        return 0.0
    
    mean = sum(prices) / len(prices)
    variance = sum((price - mean) ** 2 for price in prices) / (len(prices) - 1)
    return variance ** 0.5


def determine_trend(prices: List[float]) -> str:
    """Détermine la tendance des prix"""
    if len(prices) < 5:
        return "insufficient_data"
    
    recent_avg = sum(prices[-5:]) / 5
    older_avg = sum(prices[-10:-5]) / 5 if len(prices) >= 10 else sum(prices[:-5]) / max(1, len(prices) - 5)
    
    if recent_avg > older_avg * 1.02:
        return "uptrend"
    elif recent_avg < older_avg * 0.98:
        return "downtrend"
    else:
        return "sideways"
