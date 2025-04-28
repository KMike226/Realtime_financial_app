"""
Serveur WebSocket pour streaming de données financières en temps réel
====================================================================
Serveur WebSocket utilisant Flask-SocketIO pour diffuser les données
financières et les indicateurs techniques en temps réel aux clients.
"""

from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from flask_cors import CORS
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio
import random
import uuid

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de l'application Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'websocket-secret-key-change-in-production'

# Configuration CORS pour WebSocket
CORS(app, origins=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"])

# Initialisation de SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Stockage des connexions actives
active_connections = {}
room_subscriptions = {
    'financial_data': set(),  # Clients abonnés aux données financières
    'technical_indicators': set(),  # Clients abonnés aux indicateurs techniques
    'price_alerts': set(),  # Clients abonnés aux alertes de prix
    'system_status': set()  # Clients abonnés au statut système
}

# Configuration des symboles surveillés
monitored_symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'BTC', 'ETH']

# Données simulées pour le streaming (en production, ces données viendraient de Kinesis)
mock_financial_data = {
    'AAPL': {'price': 150.25, 'volume': 1000000, 'change': 0.5},
    'GOOGL': {'price': 2800.50, 'volume': 500000, 'change': -1.2},
    'MSFT': {'price': 300.75, 'volume': 800000, 'change': 0.8},
    'AMZN': {'price': 3200.00, 'volume': 300000, 'change': -0.3},
    'TSLA': {'price': 800.25, 'volume': 1200000, 'change': 2.1},
    'BTC': {'price': 45000.00, 'volume': 50000, 'change': 1.5},
    'ETH': {'price': 3000.00, 'volume': 75000, 'change': 0.9}
}

mock_technical_indicators = {
    'AAPL': {'rsi': 65.5, 'macd': 1.2, 'sma_20': 148.5},
    'GOOGL': {'rsi': 45.2, 'macd': -0.8, 'sma_20': 2820.0},
    'MSFT': {'rsi': 70.1, 'macd': 2.1, 'sma_20': 298.5},
    'AMZN': {'rsi': 55.8, 'macd': 0.5, 'sma_20': 3210.0},
    'TSLA': {'rsi': 75.3, 'macd': 3.2, 'sma_20': 785.0},
    'BTC': {'rsi': 60.0, 'macd': 1500.0, 'sma_20': 44000.0},
    'ETH': {'rsi': 58.7, 'macd': 200.0, 'sma_20': 2950.0}
}


