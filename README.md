# 📈 Pipeline de Données Financières Temps Réel

> **Architecture moderne de Data Engineering avec AWS et Apache Spark**  
> Traitement en temps réel de données boursières et crypto-monnaies

## 🎯 Vue d'Ensemble

Pipeline complète de données financières démontrant l'expertise en Data Engineering moderne. Le système ingère, traite et analyse les données de marchés financiers en temps réel pour fournir des insights actionnables et des alertes automatisées.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │ -> │  Kinesis/Kafka   │ -> │  Apache Spark   │
│ (APIs Externes) │    │   (Ingestion)    │    │  (Processing)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    Grafana      │ <- │   Snowflake      │ <- │      S3         │
│  (Dashboards)   │    │ (Data Warehouse) │    │  (Data Lake)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Stack Technique

### **Infrastructure Cloud**
- **AWS**: Services managés (Kinesis, S3, EMR, ECS, Lambda)
- **Terraform**: Infrastructure as Code
- **GitHub Actions**: CI/CD automatisé
- **Docker**: Containerisation des services

### **Data Engineering**
- **Apache Spark**: Structured Streaming pour traitement temps réel
- **AWS Kinesis**: Ingestion haute fréquence
- **S3**: Data Lake avec partitioning intelligent
- **Snowflake**: Data Warehouse pour analytics

### **Analytics & ML**
- **MLflow**: Gestion des modèles ML
- **Scikit-learn/TensorFlow**: Modèles de prédiction
- **Grafana**: Dashboards temps réel
- **Prometheus**: Métriques et monitoring

## 📊 Fonctionnalités

### **⚡ Ingestion Temps Réel**
- Connecteurs API multiples (Alpha Vantage, CoinGecko, Binance)
- Stream processing haute fréquence
- Validation et nettoyage automatique des données

### **🧠 Analytics Avancées**
- Calcul d'indicateurs techniques (RSI, MACD, Bollinger Bands)
- Détection d'anomalies par ML
- Prédictions de tendances de prix

### **📈 Visualisation**
- Dashboards interactifs temps réel
- Alertes intelligentes multi-canal
- Interface responsive mobile

### **🔒 Production Ready**
- Security hardening AWS IAM
- Monitoring complet CloudWatch
- High availability multi-AZ

## 🔧 Installation

### Prérequis
```bash
# AWS CLI configuré
aws configure

# Terraform >= 1.0
terraform --version

# Docker
docker --version
```

### Déploiement
```bash
# Cloner le repository
git clone <repository-url>
cd Realtime_financial_app

# Configuration environnement
cp .env.example .env
# Éditer .env avec vos API keys

# Déployer l'infrastructure
cd infrastructure/terraform/environments/dev
terraform init
terraform plan
terraform apply
```

## 📁 Structure du Projet

```
├── infrastructure/          # Infrastructure as Code
│   ├── terraform/          # Modules Terraform
│   └── docker/             # Dockerfiles
├── data-ingestion/         # Services d'ingestion
├── stream-processing/      # Jobs Spark temps réel
├── ml-pipeline/            # Machine Learning
├── dashboards/             # Grafana & visualisation
├── apis/                   # Services API
└── monitoring/             # Observabilité
```

## 🎯 Objectifs Techniques

- **Latence**: < 1 seconde pour ingestion
- **Throughput**: > 10K événements/seconde  
- **Uptime**: 99.9% disponibilité
- **Accuracy**: > 95% détection anomalies

## 📈 Feuille de Route

- [x] **Phase 1**: Infrastructure de base
- [ ] **Phase 2**: Stream processing multi-sources
- [ ] **Phase 3**: Pipeline ML et analytics
- [ ] **Phase 4**: Production hardening

## 🤝 Contribution

Les contributions sont les bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines.

## 📄 License

MIT License - voir [LICENSE](LICENSE) pour détails.

---

**Développé avec ❤️ pour démontrer l'excellence en Data Engineering moderne**