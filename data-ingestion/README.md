# Data Ingestion Module

## 📊 Vue d'ensemble

Ce module gère l'ingestion de données financières en temps réel depuis diverses sources externes vers notre data lake S3. Il est conçu pour être robuste, scalable et facilement extensible.

## 🏗️ Architecture

```
data-ingestion/
├── connectors/              # Connecteurs vers les APIs externes
│   ├── __init__.py
│   └── alpha_vantage_connector.py
├── config/                  # Configuration et symboles
│   └── symbols.json
├── config.py               # Configuration centralisée
├── scheduler.py            # Orchestrateur principal
├── requirements.txt        # Dépendances Python
├── env.example            # Exemple de variables d'environnement
└── README.md              # Ce fichier
```

## 🚀 Fonctionnalités

### Connecteur Alpha Vantage
- ✅ Quotes en temps réel
- ✅ Données intraday (1min, 5min, 15min, 30min, 60min)
- ✅ Données historiques quotidiennes
- ✅ Respect des limites de taux API (5 req/min gratuit)
- ✅ Gestion d'erreurs et retry logic
- ✅ Validation de qualité des données
- ✅ Stockage partitionné en S3

### Planificateur
- ✅ Exécution automatisée selon planification
- ✅ Mode manuel pour tests
- ✅ Monitoring des performances
- ✅ Gestion des erreurs et statistiques
- ✅ Support multi-connecteurs

### Stockage S3
- ✅ Partitioning intelligent par date/heure/symbole
- ✅ Métadonnées enrichies
- ✅ Format JSON optimisé
- ✅ Structure cohérente

## 📋 Configuration

### 1. Variables d'environnement

Copiez `env.example` vers `.env` et configurez:

```bash
cp env.example .env
```

Variables critiques:
```bash
ALPHA_VANTAGE_API_KEY=votre_cle_api
DATA_LAKE_BUCKET=nom_bucket_s3
AWS_REGION=us-east-1
```

### 2. Symboles à traiter

Modifiez `config/symbols.json` pour personnaliser les symboles:

```json
{
  "priority_symbols": ["AAPL", "GOOGL", "MSFT"],
  "stocks": {
    "tech": ["AAPL", "GOOGL", "MSFT", "..."]
  }
}
```

## 🛠️ Installation

1. **Créer un environnement virtuel:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

2. **Installer les dépendances:**
```bash
pip install -r requirements.txt
```

3. **Configurer les variables d'environnement:**
```bash
cp env.example .env
# Éditer .env avec vos clés API
```

## 🎯 Utilisation

### Mode planificateur (production)
```bash
python scheduler.py --mode scheduler
```

Planning automatique:
- **Temps réel**: toutes les 5 minutes
- **Historique**: quotidien à 18h00
- **Intraday**: toutes les 15 minutes

### Mode manuel (tests/développement)
```bash
# Test quotes temps réel
python scheduler.py --mode once --task real_time

# Test données historiques
python scheduler.py --mode once --task historical

# Test données intraday
python scheduler.py --mode once --task intraday
```

### Test direct du connecteur
```bash
python connectors/alpha_vantage_connector.py
```

## 📊 Structure des données

### Format de sortie S3
```
s3://bucket/alpha-vantage/
├── data_type=real_time_quote/
│   └── symbol=AAPL/
│       └── year=2025/month=04/day=02/hour=09/
│           └── AAPL_real_time_quote_20250402_091500.json
├── data_type=intraday/
└── data_type=daily/
```

### Format JSON
```json
{
  "symbol": "AAPL",
  "price": 150.25,
  "volume": 1000000,
  "timestamp": "2025-04-02T09:15:00Z",
  "data_type": "real_time_quote",
  "source": "alpha_vantage",
  "ingestion_timestamp": "2025-04-02T09:15:00Z"
}
```

## 🔍 Monitoring

### Santé du système
```python
from scheduler import DataIngestionScheduler

scheduler = DataIngestionScheduler()
health = scheduler.get_health_status()
print(health)
```

### Métriques disponibles
- Taux de succès des exécutions
- Temps d'exécution moyen
- Nombre total d'exécutions
- Statut des connecteurs
- Nombre de symboles chargés

## 🚨 Gestion d'erreurs

### Mécanismes implémentés
1. **Retry automatique** avec backoff exponentiel
2. **Rate limiting** respectant les limites API
3. **Validation** de qualité des données
4. **Logging** détaillé pour debugging
5. **Graceful degradation** en cas d'erreur

### Logs d'exemple
```
2025-04-02 09:15:00 - alpha_vantage - INFO - Requête Alpha Vantage (tentative 1): GLOBAL_QUOTE
2025-04-02 09:15:01 - alpha_vantage - INFO - Validation des données réussie
2025-04-02 09:15:02 - alpha_vantage - INFO - Données stockées: s3://bucket/alpha-vantage/...
```

## 🔮 Extensions futures

### Connecteurs additionnels prévus
- **IEX Cloud**: Données de marché en temps réel
- **CoinGecko**: Cryptomonnaies
- **Binance**: Trading crypto
- **Yahoo Finance**: Données gratuites complémentaires

### Améliorations techniques
- Support async/await pour meilleures performances
- Cache Redis pour données fréquemment accédées
- Métriques CloudWatch intégrées
- API REST pour contrôle manuel

## 📞 Support

Pour les questions techniques:
1. Vérifiez les logs d'erreur
2. Consultez le status de santé
3. Validez la configuration
4. Testez en mode manuel

## 📝 Contribuer

1. Suivez les conventions de code existantes
2. Ajoutez des tests pour nouvelles fonctionnalités
3. Documentez les changements dans le README
4. Respectez la structure de logging
