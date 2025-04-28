/**
 * Client WebSocket JavaScript pour le streaming de données financières
 * ===================================================================
 * Client JavaScript pour connecter le frontend au serveur WebSocket
 * et gérer le streaming de données en temps réel.
 */

class FinancialWebSocketClient {
    /**
     * Constructeur du client WebSocket.
     * 
     * @param {string} serverUrl - URL du serveur WebSocket
     * @param {Object} options - Options de configuration
     */
    constructor(serverUrl = 'http://localhost:5001', options = {}) {
        this.serverUrl = serverUrl;
        this.socket = null;
        this.connected = false;
        this.subscriptions = new Set();
        this.symbolSubscriptions = new Set();
        this.callbacks = {
            onConnect: options.onConnect || (() => {}),
            onDisconnect: options.onDisconnect || (() => {}),
            onFinancialData: options.onFinancialData || (() => {}),
            onTechnicalIndicators: options.onTechnicalIndicators || (() => {}),
            onSystemStatus: options.onSystemStatus || (() => {}),
            onSymbolData: options.onSymbolData || (() => {}),
            onError: options.onError || (() => {})
        };
        
        // Données stockées localement
        this.data = {
            financial: new Map(),
            technical: new Map(),
            systemStatus: null,
            symbolData: new Map()
        };
    }

    /**
     * Connecte le client au serveur WebSocket.
     * 
     * @returns {Promise<boolean>} - True si la connexion réussit
     */
    async connect() {
        try {
            console.log(`🔗 Connexion au serveur WebSocket: ${this.serverUrl}`);
            
            // Import dynamique de socket.io-client
            const { io } = await import('https://cdn.socket.io/4.7.2/socket.io.esm.min.js');
            
            this.socket = io(this.serverUrl, {
                transports: ['websocket', 'polling'],
                timeout: 10000,
                forceNew: true
            });

            this.setupEventHandlers();
            
            return new Promise((resolve, reject) => {
                this.socket.on('connect', () => {
                    this.connected = true;
                    console.log('✅ Connexion WebSocket établie');
                    this.callbacks.onConnect();
                    resolve(true);
                });

                this.socket.on('connect_error', (error) => {
                    console.error('❌ Erreur de connexion:', error);
                    this.callbacks.onError(error);
                    reject(error);
                });

                // Timeout de connexion
                setTimeout(() => {
                    if (!this.connected) {
                        reject(new Error('Timeout de connexion'));
                    }
                }, 10000);
            });
        } catch (error) {
            console.error('❌ Erreur lors de la connexion:', error);
            this.callbacks.onError(error);
            return false;
        }
    }

