#!/usr/bin/env python3
"""
Scheduler pour Multi-Source Data Ingestion
"""

import os
import sys
import time
import schedule
import logging
from datetime import datetime
from multi_source_connectors import DataIngestionManager
from multi_source_config import MultiSourceConfig

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IngestionScheduler:
    """Scheduler pour l'ingestion multi-sources"""
    
    def __init__(self):
        self.manager = DataIngestionManager()
        self.config = MultiSourceConfig()
        
        # Validation de la configuration
        if not self.config.validate_config():
            logger.warning("Configuration incomplète, certaines sources peuvent ne pas fonctionner")
        
        logger.info("IngestionScheduler initialisé")
    
    def run_stock_ingestion(self):
        """Exécute l'ingestion des actions"""
        logger.info("📈 Début ingestion actions")
        try:
            self.manager.run_full_ingestion(
                stock_symbols=self.config.DEFAULT_STOCK_SYMBOLS,
                crypto_symbols=None
            )
            logger.info("✅ Ingestion actions terminée")
        except Exception as e:
            logger.error(f"❌ Erreur ingestion actions: {e}")
    
    def run_crypto_ingestion(self):
        """Exécute l'ingestion des cryptos"""
        logger.info("₿ Début ingestion crypto")
        try:
            self.manager.run_full_ingestion(
                stock_symbols=None,
                crypto_symbols=self.config.DEFAULT_CRYPTO_SYMBOLS
            )
            logger.info("✅ Ingestion crypto terminée")
        except Exception as e:
            logger.error(f"❌ Erreur ingestion crypto: {e}")
    
    def run_full_ingestion(self):
        """Exécute l'ingestion complète"""
        logger.info("🚀 Début ingestion complète")
        try:
            self.manager.run_full_ingestion(
                stock_symbols=self.config.DEFAULT_STOCK_SYMBOLS,
                crypto_symbols=self.config.DEFAULT_CRYPTO_SYMBOLS
            )
            logger.info("✅ Ingestion complète terminée")
        except Exception as e:
            logger.error(f"❌ Erreur ingestion complète: {e}")
    
    def setup_schedule(self):
        """Configure le planning d'ingestion"""
        logger.info("⏰ Configuration du planning d'ingestion")
        
        # Ingestion des actions - toutes les heures pendant les heures de marché US
        schedule.every().hour.at(":00").do(self.run_stock_ingestion)
        
        # Ingestion des cryptos - toutes les 30 minutes
        schedule.every(30).minutes.do(self.run_crypto_ingestion)
        
        # Ingestion complète - toutes les 6 heures
        schedule.every(6).hours.do(self.run_full_ingestion)
        
        # Ingestion de test - toutes les 5 minutes (pour debug)
        if os.getenv('DEBUG_MODE') == 'true':
            schedule.every(5).minutes.do(self.run_crypto_ingestion)
            logger.info("🐛 Mode debug activé - ingestion crypto toutes les 5 minutes")
        
        logger.info("📅 Planning configuré:")
        logger.info("  - Actions: toutes les heures")
        logger.info("  - Crypto: toutes les 30 minutes")
        logger.info("  - Complète: toutes les 6 heures")
    
    def run_scheduler(self):
        """Exécute le scheduler"""
        logger.info("🔄 Démarrage du scheduler d'ingestion")
        
        self.setup_schedule()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Vérification toutes les minutes
                
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt du scheduler demandé")
        except Exception as e:
            logger.error(f"💥 Erreur du scheduler: {e}")
        
        logger.info("✅ Scheduler arrêté")

def main():
    """Fonction principale"""
    logger.info("🚀 Démarrage du scheduler d'ingestion multi-sources")
    
    # Arguments de ligne de commande
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        scheduler = IngestionScheduler()
        
        if command == 'stocks':
            scheduler.run_stock_ingestion()
        elif command == 'crypto':
            scheduler.run_crypto_ingestion()
        elif command == 'full':
            scheduler.run_full_ingestion()
        elif command == 'schedule':
            scheduler.run_scheduler()
        else:
            print("Usage: python scheduler.py [stocks|crypto|full|schedule]")
            sys.exit(1)
    else:
        # Mode par défaut: scheduler
        scheduler = IngestionScheduler()
        scheduler.run_scheduler()

if __name__ == "__main__":
    main()
