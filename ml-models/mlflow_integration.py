"""
Intégration MLflow avec les scripts d'entraînement existants
============================================================

Ce script intègre MLflow dans les processus d'entraînement existants
pour automatiser le suivi et la gestion des modèles.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import os
import sys

# Ajout du répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mlflow_automation import MLflowAutomation
from mlflow_config import MLflowConfig, setup_development_environment

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLflowIntegratedTrainer:
    """
    Entraîneur intégré avec MLflow pour automatiser le suivi des modèles.
    """
    
    def __init__(self, experiment_name: str = "financial_models_integrated"):
        """
        Initialise l'entraîneur avec intégration MLflow.
        
        Args:
            experiment_name: Nom de l'expérience MLflow
        """
        # Configuration MLflow
        self.mlflow_config = MLflowConfig()
        self.mlflow_auto = MLflowAutomation(experiment_name=experiment_name)
        
        # Configuration de l'environnement
        self.mlflow_config.setup_mlflow()
        
        logger.info(f"Entraîneur MLflow initialisé avec l'expérience: {experiment_name}")
    
    def train_with_mlflow(self, model, train_data: pd.DataFrame, 
                         test_data: pd.DataFrame, model_name: str,
                         model_params: Optional[Dict] = None,
                         additional_tags: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Entraîne un modèle avec intégration MLflow complète.
        
        Args:
            model: Modèle à entraîner
            train_data: Données d'entraînement
            test_data: Données de test
            model_name: Nom du modèle
            model_params: Paramètres du modèle
            additional_tags: Tags supplémentaires
            
        Returns:
            Dict contenant les résultats de l'entraînement
        """
        # Tags par défaut
        tags = {
            "model_type": type(model).__name__,
            "training_date": datetime.now().strftime("%Y-%m-%d"),
            "data_source": "financial_data"
        }
        if additional_tags:
            tags.update(additional_tags)
        
        # Entraînement avec MLflow
        results = self.mlflow_auto.auto_train_model(
            model=model,
            train_data=train_data,
            test_data=test_data,
            model_name=model_name,
            params=model_params
        )
        
        # Ajout d'informations supplémentaires
        results["mlflow_run_id"] = results.get("run_id")
        results["model_name"] = model_name
        results["training_timestamp"] = datetime.now().isoformat()
        
        logger.info(f"Entraînement MLflow terminé pour {model_name}")
        return results
    
    def train_anomaly_detection_with_mlflow(self, train_data: pd.DataFrame,
                                          test_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Entraîne le modèle de détection d'anomalies avec MLflow.
        
        Args:
            train_data: Données d'entraînement
            test_data: Données de test
            
        Returns:
            Dict contenant les résultats de l'entraînement
        """
        try:
            # Import du détecteur d'anomalies existant
            from anomaly_detection import FinancialAnomalyDetector
            from config import get_config
            
            # Configuration
            config = get_config()
            detector = FinancialAnomalyDetector(config)
            
            # Préparation des données
            train_processed = detector.prepare_features(train_data)
            test_processed = detector.prepare_features(test_data)
            
            # Entraînement avec MLflow
            tags = {
                "model_type": "anomaly_detection",
                "algorithm": "isolation_forest",
                "use_case": "financial_monitoring"
            }
            
            results = self.train_with_mlflow(
                model=detector,
                train_data=train_processed,
                test_data=test_processed,
                model_name="anomaly_detection_financial",
                model_params=config.get("model_params", {}),
                additional_tags=tags
            )
            
            logger.info("Entraînement du modèle de détection d'anomalies terminé")
            return results
            
        except ImportError as e:
            logger.error(f"Impossible d'importer les modules existants: {e}")
            return {"error": "Import failed", "details": str(e)}
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement: {e}")
            return {"error": "Training failed", "details": str(e)}
    
    def train_price_prediction_with_mlflow(self, train_data: pd.DataFrame,
                                         test_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Entraîne le modèle de prédiction de prix avec MLflow.
        
        Args:
            train_data: Données d'entraînement
            test_data: Données de test
            
        Returns:
            Dict contenant les résultats de l'entraînement
        """
        try:
            # Import du modèle de prédiction existant
            from price_prediction import PricePredictionModel
            from prediction_config import get_prediction_config
            
            # Configuration
            config = get_prediction_config()
            model = PricePredictionModel(config)
            
            # Entraînement avec MLflow
            tags = {
                "model_type": "price_prediction",
                "algorithm": "linear_regression",
                "use_case": "financial_forecasting"
            }
            
            results = self.train_with_mlflow(
                model=model,
                train_data=train_data,
                test_data=test_data,
                model_name="price_prediction_financial",
                model_params=config.get("model_params", {}),
                additional_tags=tags
            )
            
            logger.info("Entraînement du modèle de prédiction de prix terminé")
            return results
            
        except ImportError as e:
            logger.error(f"Impossible d'importer les modules existants: {e}")
            return {"error": "Import failed", "details": str(e)}
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement: {e}")
            return {"error": "Training failed", "details": str(e)}
    
    def get_model_performance_summary(self) -> Dict[str, Any]:
        """
        Récupère un résumé des performances des modèles.
        
        Returns:
            Dict contenant le résumé des performances
        """
        try:
            # Récupération du meilleur modèle pour chaque type
            best_anomaly = self.mlflow_auto.get_best_model("test_r2", ascending=False)
            best_prediction = self.mlflow_auto.get_best_model("test_r2", ascending=False)
            
            summary = {
                "best_anomaly_model": best_anomaly,
                "best_prediction_model": best_prediction,
                "summary_timestamp": datetime.now().isoformat()
            }
            
            logger.info("Résumé des performances récupéré")
            return summary
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résumé: {e}")
            return {"error": "Summary failed", "details": str(e)}


def create_sample_financial_data(n_samples: int = 1000) -> tuple:
    """
    Crée des données financières d'exemple pour les tests.
    
    Args:
        n_samples: Nombre d'échantillons à générer
        
    Returns:
        Tuple contenant (train_data, test_data)
    """
    np.random.seed(42)
    
    # Génération de données financières réalistes
    timestamps = pd.date_range(start='2024-01-01', periods=n_samples, freq='H')
    
    data = pd.DataFrame({
        'timestamp': timestamps,
        'price': 100 + np.cumsum(np.random.normal(0, 0.5, n_samples)),
        'volume': np.random.exponential(1000, n_samples),
        'volatility': np.random.gamma(2, 1, n_samples),
        'rsi': np.random.uniform(20, 80, n_samples),
        'macd': np.random.normal(0, 1, n_samples),
        'sma_20': 100 + np.cumsum(np.random.normal(0, 0.3, n_samples)),
        'ema_12': 100 + np.cumsum(np.random.normal(0, 0.4, n_samples)),
        'target': np.random.normal(0, 1, n_samples)  # Variable cible pour la prédiction
    })
    
    # Division train/test (80/20)
    split_idx = int(0.8 * n_samples)
    train_data = data[:split_idx].copy()
    test_data = data[split_idx:].copy()
    
    logger.info(f"Données d'exemple créées: {len(train_data)} train, {len(test_data)} test")
    return train_data, test_data


def main():
    """
    Fonction principale pour démontrer l'intégration MLflow.
    """
    logger.info("Démarrage de l'intégration MLflow...")
    
    # Configuration de l'environnement de développement
    dev_env = setup_development_environment()
    
    # Initialisation de l'entraîneur intégré
    trainer = MLflowIntegratedTrainer("financial_models_integrated")
    
    # Création de données d'exemple
    train_data, test_data = create_sample_financial_data(1000)
    
    # Test d'entraînement avec un modèle simple
    from sklearn.ensemble import RandomForestRegressor
    
    simple_model = RandomForestRegressor(n_estimators=10, random_state=42)
    simple_params = {"n_estimators": 10, "random_state": 42}
    
    logger.info("Test d'entraînement avec modèle simple...")
    simple_results = trainer.train_with_mlflow(
        model=simple_model,
        train_data=train_data,
        test_data=test_data,
        model_name="simple_random_forest",
        model_params=simple_params
    )
    
    logger.info(f"Résultats entraînement simple: {simple_results}")
    
    # Test d'entraînement des modèles existants (si disponibles)
    logger.info("Test d'entraînement des modèles existants...")
    
    # Test détection d'anomalies
    anomaly_results = trainer.train_anomaly_detection_with_mlflow(train_data, test_data)
    logger.info(f"Résultats détection d'anomalies: {anomaly_results}")
    
    # Test prédiction de prix
    prediction_results = trainer.train_price_prediction_with_mlflow(train_data, test_data)
    logger.info(f"Résultats prédiction de prix: {prediction_results}")
    
    # Résumé des performances
    performance_summary = trainer.get_model_performance_summary()
    logger.info(f"Résumé des performances: {performance_summary}")
    
    logger.info("Intégration MLflow terminée avec succès!")


if __name__ == "__main__":
    main()
