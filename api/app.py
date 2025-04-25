"""
API REST pour opérations CRUD et gestion de configuration
=========================================================
Application Flask pour gérer les données financières et la configuration
du système de traitement en temps réel.
"""

from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import logging
from typing import Dict, Any, Optional, List
import json

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de l'application Flask
app = Flask(__name__)

# Configuration de l'application
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///financial_app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Initialisation des extensions
db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)
CORS(app)

# Configuration CORS pour permettre les requêtes depuis le frontend
CORS(app, origins=["http://localhost:3000", "http://localhost:8080"])


class FinancialData(db.Model):
    """
    Modèle pour les données financières stockées dans la base de données.
    """
    __tablename__ = 'financial_data'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.BigInteger, nullable=False)
    open_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(50), nullable=False)  # Alpha Vantage, CoinGecko, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FinancialData {self.symbol} at {self.timestamp}>'
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour la sérialisation JSON."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'volume': self.volume,
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'close_price': self.close_price,
            'source': self.source,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class TechnicalIndicator(db.Model):
    """
    Modèle pour les indicateurs techniques calculés.
    """
    __tablename__ = 'technical_indicators'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    indicator_type = db.Column(db.String(20), nullable=False)  # RSI, MACD, SMA, etc.
    value = db.Column(db.Float, nullable=False)
    period = db.Column(db.Integer, nullable=True)  # Période de calcul
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TechnicalIndicator {self.symbol} {self.indicator_type} at {self.timestamp}>'
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour la sérialisation JSON."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'indicator_type': self.indicator_type,
            'value': self.value,
            'period': self.period,
            'created_at': self.created_at.isoformat()
        }


class SystemConfig(db.Model):
    """
    Modèle pour la configuration du système.
    """
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), nullable=False, unique=True, index=True)
    config_value = db.Column(db.Text, nullable=False)
    config_type = db.Column(db.String(20), nullable=False)  # string, int, float, bool, json
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemConfig {self.config_key}: {self.config_value}>'
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour la sérialisation JSON."""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'config_type': self.config_type,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class User(db.Model):
    """
    Modèle pour les utilisateurs de l'API.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour la sérialisation JSON."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


# Schémas Marshmallow pour la sérialisation
class FinancialDataSchema(ma.SQLAlchemyAutoSchema):
    """Schéma pour la sérialisation des données financières."""
    class Meta:
        model = FinancialData
        load_instance = True


class TechnicalIndicatorSchema(ma.SQLAlchemyAutoSchema):
    """Schéma pour la sérialisation des indicateurs techniques."""
    class Meta:
        model = TechnicalIndicator
        load_instance = True


class SystemConfigSchema(ma.SQLAlchemyAutoSchema):
    """Schéma pour la sérialisation de la configuration système."""
    class Meta:
        model = SystemConfig
        load_instance = True


class UserSchema(ma.SQLAlchemyAutoSchema):
    """Schéma pour la sérialisation des utilisateurs."""
    class Meta:
        model = User
        load_instance = True
        exclude = ('password_hash',)  # Exclure le hash du mot de passe


# Instances des schémas
financial_data_schema = FinancialDataSchema()
financial_data_schemas = FinancialDataSchema(many=True)

technical_indicator_schema = TechnicalIndicatorSchema()
technical_indicator_schemas = TechnicalIndicatorSchema(many=True)

system_config_schema = SystemConfigSchema()
system_config_schemas = SystemConfigSchema(many=True)

user_schema = UserSchema()
user_schemas = UserSchema(many=True)


# Fonctions utilitaires
def validate_financial_data(data: Dict[str, Any]) -> Optional[str]:
    """
    Valide les données financières avant insertion.
    
    Args:
        data: Dictionnaire contenant les données à valider
        
    Returns:
        Message d'erreur si validation échoue, None sinon
    """
    required_fields = ['symbol', 'timestamp', 'price', 'volume', 'open_price', 'high_price', 'low_price', 'close_price', 'source']
    
    for field in required_fields:
        if field not in data:
            return f"Le champ '{field}' est requis"
    
    # Validation des types et valeurs
    if not isinstance(data['price'], (int, float)) or data['price'] <= 0:
        return "Le prix doit être un nombre positif"
    
    if not isinstance(data['volume'], (int, float)) or data['volume'] < 0:
        return "Le volume doit être un nombre positif ou zéro"
    
    if data['high_price'] < data['low_price']:
        return "Le prix haut doit être supérieur au prix bas"
    
    return None


