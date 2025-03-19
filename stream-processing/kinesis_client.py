#!/usr/bin/env python3
"""
Client Kinesis pour ingestion de données financières temps réel
===============================================================

Ce module fournit une interface simplifiée pour envoyer des données
vers les streams Kinesis configurés pour le projet.

Fonctionnalités:
- Envoi vers multiple streams (financial, crypto, events)
- Batching automatique pour optimiser les performances
- Retry logic et gestion d'erreurs
- Monitoring et métriques
- Support partitioning intelligent

Author: Michée Project Team
Date: 2025-03-19
"""

import json
import time
import logging
import hashlib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import boto3
from botocore.exceptions import ClientError, BotoCoreError
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StreamType(Enum):
    """Types de streams Kinesis disponibles"""
    FINANCIAL = "financial"
    CRYPTO = "crypto"
    EVENTS = "events"


@dataclass
class KinesisConfig:
    """Configuration pour le client Kinesis"""
    region: str = "us-east-1"
    financial_stream: str = "realtime-financial-dev-financial-stream"
    crypto_stream: str = "realtime-financial-dev-crypto-stream"
    events_stream: str = "realtime-financial-dev-events-stream"
    batch_size: int = 500  # Limite AWS Kinesis
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_metrics: bool = True


class KinesisClient:
    """
    Client Kinesis avancé pour données financières
    
    Ce client gère l'envoi de données vers multiple streams Kinesis
    avec optimisations pour les performances et la fiabilité.
    """
    
    def __init__(self, config: KinesisConfig):
        self.config = config
        self.client = boto3.client('kinesis', region_name=config.region)
        
        # Métriques internes
        self.metrics = {
            'records_sent': 0,
            'records_failed': 0,
            'batches_sent': 0,
            'last_send_time': None,
            'total_bytes_sent': 0,
            'average_latency': 0.0
        }
        
        # Cache pour les informations de streams
        self.stream_info_cache = {}
        
        logger.info(f"Client Kinesis initialisé - Région: {config.region}")
        
        # Validation des streams au démarrage
        self._validate_streams()
    
    def _validate_streams(self):
        """Valide que tous les streams configurés existent"""
        streams_to_check = {
            StreamType.FINANCIAL: self.config.financial_stream,
            StreamType.CRYPTO: self.config.crypto_stream,
            StreamType.EVENTS: self.config.events_stream
        }
        
        for stream_type, stream_name in streams_to_check.items():
            try:
                response = self.client.describe_stream(StreamName=stream_name)
                stream_status = response['StreamDescription']['StreamStatus']
                
                if stream_status == 'ACTIVE':
                    self.stream_info_cache[stream_type] = {
                        'name': stream_name,
                        'shards': len(response['StreamDescription']['Shards']),
                        'status': stream_status
                    }
                    logger.info(f"Stream {stream_type.value} validé: {stream_name}")
                else:
                    logger.warning(f"Stream {stream_name} n'est pas actif: {stream_status}")
                    
            except ClientError as e:
                logger.error(f"Erreur lors de la validation du stream {stream_name}: {e}")
                raise
    
    def send_financial_data(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], 
                          partition_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Envoie des données financières vers le stream principal
        
        Args:
            data: Données à envoyer (dict unique ou liste)
            partition_key: Clé de partitioning (optionnel, auto-généré sinon)
            
        Returns:
            Résultats de l'envoi
        """
        return self._send_to_stream(
            stream_type=StreamType.FINANCIAL,
            data=data,
            partition_key=partition_key
        )
    
    def send_crypto_data(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], 
                        partition_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Envoie des données crypto vers le stream dédié
        
        Args:
            data: Données crypto à envoyer
            partition_key: Clé de partitioning (optionnel)
            
        Returns:
            Résultats de l'envoi
        """
        return self._send_to_stream(
            stream_type=StreamType.CRYPTO,
            data=data,
            partition_key=partition_key
        )
    
    def send_event_data(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], 
                       partition_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Envoie des événements vers le stream d'événements
        
        Args:
            data: Données d'événement à envoyer
            partition_key: Clé de partitioning (optionnel)
            
        Returns:
            Résultats de l'envoi
        """
        return self._send_to_stream(
            stream_type=StreamType.EVENTS,
            data=data,
            partition_key=partition_key
        )
    
    def _send_to_stream(self, stream_type: StreamType, 
                       data: Union[Dict[str, Any], List[Dict[str, Any]]],
                       partition_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Envoie des données vers un stream Kinesis spécifique
        
        Args:
            stream_type: Type de stream cible
            data: Données à envoyer
            partition_key: Clé de partitioning
            
        Returns:
            Résultats détaillés de l'envoi
        """
        start_time = time.time()
        
        # Normalisation des données en liste
        if isinstance(data, dict):
            data_list = [data]
        else:
            data_list = data
        
        # Validation et enrichissement des données
        enriched_data = self._enrich_data(data_list, stream_type)
        
        # Division en batches si nécessaire
        batches = self._create_batches(enriched_data)
        
        # Envoi des batches
        results = self._send_batches(stream_type, batches, partition_key)
        
        # Mise à jour des métriques
        execution_time = time.time() - start_time
        self._update_metrics(results, execution_time)
        
        return results
    
    def _enrich_data(self, data_list: List[Dict[str, Any]], 
                    stream_type: StreamType) -> List[Dict[str, Any]]:
        """Enrichit les données avec des métadonnées system"""
        enriched = []
        current_time = datetime.utcnow().isoformat()
        
        for data in data_list:
            enriched_record = {
                **data,
                'kinesis_metadata': {
                    'ingestion_timestamp': current_time,
                    'stream_type': stream_type.value,
                    'client_version': '1.0',
                    'source_system': 'kinesis-client'
                }
            }
            enriched.append(enriched_record)
        
        return enriched
    
    def _create_batches(self, data_list: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Divise les données en batches selon la limite Kinesis"""
        batches = []
        current_batch = []
        
        for record in data_list:
            current_batch.append(record)
            
            if len(current_batch) >= self.config.batch_size:
                batches.append(current_batch)
                current_batch = []
        
        # Ajouter le batch restant s'il y en a un
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _send_batches(self, stream_type: StreamType, 
                     batches: List[List[Dict[str, Any]]], 
                     partition_key: Optional[str] = None) -> Dict[str, Any]:
        """Envoie les batches vers Kinesis avec retry logic"""
        stream_name = self._get_stream_name(stream_type)
        total_records = sum(len(batch) for batch in batches)
        successful_records = 0
        failed_records = 0
        
        logger.info(f"Envoi de {total_records} enregistrements en {len(batches)} batches vers {stream_name}")
        
        for batch_idx, batch in enumerate(batches):
            for attempt in range(self.config.max_retries):
                try:
                    # Préparation des enregistrements pour Kinesis
                    kinesis_records = []
                    
                    for record in batch:
                        record_data = json.dumps(record, separators=(',', ':'))
                        
                        # Génération de la clé de partition
                        if partition_key:
                            pkey = partition_key
                        else:
                            pkey = self._generate_partition_key(record, stream_type)
                        
                        kinesis_records.append({
                            'Data': record_data,
                            'PartitionKey': pkey
                        })
                    
                    # Envoi vers Kinesis
                    response = self.client.put_records(
                        Records=kinesis_records,
                        StreamName=stream_name
                    )
                    
                    # Analyse des résultats
                    failed_count = response.get('FailedRecordCount', 0)
                    successful_count = len(batch) - failed_count
                    
                    successful_records += successful_count
                    failed_records += failed_count
                    
                    if failed_count > 0:
                        logger.warning(f"Batch {batch_idx + 1}: {failed_count} enregistrements échoués")
                        
                        # Log des erreurs spécifiques
                        for i, record_result in enumerate(response.get('Records', [])):
                            if 'ErrorCode' in record_result:
                                logger.error(f"Erreur enregistrement {i}: {record_result.get('ErrorCode')} - {record_result.get('ErrorMessage')}")
                    else:
                        logger.debug(f"Batch {batch_idx + 1}: {successful_count} enregistrements envoyés avec succès")
                    
                    break  # Succès - sortir de la boucle de retry
                    
                except (ClientError, BotoCoreError) as e:
                    logger.error(f"Erreur lors de l'envoi du batch {batch_idx + 1} (tentative {attempt + 1}): {e}")
                    
                    if attempt == self.config.max_retries - 1:
                        # Dernière tentative échouée
                        failed_records += len(batch)
                        logger.error(f"Échec définitif du batch {batch_idx + 1} après {self.config.max_retries} tentatives")
                    else:
                        # Attendre avant retry
                        time.sleep(self.config.retry_delay * (attempt + 1))
        
        results = {
            'total_records': total_records,
            'successful_records': successful_records,
            'failed_records': failed_records,
            'success_rate': (successful_records / total_records * 100) if total_records > 0 else 0,
            'batches_sent': len(batches),
            'stream_name': stream_name,
            'stream_type': stream_type.value
        }
        
        logger.info(f"Envoi terminé: {successful_records}/{total_records} enregistrements réussis ({results['success_rate']:.1f}%)")
        
        return results
    
    def _generate_partition_key(self, record: Dict[str, Any], stream_type: StreamType) -> str:
        """Génère une clé de partition intelligente selon le type de données"""
        
        # Extraction du symbole ou identifiant principal
        symbol = record.get('symbol', record.get('asset', 'unknown'))
        
        if stream_type == StreamType.FINANCIAL:
            # Partitioning par symbole pour une distribution équilibrée
            return f"symbol_{symbol}_{hash(symbol) % 100:02d}"
        
        elif stream_type == StreamType.CRYPTO:
            # Partitioning par crypto avec dispersion temporelle
            timestamp_hash = hash(datetime.utcnow().strftime('%Y%m%d%H%M'))
            return f"crypto_{symbol}_{timestamp_hash % 100:02d}"
        
        elif stream_type == StreamType.EVENTS:
            # Partitioning par type d'événement
            event_type = record.get('event_type', 'general')
            return f"event_{event_type}_{hash(event_type) % 10:01d}"
        
        else:
            # Fallback générique
            return f"data_{hash(str(record)) % 100:02d}"
    
    def _get_stream_name(self, stream_type: StreamType) -> str:
        """Retourne le nom du stream selon le type"""
        stream_mapping = {
            StreamType.FINANCIAL: self.config.financial_stream,
            StreamType.CRYPTO: self.config.crypto_stream,
            StreamType.EVENTS: self.config.events_stream
        }
        return stream_mapping[stream_type]
    
    def _update_metrics(self, results: Dict[str, Any], execution_time: float):
        """Met à jour les métriques internes"""
        self.metrics['records_sent'] += results['successful_records']
        self.metrics['records_failed'] += results['failed_records']
        self.metrics['batches_sent'] += results['batches_sent']
        self.metrics['last_send_time'] = datetime.utcnow().isoformat()
        
        # Calcul de la latence moyenne (moyenne mobile)
        if self.metrics['average_latency'] == 0:
            self.metrics['average_latency'] = execution_time
        else:
            self.metrics['average_latency'] = (self.metrics['average_latency'] * 0.8) + (execution_time * 0.2)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de performance du client"""
        total_records = self.metrics['records_sent'] + self.metrics['records_failed']
        success_rate = (self.metrics['records_sent'] / total_records * 100) if total_records > 0 else 0
        
        return {
            **self.metrics,
            'total_records_processed': total_records,
            'overall_success_rate': success_rate,
            'streams_info': self.stream_info_cache
        }
    
    def get_stream_info(self, stream_type: StreamType) -> Dict[str, Any]:
        """Retourne les informations sur un stream spécifique"""
        if stream_type in self.stream_info_cache:
            return self.stream_info_cache[stream_type]
        else:
            logger.warning(f"Aucune information cachée pour le stream {stream_type.value}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """Effectue un health check des streams Kinesis"""
        health_status = {
            'overall_status': 'healthy',
            'streams': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for stream_type in StreamType:
            try:
                stream_name = self._get_stream_name(stream_type)
                response = self.client.describe_stream(StreamName=stream_name)
                stream_status = response['StreamDescription']['StreamStatus']
                
                health_status['streams'][stream_type.value] = {
                    'name': stream_name,
                    'status': stream_status,
                    'healthy': stream_status == 'ACTIVE'
                }
                
                if stream_status != 'ACTIVE':
                    health_status['overall_status'] = 'degraded'
                    
            except Exception as e:
                health_status['streams'][stream_type.value] = {
                    'name': self._get_stream_name(stream_type),
                    'status': 'error',
                    'error': str(e),
                    'healthy': False
                }
                health_status['overall_status'] = 'unhealthy'
        
        return health_status


def create_kinesis_client(environment: str = "dev", region: str = "us-east-1") -> KinesisClient:
    """
    Factory function pour créer un client Kinesis configuré
    
    Args:
        environment: Environnement (dev, staging, prod)
        region: Région AWS
        
    Returns:
        Instance configurée du client Kinesis
    """
    config = KinesisConfig(
        region=region,
        financial_stream=f"realtime-financial-{environment}-financial-stream",
        crypto_stream=f"realtime-financial-{environment}-crypto-stream",
        events_stream=f"realtime-financial-{environment}-events-stream"
    )
    
    return KinesisClient(config)


def main():
    """Fonction de test du client Kinesis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test du client Kinesis')
    parser.add_argument('--env', default='dev', help='Environnement (dev, staging, prod)')
    parser.add_argument('--test-type', choices=['financial', 'crypto', 'events', 'all'], 
                       default='financial', help='Type de test à effectuer')
    
    args = parser.parse_args()
    
    try:
        # Création du client
        client = create_kinesis_client(environment=args.env)
        
        # Health check
        health = client.health_check()
        logger.info(f"Health check: {health}")
        
        # Données de test
        test_financial_data = {
            'symbol': 'AAPL',
            'price': 150.25,
            'volume': 1000000,
            'timestamp': datetime.utcnow().isoformat(),
            'data_type': 'real_time_quote'
        }
        
        test_crypto_data = {
            'symbol': 'BTC',
            'price': 45000.50,
            'volume': 50000,
            'timestamp': datetime.utcnow().isoformat(),
            'data_type': 'crypto_quote'
        }
        
        test_event_data = {
            'event_type': 'price_alert',
            'symbol': 'TSLA',
            'message': 'Prix dépassé seuil',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Tests selon le type demandé
        if args.test_type in ['financial', 'all']:
            logger.info("Test d'envoi de données financières...")
            result = client.send_financial_data(test_financial_data)
            logger.info(f"Résultat financier: {result}")
        
        if args.test_type in ['crypto', 'all']:
            logger.info("Test d'envoi de données crypto...")
            result = client.send_crypto_data(test_crypto_data)
            logger.info(f"Résultat crypto: {result}")
        
        if args.test_type in ['events', 'all']:
            logger.info("Test d'envoi d'événements...")
            result = client.send_event_data(test_event_data)
            logger.info(f"Résultat événements: {result}")
        
        # Affichage des métriques finales
        metrics = client.get_metrics()
        logger.info(f"Métriques finales: {metrics}")
        
    except Exception as e:
        logger.error(f"Erreur lors du test: {e}")
        raise


if __name__ == "__main__":
    main()
