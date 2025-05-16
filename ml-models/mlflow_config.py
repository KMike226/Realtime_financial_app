"""
Configuration MLflow pour l'application financière
=================================================

Script de configuration simple pour MLflow avec des paramètres
optimisés pour l'environnement de développement MVP.
"""

import os
import mlflow
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLflowConfig:
    """
    Configuration centralisée pour MLflow.
    """
    
    def __init__(self):
        """Initialise la configuration MLflow."""
        self.base_dir = Path("/tmp/mlflow")
        self.experiment_name = "financial_models"
        self.tracking_uri = f"file://{self.base_dir}"
        
    def setup_mlflow(self, custom_tracking_uri: Optional[str] = None,
                    custom_experiment: Optional[str] = None) -> Dict[str, Any]:
        """
        Configure MLflow avec les paramètres de base.
        
        Args:
            custom_tracking_uri: URI personnalisé pour le tracking
            custom_experiment: Nom d'expérience personnalisé
            
        Returns:
            Dict contenant la configuration appliquée
        """
        # Configuration du répertoire de base
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration de l'URI de tracking
        if custom_tracking_uri:
            self.tracking_uri = custom_tracking_uri
        
        # Configuration du nom d'expérience
        if custom_experiment:
            self.experiment_name = custom_experiment
        
        # Application de la configuration MLflow
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)
        
        # Configuration des variables d'environnement
        os.environ["MLFLOW_TRACKING_URI"] = self.tracking_uri
        
        config = {
            "tracking_uri": self.tracking_uri,
            "experiment_name": self.experiment_name,
            "base_dir": str(self.base_dir)
        }
        
        logger.info(f"MLflow configuré avec: {config}")
        return config
    
    def create_experiment(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """
        Crée une nouvelle expérience MLflow.
        
        Args:
            name: Nom de l'expérience
            tags: Tags à associer à l'expérience
            
        Returns:
            ID de l'expérience créée
        """
        tags = tags or {}
        default_tags = {
            "project": "financial_app",
            "version": "mvp",
            "environment": "development"
        }
        default_tags.update(tags)
        
        try:
            experiment_id = mlflow.create_experiment(name, tags=default_tags)
            logger.info(f"Expérience créée: {name} (ID: {experiment_id})")
            return experiment_id
        except mlflow.exceptions.MlflowException as e:
            if "already exists" in str(e):
                experiment = mlflow.get_experiment_by_name(name)
                logger.info(f"Expérience existante utilisée: {name} (ID: {experiment.experiment_id})")
                return experiment.experiment_id
            else:
                raise e
    
    def get_experiment_info(self) -> Dict[str, Any]:
        """
        Récupère les informations sur l'expérience actuelle.
        
        Returns:
            Dict contenant les informations de l'expérience
        """
        try:
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if experiment:
                return {
                    "experiment_id": experiment.experiment_id,
                    "name": experiment.name,
                    "artifact_location": experiment.artifact_location,
                    "tags": experiment.tags
                }
            else:
                logger.warning(f"Expérience '{self.experiment_name}' non trouvée")
                return {}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations: {e}")
            return {}
    
    def cleanup_old_runs(self, keep_last_n: int = 10):
        """
        Nettoie les anciennes exécutions pour économiser l'espace.
        
        Args:
            keep_last_n: Nombre d'exécutions à conserver
        """
        try:
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if not experiment:
                logger.warning("Aucune expérience trouvée pour le nettoyage")
                return
            
            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["start_time DESC"]
            )
            
            if len(runs) > keep_last_n:
                runs_to_delete = runs.iloc[keep_last_n:]
                for _, run in runs_to_delete.iterrows():
                    mlflow.delete_run(run["run_id"])
                    logger.info(f"Exécution supprimée: {run['run_id']}")
                
                logger.info(f"Nettoyage terminé: {len(runs_to_delete)} exécutions supprimées")
            else:
                logger.info("Aucun nettoyage nécessaire")
                
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")


def setup_development_environment():
    """
    Configure l'environnement de développement MLflow.
    """
    config = MLflowConfig()
    
    # Configuration de base
    mlflow_config = config.setup_mlflow()
    
    # Création de l'expérience principale
    experiment_id = config.create_experiment(
        name="financial_models_dev",
        tags={"environment": "development", "phase": "mvp"}
    )
    
    # Création d'une expérience pour les tests
    test_experiment_id = config.create_experiment(
        name="financial_models_test",
        tags={"environment": "test", "phase": "mvp"}
    )
    
    logger.info("Environnement de développement MLflow configuré")
    return {
        "main_experiment": experiment_id,
        "test_experiment": test_experiment_id,
        "config": mlflow_config
    }


def setup_production_environment(tracking_server_uri: str):
    """
    Configure l'environnement de production MLflow.
    
    Args:
        tracking_server_uri: URI du serveur MLflow en production
    """
    config = MLflowConfig()
    
    # Configuration pour la production
    mlflow_config = config.setup_mlflow(
        custom_tracking_uri=tracking_server_uri,
        custom_experiment="financial_models_prod"
    )
    
    # Création de l'expérience de production
    experiment_id = config.create_experiment(
        name="financial_models_prod",
        tags={"environment": "production", "phase": "mvp"}
    )
    
    logger.info("Environnement de production MLflow configuré")
    return {
        "production_experiment": experiment_id,
        "config": mlflow_config
    }


def main():
    """
    Fonction principale pour tester la configuration MLflow.
    """
    logger.info("Démarrage de la configuration MLflow...")
    
    # Configuration de l'environnement de développement
    dev_env = setup_development_environment()
    
    # Affichage des informations de configuration
    config = MLflowConfig()
    experiment_info = config.get_experiment_info()
    
    logger.info("Configuration terminée:")
    logger.info(f"- Expérience principale: {dev_env['main_experiment']}")
    logger.info(f"- Expérience de test: {dev_env['test_experiment']}")
    logger.info(f"- Informations expérience: {experiment_info}")
    
    # Test de nettoyage (optionnel)
    # config.cleanup_old_runs(keep_last_n=5)


if __name__ == "__main__":
    main()
