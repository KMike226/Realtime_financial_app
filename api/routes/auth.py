"""
Endpoints d'authentification et gestion des utilisateurs
=======================================================
Routes Flask pour l'authentification JWT et la gestion des utilisateurs.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional

from app import db, User, user_schema, user_schemas

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du blueprint pour l'authentification
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Enregistre un nouvel utilisateur.
    
    Body (JSON):
        - username: Nom d'utilisateur (requis, unique)
        - email: Adresse email (requis, unique)
        - password: Mot de passe (requis, min 8 caractères)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Validation des champs requis
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Le champ "{field}" est requis'}), 400
        
        # Validation du mot de passe
        if len(data['password']) < 8:
            return jsonify({'error': 'Le mot de passe doit contenir au moins 8 caractères'}), 400
        
        # Validation de l'email (format basique)
        if '@' not in data['email'] or '.' not in data['email']:
            return jsonify({'error': 'Format d\'email invalide'}), 400
        
        # Vérification de l'unicité du nom d'utilisateur
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'error': 'Ce nom d\'utilisateur est déjà utilisé'}), 409
        
        # Vérification de l'unicité de l'email
        existing_email = User.query.filter_by(email=data['email']).first()
        if existing_email:
            return jsonify({'error': 'Cette adresse email est déjà utilisée'}), 409
        
        # Création du nouvel utilisateur
        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            is_active=True
        )
        
        # Sauvegarde en base de données
        db.session.add(user)
        db.session.commit()
        
        # Génération du token d'accès
        access_token = create_access_token(identity=user.id)
        
        # Retour des informations utilisateur (sans le mot de passe)
        result = user_schema.dump(user)
        
        logger.info(f"Nouvel utilisateur enregistré: {user.username}")
        
        return jsonify({
            'message': 'Utilisateur enregistré avec succès',
            'user': result,
            'access_token': access_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'enregistrement de l'utilisateur: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authentifie un utilisateur et retourne un token JWT.
    
    Body (JSON):
        - username: Nom d'utilisateur ou email
        - password: Mot de passe
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Validation des champs requis
        if 'username' not in data or not data['username']:
            return jsonify({'error': 'Le nom d\'utilisateur est requis'}), 400
        
        if 'password' not in data or not data['password']:
            return jsonify({'error': 'Le mot de passe est requis'}), 400
        
        # Recherche de l'utilisateur par nom d'utilisateur ou email
        user = User.query.filter(
            db.or_(
                User.username == data['username'],
                User.email == data['username']
            )
        ).first()
        
        if not user:
            return jsonify({'error': 'Nom d\'utilisateur ou mot de passe incorrect'}), 401
        
        # Vérification du mot de passe
        if not check_password_hash(user.password_hash, data['password']):
            return jsonify({'error': 'Nom d\'utilisateur ou mot de passe incorrect'}), 401
        
        # Vérification que l'utilisateur est actif
        if not user.is_active:
            return jsonify({'error': 'Compte utilisateur désactivé'}), 401
        
        # Mise à jour de la dernière connexion
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Génération du token d'accès
        access_token = create_access_token(identity=user.id)
        
        # Retour des informations utilisateur (sans le mot de passe)
        result = user_schema.dump(user)
        
        logger.info(f"Utilisateur connecté: {user.username}")
        
        return jsonify({
            'message': 'Connexion réussie',
            'user': result,
            'access_token': access_token
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Récupère le profil de l'utilisateur connecté.
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        result = user_schema.dump(user)
        return jsonify({'user': result})
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du profil: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Met à jour le profil de l'utilisateur connecté.
    
    Body (JSON):
        - email: Nouvelle adresse email (optionnel)
        - password: Nouveau mot de passe (optionnel)
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Mise à jour de l'email si fourni
        if 'email' in data:
            if '@' not in data['email'] or '.' not in data['email']:
                return jsonify({'error': 'Format d\'email invalide'}), 400
            
            # Vérification de l'unicité de l'email
            existing_email = User.query.filter(
                db.and_(
                    User.email == data['email'],
                    User.id != user_id
                )
            ).first()
            
            if existing_email:
                return jsonify({'error': 'Cette adresse email est déjà utilisée'}), 409
            
            user.email = data['email']
        
        # Mise à jour du mot de passe si fourni
        if 'password' in data:
            if len(data['password']) < 8:
                return jsonify({'error': 'Le mot de passe doit contenir au moins 8 caractères'}), 400
            
            user.password_hash = generate_password_hash(data['password'])
        
        # Sauvegarde des modifications
        db.session.commit()
        
        # Retour des informations utilisateur mises à jour
        result = user_schema.dump(user)
        
        logger.info(f"Profil utilisateur mis à jour: {user.username}")
        
        return jsonify({
            'message': 'Profil mis à jour avec succès',
            'user': result
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la mise à jour du profil: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Déconnecte l'utilisateur (côté client, le token JWT reste valide jusqu'à expiration).
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user:
            logger.info(f"Utilisateur déconnecté: {user.username}")
        
        return jsonify({
            'message': 'Déconnexion réussie'
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la déconnexion: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@auth_bp.route('/verify', methods=['POST'])
@jwt_required()
def verify_token():
    """
    Vérifie la validité du token JWT.
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'Token invalide ou utilisateur inactif'}), 401
        
        result = user_schema.dump(user)
        
        return jsonify({
            'valid': True,
            'user': result
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du token: {str(e)}")
        return jsonify({'error': 'Token invalide'}), 401


# Routes pour la gestion des utilisateurs (admin)
@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """
    Récupère la liste de tous les utilisateurs (admin seulement).
    
    Query Parameters:
        - active_only: Récupérer seulement les utilisateurs actifs (true/false)
        - limit: Nombre maximum de résultats (défaut: 100)
        - offset: Décalage pour la pagination (défaut: 0)
    """
    try:
        # Vérification des droits admin (simplifiée pour MVP)
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)
        
        if not current_user or not current_user.is_active:
            return jsonify({'error': 'Non autorisé'}), 401
        
        # Récupération des paramètres de requête
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        
        # Construction de la requête
        query = User.query
        
        if active_only:
            query = query.filter(User.is_active == True)
        
        # Tri par nom d'utilisateur
        query = query.order_by(User.username)
        
        # Application de la pagination
        total_count = query.count()
        users = query.offset(offset).limit(limit).all()
        
        # Sérialisation des données
        result = user_schemas.dump(users)
        
        return jsonify({
            'data': result,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'filters': {
                'active_only': active_only
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user_status(user_id: int):
    """
    Met à jour le statut d'un utilisateur (admin seulement).
    
    Args:
        user_id: ID de l'utilisateur à modifier
        
    Body (JSON):
        - is_active: Statut actif/inactif de l'utilisateur
    """
    try:
        # Vérification des droits admin (simplifiée pour MVP)
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_active:
            return jsonify({'error': 'Non autorisé'}), 401
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Récupération de l'utilisateur à modifier
        user = User.query.get_or_404(user_id)
        
        # Mise à jour du statut
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        
        # Sauvegarde des modifications
        db.session.commit()
        
        # Retour des informations utilisateur mises à jour
        result = user_schema.dump(user)
        
        logger.info(f"Statut utilisateur mis à jour: {user.username} -> {'actif' if user.is_active else 'inactif'}")
        
        return jsonify({
            'message': 'Statut utilisateur mis à jour avec succès',
            'user': result
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la mise à jour du statut utilisateur: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@auth_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_auth_stats():
    """
    Récupère des statistiques sur les utilisateurs.
    """
    try:
        # Vérification des droits admin (simplifiée pour MVP)
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)
        
        if not current_user or not current_user.is_active:
            return jsonify({'error': 'Non autorisé'}), 401
        
        # Statistiques de base
        total_users = User.query.count()
        active_users = User.query.filter(User.is_active == True).count()
        inactive_users = total_users - active_users
        
        # Utilisateurs créés dans les 30 derniers jours
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_users = User.query.filter(User.created_at >= thirty_days_ago).count()
        
        # Utilisateurs connectés dans les 7 derniers jours
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_logins = User.query.filter(User.last_login >= seven_days_ago).count()
        
        return jsonify({
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'recent_users_30d': recent_users,
                'recent_logins_7d': recent_logins
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques d'authentification: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500
