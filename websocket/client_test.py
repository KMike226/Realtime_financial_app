"""
Client WebSocket de test pour le streaming de données financières
================================================================
Client Python pour tester la connectivité et le streaming du serveur WebSocket.
"""

import socketio
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration du client SocketIO
sio = socketio.Client()

# Stockage des données reçues
received_data = {
    'financial_data': {},
    'technical_indicators': {},
    'system_status': {},
    'symbol_data': {}
}


@sio.event
def connect():
    """
    Gestionnaire de connexion du client.
    """
    logger.info("✅ Client connecté au serveur WebSocket")
    print("🔗 Connexion établie avec le serveur WebSocket")
    print("📊 Prêt à recevoir des données financières en temps réel")


@sio.event
def disconnect():
    """
    Gestionnaire de déconnexion du client.
    """
    logger.info("❌ Client déconnecté du serveur WebSocket")
    print("🔌 Connexion fermée avec le serveur WebSocket")


@sio.event
def connected(data):
    """
    Gestionnaire pour l'événement de confirmation de connexion.
    
    Args:
        data: Données de confirmation de connexion
    """
    logger.info(f"Connexion confirmée: {data}")
    print(f"✅ Connexion confirmée - Client ID: {data.get('client_id')}")
    print(f"🏠 Rooms disponibles: {', '.join(data.get('available_rooms', []))}")


@sio.event
def financial_data_update(data):
    """
    Gestionnaire pour les mises à jour de données financières.
    
    Args:
        data: Données financières mises à jour
    """
    symbol = data.get('symbol')
    financial_data = data.get('data')
    timestamp = data.get('timestamp')
    
    received_data['financial_data'][symbol] = financial_data
    
    print(f"💰 {symbol}: ${financial_data['price']:.2f} "
          f"(Volume: {financial_data['volume']:,}, "
          f"Change: {financial_data['change']:+.2f}%) "
          f"[{timestamp}]")


@sio.event
def technical_indicators_update(data):
    """
    Gestionnaire pour les mises à jour d'indicateurs techniques.
    
    Args:
        data: Indicateurs techniques mis à jour
    """
    symbol = data.get('symbol')
    indicators = data.get('indicators')
    timestamp = data.get('timestamp')
    
    received_data['technical_indicators'][symbol] = indicators
    
    print(f"📈 {symbol} - RSI: {indicators['rsi']:.1f}, "
          f"MACD: {indicators['macd']:.2f}, "
          f"SMA20: {indicators['sma_20']:.2f} "
          f"[{timestamp}]")


@sio.event
def system_status_update(data):
    """
    Gestionnaire pour les mises à jour du statut système.
    
    Args:
        data: Statut système mis à jour
    """
    received_data['system_status'] = data
    
    print(f"🖥️  Système - Connexions: {data['active_connections']}, "
          f"Symboles: {data['monitored_symbols']}, "
          f"Statut: {data['status']} "
          f"[{data['timestamp']}]")


@sio.event
def symbol_data(data):
    """
    Gestionnaire pour les données d'un symbole spécifique.
    
    Args:
        data: Données complètes du symbole
    """
    symbol = data.get('symbol')
    financial_data = data.get('financial_data')
    technical_indicators = data.get('technical_indicators')
    timestamp = data.get('timestamp')
    
    received_data['symbol_data'][symbol] = {
        'financial': financial_data,
        'technical': technical_indicators,
        'timestamp': timestamp
    }
    
    print(f"🎯 {symbol} - Prix: ${financial_data['price']:.2f}, "
          f"RSI: {technical_indicators['rsi']:.1f}, "
          f"MACD: {technical_indicators['macd']:.2f} "
          f"[{timestamp}]")


@sio.event
def room_joined(data):
    """
    Gestionnaire pour la confirmation de jointure de room.
    
    Args:
        data: Données de confirmation de jointure
    """
    room = data.get('room')
    message = data.get('message')
    print(f"🚪 Rejoint la room '{room}': {message}")


