# Module S3 Data Lake avec Partitioning Intelligent

Ce module Terraform configure un Data Lake S3 avec une structure de partitioning intelligente optimisée pour les données financières en temps réel.

## Fonctionnalités

### 🗂️ Structure de Partitioning Intelligente

Le module implémente une stratégie de partitioning hiérarchique qui organise automatiquement les données selon plusieurs dimensions :

#### Structure Raw Data
```
raw/
├── financial/
│   └── year=2025/month=03/day=15/hour=14/symbol=AAPL/
│       ├── AAPL_20250315_140530_123.json
│       └── AAPL_20250315_140532_456.json
└── crypto/
    └── year=2025/month=03/day=15/hour=14/symbol=BTC/
        ├── BTC_20250315_140530_789.json
        └── BTC_20250315_140532_012.json
```

#### Structure Processed Data
```
processed/
├── data_type=indicators/
│   └── year=2025/month=03/day=15/
│       ├── RSI_AAPL_20250315.json
│       └── MACD_BTC_20250315.json
├── data_type=alerts/
│   └── year=2025/month=03/day=15/
│       └── price_alerts_20250315.json
└── analytics/
    └── report_type=daily_summary/year=2025/month=03/
        └── market_summary_20250315.json
```

### 🔄 Lifecycle Management Automatisé

Le module configure des politiques de cycle de vie différenciées selon le type de données :

#### Données Financières Traditionnelles
- **Standard** (0-30 jours) : Accès fréquent
- **Standard IA** (30-90 jours) : Accès occasionnel  
- **Glacier** (90-365 jours) : Archivage
- **Deep Archive** (365+ jours) : Archivage long terme
- **Suppression** après 7 ans

#### Données Crypto
- **Standard** (0-7 jours) : Accès très fréquent
- **Standard IA** (7-30 jours) : Accès fréquent
- **Glacier** (30-180 jours) : Archivage
- **Deep Archive** (180+ jours) : Archivage long terme
- **Suppression** après 3 ans

#### Données Processées
- **Standard** (0-90 jours) : Accès pour analytics
- **Standard IA** (90-365 jours) : Accès occasionnel
- **Glacier** (365+ jours) : Archivage long terme
- **Suppression** après 10 ans

### 🔔 Notifications Automatiques

Le module configure des notifications S3 pour déclencher automatiquement le traitement des nouvelles données :

- **Nouvelles données financières** → Trigger Lambda de partitioning
- **Nouvelles données crypto** → Trigger Lambda de partitioning
- **Support des formats JSON** avec filtrage automatique

### 🔒 Sécurité et Contrôle d'Accès

#### Chiffrement
- **AES-256** pour tous les objets
- **Chiffrement côté serveur** automatique
- **Bucket key enabled** pour optimiser les coûts

#### Politiques d'Accès
- **Blocage des accès publics** complet
- **Accès rôle-basé** pour les services de traitement
- **Permissions granulaires** par type de données

## Variables d'Entrée

| Variable | Type | Description | Défaut |
|----------|------|-------------|--------|
| `project_name` | string | Nom du projet | - |
| `environment` | string | Environnement (dev, staging, prod) | - |
| `partition_lambda_arn` | string | ARN de la Lambda de partitioning | "" |
| `processing_role_arn` | string | ARN du rôle de traitement | "*" |
| `analytics_role_arn` | string | ARN du rôle d'analytics | "*" |

## Outputs

| Output | Description |
|--------|-------------|
| `bucket_name` | Nom du bucket Data Lake |
| `bucket_arn` | ARN du bucket Data Lake |
| `processed_bucket_name` | Nom du bucket données processées |
| `processed_bucket_arn` | ARN du bucket données processées |
| `bucket_domain_name` | Nom de domaine du bucket |
| `partition_structure` | Structure de partitioning recommandée |
| `lifecycle_policies` | Résumé des politiques de cycle de vie |

## Utilisation

### Configuration de Base

```hcl
module "data_lake" {
  source = "./modules/s3"

  project_name = "financial-pipeline"
  environment  = "dev"
}
```

### Configuration Avancée avec Lambda

```hcl
module "data_lake" {
  source = "./modules/s3"

  project_name         = "financial-pipeline"
  environment          = "dev"
  partition_lambda_arn = aws_lambda_function.partition_lambda.arn
  processing_role_arn  = aws_iam_role.processing_role.arn
  analytics_role_arn   = aws_iam_role.analytics_role.arn
}
```

