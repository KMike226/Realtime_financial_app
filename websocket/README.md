# WebSocket API pour Streaming de Données Financières
# ===================================================
# Serveur WebSocket utilisant Flask-SocketIO pour diffuser les données
# financières et les indicateurs techniques en temps réel.

## Vue d'ensemble

Cette API WebSocket fournit un streaming en temps réel de :
- **Données financières** : Prix, volume, variations des actifs
- **Indicateurs techniques** : RSI, MACD, SMA, etc.
- **Statut système** : Connexions actives, performance serveur
- **Données de symboles** : Informations complètes par symbole

## Architecture

### Serveur WebSocket (`server.py`)
- **Flask-SocketIO** pour la gestion des connexions WebSocket
- **Gestion des rooms** pour organiser les abonnements
- **Streaming en temps réel** avec simulation de données
- **Gestion des connexions** avec tracking des clients actifs
- **API REST** intégrée pour le monitoring

### Clients de test
- **Client Python** (`client_test.py`) : Test complet avec démonstration
- **Client JavaScript** (`client.js`) : Intégration frontend
- **Démonstration HTML** (`demo.html`) : Interface web complète

## Fonctionnalités

### Connexion et gestion des clients
- Connexion automatique avec génération d'ID unique
- Gestion des déconnexions avec nettoyage des ressources
- Tracking des connexions actives
- Support des transports WebSocket et polling

