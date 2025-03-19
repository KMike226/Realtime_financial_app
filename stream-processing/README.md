# Stream Processing Module

## 📊 Vue d'ensemble

Ce module gère le traitement de flux de données financières en temps réel via AWS Kinesis. Il fournit une infrastructure robuste pour l'ingestion, le traitement et l'acheminement des données vers différents systèmes.

## 🏗️ Architecture

```
stream-processing/
├── kinesis_client.py              # Client Kinesis avancé
├── alpha_vantage_to_kinesis.py    # Intégration Alpha Vantage → Kinesis
├── spark-jobs/                    # Jobs Spark Streaming (à venir)
├── technical-indicators/          # Calculs d'indicateurs techniques
└── README.md                      # Ce fichier
```

## 🚀 Fonctionnalités

### Client Kinesis (`kinesis_client.py`)
- ✅ Support multi-streams (financial, crypto, events)
- ✅ Batching automatique pour optimiser les performances
- ✅ Retry logic avec backoff exponentiel
- ✅ Partitioning intelligent par symbole/type
- ✅ Monitoring et métriques en temps réel
- ✅ Health checks automatisés

### Intégration Alpha Vantage (`alpha_vantage_to_kinesis.py`)
- ✅ Pipeline Alpha Vantage → Kinesis
- ✅ Traitement cotations temps réel
- ✅ Traitement données intraday
- ✅ Mode batch mixte (financial + crypto)
- ✅ Validation et enrichissement des données
- ✅ Monitoring intégré

## ⚙️ Configuration

### Variables d'environnement
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Alpha Vantage
ALPHA_VANTAGE_API_KEY=your_api_key

# Streams Kinesis (auto-générés selon l'environnement)
KINESIS_FINANCIAL_STREAM=realtime-financial-dev-financial-stream
KINESIS_CRYPTO_STREAM=realtime-financial-dev-crypto-stream
KINESIS_EVENTS_STREAM=realtime-financial-dev-events-stream
```

### Streams Kinesis configurés

1. **Financial Stream** (`financial-stream`)
   - Données boursières traditionnelles
   - Cotations temps réel
   - Données historiques et intraday
   - Partitioning par symbole

2. **Crypto Stream** (`crypto-stream`)
   - Données cryptomonnaies
   - Prix et volumes crypto
   - Partitioning par crypto + dispersion temporelle

3. **Events Stream** (`events-stream`)
   - Événements système
   - Alertes et notifications
   - Logs d'activité
   - Partitioning par type d'événement

## 🎯 Utilisation

### Client Kinesis Direct

```python
from kinesis_client import create_kinesis_client

# Création du client
client = create_kinesis_client(environment="dev")

# Envoi de données financières
financial_data = {
    'symbol': 'AAPL',
    'price': 150.25,
    'volume': 1000000,
    'timestamp': '2025-04-02T09:15:00Z'
}

result = client.send_financial_data(financial_data)
print(f"Envoi réussi: {result['successful_records']} enregistrements")

# Health check
health = client.health_check()
print(f"État des streams: {health['overall_status']}")
```

### Intégration Alpha Vantage → Kinesis

```python
from alpha_vantage_to_kinesis import AlphaVantageKinesisIntegration

# Initialisation
integration = AlphaVantageKinesisIntegration(
    alpha_vantage_api_key="your_api_key",
    environment="dev"
)

# Traitement cotations temps réel
symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN']
results = integration.process_real_time_quotes(symbols)

print(f"Traité: {results['symbols_processed']}/{len(symbols)} symboles")

# Batch mixte financier + crypto
mixed_results = integration.process_mixed_batch(
    financial_symbols=['AAPL', 'TSLA'],
    crypto_symbols=['BTC', 'ETH']
)
```

## 📋 Scripts et Outils

### Test du client Kinesis
```bash
# Test basique
python kinesis_client.py --env dev --test-type financial

# Test complet (tous les streams)
python kinesis_client.py --env dev --test-type all
```

### Test de l'intégration Alpha Vantage
```bash
# Cotations temps réel
python alpha_vantage_to_kinesis.py \
  --api-key YOUR_API_KEY \
  --env dev \
  --mode quotes \
  --symbols AAPL GOOGL MSFT

# Données intraday
python alpha_vantage_to_kinesis.py \
  --api-key YOUR_API_KEY \
  --env dev \
  --mode intraday \
  --symbols AAPL TSLA