## Script de Partitioning

Le module inclut un script Python (`scripts/partition-data.py`) pour gérer le partitioning intelligent :

### Utilisation en Ligne de Commande

```bash
# Partitioning d'un fichier spécifique
python scripts/partition-data.py --bucket my-data-lake --file raw/upload/data.json

# Partitioning en lot
python scripts/partition-data.py --bucket my-data-lake --prefix raw/upload/ --max-files 50
```

### Utilisation comme Lambda

Le script peut être déployé comme fonction AWS Lambda pour traiter automatiquement les nouvelles données via les notifications S3.

### Fonctionnalités du Script

- **Détection automatique** du type de données
- **Extraction intelligente** des métadonnées (timestamp, symbole, etc.)
- **Gestion des erreurs** robuste
- **Support multi-format** de timestamps
- **Évitement des doublons** et optimisations

## Optimisations de Performance

### Requêtes Efficaces

La structure de partitioning permet des requêtes optimisées :

```sql
-- Requête optimisée avec partition pruning
SELECT * FROM financial_data 
WHERE year = 2025 
  AND month = 3 
  AND day = 15 
  AND symbol = 'AAPL'
```

### Stratégies de Lecture

- **Lecture parallèle** par partition
- **Filtrage précoce** sur les métadonnées
- **Minimisation du scan** de données

## Monitoring et Alertes

### Métriques CloudWatch

Le module supporte le monitoring via :
- **Nombre d'objets** par partition
- **Taille des données** par type
- **Latence d'accès** aux données
- **Coûts de stockage** par lifecycle tier

### Alertes Recommandées

- **Croissance anormale** de certaines partitions
- **Échecs de partitioning** répétés  
- **Dépassement des coûts** de stockage
- **Latence d'accès** élevée

## Maintenance

### Nettoyage Périodique

```bash
# Vérification de l'intégrité des partitions
aws s3 ls s3://bucket-name/raw/ --recursive | grep -v "year="

# Statistiques par partition
aws s3 ls s3://bucket-name/raw/financial/ --recursive --summarize
```

### Optimisation des Coûts

- **Révision périodique** des policies de lifecycle
- **Analyse des patterns** d'accès aux données
- **Ajustement des transitions** selon l'usage réel

## Bonnes Pratiques

### Nomenclature des Fichiers

- **Format recommandé** : `SYMBOL_YYYYMMDD_HHMMSS_microseconds.json`
- **Caractères autorisés** : alphanumériques, tirets, underscores
- **Casse recommandée** : symboles en majuscules

### Structure des Données JSON

```json
{
  "timestamp": "2025-03-15T14:30:45.123Z",
  "symbol": "AAPL",
  "price": 150.25,
  "volume": 1000000,
  "source": "alpha_vantage",
  "data_type": "quote"
}
```

### Gestion des Erreurs

- **Retry automatique** pour les erreurs temporaires
- **Dead letter queue** pour les échecs persistants
- **Logging détaillé** pour le debugging
- **Alertes** sur les patterns d'erreurs

## Troubleshooting

### Problèmes Courants

#### Permissions Insuffisantes
```bash
# Vérifier les permissions IAM
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::account:role/role-name \
  --action-names s3:PutObject \
  --resource-arns arn:aws:s3:::bucket-name/raw/financial/*
```

#### Notifications Non Déclenchées
```bash
# Vérifier la configuration des notifications
aws s3api get-bucket-notification-configuration --bucket bucket-name
```

#### Performance de Requête
```bash
# Analyser la distribution des partitions
aws s3 ls s3://bucket-name/raw/financial/ --recursive | \
  awk -F'/' '{print $3"/"$4"/"$5}' | sort | uniq -c
```

## Migration et Évolution

### Migration depuis Structure Existante

Le script de partitioning supporte la migration de données existantes :

```bash
# Migration progressive par batch
python scripts/partition-data.py \
  --bucket existing-bucket \
  --prefix legacy/ \
  --max-files 100
```

### Évolution du Schema

- **Backward compatibility** maintenue
- **Versioning** des structures de partitioning
- **Migration progressive** des données legacy
- **Tests de regression** automatisés
