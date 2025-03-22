# Lambda Functions Module

## 📊 Vue d'ensemble

Ce module contient les fonctions AWS Lambda serverless pour le traitement des données financières en temps réel. Les fonctions sont optimisées pour gérer de gros volumes de données avec une latence minimale et une haute disponibilité.

## 🏗️ Architecture

```
lambda-functions/
├── kinesis-processor/              # Traitement des données Kinesis
│   └── lambda_function.py
├── alert-processor/                # Traitement des alertes intelligentes
│   └── lambda_function.py
├── deploy_and_test.py             # Script de déploiement et test
└── README.md                      # Ce fichier
```

## 🚀 Fonctions Lambda

### 1. Kinesis Processor (`kinesis-processor/`)

**Fonction**: `realtime-financial-{env}-kinesis-processor`

#### Fonctionnalités
- ✅ Traitement en temps réel des événements Kinesis
- ✅ Validation et nettoyage des données financières
- ✅ Calcul d'indicateurs techniques de base (SMA, tendances)
- ✅ Détection d'anomalies (prix, volume)
- ✅ Stockage optimisé S3 + DynamoDB
- ✅ Génération d'alertes pour événements critiques

#### Déclencheurs
- **Kinesis Stream**: `realtime-financial-{env}-financial-stream`
- **Batch Size**: 100 enregistrements
- **Window**: 5 secondes max

#### Configuration
- **Runtime**: Python 3.9
- **Memory**: 256 MB
- **Timeout**: 5 minutes
- **Concurrency**: 10 réservée

#### Variables d'environnement
```bash
ENVIRONMENT=dev
PROJECT_NAME=realtime-financial
S3_BUCKET=realtime-financial-dev-data-lake
DYNAMODB_TABLE=realtime-financial-dev-processed-data
SNS_ALERTS_TOPIC=arn:aws:sns:region:account:alerts-topic
```

### 2. Alert Processor (`alert-processor/`)

**Fonction**: `realtime-financial-{env}-alert-processor`

#### Fonctionnalités
- ✅ Traitement d'alertes financières intelligentes
- ✅ Classification automatique de sévérité
- ✅ Notifications multi-canal (Email, SMS, Slack, Discord)
- ✅ Gestion des préférences utilisateur
- ✅ Rate limiting anti-spam
- ✅ Escalade automatique pour alertes critiques

#### Déclencheurs
- **SNS Topic**: Alertes depuis le Kinesis Processor
- **EventBridge**: Planification périodique

#### Configuration
- **Runtime**: Python 3.9
- **Memory**: 192 MB
- **Timeout**: 3 minutes
- **Concurrency**: Selon besoin

#### Variables d'environnement
```bash
ENVIRONMENT=dev
PROJECT_NAME=realtime-financial
USER_PREFERENCES_TABLE=realtime-financial-dev-user-preferences
ALERT_HISTORY_TABLE=realtime-financial-dev-alert-history
SNS_TOPIC_ARN=arn:aws:sns:region:account:alerts-topic
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
FROM_EMAIL=alerts@realtime-financial.com
```

## 🛠️ Déploiement

### Script automatisé

Le script `deploy_and_test.py` simplifie le déploiement et les tests.

#### Déploiement complet
```bash
# Déploiement et test automatique
python deploy_and_test.py --env dev --action deploy-test

# Déploiement seulement
python deploy_and_test.py --env dev --action deploy

# Mise à jour du code seulement
python deploy_and_test.py --env dev --action deploy --update-code-only
```

#### Déploiement d'une fonction spécifique
```bash
# Kinesis processor seulement
python deploy_and_test.py --env dev --function kinesis-processor

# Alert processor seulement
python deploy_and_test.py --env dev --function alert-processor
```

#### Tests
```bash
# Test de toutes les fonctions
python deploy_and_test.py --env dev --action test

# Test d'une fonction spécifique
python deploy_and_test.py --env dev --action test --function kinesis-processor
```

#### Monitoring
```bash
# Surveillance des métriques
python deploy_and_test.py --env dev --action monitor
```

### Déploiement Terraform

Les fonctions sont également déployables via Terraform :

```hcl
module "lambda" {
  source = "./modules/lambda"
  
  project_name         = "realtime-financial"
  environment          = "dev"
  s3_bucket_name      = module.s3.bucket_name
  kinesis_stream_arn  = module.kinesis.stream_arn
  sns_alerts_topic_arn = module.sns.topic_arn
}
```

## 📋 Tests et Validation

### Tests intégrés

Le déployeur inclut des tests automatiques :

#### Kinesis Processor
```json
{
  "Records": [
    {
      "kinesis": {
        "data": "base64_encoded_financial_data",
        "partitionKey": "symbol_AAPL",
        "sequenceNumber": "12345"
      }
    }
  ]
}
```

#### Alert Processor
```json
{
  "Records": [
    {
      "EventSource": "aws:sns",
      "Sns": {
        "Message": "{\"alert_type\":\"financial_anomaly\",\"symbol\":\"TSLA\"...}",
        "Subject": "Financial Anomaly Alert"
      }
    }
  ]
}
```

### Tests manuels

#### Invocation directe
```bash
aws lambda invoke \
  --function-name realtime-financial-dev-kinesis-processor \
  --payload '{"test": true}' \
  response.json
```

#### Test avec données réelles
```python
import boto3
import json

lambda_client = boto3.client('lambda')

# Test data
test_payload = {
    "Records": [...] # Données Kinesis simulées
}

response = lambda_client.invoke(
    FunctionName='realtime-financial-dev-kinesis-processor',
    Payload=json.dumps(test_payload)
)

print(response['Payload'].read().decode())
```

## 📊 Monitoring et Métriques