    /**
     * Configure les gestionnaires d'événements du socket.
     */
    setupEventHandlers() {
        // Événement de connexion
        this.socket.on('connect', () => {
            this.connected = true;
            console.log('✅ Client connecté au serveur WebSocket');
        });

        // Événement de déconnexion
        this.socket.on('disconnect', () => {
            this.connected = false;
            console.log('🔌 Client déconnecté du serveur WebSocket');
            this.callbacks.onDisconnect();
        });

        // Confirmation de connexion
        this.socket.on('connected', (data) => {
            console.log('✅ Connexion confirmée:', data);
        });

        // Mises à jour de données financières
        this.socket.on('financial_data_update', (data) => {
            const { symbol, data: financialData, timestamp } = data;
            this.data.financial.set(symbol, { ...financialData, timestamp });
            console.log(`💰 ${symbol}: $${financialData.price.toFixed(2)} (${financialData.change > 0 ? '+' : ''}${financialData.change.toFixed(2)}%)`);
            this.callbacks.onFinancialData(data);
        });

        // Mises à jour d'indicateurs techniques
        this.socket.on('technical_indicators_update', (data) => {
            const { symbol, indicators, timestamp } = data;
            this.data.technical.set(symbol, { ...indicators, timestamp });
            console.log(`📈 ${symbol} - RSI: ${indicators.rsi.toFixed(1)}, MACD: ${indicators.macd.toFixed(2)}`);
            this.callbacks.onTechnicalIndicators(data);
        });

        // Mises à jour du statut système
        this.socket.on('system_status_update', (data) => {
            this.data.systemStatus = data;
            console.log(`🖥️ Système - Connexions: ${data.active_connections}, Statut: ${data.status}`);
            this.callbacks.onSystemStatus(data);
        });

        // Données de symbole spécifique
        this.socket.on('symbol_data', (data) => {
            const { symbol, financial_data, technical_indicators, timestamp } = data;
            this.data.symbolData.set(symbol, {
                financial: financial_data,
                technical: technical_indicators,
                timestamp
            });
            console.log(`🎯 ${symbol} - Prix: $${financial_data.price.toFixed(2)}, RSI: ${technical_indicators.rsi.toFixed(1)}`);
            this.callbacks.onSymbolData(data);
        });

        // Confirmations de rooms
        this.socket.on('room_joined', (data) => {
            console.log(`🚪 Rejoint la room '${data.room}': ${data.message}`);
        });

        this.socket.on('room_left', (data) => {
            console.log(`🚪 Quitté la room '${data.room}': ${data.message}`);
        });

        // Confirmations de symboles
        this.socket.on('symbol_subscribed', (data) => {
            console.log(`📊 Abonné au symbole '${data.symbol}': ${data.message}`);
        });

        this.socket.on('symbol_unsubscribed', (data) => {
            console.log(`📊 Désabonné du symbole '${data.symbol}': ${data.message}`);
        });

        // Statut du serveur
        this.socket.on('server_status', (data) => {
            console.log('🖥️ Statut serveur:', data);
        });

        // Pong (test de latence)
        this.socket.on('pong', (data) => {
            console.log(`🏓 Pong reçu: ${data.message} [${data.timestamp}]`);
        });

        // Données actuelles
        this.socket.on('current_financial_data', (data) => {
            console.log('💰 Données financières actuelles reçues:', data);
            Object.entries(data.data).forEach(([symbol, financialData]) => {
                this.data.financial.set(symbol, { ...financialData, timestamp: data.timestamp });
            });
        });

        this.socket.on('current_technical_indicators', (data) => {
            console.log('📈 Indicateurs techniques actuels reçus:', data);
            Object.entries(data.indicators).forEach(([symbol, indicators]) => {
                this.data.technical.set(symbol, { ...indicators, timestamp: data.timestamp });
            });
        });

        // Gestion des erreurs
        this.socket.on('error', (data) => {
            console.error('❌ Erreur serveur:', data.message);
            this.callbacks.onError(data);
        });

        this.socket.on('connect_error', (error) => {
            console.error('❌ Erreur de connexion:', error);
            this.callbacks.onError(error);
        });
    }

    /**
     * Déconnecte le client du serveur WebSocket.
     */
    disconnect() {
        if (this.socket && this.connected) {
            this.socket.disconnect();
            this.connected = false;
            this.subscriptions.clear();
            this.symbolSubscriptions.clear();
            console.log('🔌 Client déconnecté');
        }
    }

    /**
     * Rejoint une room de streaming.
     * 
     * @param {string} room - Nom de la room à rejoindre
     */
    joinRoom(room) {
        if (this.connected && this.socket) {
            this.socket.emit('join_room', { room });
            this.subscriptions.add(room);
            console.log(`🚪 Tentative de jointure de la room '${room}'`);
        } else {
            console.warn('⚠️ Client non connecté');
        }
    }

    /**
     * Quitte une room de streaming.
     * 
     * @param {string} room - Nom de la room à quitter
     */
    leaveRoom(room) {
        if (this.connected && this.socket) {
            this.socket.emit('leave_room', { room });
            this.subscriptions.delete(room);
            console.log(`🚪 Tentative de sortie de la room '${room}'`);
        } else {
            console.warn('⚠️ Client non connecté');
        }
    }