@sio.event
def room_left(data):
    """
    Gestionnaire pour la confirmation de sortie de room.
    
    Args:
        data: Données de confirmation de sortie
    """
    room = data.get('room')
    message = data.get('message')
    print(f"🚪 Quitté la room '{room}': {message}")


@sio.event
def symbol_subscribed(data):
    """
    Gestionnaire pour la confirmation d'abonnement à un symbole.
    
    Args:
        data: Données de confirmation d'abonnement
    """
    symbol = data.get('symbol')
    message = data.get('message')
    print(f"📊 Abonné au symbole '{symbol}': {message}")


@sio.event
def symbol_unsubscribed(data):
    """
    Gestionnaire pour la confirmation de désabonnement d'un symbole.
    
    Args:
        data: Données de confirmation de désabonnement
    """
    symbol = data.get('symbol')
    message = data.get('message')
    print(f"📊 Désabonné du symbole '{symbol}': {message}")


@sio.event
def server_status(data):
    """
    Gestionnaire pour le statut du serveur.
    
    Args:
        data: Statut du serveur
    """
    print(f"🖥️  Statut serveur:")
    print(f"   - Connexions actives: {data['active_connections']}")
    print(f"   - Streaming actif: {data['streaming_active']}")
    print(f"   - Symboles surveillés: {', '.join(data['monitored_symbols'])}")
    print(f"   - Rooms disponibles: {', '.join(data['available_rooms'])}")


@sio.event
def pong(data):
    """
    Gestionnaire pour la réponse pong (test de latence).
    
    Args:
        data: Données de réponse pong
    """
    print(f"🏓 Pong reçu: {data['message']} [{data['timestamp']}]")


@sio.event
def error(data):
    """
    Gestionnaire pour les erreurs du serveur.
    
    Args:
        data: Données d'erreur
    """
    message = data.get('message', 'Erreur inconnue')
    print(f"❌ Erreur: {message}")


@sio.event
def current_financial_data(data):
    """
    Gestionnaire pour les données financières actuelles.
    
    Args:
        data: Données financières actuelles
    """
    financial_data = data.get('data')
    timestamp = data.get('timestamp')
    
    print(f"💰 Données financières actuelles reçues:")
    for symbol, data in financial_data.items():
        print(f"   {symbol}: ${data['price']:.2f} "
              f"(Volume: {data['volume']:,}, Change: {data['change']:+.2f}%)")
    print(f"   Timestamp: {timestamp}")


@sio.event
def current_technical_indicators(data):
    """
    Gestionnaire pour les indicateurs techniques actuels.
    
    Args:
        data: Indicateurs techniques actuels
    """
    indicators = data.get('indicators')
    timestamp = data.get('timestamp')
    
    print(f"📈 Indicateurs techniques actuels reçus:")
    for symbol, data in indicators.items():
        print(f"   {symbol}: RSI {data['rsi']:.1f}, "
              f"MACD {data['macd']:.2f}, SMA20 {data['sma_20']:.2f}")
    print(f"   Timestamp: {timestamp}")