# Mode mixte avec crypto
python alpha_vantage_to_kinesis.py \
  --api-key YOUR_API_KEY \
  --env dev \
  --mode mixed \
  --symbols AAPL GOOGL \
  --crypto-symbols BTC ETH

# Monitoring
python alpha_vantage_to_kinesis.py \
  --api-key YOUR_API_KEY \
  --env dev \
  --mode monitoring
```

## 📊 Monitoring et Métriques

### Métriques du client Kinesis
- Nombre d'enregistrements envoyés/échoués
- Taux de succès global
- Latence moyenne d'envoi
- Statut des streams
- Nombre de batches traités

### Métriques d'intégration
- Données récupérées depuis Alpha Vantage
- Données envoyées vers Kinesis
- Temps de traitement
- Taux d'erreur

### Health Checks
```python
# Vérification santé Kinesis
health = client.health_check()
# Résultat: {'overall_status': 'healthy', 'streams': {...}}

# Monitoring complet intégration
monitoring = integration.run_monitoring_check()
# Inclut: santé Kinesis + métriques intégration + recommandations
```

## 🔧 Partitioning Strategy

### Financial Stream
- **Clé**: `symbol_{SYMBOL}_{hash % 100}`
- **Objectif**: Distribution équilibrée par symbole
- **Exemple**: `symbol_AAPL_42`

### Crypto Stream
- **Clé**: `crypto_{SYMBOL}_{timestamp_hash % 100}`
- **Objectif**: Distribution par crypto + dispersion temporelle
- **Exemple**: `crypto_BTC_73`

### Events Stream
- **Clé**: `event_{EVENT_TYPE}_{hash % 10}`
- **Objectif**: Distribution par type d'événement
- **Exemple**: `event_price_alert_5`

## 🔒 Sécurité et Fiabilité

### Retry Logic
- **Max retries**: 3 tentatives
- **Backoff**: Exponentiel (1s, 2s, 4s)
- **Gestion errors**: Logging détaillé + métriques

### Validation des données
- Champs requis présents
- Valeurs dans les ranges attendus
- Format timestamp cohérent
- Détection anomalies de base

### Chiffrement
- Transport: HTTPS/TLS pour toutes les APIs
- At-rest: Chiffrement KMS pour streams Kinesis
- Clés API: Variables d'environnement sécurisées

## 🚀 Performances

### Optimisations
- **Batching**: Jusqu'à 500 enregistrements par batch
- **Compression**: GZIP pour Kinesis Firehose
- **Partitioning**: Distribution équilibrée des charges
- **Connection pooling**: Réutilisation des connexions

### Limites et Quotas
- **Kinesis**: 1000 records/sec par shard
- **Alpha Vantage**: 5 requêtes/minute (gratuit)
- **Batch size**: 500 records max (limite AWS)
- **Payload size**: 1MB max par record

## 🔮 Évolutions futures

### Prochaines étapes
1. **Jobs Spark Streaming** pour traitement en temps réel
2. **Connecteurs additionnels** (CoinGecko, Binance)
3. **Indicateurs techniques** calculés en streaming
4. **Auto-scaling** des shards Kinesis
5. **Alertes CloudWatch** intégrées

### Améliorations prévues
- **Cache Redis** pour optimiser les performances
- **Dead Letter Queues** pour les erreurs persistantes
- **Métriques CloudWatch** custom
- **Dashboard Grafana** pour monitoring
- **Tests d'intégration** automatisés

## 🐛 Debugging

### Logs utiles
```bash
# Logs du client Kinesis
grep "kinesis_client" /var/log/application.log

# Logs d'intégration Alpha Vantage
grep "alpha_vantage_to_kinesis" /var/log/application.log

# Erreurs Kinesis spécifiques
grep "ProvisionedThroughputExceededException" /var/log/application.log
```

### Problèmes courants

1. **Rate limiting Alpha Vantage**
   - Symptôme: `API call frequency` dans les logs
   - Solution: Vérifier quota API, ajuster délais

2. **Throughput exceeded Kinesis**
   - Symptôme: `WriteProvisionedThroughputExceeded`
   - Solution: Augmenter nombre de shards ou optimiser batching

3. **Données invalides**
   - Symptôme: Enregistrements marqués `ProcessingFailed`
   - Solution: Vérifier validation des données

## 📞 Support

Pour les questions techniques:
1. Vérifiez les health checks
2. Consultez les métriques de monitoring
3. Analysez les logs d'erreur
4. Testez en mode isolation avec un seul symbole