    /**
     * S'abonne aux données d'un symbole spécifique.
     * 
     * @param {string} symbol - Symbole à surveiller
     */
    subscribeToSymbol(symbol) {
        if (this.connected && this.socket) {
            this.socket.emit('subscribe_symbol', { symbol: symbol.toUpperCase() });
            this.symbolSubscriptions.add(symbol.toUpperCase());
            console.log(`📊 Tentative d'abonnement au symbole '${symbol}'`);
        } else {
            console.warn('⚠️ Client non connecté');
        }
    }

    /**
     * Se désabonne des données d'un symbole spécifique.
     * 
     * @param {string} symbol - Symbole à ne plus surveiller
     */
    unsubscribeFromSymbol(symbol) {
        if (this.connected && this.socket) {
            this.socket.emit('unsubscribe_symbol', { symbol: symbol.toUpperCase() });
            this.symbolSubscriptions.delete(symbol.toUpperCase());
            console.log(`📊 Tentative de désabonnement du symbole '${symbol}'`);
        } else {
            console.warn('⚠️ Client non connecté');
        }
    }

    /**
     * Demande le statut du serveur.
     */
    getServerStatus() {
        if (this.connected && this.socket) {
            this.socket.emit('get_status');
            console.log('🖥️ Demande du statut serveur');
        } else {
            console.warn('⚠️ Client non connecté');
        }
    }

    /**
     * Envoie un ping pour tester la latence.
     */
    ping() {
        if (this.connected && this.socket) {
            this.socket.emit('ping');
            console.log('🏓 Ping envoyé');
        } else {
            console.warn('⚠️ Client non connecté');
        }
    }

    /**
     * S'abonne aux données financières.
     */
    subscribeToFinancialData() {
        this.joinRoom('financial_data');
    }

    /**
     * S'abonne aux indicateurs techniques.
     */
    subscribeToTechnicalIndicators() {
        this.joinRoom('technical_indicators');
    }

    /**
     * S'abonne au statut système.
     */
    subscribeToSystemStatus() {
        this.joinRoom('system_status');
    }

    /**
     * Se désabonne des données financières.
     */
    unsubscribeFromFinancialData() {
        this.leaveRoom('financial_data');
    }

    /**
     * Se désabonne des indicateurs techniques.
     */
    unsubscribeFromTechnicalIndicators() {
        this.leaveRoom('technical_indicators');
    }

    /**
     * Se désabonne du statut système.
     */
    unsubscribeFromSystemStatus() {
        this.leaveRoom('system_status');
    }

    /**
     * Récupère les données financières stockées localement.
     * 
     * @param {string} symbol - Symbole spécifique (optionnel)
     * @returns {Object|Map} - Données financières
     */
    getFinancialData(symbol = null) {
        if (symbol) {
            return this.data.financial.get(symbol.toUpperCase());
        }
        return this.data.financial;
    }

    /**
     * Récupère les indicateurs techniques stockés localement.
     * 
     * @param {string} symbol - Symbole spécifique (optionnel)
     * @returns {Object|Map} - Indicateurs techniques
     */
    getTechnicalIndicators(symbol = null) {
        if (symbol) {
            return this.data.technical.get(symbol.toUpperCase());
        }
        return this.data.technical;
    }

    /**
     * Récupère le statut système stocké localement.
     * 
     * @returns {Object|null} - Statut système
     */
    getSystemStatus() {
        return this.data.systemStatus;
    }

    /**
     * Récupère les données d'un symbole spécifique.
     * 
     * @param {string} symbol - Symbole à récupérer
     * @returns {Object|undefined} - Données du symbole
     */
    getSymbolData(symbol) {
        return this.data.symbolData.get(symbol.toUpperCase());
    }

    /**
     * Vérifie si le client est connecté.
     * 
     * @returns {boolean} - True si connecté
     */
    isConnected() {
        return this.connected;
    }