def validate_config_data(data: Dict[str, Any]) -> Optional[str]:
    """
    Valide les données de configuration avant insertion.
    
    Args:
        data: Dictionnaire contenant les données à valider
        
    Returns:
        Message d'erreur si validation échoue, None sinon
    """
    required_fields = ['config_key', 'config_value', 'config_type']
    
    for field in required_fields:
        if field not in data:
            return f"Le champ '{field}' est requis"
    
    # Validation du type de configuration
    valid_types = ['string', 'int', 'float', 'bool', 'json']
    if data['config_type'] not in valid_types:
        return f"Le type de configuration doit être l'un de: {', '.join(valid_types)}"
    
    # Validation de la valeur selon le type
    try:
        if data['config_type'] == 'int':
            int(data['config_value'])
        elif data['config_type'] == 'float':
            float(data['config_value'])
        elif data['config_type'] == 'bool':
            if data['config_value'].lower() not in ['true', 'false']:
                return "La valeur booléenne doit être 'true' ou 'false'"
        elif data['config_type'] == 'json':
            json.loads(data['config_value'])
    except (ValueError, json.JSONDecodeError) as e:
        return f"Valeur invalide pour le type {data['config_type']}: {str(e)}"
    
    return None


# Gestion des erreurs
@app.errorhandler(400)
def bad_request(error):
    """Gestionnaire d'erreur pour les requêtes malformées."""
    return jsonify({'error': 'Requête malformée', 'message': str(error)}), 400


@app.errorhandler(401)
def unauthorized(error):
    """Gestionnaire d'erreur pour les requêtes non autorisées."""
    return jsonify({'error': 'Non autorisé', 'message': 'Token d\'authentification requis'}), 401


@app.errorhandler(404)
def not_found(error):
    """Gestionnaire d'erreur pour les ressources non trouvées."""
    return jsonify({'error': 'Ressource non trouvée', 'message': str(error)}), 404


@app.errorhandler(500)
def internal_error(error):
    """Gestionnaire d'erreur pour les erreurs serveur internes."""
    db.session.rollback()
    return jsonify({'error': 'Erreur serveur interne', 'message': str(error)}), 500


# Routes de base
@app.route('/')
def index():
    """Route de base pour vérifier que l'API fonctionne."""
    return jsonify({
        'message': 'API REST pour données financières',
        'version': '1.0.0',
        'status': 'active',
        'endpoints': {
            'financial_data': '/api/financial-data',
            'technical_indicators': '/api/technical-indicators',
            'system_config': '/api/system-config',
            'users': '/api/users',
            'auth': '/api/auth'
        }
    })


@app.route('/health')
def health_check():
    """Point de contrôle de santé de l'API."""
    try:
        # Vérifier la connexion à la base de données
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': db_status,
        'version': '1.0.0'
    })


if __name__ == '__main__':
    # Création des tables de base de données
    with app.app_context():
        db.create_all()
        
        # Initialisation de la configuration par défaut
        default_configs = [
            {
                'config_key': 'api_rate_limit',
                'config_value': '1000',
                'config_type': 'int',
                'description': 'Limite de requêtes par heure par utilisateur'
            },
            {
                'config_key': 'data_retention_days',
                'config_value': '365',
                'config_type': 'int',
                'description': 'Nombre de jours de rétention des données'
            },
            {
                'config_key': 'enable_real_time',
                'config_value': 'true',
                'config_type': 'bool',
                'description': 'Activer le traitement en temps réel'
            },
            {
                'config_key': 'kinesis_stream_name',
                'config_value': 'financial-data-stream',
                'config_type': 'string',
                'description': 'Nom du stream Kinesis pour les données'
            }
        ]
        
        for config_data in default_configs:
            existing_config = SystemConfig.query.filter_by(config_key=config_data['config_key']).first()
            if not existing_config:
                config = SystemConfig(**config_data)
                db.session.add(config)
        
        db.session.commit()
        logger.info("Configuration par défaut initialisée")
    
    # Démarrage de l'application
    app.run(debug=True, host='0.0.0.0', port=5000)