class WebSocketManager:
    """
    Gestionnaire principal pour les connexions WebSocket et le streaming de données.
    """
    
    def __init__(self):
        self.is_streaming = False
        self.stream_thread = None
        self.connection_count = 0
        
    def start_streaming(self):
        """Démarre le streaming de données en arrière-plan."""
        if not self.is_streaming:
            self.is_streaming = True
            self.stream_thread = threading.Thread(target=self._stream_data_loop, daemon=True)
            self.stream_thread.start()
            logger.info("Streaming de données démarré")
    
    def stop_streaming(self):
        """Arrête le streaming de données."""
        self.is_streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=1)
        logger.info("Streaming de données arrêté")
    
    def _stream_data_loop(self):
        """Boucle principale de streaming des données."""
        while self.is_streaming:
            try:
                # Streaming des données financières
                if room_subscriptions['financial_data']:
                    self._stream_financial_data()
                
                # Streaming des indicateurs techniques
                if room_subscriptions['technical_indicators']:
                    self._stream_technical_indicators()
                
                # Streaming du statut système
                if room_subscriptions['system_status']:
                    self._stream_system_status()
                
                # Attente avant la prochaine itération
                time.sleep(1)  # 1 seconde pour simuler le temps réel
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de streaming: {str(e)}")
                time.sleep(5)  # Attente en cas d'erreur
    
    def _stream_financial_data(self):
        """Stream les données financières aux clients abonnés."""
        for symbol in monitored_symbols:
            if symbol in mock_financial_data:
                # Simulation de variation de prix
                current_data = mock_financial_data[symbol].copy()
                current_data['price'] += random.uniform(-0.5, 0.5)
                current_data['volume'] += random.randint(-10000, 10000)
                current_data['change'] = random.uniform(-2.0, 2.0)
                current_data['timestamp'] = datetime.utcnow().isoformat()
                current_data['symbol'] = symbol
                
                # Mise à jour des données simulées
                mock_financial_data[symbol] = current_data
                
                # Envoi aux clients abonnés
                socketio.emit('financial_data_update', {
                    'symbol': symbol,
                    'data': current_data,
                    'timestamp': current_data['timestamp']
                }, room='financial_data')
    
    def _stream_technical_indicators(self):
        """Stream les indicateurs techniques aux clients abonnés."""
        for symbol in monitored_symbols:
            if symbol in mock_technical_indicators:
                # Simulation de variation des indicateurs
                current_indicators = mock_technical_indicators[symbol].copy()
                current_indicators['rsi'] += random.uniform(-2.0, 2.0)
                current_indicators['macd'] += random.uniform(-0.1, 0.1)
                current_indicators['sma_20'] += random.uniform(-1.0, 1.0)
                current_indicators['timestamp'] = datetime.utcnow().isoformat()
                current_indicators['symbol'] = symbol
                
                # Mise à jour des indicateurs simulés
                mock_technical_indicators[symbol] = current_indicators
                
                # Envoi aux clients abonnés
                socketio.emit('technical_indicators_update', {
                    'symbol': symbol,
                    'indicators': current_indicators,
                    'timestamp': current_indicators['timestamp']
                }, room='technical_indicators')
    
    def _stream_system_status(self):
        """Stream le statut système aux clients abonnés."""
        system_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'active_connections': len(active_connections),
            'monitored_symbols': len(monitored_symbols),
            'streaming_active': self.is_streaming,
            'uptime': time.time(),
            'memory_usage': '85%',  # Simulation
            'cpu_usage': '45%',    # Simulation
            'status': 'healthy'
        }
        
        socketio.emit('system_status_update', system_status, room='system_status')


# Instance du gestionnaire WebSocket
websocket_manager = WebSocketManager()


@socketio.on('connect')
def handle_connect():
    """
    Gestionnaire de connexion WebSocket.
    Enregistre le client et démarre le streaming si nécessaire.
    """
    client_id = str(uuid.uuid4())
    active_connections[client_id] = {
        'id': client_id,
        'connected_at': datetime.utcnow().isoformat(),
        'rooms': [],
        'ip': request.remote_addr
    }
    
    websocket_manager.connection_count = len(active_connections)
    
    logger.info(f"Client connecté: {client_id} depuis {request.remote_addr}")
    
    # Envoi de la confirmation de connexion
    emit('connected', {
        'client_id': client_id,
        'message': 'Connexion WebSocket établie',
        'timestamp': datetime.utcnow().isoformat(),
        'available_rooms': list(room_subscriptions.keys())
    })
    
    # Démarrage du streaming si c'est la première connexion
    if len(active_connections) == 1:
        websocket_manager.start_streaming()


@socketio.on('disconnect')
def handle_disconnect():
    """
    Gestionnaire de déconnexion WebSocket.
    Nettoie les données du client et arrête le streaming si nécessaire.
    """
    # Trouver le client qui se déconnecte
    client_id = None
    for cid, client_data in active_connections.items():
        if client_data['ip'] == request.remote_addr:
            client_id = cid
            break
    
    if client_id:
        # Retirer le client de toutes les rooms
        client_rooms = active_connections[client_id]['rooms']
        for room in client_rooms:
            leave_room(room)
            room_subscriptions[room].discard(client_id)
        
        # Supprimer le client des connexions actives
        del active_connections[client_id]
        websocket_manager.connection_count = len(active_connections)
        
        logger.info(f"Client déconnecté: {client_id}")
        
        # Arrêter le streaming si plus de connexions
        if len(active_connections) == 0:
            websocket_manager.stop_streaming()