    /**
     * Récupère la liste des abonnements actifs.
     * 
     * @returns {Object} - Abonnements actifs
     */
    getSubscriptions() {
        return {
            rooms: Array.from(this.subscriptions),
            symbols: Array.from(this.symbolSubscriptions)
        };
    }

    /**
     * Configure les callbacks pour les événements.
     * 
     * @param {Object} callbacks - Objet contenant les callbacks
     */
    setCallbacks(callbacks) {
        this.callbacks = { ...this.callbacks, ...callbacks };
    }
}

// Export pour utilisation en module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FinancialWebSocketClient;
}

// Export pour utilisation en module ES6
if (typeof window !== 'undefined') {
    window.FinancialWebSocketClient = FinancialWebSocketClient;
}

// Exemple d'utilisation
if (typeof window !== 'undefined') {
    // Exemple d'utilisation dans le navigateur
    window.addEventListener('DOMContentLoaded', () => {
        console.log('🌐 Client WebSocket JavaScript chargé');
        
        // Exemple de création et utilisation du client
        const client = new FinancialWebSocketClient('http://localhost:5001', {
            onConnect: () => {
                console.log('🎉 Connexion établie!');
                // S'abonner aux données financières
                client.subscribeToFinancialData();
                // S'abonner à un symbole spécifique
                client.subscribeToSymbol('AAPL');
            },
            onFinancialData: (data) => {
                console.log('💰 Données financières reçues:', data);
                // Mettre à jour l'interface utilisateur
                updateFinancialDisplay(data);
            },
            onTechnicalIndicators: (data) => {
                console.log('📈 Indicateurs techniques reçus:', data);
                // Mettre à jour l'interface utilisateur
                updateTechnicalDisplay(data);
            },
            onError: (error) => {
                console.error('❌ Erreur:', error);
                // Afficher l'erreur à l'utilisateur
                showError(error);
            }
        });

        // Fonctions d'exemple pour mettre à jour l'interface
        function updateFinancialDisplay(data) {
            const element = document.getElementById('financial-data');
            if (element) {
                element.innerHTML = `
                    <div class="symbol-data">
                        <h3>${data.symbol}</h3>
                        <p>Prix: $${data.data.price.toFixed(2)}</p>
                        <p>Volume: ${data.data.volume.toLocaleString()}</p>
                        <p>Change: ${data.data.change > 0 ? '+' : ''}${data.data.change.toFixed(2)}%</p>
                    </div>
                `;
            }
        }

        function updateTechnicalDisplay(data) {
            const element = document.getElementById('technical-indicators');
            if (element) {
                element.innerHTML = `
                    <div class="indicators-data">
                        <h3>${data.symbol}</h3>
                        <p>RSI: ${data.indicators.rsi.toFixed(1)}</p>
                        <p>MACD: ${data.indicators.macd.toFixed(2)}</p>
                        <p>SMA20: ${data.indicators.sma_20.toFixed(2)}</p>
                    </div>
                `;
            }
        }

        function showError(error) {
            const element = document.getElementById('error-message');
            if (element) {
                element.innerHTML = `<div class="error">Erreur: ${error.message || error}</div>`;
            }
        }

        // Boutons de contrôle (si présents dans le HTML)
        const connectBtn = document.getElementById('connect-btn');
        const disconnectBtn = document.getElementById('disconnect-btn');
        const subscribeBtn = document.getElementById('subscribe-btn');
        const unsubscribeBtn = document.getElementById('unsubscribe-btn');

        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                client.connect();
            });
        }

        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => {
                client.disconnect();
            });
        }

        if (subscribeBtn) {
            subscribeBtn.addEventListener('click', () => {
                client.subscribeToSymbol('AAPL');
            });
        }

        if (unsubscribeBtn) {
            unsubscribeBtn.addEventListener('click', () => {
                client.unsubscribeFromSymbol('AAPL');
            });
        }
    });
}
