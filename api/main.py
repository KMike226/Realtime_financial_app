"""
Point d'entrée principal de l'API REST
=======================================
Configuration et démarrage de l'application Flask avec tous les blueprints.
"""

from app import app, db
from routes.financial_data import financial_data_bp
from routes.system_config import config_bp
from routes.auth import auth_bp
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enregistrement des blueprints
app.register_blueprint(financial_data_bp)
app.register_blueprint(config_bp)
app.register_blueprint(auth_bp)

# Route de test pour vérifier que tous les blueprints sont enregistrés
@app.route('/api/status')
def api_status():
    """Point de contrôle pour vérifier le statut de l'API."""
    return {
        'status': 'active',
        'version': '1.0.0',
        'blueprints': [
            'financial_data',
            'system_config', 
            'auth'
        ],
        'endpoints': {
            'financial_data': [
                'GET /api/financial-data/',
                'GET /api/financial-data/<id>',
                'POST /api/financial-data/',
                'PUT /api/financial-data/<id>',
                'DELETE /api/financial-data/<id>',
                'POST /api/financial-data/batch',
                'GET /api/financial-data/symbols',
                'GET /api/financial-data/sources',
                'GET /api/financial-data/stats'
            ],
            'system_config': [
                'GET /api/system-config/',
                'GET /api/system-config/<id>',
                'GET /api/system-config/key/<key>',
                'POST /api/system-config/',
                'PUT /api/system-config/<id>',
                'PUT /api/system-config/key/<key>',
                'DELETE /api/system-config/<id>',
                'POST /api/system-config/batch',
                'GET /api/system-config/types',
                'GET /api/system-config/export',
                'POST /api/system-config/import'
            ],
            'auth': [
                'POST /api/auth/register',
                'POST /api/auth/login',
                'GET /api/auth/profile',
                'PUT /api/auth/profile',
                'POST /api/auth/logout',
                'POST /api/auth/verify',
                'GET /api/auth/users',
                'PUT /api/auth/users/<id>',
                'GET /api/auth/stats'
            ]
        }
    }

if __name__ == '__main__':
    # Création des tables de base de données
    with app.app_context():
        db.create_all()
        logger.info("Tables de base de données créées")
    
    # Démarrage de l'application
    logger.info("Démarrage de l'API REST pour données financières")
    app.run(debug=True, host='0.0.0.0', port=5000)