class WebSocketClient:
    """
    Classe principale pour le client WebSocket de test.
    """
    
    def __init__(self, server_url: str = 'http://localhost:5001'):
        self.server_url = server_url
        self.connected = False
    
    def connect(self):
        """
        Connecte le client au serveur WebSocket.
        """
        try:
            print(f"🔗 Connexion au serveur WebSocket: {self.server_url}")
            sio.connect(self.server_url)
            self.connected = True
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion: {str(e)}")
            return False
    
    def disconnect(self):
        """
        Déconnecte le client du serveur WebSocket.
        """
        if self.connected:
            sio.disconnect()
            self.connected = False
            print("🔌 Client déconnecté")
    
    def join_room(self, room: str):
        """
        Rejoint une room de streaming.
        
        Args:
            room: Nom de la room à rejoindre
        """
        if self.connected:
            sio.emit('join_room', {'room': room})
            print(f"🚪 Tentative de jointure de la room '{room}'")
    
    def leave_room(self, room: str):
        """
        Quitte une room de streaming.
        
        Args:
            room: Nom de la room à quitter
        """
        if self.connected:
            sio.emit('leave_room', {'room': room})
            print(f"🚪 Tentative de sortie de la room '{room}'")
    
    def subscribe_symbol(self, symbol: str):
        """
        S'abonne aux données d'un symbole spécifique.
        
        Args:
            symbol: Symbole à surveiller
        """
        if self.connected:
            sio.emit('subscribe_symbol', {'symbol': symbol})
            print(f"📊 Tentative d'abonnement au symbole '{symbol}'")
    
    def unsubscribe_symbol(self, symbol: str):
        """
        Se désabonne des données d'un symbole spécifique.
        
        Args:
            symbol: Symbole à ne plus surveiller
        """
        if self.connected:
            sio.emit('unsubscribe_symbol', {'symbol': symbol})
            print(f"📊 Tentative de désabonnement du symbole '{symbol}'")
    
    def get_status(self):
        """
        Demande le statut du serveur.
        """
        if self.connected:
            sio.emit('get_status')
            print("🖥️  Demande du statut serveur")
    
    def ping(self):
        """
        Envoie un ping pour tester la latence.
        """
        if self.connected:
            sio.emit('ping')
            print("🏓 Ping envoyé")
    
    def run_demo(self):
        """
        Exécute une démonstration complète du client WebSocket.
        """
        print("🚀 Démonstration du client WebSocket")
        print("=" * 50)
        
        # Connexion au serveur
        if not self.connect():
            return
        
        time.sleep(2)
        
        # Demande du statut serveur
        print("\n📊 Statut du serveur:")
        self.get_status()
        time.sleep(2)
        
        # Test de ping
        print("\n🏓 Test de latence:")
        self.ping()
        time.sleep(2)
        
        # Abonnement aux données financières
        print("\n💰 Abonnement aux données financières:")
        self.join_room('financial_data')
        time.sleep(3)
        
        # Abonnement aux indicateurs techniques
        print("\n📈 Abonnement aux indicateurs techniques:")
        self.join_room('technical_indicators')
        time.sleep(3)
        
        # Abonnement au statut système
        print("\n🖥️  Abonnement au statut système:")
        self.join_room('system_status')
        time.sleep(3)
        
        # Abonnement à un symbole spécifique
        print("\n🎯 Abonnement au symbole AAPL:")
        self.subscribe_symbol('AAPL')
        time.sleep(3)
        
        # Abonnement à un autre symbole
        print("\n🎯 Abonnement au symbole BTC:")
        self.subscribe_symbol('BTC')
        time.sleep(3)
        
        # Streaming pendant 30 secondes
        print("\n⏱️  Streaming de données pendant 30 secondes...")
        print("(Appuyez sur Ctrl+C pour arrêter)")
        
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n⏹️  Arrêt demandé par l'utilisateur")
        
        # Désabonnement
        print("\n📊 Désabonnement des symboles:")
        self.unsubscribe_symbol('AAPL')
        self.unsubscribe_symbol('BTC')
        time.sleep(2)
        
        # Sortie des rooms
        print("\n🚪 Sortie des rooms:")
        self.leave_room('financial_data')
        self.leave_room('technical_indicators')
        self.leave_room('system_status')
        time.sleep(2)
        
        # Déconnexion
        print("\n🔌 Déconnexion:")
        self.disconnect()
        
        # Résumé des données reçues
        print("\n📊 Résumé des données reçues:")
        print(f"   - Données financières: {len(received_data['financial_data'])} symboles")
        print(f"   - Indicateurs techniques: {len(received_data['technical_indicators'])} symboles")
        print(f"   - Données de symboles: {len(received_data['symbol_data'])} symboles")
        print(f"   - Statuts système: {len(received_data['system_status'])} mises à jour")
        
        print("\n✅ Démonstration terminée!")


def main():
    """
    Fonction principale pour exécuter le client de test.
    """
    print("🌐 Client WebSocket de test pour données financières")
    print("=" * 60)
    
    # Création du client
    client = WebSocketClient()
    
    # Exécution de la démonstration
    client.run_demo()


if __name__ == '__main__':
    main()
