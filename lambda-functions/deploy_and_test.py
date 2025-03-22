#!/usr/bin/env python3
"""
Script de déploiement et test des fonctions Lambda
=================================================

Ce script facilite le déploiement et le test des fonctions Lambda
pour le traitement des données financières.

Fonctionnalités:
- Packaging automatique des fonctions Lambda
- Upload vers AWS
- Tests d'intégration
- Monitoring des performances

Author: Michée Project Team
Date: 2025-03-22
"""

import os
import sys
import json
import logging
import zipfile
import boto3
import time
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Clients AWS
lambda_client = boto3.client('lambda')
kinesis_client = boto3.client('kinesis')
s3_client = boto3.client('s3')


class LambdaDeployer:
    """Gestionnaire de déploiement et test des fonctions Lambda"""
    
    def __init__(self, environment: str = "dev", region: str = "us-east-1"):
        """
        Initialise le déployeur
        
        Args:
            environment: Environnement de déploiement
            region: Région AWS
        """
        self.environment = environment
        self.region = region
        self.project_name = "realtime-financial"
        
        # Configuration des fonctions Lambda
        self.lambda_functions = {
            'kinesis-processor': {
                'path': 'kinesis-processor',
                'handler': 'lambda_function.lambda_handler',
                'runtime': 'python3.9',
                'timeout': 300,
                'memory': 256,
                'description': 'Process financial data from Kinesis streams'
            },
            'alert-processor': {
                'path': 'alert-processor',
                'handler': 'lambda_function.lambda_handler',
                'runtime': 'python3.9',
                'timeout': 180,
                'memory': 192,
                'description': 'Process and send financial alerts'
            }
        }
        
        logger.info(f"Déployeur initialisé - Env: {environment}, Région: {region}")
    
    def package_function(self, function_name: str) -> str:
        """
        Package une fonction Lambda en ZIP
        
        Args:
            function_name: Nom de la fonction à packager
            
        Returns:
            Chemin vers le fichier ZIP créé
        """
        if function_name not in self.lambda_functions:
            raise ValueError(f"Fonction inconnue: {function_name}")
        
        function_config = self.lambda_functions[function_name]
        function_path = function_config['path']
        
        # Chemin vers le dossier de la fonction
        source_dir = os.path.join(os.path.dirname(__file__), function_path)
        if not os.path.exists(source_dir):
            raise FileNotFoundError(f"Dossier fonction non trouvé: {source_dir}")
        
        # Nom du fichier ZIP
        zip_filename = f"{function_name}-{self.environment}.zip"
        zip_path = os.path.join(os.path.dirname(__file__), zip_filename)
        
        logger.info(f"Packaging {function_name} vers {zip_path}")
        
        # Création du ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Ajout des fichiers Python
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, arcname)
                        logger.debug(f"Ajouté: {arcname}")
            
            # Ajout de requirements.txt si présent
            requirements_path = os.path.join(source_dir, 'requirements.txt')
            if os.path.exists(requirements_path):
                zipf.write(requirements_path, 'requirements.txt')
        
        logger.info(f"Package créé: {zip_path} ({os.path.getsize(zip_path)} bytes)")
        return zip_path
    
    def deploy_function(self, function_name: str, update_code_only: bool = False) -> Dict[str, Any]:
        """
        Déploie une fonction Lambda
        
        Args:
            function_name: Nom de la fonction à déployer
            update_code_only: Si True, met à jour seulement le code
            
        Returns:
            Résultats du déploiement
        """
        if function_name not in self.lambda_functions:
            raise ValueError(f"Fonction inconnue: {function_name}")
        
        function_config = self.lambda_functions[function_name]
        full_function_name = f"{self.project_name}-{self.environment}-{function_name}"
        
        # Package de la fonction
        zip_path = self.package_function(function_name)
        
        try:
            with open(zip_path, 'rb') as zip_file:
                zip_content = zip_file.read()
            
            if update_code_only:
                # Mise à jour du code seulement
                logger.info(f"Mise à jour du code pour {full_function_name}")
                response = lambda_client.update_function_code(
                    FunctionName=full_function_name,
                    ZipFile=zip_content
                )
            else:
                # Vérification si la fonction existe
                function_exists = self._function_exists(full_function_name)
                
                if function_exists:
                    logger.info(f"Mise à jour de la fonction existante: {full_function_name}")
                    
                    # Mise à jour du code
                    lambda_client.update_function_code(
                        FunctionName=full_function_name,
                        ZipFile=zip_content
                    )
                    
                    # Mise à jour de la configuration
                    response = lambda_client.update_function_configuration(
                        FunctionName=full_function_name,
                        Runtime=function_config['runtime'],
                        Handler=function_config['handler'],
                        Timeout=function_config['timeout'],
                        MemorySize=function_config['memory'],
                        Description=function_config['description'],
                        Environment={
                            'Variables': {
                                'ENVIRONMENT': self.environment,
                                'PROJECT_NAME': self.project_name
                            }
                        }
                    )
                else:
                    logger.info(f"Création nouvelle fonction: {full_function_name}")
                    
                    # Création de la fonction
                    response = lambda_client.create_function(
                        FunctionName=full_function_name,
                        Runtime=function_config['runtime'],
                        Role=self._get_lambda_role_arn(),
                        Handler=function_config['handler'],
                        Code={'ZipFile': zip_content},
                        Description=function_config['description'],
                        Timeout=function_config['timeout'],
                        MemorySize=function_config['memory'],
                        Environment={
                            'Variables': {
                                'ENVIRONMENT': self.environment,
                                'PROJECT_NAME': self.project_name
                            }
                        },
                        Tags={
                            'Environment': self.environment,
                            'Project': self.project_name,
                            'Function': function_name
                        }
                    )
            
            logger.info(f"Déploiement réussi pour {full_function_name}")
            return {
                'success': True,
                'function_name': full_function_name,
                'function_arn': response['FunctionArn'],
                'last_modified': response['LastModified'],
                'code_size': response['CodeSize']
            }
            
        except Exception as e:
            logger.error(f"Erreur déploiement {function_name}: {str(e)}")
            return {
                'success': False,
                'function_name': full_function_name,
                'error': str(e)
            }
        finally:
            # Nettoyage du fichier ZIP
            if os.path.exists(zip_path):
                os.remove(zip_path)
    
    def test_function(self, function_name: str, test_type: str = 'basic') -> Dict[str, Any]:
        """
        Teste une fonction Lambda
        
        Args:
            function_name: Nom de la fonction à tester
            test_type: Type de test ('basic', 'kinesis', 'sns')
            
        Returns:
            Résultats du test
        """
        full_function_name = f"{self.project_name}-{self.environment}-{function_name}"
        
        # Génération du payload de test selon le type
        test_payload = self._generate_test_payload(function_name, test_type)
        
        logger.info(f"Test de {full_function_name} avec payload {test_type}")
        
        try:
            start_time = time.time()
            
            response = lambda_client.invoke(
                FunctionName=full_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_payload)
            )
            
            execution_time = time.time() - start_time
            
            # Lecture de la réponse
            response_payload = response['Payload'].read()
            status_code = response['StatusCode']
            
            # Parse de la réponse
            if response_payload:
                try:
                    result = json.loads(response_payload.decode('utf-8'))
                except json.JSONDecodeError:
                    result = {'raw_response': response_payload.decode('utf-8')}
            else:
                result = {}
            
            logger.info(f"Test terminé en {execution_time:.2f}s - Status: {status_code}")
            
            return {
                'success': status_code == 200,
                'function_name': full_function_name,
                'execution_time': execution_time,
                'status_code': status_code,
                'result': result,
                'test_type': test_type
            }
            
        except Exception as e:
            logger.error(f"Erreur test {function_name}: {str(e)}")
            return {
                'success': False,
                'function_name': full_function_name,
                'error': str(e),
                'test_type': test_type
            }
    
    def deploy_all_functions(self) -> Dict[str, Any]:
        """Déploie toutes les fonctions Lambda"""
        logger.info("Déploiement de toutes les fonctions Lambda")
        
        results = {}
        
        for function_name in self.lambda_functions.keys():
            logger.info(f"Déploiement de {function_name}...")
            result = self.deploy_function(function_name)
            results[function_name] = result
            
            if result['success']:
                logger.info(f"✅ {function_name} déployé avec succès")
            else:
                logger.error(f"❌ Échec déploiement {function_name}: {result.get('error', 'Unknown')}")
        
        # Statistiques
        successful_deployments = sum(1 for r in results.values() if r['success'])
        total_deployments = len(results)
        
        logger.info(f"Déploiement terminé: {successful_deployments}/{total_deployments} réussis")
        
        return {
            'total_functions': total_deployments,
            'successful_deployments': successful_deployments,
            'results': results
        }
    
    def test_all_functions(self) -> Dict[str, Any]:
        """Teste toutes les fonctions Lambda"""
        logger.info("Test de toutes les fonctions Lambda")
        
        results = {}
        
        for function_name in self.lambda_functions.keys():
            logger.info(f"Test de {function_name}...")
            
            # Test basique pour toutes les fonctions
            basic_result = self.test_function(function_name, 'basic')
            results[f"{function_name}_basic"] = basic_result
            
            # Tests spécifiques selon la fonction
            if function_name == 'kinesis-processor':
                kinesis_result = self.test_function(function_name, 'kinesis')
                results[f"{function_name}_kinesis"] = kinesis_result
            
            elif function_name == 'alert-processor':
                sns_result = self.test_function(function_name, 'sns')
                results[f"{function_name}_sns"] = sns_result
        
        # Statistiques
        successful_tests = sum(1 for r in results.values() if r['success'])
        total_tests = len(results)
        
        logger.info(f"Tests terminés: {successful_tests}/{total_tests} réussis")
        
        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'results': results
        }
    
    def _function_exists(self, function_name: str) -> bool:
        """Vérifie si une fonction Lambda existe"""
        try:
            lambda_client.get_function(FunctionName=function_name)
            return True
        except lambda_client.exceptions.ResourceNotFoundException:
            return False
        except Exception as e:
            logger.warning(f"Erreur vérification existence fonction {function_name}: {str(e)}")
            return False
    
    def _get_lambda_role_arn(self) -> str:
        """Retourne l'ARN du rôle Lambda (simulé pour l'instant)"""
        # En production, ceci devrait récupérer le vrai ARN du rôle
        account_id = "123456789012"  # À remplacer par le vrai account ID
        return f"arn:aws:iam::{account_id}:role/{self.project_name}-{self.environment}-lambda-processor-role"
    
    def _generate_test_payload(self, function_name: str, test_type: str) -> Dict[str, Any]:
        """Génère un payload de test selon la fonction et le type"""
        current_time = datetime.utcnow().isoformat()
        
        if function_name == 'kinesis-processor':
            if test_type == 'kinesis':
                # Simulation d'un événement Kinesis
                test_data = {
                    'symbol': 'AAPL',
                    'price': 150.25,
                    'volume': 1000000,
                    'timestamp': current_time,
                    'data_type': 'real_time_quote'
                }
                
                encoded_data = base64.b64encode(json.dumps(test_data).encode()).decode()
                
                return {
                    'Records': [
                        {
                            'kinesis': {
                                'data': encoded_data,
                                'partitionKey': 'symbol_AAPL',
                                'sequenceNumber': '12345'
                            },
                            'eventSource': 'aws:kinesis'
                        }
                    ]
                }
            else:
                # Test basique
                return {
                    'test': True,
                    'timestamp': current_time,
                    'function': function_name
                }
        
        elif function_name == 'alert-processor':
            if test_type == 'sns':
                # Simulation d'un événement SNS
                alert_data = {
                    'alert_type': 'financial_anomaly',
                    'symbol': 'TSLA',
                    'anomalies': ['extreme_price_change_12.5%'],
                    'current_data': {
                        'price': 800.75,
                        'volume': 5000000,
                        'timestamp': current_time
                    },
                    'derived_metrics': {
                        'price_change_percent': 12.5,
                        'volume_ratio': 3.2
                    }
                }
                
                return {
                    'Records': [
                        {
                            'EventSource': 'aws:sns',
                            'Sns': {
                                'Message': json.dumps(alert_data),
                                'Subject': 'Financial Anomaly Alert'
                            }
                        }
                    ]
                }
            else:
                # Test basique
                return {
                    'alert_type': 'test_alert',
                    'symbol': 'TEST',
                    'timestamp': current_time
                }
        
        else:
            # Payload générique
            return {
                'test': True,
                'timestamp': current_time,
                'function': function_name
            }
    
    def monitor_functions(self) -> Dict[str, Any]:
        """Surveille les métriques des fonctions Lambda"""
        logger.info("Surveillance des métriques des fonctions Lambda")
        
        results = {}
        
        for function_name in self.lambda_functions.keys():
            full_function_name = f"{self.project_name}-{self.environment}-{function_name}"
            
            try:
                # Récupération des informations de la fonction
                function_info = lambda_client.get_function(FunctionName=full_function_name)
                
                # Métriques CloudWatch (simplifiées pour l'instant)
                metrics = {
                    'last_modified': function_info['Configuration']['LastModified'],
                    'code_size': function_info['Configuration']['CodeSize'],
                    'timeout': function_info['Configuration']['Timeout'],
                    'memory_size': function_info['Configuration']['MemorySize'],
                    'runtime': function_info['Configuration']['Runtime'],
                    'state': function_info['Configuration']['State']
                }
                
                results[function_name] = {
                    'success': True,
                    'metrics': metrics
                }
                
                logger.info(f"Métriques récupérées pour {function_name}")
                
            except Exception as e:
                logger.error(f"Erreur récupération métriques {function_name}: {str(e)}")
                results[function_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results


def main():
    """Fonction principale du script"""
    parser = argparse.ArgumentParser(description='Déployeur et testeur de fonctions Lambda')
    parser.add_argument('--env', default='dev', help='Environnement (dev, staging, prod)')
    parser.add_argument('--region', default='us-east-1', help='Région AWS')
    parser.add_argument('--action', choices=['deploy', 'test', 'deploy-test', 'monitor'], 
                       default='deploy-test', help='Action à effectuer')
    parser.add_argument('--function', help='Fonction spécifique à traiter (optionnel)')
    parser.add_argument('--update-code-only', action='store_true', 
                       help='Mettre à jour seulement le code')
    
    args = parser.parse_args()
    
    try:
        deployer = LambdaDeployer(environment=args.env, region=args.region)
        
        if args.action == 'deploy':
            if args.function:
                result = deployer.deploy_function(args.function, args.update_code_only)
                print(json.dumps(result, indent=2, default=str))
            else:
                result = deployer.deploy_all_functions()
                print(json.dumps(result, indent=2, default=str))
        
        elif args.action == 'test':
            if args.function:
                result = deployer.test_function(args.function)
                print(json.dumps(result, indent=2, default=str))
            else:
                result = deployer.test_all_functions()
                print(json.dumps(result, indent=2, default=str))
        
        elif args.action == 'deploy-test':
            logger.info("=== PHASE DÉPLOIEMENT ===")
            if args.function:
                deploy_result = deployer.deploy_function(args.function, args.update_code_only)
                if deploy_result['success']:
                    logger.info("=== PHASE TEST ===")
                    test_result = deployer.test_function(args.function)
                    result = {'deploy': deploy_result, 'test': test_result}
                else:
                    result = {'deploy': deploy_result, 'test': {'skipped': 'deployment_failed'}}
            else:
                deploy_result = deployer.deploy_all_functions()
                logger.info("=== PHASE TEST ===")
                test_result = deployer.test_all_functions()
                result = {'deploy': deploy_result, 'test': test_result}
            
            print(json.dumps(result, indent=2, default=str))
        
        elif args.action == 'monitor':
            result = deployer.monitor_functions()
            print(json.dumps(result, indent=2, default=str))
        
        logger.info("Script terminé avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
