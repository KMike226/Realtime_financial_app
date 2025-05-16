"""
Automatisation de l'entraînement de modèles avec MLflow
======================================================

Ce module fournit une intégration simple avec MLflow pour automatiser
l'entraînement, le suivi et le déploiement des modèles ML.
"""

import mlflow
import mlflow.sklearn
import mlflow.pytorch
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import os
import json
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLflowAutomation:
    """
    Classe pour automatiser l'entraînement et le suivi des modèles avec MLflow.
    """
    
    def __init__(self, experiment_name: str = "financial_models", 
                 tracking_uri: Optional[str] = None):
        """
        Initialise l'automatisation MLflow.
        
        Args:
            experiment_name: Nom de l'expérience MLflow
            tracking_uri: URI du serveur de tracking MLflow (optionnel)
        """
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri or "file:///tmp/mlflow"
        
        # Configuration MLflow
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)
        
        logger.info(f"MLflow configuré avec l'expérience: {self.experiment_name}")
    
    def start_run(self, run_name: Optional[str] = None, 
                  tags: Optional[Dict[str, str]] = None) -> mlflow.ActiveRun:
        """
        Démarre une nouvelle exécution MLflow.
        
        Args:
            run_name: Nom de l'exécution
            tags: Tags à associer à l'exécution
            
        Returns:
            ActiveRun: Objet de l'exécution active
        """
        run_name = run_name or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        tags = tags or {}
        
        # Tags par défaut
        default_tags = {
            "framework": "scikit-learn",
            "project": "financial_app",
            "version": "1.0.0"
        }
        default_tags.update(tags)
        
        run = mlflow.start_run(run_name=run_name, tags=default_tags)
        logger.info(f"Exécution démarrée: {run_name}")
        return run
    
    def log_parameters(self, params: Dict[str, Any]):
        """
        Enregistre les paramètres de l'exécution.
        
        Args:
            params: Dictionnaire des paramètres à enregistrer
        """
        mlflow.log_params(params)
        logger.info(f"Paramètres enregistrés: {list(params.keys())}")
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """
        Enregistre les métriques de l'exécution.
        
        Args:
            metrics: Dictionnaire des métriques à enregistrer
            step: Étape de l'entraînement (optionnel)
        """
        mlflow.log_metrics(metrics, step=step)
        logger.info(f"Métriques enregistrées: {list(metrics.keys())}")
    
    def log_model(self, model, model_name: str, 
                  signature: Optional[mlflow.models.signature.ModelSignature] = None,
                  input_example: Optional[Any] = None):
        """
        Enregistre le modèle dans MLflow.
        
        Args:
            model: Modèle entraîné à enregistrer
            model_name: Nom du modèle
            signature: Signature du modèle (optionnel)
            input_example: Exemple d'entrée (optionnel)
        """
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path=model_name,
            signature=signature,
            input_example=input_example
        )
        logger.info(f"Modèle enregistré: {model_name}")
    
    def log_artifacts(self, artifacts_dir: str, artifact_path: Optional[str] = None):
        """
        Enregistre des artefacts (fichiers) dans MLflow.
        
        Args:
            artifacts_dir: Répertoire contenant les artefacts
            artifact_path: Chemin de destination dans MLflow (optionnel)
        """
        mlflow.log_artifacts(artifacts_dir, artifact_path)
        logger.info(f"Artefacts enregistrés depuis: {artifacts_dir}")
    
    def log_data_info(self, data: pd.DataFrame, data_name: str = "dataset"):
        """
        Enregistre des informations sur le dataset.
        
        Args:
            data: DataFrame à analyser
            data_name: Nom du dataset
        """
        # Informations de base
        info = {
            f"{data_name}_shape": data.shape,
            f"{data_name}_columns": len(data.columns),
            f"{data_name}_rows": len(data),
            f"{data_name}_memory_usage": data.memory_usage(deep=True).sum()
        }
        
        # Informations sur les colonnes numériques
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            info[f"{data_name}_numeric_columns"] = len(numeric_cols)
            info[f"{data_name}_missing_values"] = data.isnull().sum().sum()
        
        mlflow.log_params(info)
        logger.info(f"Informations dataset enregistrées: {data_name}")
    
    def auto_train_model(self, model, train_data: pd.DataFrame, 
                        test_data: pd.DataFrame, model_name: str,
                        params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Automatise l'entraînement et l'enregistrement d'un modèle.
        
        Args:
            model: Modèle à entraîner
            train_data: Données d'entraînement
            test_data: Données de test
            model_name: Nom du modèle
            params: Paramètres du modèle
            
        Returns:
            Dict contenant les résultats de l'entraînement
        """
        with self.start_run(run_name=f"train_{model_name}"):
            # Enregistrement des paramètres
            if params:
                self.log_parameters(params)
            
            # Enregistrement des informations sur les données
            self.log_data_info(train_data, "train")
            self.log_data_info(test_data, "test")
            
            # Entraînement du modèle
            logger.info(f"Démarrage de l'entraînement: {model_name}")
            
            # Supposons que le modèle a une méthode fit
            if hasattr(model, 'fit'):
                model.fit(train_data.drop(columns=['target']), train_data['target'])
            else:
                logger.warning("Le modèle n'a pas de méthode fit standard")
            
            # Prédictions et métriques
            if hasattr(model, 'predict'):
                train_pred = model.predict(train_data.drop(columns=['target']))
                test_pred = model.predict(test_data.drop(columns=['target']))
                
                # Calcul des métriques simples
                from sklearn.metrics import mean_squared_error, r2_score
                
                train_mse = mean_squared_error(train_data['target'], train_pred)
                test_mse = mean_squared_error(test_data['target'], test_pred)
                train_r2 = r2_score(train_data['target'], train_pred)
                test_r2 = r2_score(test_data['target'], test_pred)
                
                metrics = {
                    "train_mse": train_mse,
                    "test_mse": test_mse,
                    "train_r2": train_r2,
                    "test_r2": test_r2
                }
                
                self.log_metrics(metrics)
                
                # Enregistrement du modèle
                self.log_model(model, model_name)
                
                logger.info(f"Entraînement terminé: {model_name}")
                logger.info(f"Métriques: {metrics}")
                
                return {
                    "model": model,
                    "metrics": metrics,
                    "run_id": mlflow.active_run().info.run_id
                }
            else:
                logger.warning("Le modèle n'a pas de méthode predict")
                return {"model": model, "run_id": mlflow.active_run().info.run_id}
    
    def get_best_model(self, metric_name: str = "test_r2", 
                      ascending: bool = False) -> Optional[Dict[str, Any]]:
        """
        Récupère le meilleur modèle basé sur une métrique.
        
        Args:
            metric_name: Nom de la métrique à utiliser
            ascending: True pour minimiser, False pour maximiser
            
        Returns:
            Dict contenant les informations du meilleur modèle
        """
        try:
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
            
            if runs.empty:
                logger.warning("Aucune exécution trouvée")
                return None
            
            # Trier par métrique
            if metric_name in runs.columns:
                best_run = runs.sort_values(metric_name, ascending=ascending).iloc[0]
                
                return {
                    "run_id": best_run["run_id"],
                    "metric_value": best_run[metric_name],
                    "model_uri": f"runs:/{best_run['run_id']}/model"
                }
            else:
                logger.warning(f"Métrique {metric_name} non trouvée")
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du meilleur modèle: {e}")
            return None
    
    def deploy_model(self, model_uri: str, deployment_name: str = "production"):
        """
        Déploie un modèle pour la production.
        
        Args:
            model_uri: URI du modèle à déployer
            deployment_name: Nom du déploiement
        """
        try:
            # Pour un MVP simple, on sauvegarde juste l'URI
            deployment_info = {
                "model_uri": model_uri,
                "deployment_name": deployment_name,
                "deployment_time": datetime.now().isoformat(),
                "status": "deployed"
            }
            
            # Sauvegarde dans un fichier JSON simple
            deployment_file = Path(f"deployments/{deployment_name}.json")
            deployment_file.parent.mkdir(exist_ok=True)
            
            with open(deployment_file, 'w') as f:
                json.dump(deployment_info, f, indent=2)
            
            logger.info(f"Modèle déployé: {deployment_name}")
            logger.info(f"URI du modèle: {model_uri}")
            
        except Exception as e:
            logger.error(f"Erreur lors du déploiement: {e}")


def create_sample_training_data(n_samples: int = 1000) -> tuple:
    """
    Crée des données d'exemple pour l'entraînement.
    
    Args:
        n_samples: Nombre d'échantillons à générer
        
    Returns:
        Tuple contenant (train_data, test_data)
    """
    np.random.seed(42)
    
    # Génération de données financières simulées
    data = pd.DataFrame({
        'price': np.random.normal(100, 10, n_samples),
        'volume': np.random.exponential(1000, n_samples),
        'volatility': np.random.gamma(2, 1, n_samples),
        'rsi': np.random.uniform(0, 100, n_samples),
        'macd': np.random.normal(0, 1, n_samples),
        'target': np.random.normal(0, 1, n_samples)  # Variable cible simulée
    })
    
    # Division train/test
    split_idx = int(0.8 * n_samples)
    train_data = data[:split_idx]
    test_data = data[split_idx:]
    
    return train_data, test_data


def main():
    """
    Fonction principale pour démontrer l'utilisation de MLflowAutomation.
    """
    # Initialisation de l'automatisation MLflow
    mlflow_auto = MLflowAutomation(experiment_name="financial_models_mvp")
    
    # Création de données d'exemple
    train_data, test_data = create_sample_training_data(1000)
    
    # Exemple d'entraînement d'un modèle simple
    from sklearn.ensemble import RandomForestRegressor
    
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    params = {
        "n_estimators": 10,
        "random_state": 42,
        "max_depth": None
    }
    
    # Entraînement automatique
    results = mlflow_auto.auto_train_model(
        model=model,
        train_data=train_data,
        test_data=test_data,
        model_name="random_forest_financial",
        params=params
    )
    
    # Récupération du meilleur modèle
    best_model = mlflow_auto.get_best_model(metric_name="test_r2")
    if best_model:
        logger.info(f"Meilleur modèle trouvé: {best_model}")
        
        # Déploiement du modèle
        mlflow_auto.deploy_model(
            model_uri=best_model["model_uri"],
            deployment_name="financial_model_v1"
        )


if __name__ == "__main__":
    main()
