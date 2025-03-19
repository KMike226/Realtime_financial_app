#!/usr/bin/env python3
"""
Intégration Alpha Vantage → Kinesis
===================================

Ce script intègre le connecteur Alpha Vantage avec Kinesis pour
envoyer les données financières en temps réel vers les streams configurés.

Workflow:
1. Récupération données Alpha Vantage
2. Validation et enrichissement
3. Envoi vers Kinesis streams appropriés
4. Monitoring et logging

Author: Michée Project Team
Date: 2025-04-02
"""

import sys
import os
import logging
import time
from typing import Dict, List, Any
from datetime import datetime
import json

# Ajout du chemin pour importer les modules du projet
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data-ingestion'))

from connectors.alpha_vantage_connector import AlphaVantageConnector, AlphaVantageConfig, DataType
from kinesis_client import KinesisClient, StreamType, create_kinesis_client

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlphaVantageKinesisIntegration:
    """
    Intégration Alpha Vantage → Kinesis
    
    Cette classe orchestre la récupération de données depuis Alpha Vantage
    et leur envoi vers les streams Kinesis appropriés.
    """
    
    def __init__(self, alpha_vantage_api_key: str, environment: str = "dev"):
        """
        Initialise l'intégration
        
        Args:
            alpha_vantage_api_key: Clé API Alpha Vantage
            environment: Environnement (dev, staging, prod)
        """
        self.environment = environment
        
        # Configuration Alpha Vantage
        alpha_config = AlphaVantageConfig(api_key=alpha_vantage_api_key)
        self.alpha_connector = AlphaVantageConnector(alpha_config)
        
        # Configuration Kinesis
        self.kinesis_client = create_kinesis_client(environment=environment)
        
        # Métriques d'intégration
        self.integration_metrics = {
            'total_data_fetched': 0,
            'total_data_sent': 0,
            'errors_count': 0,
            'last_execution': None,
            'processing_time': 0.0
        }
        
        logger.info(f"Intégration Alpha Vantage → Kinesis initialisée (env: {environment})")
    
    def process_real_time_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Traite les cotations en temps réel et les envoie vers Kinesis
        
        Args:
            symbols: Liste des symboles à traiter
            
        Returns:
            Résultats du traitement
        """
        start_time = time.time()
        logger.info(f"Traitement des cotations temps réel pour {len(symbols)} symboles")
        
        results = {
            'symbols_processed': 0,
            'symbols_failed': 0,
            'kinesis_results': [],
            'errors': []
        }
        
        for symbol in symbols:
            try:
                # Récupération des données Alpha Vantage
                logger.debug(f"Récupération cotation pour {symbol}")
                quote_data = self.alpha_connector.get_real_time_quote(symbol)
                
                # Validation des données
                if self._validate_quote_data(quote_data):
                    # Enrichissement pour Kinesis
                    enriched_data = self._enrich_for_kinesis(quote_data, 'real_time_quote')
                    
                    # Envoi vers Kinesis
                    kinesis_result = self.kinesis_client.send_financial_data(
                        data=enriched_data,
                        partition_key=f"symbol_{symbol}"
                    )
                    
                    results['kinesis_results'].append(kinesis_result)
                    results['symbols_processed'] += 1
                    
                    logger.debug(f"Cotation {symbol} envoyée vers Kinesis avec succès")
                    
                else:
                    logger.warning(f"Données invalides pour {symbol}, ignoré")
                    results['symbols_failed'] += 1
                    
            except Exception as e:
                error_msg = f"Erreur lors du traitement de {symbol}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                results['symbols_failed'] += 1
        
        # Mise à jour des métriques
        processing_time = time.time() - start_time
        self._update_integration_metrics(results, processing_time)
        
        logger.info(f"Traitement terminé: {results['symbols_processed']}/{len(symbols)} symboles traités en {processing_time:.2f}s")
        
        return results
    
    def process_intraday_data(self, symbols: List[str], interval: str = '1min') -> Dict[str, Any]:
        """
        Traite les données intraday et les envoie vers Kinesis
        
        Args:
            symbols: Liste des symboles à traiter
            interval: Intervalle des données intraday
            
        Returns:
            Résultats du traitement
        """
        start_time = time.time()
        logger.info(f"Traitement des données intraday pour {len(symbols)} symboles (interval: {interval})")
        
        results = {
            'symbols_processed': 0,
            'symbols_failed': 0,
            'total_data_points': 0,
            'kinesis_results': [],
            'errors': []
        }
        
        for symbol in symbols:
            try:
                # Récupération des données intraday
                logger.debug(f"Récupération données intraday pour {symbol}")
                intraday_data = self.alpha_connector.get_intraday_data(symbol, interval)
                
                # Validation des données
                if self._validate_intraday_data(intraday_data):
                    # Les données intraday contiennent plusieurs points
                    # On les envoie par batch pour optimiser
                    data_points = intraday_data.get('data_points', [])
                    
                    if data_points:
                        # Enrichissement des données
                        enriched_data = self._enrich_for_kinesis(intraday_data, 'intraday')
                        
                        # Envoi vers Kinesis
                        kinesis_result = self.kinesis_client.send_financial_data(
                            data=enriched_data,
                            partition_key=f"intraday_{symbol}_{interval}"
                        )
                        
                        results['kinesis_results'].append(kinesis_result)
                        results['symbols_processed'] += 1
                        results['total_data_points'] += len(data_points)
                        
                        logger.debug(f"Données intraday {symbol} envoyées ({len(data_points)} points)")
                    else:
                        logger.warning(f"Aucun point de données intraday pour {symbol}")
                        results['symbols_failed'] += 1
                else:
                    logger.warning(f"Données intraday invalides pour {symbol}")
                    results['symbols_failed'] += 1
                    
            except Exception as e:
                error_msg = f"Erreur intraday pour {symbol}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                results['symbols_failed'] += 1
        
        # Métriques
        processing_time = time.time() - start_time
        self._update_integration_metrics(results, processing_time)
        
        logger.info(f"Traitement intraday terminé: {results['symbols_processed']}/{len(symbols)} symboles, {results['total_data_points']} points de données")
        
        return results
    
    def process_mixed_batch(self, financial_symbols: List[str], 
                          crypto_symbols: List[str] = None) -> Dict[str, Any]:
        """
        Traite un batch mixte de données financières et crypto
        
        Args:
            financial_symbols: Symboles financiers traditionnels
            crypto_symbols: Symboles crypto (optionnel)
            
        Returns:
            Résultats consolidés du traitement
        """
        start_time = time.time()
        logger.info(f"Traitement batch mixte: {len(financial_symbols)} financiers, {len(crypto_symbols or [])} crypto")
        
        consolidated_results = {
            'financial_results': None,
            'crypto_results': None,
            'total_processing_time': 0.0,
            'overall_success': True
        }
        
        try:
            # Traitement des données financières
            if financial_symbols:
                logger.info("Traitement des symboles financiers...")
                consolidated_results['financial_results'] = self.process_real_time_quotes(financial_symbols)
            
            # Traitement des données crypto (simulé pour l'instant)
            if crypto_symbols:
                logger.info("Traitement des symboles crypto...")
                consolidated_results['crypto_results'] = self._process_crypto_symbols(crypto_symbols)
            
            # Génération d'événements de traitement
            processing_event = {
                'event_type': 'batch_processing_completed',
                'financial_symbols_count': len(financial_symbols),
                'crypto_symbols_count': len(crypto_symbols or []),
                'timestamp': datetime.utcnow().isoformat(),
                'environment': self.environment
            }
            
            # Envoi de l'événement vers le stream d'événements
            event_result = self.kinesis_client.send_event_data(processing_event)
            consolidated_results['event_result'] = event_result
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement batch mixte: {str(e)}")
            consolidated_results['overall_success'] = False
            consolidated_results['error'] = str(e)
        
        consolidated_results['total_processing_time'] = time.time() - start_time
        
        return consolidated_results
    
    def _process_crypto_symbols(self, crypto_symbols: List[str]) -> Dict[str, Any]:
        """
        Traite les symboles crypto (simulation pour l'instant)
        
        Note: Ceci est une simulation. Dans un déploiement réel,
        nous utiliserions CoinGecko ou Binance API.
        """
        logger.info(f"Simulation du traitement crypto pour {len(crypto_symbols)} symboles")
        
        # Simulation de données crypto
        simulated_results = {
            'symbols_processed': len(crypto_symbols),
            'symbols_failed': 0,
            'kinesis_results': [],
            'note': 'Simulation - CoinGecko connector à implémenter'
        }
        
        for symbol in crypto_symbols:
            # Simulation de données crypto
            simulated_crypto_data = {
                'symbol': symbol,
                'price': 45000.0 + (hash(symbol) % 10000),  # Prix simulé
                'volume': 1000000 + (hash(symbol) % 5000000),
                'market_cap': 800000000000,
                'timestamp': datetime.utcnow().isoformat(),
                'data_type': 'crypto_quote',
                'source': 'simulated'
            }
            
            # Enrichissement et envoi vers Kinesis crypto stream
            enriched_data = self._enrich_for_kinesis(simulated_crypto_data, 'crypto_quote')
            
            kinesis_result = self.kinesis_client.send_crypto_data(
                data=enriched_data,
                partition_key=f"crypto_{symbol}"
            )
            
            simulated_results['kinesis_results'].append(kinesis_result)
        
        return simulated_results
    
    def _validate_quote_data(self, quote_data: Dict[str, Any]) -> bool:
        """Valide les données de cotation"""
        required_fields = ['symbol', 'price', 'volume', 'timestamp']
        
        for field in required_fields:
            if field not in quote_data or quote_data[field] is None:
                return False
        
        # Validation des valeurs
        if quote_data['price'] <= 0 or quote_data['volume'] < 0:
            return False
        
        return True
    
    def _validate_intraday_data(self, intraday_data: Dict[str, Any]) -> bool:
        """Valide les données intraday"""
        if not intraday_data.get('symbol'):
            return False
        
        data_points = intraday_data.get('data_points', [])
        return len(data_points) > 0
    
    def _enrich_for_kinesis(self, data: Dict[str, Any], data_category: str) -> Dict[str, Any]:
        """Enrichit les données pour l'envoi vers Kinesis"""
        enriched = {
            **data,
            'kinesis_enrichment': {
                'integration_timestamp': datetime.utcnow().isoformat(),
                'integration_version': '1.0',
                'data_category': data_category,
                'environment': self.environment,
                'source_system': 'alpha_vantage_kinesis_integration'
            }
        }
        
        return enriched
    
    def _update_integration_metrics(self, results: Dict[str, Any], processing_time: float):
        """Met à jour les métriques d'intégration"""
        self.integration_metrics['total_data_fetched'] += results.get('symbols_processed', 0)
        self.integration_metrics['total_data_sent'] += sum(
            r.get('successful_records', 0) for r in results.get('kinesis_results', [])
        )
        self.integration_metrics['errors_count'] += len(results.get('errors', []))
        self.integration_metrics['last_execution'] = datetime.utcnow().isoformat()
        self.integration_metrics['processing_time'] = processing_time
    
    def get_integration_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques d'intégration"""
        # Métriques Kinesis
        kinesis_metrics = self.kinesis_client.get_metrics()
        
        # Métriques complètes
        return {
            'integration_metrics': self.integration_metrics,
            'kinesis_metrics': kinesis_metrics,
            'alpha_vantage_status': 'active',  # Pourrait être enrichi
            'health_status': self._get_health_status()
        }
    
    def _get_health_status(self) -> str:
        """Détermine l'état de santé de l'intégration"""
        if self.integration_metrics['errors_count'] == 0:
            return 'healthy'
        elif self.integration_metrics['errors_count'] < 5:
            return 'degraded'
        else:
            return 'unhealthy'
    
    def run_monitoring_check(self) -> Dict[str, Any]:
        """Effectue un check de monitoring complet"""
        logger.info("Exécution du check de monitoring...")
        
        # Health check Kinesis
        kinesis_health = self.kinesis_client.health_check()
        
        # Métriques complètes
        metrics = self.get_integration_metrics()
        
        # Résultat consolidé
        monitoring_result = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_health': 'healthy',
            'kinesis_health': kinesis_health,
            'integration_metrics': metrics,
            'recommendations': []
        }
        
        # Évaluation de la santé globale
        if kinesis_health['overall_status'] != 'healthy':
            monitoring_result['overall_health'] = 'degraded'
            monitoring_result['recommendations'].append('Vérifier la configuration Kinesis')
        
        if self.integration_metrics['errors_count'] > 10:
            monitoring_result['overall_health'] = 'unhealthy'
            monitoring_result['recommendations'].append('Investiguer les erreurs d\'intégration')
        
        return monitoring_result


