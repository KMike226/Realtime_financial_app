#!/usr/bin/env python3
"""
Data Ingestion Scheduler
========================

Orchestrateur principal pour l'ingestion automatisée de données financières.
Gère la planification et l'exécution des connecteurs de données.

Author: Michée Project Team
Date: 2025-04-02
"""

import json
import time
import logging
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from connectors.alpha_vantage_connector import AlphaVantageConnector, DataType
from config import config, alpha_vantage_config, validate_config

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataIngestionScheduler:
    """
    Planificateur principal pour l'ingestion de données
    
    Fonctionnalités:
    - Planification automatique des tâches d'ingestion
    - Exécution parallèle des connecteurs
    - Gestion des erreurs et reprises
    - Monitoring des performances
    """
    
    def __init__(self):
        self.connectors = {}
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'last_execution': None,
            'average_execution_time': 0
        }
        
        # Validation de la configuration
        validate_config()
        
        # Initialisation des connecteurs
        self._initialize_connectors()
        
        # Chargement des symboles
        self.symbols = self._load_symbols()
        
        logger.info("Planificateur d'ingestion initialisé")
    
    def _initialize_connectors(self):
        """Initialise tous les connecteurs de données"""
        try:
            # Alpha Vantage connector
            self.connectors['alpha_vantage'] = AlphaVantageConnector(alpha_vantage_config)
            logger.info("Connecteur Alpha Vantage initialisé")
            
            # TODO: Ajouter d'autres connecteurs ici
            # self.connectors['iex_cloud'] = IEXCloudConnector(iex_config)
            # self.connectors['coingecko'] = CoinGeckoConnector(coingecko_config)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des connecteurs: {e}")
            raise
    
    def _load_symbols(self) -> Dict[str, List[str]]:
        """Charge la liste des symboles à traiter"""
        try:
            with open(config.symbols_file, 'r') as f:
                symbols_data = json.load(f)
            
            logger.info(f"Symboles chargés depuis {config.symbols_file}")
            return symbols_data
            
        except FileNotFoundError:
            logger.warning(f"Fichier de symboles non trouvé: {config.symbols_file}")
            # Fallback sur une liste par défaut
            return {
                'priority_symbols': ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
            }
        except Exception as e:
            logger.error(f"Erreur lors du chargement des symboles: {e}")
            raise
    
    def execute_real_time_ingestion(self):
        """Exécute l'ingestion de données en temps réel"""
        start_time = time.time()
        
        try:
            logger.info("Démarrage de l'ingestion en temps réel")
            
            # Récupération des symboles prioritaires
            symbols_to_process = self.symbols.get('priority_symbols', [])
            
            if not symbols_to_process:
                logger.warning("Aucun symbole prioritaire trouvé")
                return
            
            # Limitation du nombre de symboles par batch
            batch_size = min(len(symbols_to_process), config.max_symbols_per_request)
            symbols_batch = symbols_to_process[:batch_size]
            
            logger.info(f"Traitement de {len(symbols_batch)} symboles: {symbols_batch}")
            
            # Exécution avec le connecteur Alpha Vantage
            connector = self.connectors['alpha_vantage']
            results = connector.fetch_and_store_data(
                symbols=symbols_batch,
                data_types=[DataType.REAL_TIME_QUOTE]
            )
            
            # Statistiques
            execution_time = time.time() - start_time
            self._update_stats(True, execution_time)
            
            total_files = sum(len(files) for files in results.values())
            logger.info(f"Ingestion réussie: {total_files} fichiers créés en {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(False, execution_time)
            logger.error(f"Erreur lors de l'ingestion en temps réel: {e}")
            raise
    
    def execute_historical_ingestion(self):
        """Exécute l'ingestion de données historiques"""
        start_time = time.time()
        
        try:
            logger.info("Démarrage de l'ingestion historique")
            
            # Sélection d'un sous-ensemble de symboles pour l'historique
            tech_symbols = self.symbols.get('stocks', {}).get('tech', [])[:5]
            
            if not tech_symbols:
                logger.warning("Aucun symbole tech trouvé pour l'historique")
                return
            
            logger.info(f"Traitement historique de {len(tech_symbols)} symboles: {tech_symbols}")
            
            # Exécution avec le connecteur Alpha Vantage
            connector = self.connectors['alpha_vantage']
            results = connector.fetch_and_store_data(
                symbols=tech_symbols,
                data_types=[DataType.DAILY]
            )
            
            # Statistiques
            execution_time = time.time() - start_time
            self._update_stats(True, execution_time)
            
            total_files = sum(len(files) for files in results.values())
            logger.info(f"Ingestion historique réussie: {total_files} fichiers créés en {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(False, execution_time)
            logger.error(f"Erreur lors de l'ingestion historique: {e}")
    
    def execute_intraday_ingestion(self):
        """Exécute l'ingestion de données intraday"""
        start_time = time.time()
        
        try:
            logger.info("Démarrage de l'ingestion intraday")
            
            # Focus sur les indices principaux pour l'intraday
            indices = self.symbols.get('indices', [])[:3]
            
            if not indices:
                logger.warning("Aucun indice trouvé pour l'intraday")
                return
            
            logger.info(f"Traitement intraday de {len(indices)} indices: {indices}")
            
            # Exécution avec le connecteur Alpha Vantage
            connector = self.connectors['alpha_vantage']
            results = connector.fetch_and_store_data(
                symbols=indices,
                data_types=[DataType.INTRADAY]
            )
            
            # Statistiques
            execution_time = time.time() - start_time
            self._update_stats(True, execution_time)
            
            total_files = sum(len(files) for files in results.values())
            logger.info(f"Ingestion intraday réussie: {total_files} fichiers créés en {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(False, execution_time)
            logger.error(f"Erreur lors de l'ingestion intraday: {e}")
    
    def _update_stats(self, success: bool, execution_time: float):
        """Met à jour les statistiques d'exécution"""
        self.execution_stats['total_executions'] += 1
        self.execution_stats['last_execution'] = datetime.utcnow().isoformat()
        
        if success:
            self.execution_stats['successful_executions'] += 1
        else:
            self.execution_stats['failed_executions'] += 1
        
        # Calcul de la moyenne mobile du temps d'exécution
        current_avg = self.execution_stats['average_execution_time']
        total_executions = self.execution_stats['total_executions']
        
        new_avg = ((current_avg * (total_executions - 1)) + execution_time) / total_executions
        self.execution_stats['average_execution_time'] = new_avg
    
    def get_health_status(self) -> Dict[str, Any]:
        """Retourne l'état de santé du planificateur"""
        success_rate = 0
        if self.execution_stats['total_executions'] > 0:
            success_rate = (
                self.execution_stats['successful_executions'] / 
                self.execution_stats['total_executions']
            ) * 100
        
        return {
            'status': 'healthy' if success_rate >= 90 else 'degraded' if success_rate >= 70 else 'unhealthy',
            'success_rate': f"{success_rate:.1f}%",
            'statistics': self.execution_stats,
            'connectors_status': {
                name: 'active' for name in self.connectors.keys()
            },
            'symbols_loaded': sum(len(symbols) for symbols in self.symbols.values() if isinstance(symbols, list))
        }
    
    def setup_schedule(self):
        """Configure la planification automatique des tâches"""
        logger.info("Configuration de la planification automatique")
        
        # Ingestion en temps réel - toutes les 5 minutes pendant les heures de marché
        schedule.every(5).minutes.do(self.execute_real_time_ingestion)
        
        # Ingestion historique - une fois par jour à 18h00 ET
        schedule.every().day.at("18:00").do(self.execute_historical_ingestion)
        
        # Ingestion intraday - toutes les 15 minutes pendant les heures de marché
        schedule.every(15).minutes.do(self.execute_intraday_ingestion)
        
        logger.info("Planification configurée:")
        logger.info("- Temps réel: toutes les 5 minutes")
        logger.info("- Historique: quotidien à 18h00")
        logger.info("- Intraday: toutes les 15 minutes")
    
    def run_scheduler(self):
        """Lance le planificateur en continu"""
        logger.info("Démarrage du planificateur d'ingestion de données")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Vérification toutes les minutes
                
        except KeyboardInterrupt:
            logger.info("Arrêt du planificateur demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"Erreur fatale du planificateur: {e}")
            raise
    
    def run_once(self, task_type: str = 'real_time'):
        """Exécute une tâche d'ingestion une seule fois"""
        logger.info(f"Exécution unique: {task_type}")
        
        if task_type == 'real_time':
            self.execute_real_time_ingestion()
        elif task_type == 'historical':
            self.execute_historical_ingestion()
        elif task_type == 'intraday':
            self.execute_intraday_ingestion()
        else:
            raise ValueError(f"Type de tâche non supporté: {task_type}")


def main():
    """Fonction principale du planificateur"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Planificateur d\'ingestion de données financières')
    parser.add_argument(
        '--mode',
        choices=['scheduler', 'once'],
        default='once',
        help='Mode d\'exécution: scheduler (continu) ou once (une fois)'
    )
    parser.add_argument(
        '--task',
        choices=['real_time', 'historical', 'intraday'],
        default='real_time',
        help='Type de tâche pour le mode once'
    )
    
    args = parser.parse_args()
    
    try:
        scheduler = DataIngestionScheduler()
        
        if args.mode == 'scheduler':
            scheduler.setup_schedule()
            scheduler.run_scheduler()
        else:
            scheduler.run_once(args.task)
            
        # Affichage des statistiques finales
        health_status = scheduler.get_health_status()
        logger.info(f"État final: {health_status}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {e}")
        raise


if __name__ == "__main__":
    main()
