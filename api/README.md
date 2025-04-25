# API REST pour Données Financières
# =================================
# API Flask pour la gestion des données financières et la configuration système.

## Vue d'ensemble

Cette API REST fournit des endpoints complets pour :
- **Gestion des données financières** : CRUD complet avec filtres et pagination
- **Configuration système** : Gestion dynamique de la configuration
- **Authentification** : JWT avec gestion des utilisateurs
- **Indicateurs techniques** : Stockage et récupération des calculs

## Architecture

### Modèles de données
- **FinancialData** : Données de prix et volume des actifs
- **TechnicalIndicator** : Indicateurs techniques calculés (RSI, MACD, etc.)
- **SystemConfig** : Configuration système dynamique
- **User** : Gestion des utilisateurs et authentification

### Endpoints principaux

#### Données financières (`/api/financial-data/`)
- `GET /` : Liste avec filtres et pagination
- `GET /<id>` : Récupération par ID
- `POST /` : Création d'une donnée
- `PUT /<id>` : Mise à jour
- `DELETE /<id>` : Suppression
- `POST /batch` : Création en lot
- `GET /symbols` : Symboles disponibles
- `GET /sources` : Sources disponibles
- `GET /stats` : Statistiques

#### Configuration système (`/api/system-config/`)
- `GET /` : Liste des configurations
- `GET /<id>` : Configuration par ID
- `GET /key/<key>` : Configuration par clé
- `POST /` : Création
- `PUT /<id>` : Mise à jour
- `DELETE /<id>` : Suppression
- `POST /batch` : Création en lot
- `GET /export` : Export JSON
- `POST /import` : Import JSON

#### Authentification (`/api/auth/`)
- `POST /register` : Enregistrement utilisateur
- `POST /login` : Connexion
- `GET /profile` : Profil utilisateur
- `PUT /profile` : Mise à jour profil
- `POST /logout` : Déconnexion
- `POST /verify` : Vérification token
- `GET /users` : Liste utilisateurs (admin)
- `GET /stats` : Statistiques utilisateurs

## Installation et configuration

### Prérequis
- Python 3.8+
- pip
- Base de données (SQLite, PostgreSQL, MySQL)

### Installation

```bash
# Cloner le projet
cd api/

# Installer les dépendances
pip install -r requirements.txt

# Configurer l'environnement
cp env.example .env
# Éditer .env avec vos paramètres

# Initialiser la base de données
python main.py
```

### Configuration de la base de données

#### SQLite (développement)
```bash
DATABASE_URL=sqlite:///financial_app.db
```

#### PostgreSQL (production)
```bash
DATABASE_URL=postgresql://username:password@localhost/financial_app
```

#### MySQL
```bash
DATABASE_URL=mysql+pymysql://username:password@localhost/financial_app
```

## Utilisation

### Démarrage de l'API

```bash
# Mode développement
python main.py

# Mode production avec Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

### Authentification

1. **Enregistrement d'un utilisateur** :
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

2. **Connexion** :
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

3. **Utilisation du token** :
```bash
curl -X GET http://localhost:5000/api/financial-data/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Exemples d'utilisation

#### Création de données financières
```bash
curl -X POST http://localhost:5000/api/financial-data/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "symbol": "AAPL",
    "timestamp": "2024-01-01T12:00:00Z",
    "price": 150.25,
    "volume": 1000000,
    "open_price": 149.50,
    "high_price": 151.00,
    "low_price": 148.75,
    "close_price": 150.25,
    "source": "Alpha Vantage"
  }'
```

#### Récupération avec filtres
```bash
curl -X GET "http://localhost:5000/api/financial-data/?symbol=AAPL&limit=10&sort=timestamp_desc" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Configuration système
```bash
curl -X POST http://localhost:5000/api/system-config/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "config_key": "api_rate_limit",
    "config_value": "2000",
    "config_type": "int",
    "description": "Limite de requêtes par heure"
  }'
```

## Sécurité

### Authentification JWT
- Tokens d'accès avec expiration configurable
- Validation des tokens sur toutes les routes protégées
- Gestion des utilisateurs actifs/inactifs

### Validation des données
- Validation stricte des types de données
- Vérification des formats (email, dates, etc.)
- Limitation de la taille des requêtes

### CORS
- Configuration CORS pour les domaines autorisés
- Support des requêtes cross-origin sécurisées

## Monitoring et logs

### Logs
- Logging structuré avec niveaux configurables
- Logs d'authentification et d'erreurs
- Traçabilité des opérations CRUD

### Santé de l'API
- Endpoint `/health` pour vérification de l'état
- Vérification de la connexion base de données
- Statut des services dépendants

## Déploiement

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "main.py"]
```

### Variables d'environnement de production
```bash
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-production-jwt-key
DATABASE_URL=postgresql://user:pass@db:5432/financial_app
```

## Tests

### Exécution des tests
```bash
# Tests unitaires
pytest tests/

# Tests avec couverture
pytest --cov=api tests/

# Tests d'intégration
pytest tests/integration/
```

### Tests d'API
```bash
# Test des endpoints
curl -X GET http://localhost:5000/api/status
curl -X GET http://localhost:5000/health
```

## Support et maintenance

### Sauvegarde de la base de données
```bash
# SQLite
cp financial_app.db backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump financial_app > backup_$(date +%Y%m%d).sql
```

### Migration de la base de données
```bash
# Avec Alembic
alembic upgrade head
```

### Monitoring des performances
- Utilisation de Flask-Caching pour les requêtes fréquentes
- Pagination pour éviter les requêtes trop lourdes
- Index sur les colonnes fréquemment utilisées

## Roadmap

### Fonctionnalités futures
- [ ] Support des WebSockets pour les données temps réel
- [ ] Cache Redis pour améliorer les performances
- [ ] Rate limiting avancé par utilisateur
- [ ] Documentation API automatique avec Swagger
- [ ] Support des webhooks pour les notifications
- [ ] Chiffrement des données sensibles
- [ ] Audit trail complet des modifications