### Rooms de streaming
- **`financial_data`** : Données financières en temps réel
- **`technical_indicators`** : Indicateurs techniques calculés
- **`price_alerts`** : Alertes de prix (préparé pour l'avenir)
- **`system_status`** : Statut et performance du serveur

### Abonnement aux symboles
- Abonnement à des symboles spécifiques (AAPL, BTC, etc.)
- Rooms dédiées par symbole (`symbol_AAPL`, `symbol_BTC`)
- Données complètes (financières + techniques) par symbole

### Événements WebSocket

#### Événements du serveur vers le client
- `connected` : Confirmation de connexion
- `financial_data_update` : Mise à jour des données financières
- `technical_indicators_update` : Mise à jour des indicateurs
- `system_status_update` : Mise à jour du statut système
- `symbol_data` : Données complètes d'un symbole
- `room_joined` : Confirmation de jointure de room
- `symbol_subscribed` : Confirmation d'abonnement à un symbole
- `server_status` : Statut détaillé du serveur
- `pong` : Réponse au ping (test de latence)

#### Événements du client vers le serveur
- `join_room` : Rejoindre une room de streaming
- `leave_room` : Quitter une room
- `subscribe_symbol` : S'abonner à un symbole
- `unsubscribe_symbol` : Se désabonner d'un symbole
- `get_status` : Demander le statut serveur
- `ping` : Test de latence

## Installation et configuration

### Prérequis
- Python 3.8+
- pip
- Node.js (pour les tests frontend)

### Installation

```bash
# Cloner le projet
cd websocket/

# Installer les dépendances
pip install -r requirements.txt

# Configurer l'environnement
cp config.env .env
# Éditer .env avec vos paramètres

# Démarrer le serveur WebSocket
python server.py
```

### Configuration

#### Variables d'environnement principales
```bash
# Serveur WebSocket
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=5001
WEBSOCKET_DEBUG=True

# Symboles surveillés
MONITORED_SYMBOLS=AAPL,GOOGL,MSFT,AMZN,TSLA,BTC,ETH

# Configuration du streaming
STREAMING_INTERVAL=1  # Secondes entre les mises à jour
STREAMING_ENABLED=True

# Rooms disponibles
AVAILABLE_ROOMS=financial_data,technical_indicators,price_alerts,system_status
```

## Utilisation

### Démarrage du serveur

```bash
# Mode développement
python server.py

# Mode production avec Gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5001 server:app
```

### Test avec le client Python

```bash
# Exécuter le client de test
python client_test.py

# Le client exécutera automatiquement une démonstration complète
```

### Test avec le client JavaScript

```html
<!-- Inclure le client JavaScript -->
<script src="client.js"></script>

<script>
// Créer et utiliser le client
const client = new FinancialWebSocketClient('http://localhost:5001', {
    onConnect: () => {
        console.log('Connecté!');
        client.subscribeToFinancialData();
        client.subscribeToSymbol('AAPL');
    },
    onFinancialData: (data) => {
        console.log('Données financières:', data);
    }
});

// Se connecter
client.connect();
</script>
```

### Démonstration HTML

Ouvrir `demo.html` dans un navigateur pour une interface complète de test.

## API REST intégrée

Le serveur WebSocket expose également des endpoints REST pour le monitoring :

### Endpoints de monitoring
- `GET /websocket/status` : Statut du serveur WebSocket
- `GET /websocket/connections` : Liste des connexions actives
- `GET /websocket/rooms` : Rooms et leurs abonnés

### Exemples d'utilisation

```bash
# Statut du serveur
curl http://localhost:5001/websocket/status

# Connexions actives
curl http://localhost:5001/websocket/connections

# Rooms et abonnés
curl http://localhost:5001/websocket/rooms
```

## Structure des données

### Données financières
```json
{
  "symbol": "AAPL",
  "data": {
    "price": 150.25,
    "volume": 1000000,
    "change": 0.5,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Indicateurs techniques
```json
{
  "symbol": "AAPL",
  "indicators": {
    "rsi": 65.5,
    "macd": 1.2,
    "sma_20": 148.5,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Statut système
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "active_connections": 5,
  "monitored_symbols": 7,
  "streaming_active": true,
  "uptime": 3600,
  "memory_usage": "85%",
  "cpu_usage": "45%",
  "status": "healthy"
}
```

## Performance et scalabilité

### Optimisations implémentées
- **Threading** : Streaming en arrière-plan sans bloquer les connexions
- **Rooms** : Organisation des abonnements pour réduire la charge
- **Simulation efficace** : Données simulées avec variations réalistes
- **Gestion mémoire** : Nettoyage automatique des connexions fermées

### Limites actuelles (MVP)
- **Connexions simultanées** : 1000 (configurable)
- **Symboles surveillés** : 7 symboles prédéfinis
- **Intervalle de streaming** : 1 seconde (configurable)
- **Données simulées** : Pas d'intégration avec des sources réelles

### Améliorations futures
- Intégration avec Kinesis pour données réelles
- Support de plus de symboles
- Persistance des données en base
- Authentification et autorisation
- Clustering pour haute disponibilité

## Sécurité

### Mesures de sécurité actuelles
- **CORS configuré** : Domaines autorisés spécifiés
- **Limitation des connexions** : Protection contre les attaques DDoS
- **Validation des données** : Vérification des paramètres d'entrée
- **Gestion des erreurs** : Pas d'exposition d'informations sensibles

### Améliorations recommandées
- Authentification JWT
- Chiffrement des données sensibles
- Rate limiting par client
- Logs de sécurité détaillés

## Monitoring et logs

### Logs disponibles
- Connexions/déconnexions des clients
- Abonnements aux rooms et symboles
- Erreurs de streaming et de connexion
- Performance du serveur

### Métriques de monitoring
- Nombre de connexions actives
- Nombre d'abonnés par room
- Latence des événements
- Utilisation des ressources

## Déploiement

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["python", "server.py"]
```

### Variables d'environnement de production
```bash
FLASK_ENV=production
FLASK_DEBUG=False
WEBSOCKET_DEBUG=False
LOG_LEVEL=WARNING
MAX_CONNECTIONS=1000
```

### Load balancing
Pour plusieurs instances :
```bash
# Avec Nginx
upstream websocket {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
}
```

## Tests

### Tests manuels
```bash
# Test de connexion
python client_test.py

# Test de l'interface web
open demo.html

# Test des endpoints REST
curl http://localhost:5001/websocket/status
```

### Tests automatisés (futur)
```bash
# Tests unitaires
pytest tests/

# Tests d'intégration
pytest tests/integration/

# Tests de charge
pytest tests/load/
```

## Support et maintenance

### Surveillance
- Monitoring des connexions actives
- Vérification de la santé du serveur
- Alertes en cas de problème

### Maintenance
- Redémarrage périodique pour libérer la mémoire
- Rotation des logs
- Mise à jour des dépendances

## Roadmap

### Fonctionnalités futures
- [ ] Intégration avec Kinesis pour données réelles
- [ ] Support de plus de symboles (100+)
- [ ] Authentification et autorisation
- [ ] Persistance des données en base
- [ ] Clustering pour haute disponibilité
- [ ] Support des alertes de prix
- [ ] API GraphQL pour les requêtes complexes
- [ ] Chiffrement des données sensibles
- [ ] Tests automatisés complets
- [ ] Documentation API interactive