@socketio.on('join_room')
def handle_join_room(data):
    """
    Gestionnaire pour rejoindre une room de streaming.
    
    Args:
        data: Dictionnaire contenant 'room' (nom de la room)
    """
    try:
        room = data.get('room')
        if not room:
            emit('error', {'message': 'Nom de room requis'})
            return
        
        if room not in room_subscriptions:
            emit('error', {'message': f'Room "{room}" non disponible'})
            return
        
        # Trouver le client
        client_id = None
        for cid, client_data in active_connections.items():
            if client_data['ip'] == request.remote_addr:
                client_id = cid
                break
        
        if not client_id:
            emit('error', {'message': 'Client non identifié'})
            return
        
        # Rejoindre la room
        join_room(room)
        room_subscriptions[room].add(client_id)
        active_connections[client_id]['rooms'].append(room)
        
        logger.info(f"Client {client_id} a rejoint la room {room}")
        
        emit('room_joined', {
            'room': room,
            'message': f'Abonné à {room}',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Envoyer les données actuelles si disponibles
        if room == 'financial_data':
            emit('current_financial_data', {
                'data': mock_financial_data,
                'timestamp': datetime.utcnow().isoformat()
            })
        elif room == 'technical_indicators':
            emit('current_technical_indicators', {
                'indicators': mock_technical_indicators,
                'timestamp': datetime.utcnow().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Erreur lors de la jointure de room: {str(e)}")
        emit('error', {'message': 'Erreur lors de la jointure de room'})


@socketio.on('leave_room')
def handle_leave_room(data):
    """
    Gestionnaire pour quitter une room de streaming.
    
    Args:
        data: Dictionnaire contenant 'room' (nom de la room)
    """
    try:
        room = data.get('room')
        if not room:
            emit('error', {'message': 'Nom de room requis'})
            return
        
        # Trouver le client
        client_id = None
        for cid, client_data in active_connections.items():
            if client_data['ip'] == request.remote_addr:
                client_id = cid
                break
        
        if not client_id:
            emit('error', {'message': 'Client non identifié'})
            return
        
        # Quitter la room
        leave_room(room)
        room_subscriptions[room].discard(client_id)
        if room in active_connections[client_id]['rooms']:
            active_connections[client_id]['rooms'].remove(room)
        
        logger.info(f"Client {client_id} a quitté la room {room}")
        
        emit('room_left', {
            'room': room,
            'message': f'Désabonné de {room}',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la sortie de room: {str(e)}")
        emit('error', {'message': 'Erreur lors de la sortie de room'})


@socketio.on('subscribe_symbol')
def handle_subscribe_symbol(data):
    """
    Gestionnaire pour s'abonner à un symbole spécifique.
    
    Args:
        data: Dictionnaire contenant 'symbol' (symbole à surveiller)
    """
    try:
        symbol = data.get('symbol')
        if not symbol:
            emit('error', {'message': 'Symbole requis'})
            return
        
        symbol = symbol.upper()
        
        if symbol not in monitored_symbols:
            emit('error', {'message': f'Symbole "{symbol}" non surveillé'})
            return
        
        # Trouver le client
        client_id = None
        for cid, client_data in active_connections.items():
            if client_data['ip'] == request.remote_addr:
                client_id = cid
                break
        
        if not client_id:
            emit('error', {'message': 'Client non identifié'})
            return
        
        # Créer une room spécifique au symbole
        symbol_room = f'symbol_{symbol}'
        join_room(symbol_room)
        
        logger.info(f"Client {client_id} s'est abonné au symbole {symbol}")
        
        emit('symbol_subscribed', {
            'symbol': symbol,
            'message': f'Abonné aux données de {symbol}',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Envoyer les données actuelles du symbole
        if symbol in mock_financial_data:
            emit('symbol_data', {
                'symbol': symbol,
                'financial_data': mock_financial_data[symbol],
                'technical_indicators': mock_technical_indicators.get(symbol, {}),
                'timestamp': datetime.utcnow().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'abonnement au symbole: {str(e)}")
        emit('error', {'message': 'Erreur lors de l\'abonnement au symbole'})


@socketio.on('unsubscribe_symbol')
def handle_unsubscribe_symbol(data):
    """
    Gestionnaire pour se désabonner d'un symbole spécifique.
    
    Args:
        data: Dictionnaire contenant 'symbol' (symbole à ne plus surveiller)
    """
    try:
        symbol = data.get('symbol')
        if not symbol:
            emit('error', {'message': 'Symbole requis'})
            return
        
        symbol = symbol.upper()
        
        # Trouver le client
        client_id = None
        for cid, client_data in active_connections.items():
            if client_data['ip'] == request.remote_addr:
                client_id = cid
                break
        
        if not client_id:
            emit('error', {'message': 'Client non identifié'})
            return
        
        # Quitter la room spécifique au symbole
        symbol_room = f'symbol_{symbol}'
        leave_room(symbol_room)
        
        logger.info(f"Client {client_id} s'est désabonné du symbole {symbol}")
        
        emit('symbol_unsubscribed', {
            'symbol': symbol,
            'message': f'Désabonné des données de {symbol}',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du désabonnement du symbole: {str(e)}")
        emit('error', {'message': 'Erreur lors du désabonnement du symbole'})


@socketio.on('get_status')
def handle_get_status():
    """
    Gestionnaire pour obtenir le statut du serveur WebSocket.
    """
    try:
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'active_connections': len(active_connections),
            'streaming_active': websocket_manager.is_streaming,
            'monitored_symbols': monitored_symbols,
            'available_rooms': list(room_subscriptions.keys()),
            'room_subscriptions': {
                room: len(subscribers) for room, subscribers in room_subscriptions.items()
            },
            'server_uptime': time.time(),
            'status': 'healthy'
        }
        
        emit('server_status', status)
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
        emit('error', {'message': 'Erreur lors de la récupération du statut'})


@socketio.on('ping')
def handle_ping():
    """
    Gestionnaire pour le ping/pong (test de latence).
    """
    emit('pong', {
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'pong'
    })


# Routes HTTP pour la gestion du serveur WebSocket
@app.route('/websocket/status')
def websocket_status():
    """Endpoint HTTP pour vérifier le statut du serveur WebSocket."""
    return {
        'status': 'active',
        'active_connections': len(active_connections),
        'streaming_active': websocket_manager.is_streaming,
        'monitored_symbols': monitored_symbols,
        'available_rooms': list(room_subscriptions.keys()),
        'timestamp': datetime.utcnow().isoformat()
    }


@app.route('/websocket/connections')
def websocket_connections():
    """Endpoint HTTP pour lister les connexions actives."""
    return {
        'connections': list(active_connections.values()),
        'total': len(active_connections),
        'timestamp': datetime.utcnow().isoformat()
    }


@app.route('/websocket/rooms')
def websocket_rooms():
    """Endpoint HTTP pour lister les rooms et leurs abonnés."""
    return {
        'rooms': {
            room: {
                'subscribers': len(subscribers),
                'subscriber_ids': list(subscribers)
            } for room, subscribers in room_subscriptions.items()
        },
        'timestamp': datetime.utcnow().isoformat()
    }


if __name__ == '__main__':
    logger.info("Démarrage du serveur WebSocket pour données financières")
    logger.info(f"Symboles surveillés: {', '.join(monitored_symbols)}")
    logger.info(f"Rooms disponibles: {', '.join(room_subscriptions.keys())}")
    
    # Démarrage du serveur WebSocket
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