### CloudWatch Metrics

Les fonctions Lambda exposent automatiquement :
- **Invocations**: Nombre d'exécutions
- **Duration**: Temps d'exécution
- **Errors**: Nombre d'erreurs
- **Throttles**: Limitations de concurrence

### Alertes configurées

#### Kinesis Processor
- ❌ **Errors > 5** en 5 minutes
- ⏱️ **Duration > 4 minutes** (proche timeout)
- 🚫 **Throttles > 1**

#### Alert Processor  
- ❌ **Errors > 3** en 5 minutes
- ⏱️ **Duration > 2.5 minutes**

### Logs CloudWatch

Format des logs :
```
/aws/lambda/realtime-financial-dev-kinesis-processor
/aws/lambda/realtime-financial-dev-alert-processor
```

Rétention : **14 jours**

### Métriques custom

Les fonctions logguent des métriques custom :

#### Kinesis Processor
- Enregistrements traités/échoués
- Anomalies détectées
- Temps de traitement par record
- Taille des batches

#### Alert Processor
- Notifications envoyées par canal
- Taux de succès par type d'alerte
- Temps de traitement des alertes

## 🔧 Configuration avancée

### Gestion des erreurs

#### Dead Letter Queue
- **SQS DLQ**: `realtime-financial-dev-lambda-dlq`
- **Retention**: 14 jours
- **Retry**: 3 tentatives avant DLQ

#### Bisecting sur erreur
```python
# Configuration automatique dans Terraform
bisect_batch_on_function_error = true
maximum_retry_attempts = 3
```

### Performance Tuning

#### Kinesis Processor
```python
# Optimisations recommandées
batch_size = 100                    # Max records par invocation
parallelization_factor = 10         # Parallélisme Kinesis
maximum_batching_window = 5         # Secondes max d'attente
reserved_concurrent_executions = 10 # Concurrence réservée
```

#### Alert Processor
```python
# Configuration légère
memory_size = 192                   # MB - suffisant pour alertes
timeout = 180                       # 3 minutes max
```

### Variables d'environnement par environnement

#### Development
```bash
ENVIRONMENT=dev
LOG_LEVEL=DEBUG
BATCH_SIZE=50
ALERT_RATE_LIMIT=10
```

#### Staging
```bash
ENVIRONMENT=staging
LOG_LEVEL=INFO
BATCH_SIZE=75
ALERT_RATE_LIMIT=5
```

#### Production
```bash
ENVIRONMENT=prod
LOG_LEVEL=WARN
BATCH_SIZE=100
ALERT_RATE_LIMIT=3
```

## 🚨 Gestion d'erreurs et troubleshooting

### Erreurs communes

#### 1. Timeout Lambda
```
Task timed out after 300.00 seconds
```
**Solutions** :
- Augmenter le timeout
- Optimiser le code de traitement
- Réduire la taille des batches

#### 2. Memory exceeded
```
Runtime exited with error: signal: killed
```
**Solutions** :
- Augmenter la mémoire allouée
- Optimiser l'utilisation mémoire
- Traiter les données par plus petits chunks

#### 3. Throttling Kinesis
```
ProvisionedThroughputExceededException
```
**Solutions** :
- Augmenter les shards Kinesis
- Optimiser le partitioning
- Réduire la fréquence de traitement

#### 4. DynamoDB throttling
```
ProvisionedThroughputExceededException on DynamoDB
```
**Solutions** :
- Utiliser mode PAY_PER_REQUEST
- Optimiser les patterns d'accès
- Implémenter un retry avec backoff

### Debugging

#### Logs détaillés
```bash
# Recherche d'erreurs
aws logs filter-log-events \
  --log-group-name "/aws/lambda/realtime-financial-dev-kinesis-processor" \
  --filter-pattern "ERROR"

# Surveillance en temps réel
aws logs tail "/aws/lambda/realtime-financial-dev-kinesis-processor" --follow
```

#### X-Ray Tracing
Activé automatiquement pour tracer :
- Appels AWS services
- Durée de chaque opération
- Goulots d'étranglement

#### Métriques enhanced
```python
# Métriques custom dans le code
import boto3
cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='RealTimeFinancial/Lambda',
    MetricData=[
        {
            'MetricName': 'ProcessedRecords',
            'Value': processed_count,
            'Unit': 'Count'
        }
    ]
)
```

## 🔮 Évolutions futures

### Améliorations prévues

1. **Auto-scaling intelligent**
   - Scaling selon les patterns de marché
   - Pré-scaling avant l'ouverture des marchés

2. **ML intégré**
   - Détection d'anomalies ML en temps réel
   - Prédictions intégrées dans le flux

3. **Caching avancé**
   - Cache Redis pour données de référence
   - Réduction des appels DynamoDB

4. **Alertes personnalisées**
   - Système de règles utilisateur complexes
   - Machine learning pour alertes personnalisées

### Optimisations techniques

1. **Code optimized**
   - Parallélisation accrue
   - Optimisations mémoire
   - Lazy loading des dépendances

2. **Infrastructure**
   - Migration vers Graviton2
   - Optimisation des VPC endpoints
   - Réduction de la latence

## 📞 Support

### Ressources de monitoring
1. **CloudWatch Dashboards** pour métriques Lambda
2. **X-Ray Service Map** pour traçabilité
3. **CloudWatch Insights** pour analyse de logs

### Ressources de debugging
1. Logs détaillés avec correlation IDs
2. Métriques custom business
3. Dead Letter Queue pour erreurs persistantes

### Escalation
- **Alertes critiques** : Notification immédiate
- **Anomalies système** : Alert sur Slack/Discord
- **Erreurs répétées** : Ticket automatique