def main():
    """Fonction principale pour tester l'intégration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Intégration Alpha Vantage → Kinesis')
    parser.add_argument('--api-key', required=True, help='Clé API Alpha Vantage')
    parser.add_argument('--env', default='dev', help='Environnement (dev, staging, prod)')
    parser.add_argument('--symbols', nargs='+', default=['AAPL', 'GOOGL', 'MSFT'], 
                       help='Symboles à traiter')
    parser.add_argument('--mode', choices=['quotes', 'intraday', 'mixed', 'monitoring'], 
                       default='quotes', help='Mode de traitement')
    parser.add_argument('--crypto-symbols', nargs='+', help='Symboles crypto pour le mode mixte')
    
    args = parser.parse_args()
    
    try:
        # Création de l'intégration
        integration = AlphaVantageKinesisIntegration(
            alpha_vantage_api_key=args.api_key,
            environment=args.env
        )
        
        # Exécution selon le mode choisi
        if args.mode == 'quotes':
            logger.info(f"Mode cotations temps réel pour {args.symbols}")
            results = integration.process_real_time_quotes(args.symbols)
            
        elif args.mode == 'intraday':
            logger.info(f"Mode intraday pour {args.symbols}")
            results = integration.process_intraday_data(args.symbols)
            
        elif args.mode == 'mixed':
            logger.info(f"Mode mixte: financier {args.symbols}, crypto {args.crypto_symbols}")
            results = integration.process_mixed_batch(
                financial_symbols=args.symbols,
                crypto_symbols=args.crypto_symbols
            )
            
        elif args.mode == 'monitoring':
            logger.info("Mode monitoring")
            results = integration.run_monitoring_check()
        
        # Affichage des résultats
        logger.info("=== RÉSULTATS ===")
        print(json.dumps(results, indent=2, default=str))
        
        # Métriques finales
        metrics = integration.get_integration_metrics()
        logger.info("=== MÉTRIQUES ===")
        print(json.dumps(metrics, indent=2, default=str))
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {e}")
        raise


if __name__ == "__main__":
    main()
