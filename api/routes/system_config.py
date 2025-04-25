"""
Endpoints pour la gestion de configuration système
=================================================
Routes Flask pour gérer la configuration du système via API.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc, asc
from datetime import datetime
import logging
import json
from typing import Dict, Any, Optional

from app import db, SystemConfig, system_config_schema, system_config_schemas, validate_config_data

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du blueprint pour la configuration système
config_bp = Blueprint('system_config', __name__, url_prefix='/api/system-config')


@config_bp.route('/', methods=['GET'])
@jwt_required()
def get_system_configs():
    """
    Récupère toutes les configurations système avec filtres.
    
    Query Parameters:
        - active_only: Récupérer seulement les configurations actives (true/false)
        - config_type: Filtre par type de configuration
        - search: Recherche dans les clés et descriptions
        - limit: Nombre maximum de résultats (défaut: 100)
        - offset: Décalage pour la pagination (défaut: 0)
    """
    try:
        # Récupération des paramètres de requête
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        config_type = request.args.get('config_type')
        search = request.args.get('search')
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        
        # Construction de la requête de base
        query = SystemConfig.query
        
        # Application des filtres
        if active_only:
            query = query.filter(SystemConfig.is_active == True)
        
        if config_type:
            query = query.filter(SystemConfig.config_type == config_type)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                db.or_(
                    SystemConfig.config_key.ilike(search_filter),
                    SystemConfig.description.ilike(search_filter)
                )
            )
        
        # Tri par clé de configuration
        query = query.order_by(asc(SystemConfig.config_key))
        
        # Application de la pagination
        total_count = query.count()
        configs = query.offset(offset).limit(limit).all()
        
        # Sérialisation des données
        result = system_config_schemas.dump(configs)
        
        return jsonify({
            'data': result,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'filters': {
                'active_only': active_only,
                'config_type': config_type,
                'search': search
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des configurations: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@config_bp.route('/<int:config_id>', methods=['GET'])
@jwt_required()
def get_system_config_by_id(config_id: int):
    """
    Récupère une configuration système spécifique par son ID.
    
    Args:
        config_id: ID de la configuration à récupérer
    """
    try:
        config = SystemConfig.query.get_or_404(config_id)
        result = system_config_schema.dump(config)
        return jsonify({'data': result})
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la configuration {config_id}: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@config_bp.route('/key/<config_key>', methods=['GET'])
@jwt_required()
def get_system_config_by_key(config_key: str):
    """
    Récupère une configuration système par sa clé.
    
    Args:
        config_key: Clé de la configuration à récupérer
    """
    try:
        config = SystemConfig.query.filter_by(config_key=config_key).first()
        
        if not config:
            return jsonify({'error': f'Configuration "{config_key}" non trouvée'}), 404
        
        result = system_config_schema.dump(config)
        return jsonify({'data': result})
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la configuration {config_key}: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@config_bp.route('/', methods=['POST'])
@jwt_required()
def create_system_config():
    """
    Crée une nouvelle configuration système.
    
    Body (JSON):
        - config_key: Clé de la configuration (requis, unique)
        - config_value: Valeur de la configuration (requis)
        - config_type: Type de la configuration (requis: string, int, float, bool, json)
        - description: Description de la configuration (optionnel)
        - is_active: Si la configuration est active (défaut: true)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Validation des données
        validation_error = validate_config_data(data)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Vérification de l'unicité de la clé
        existing_config = SystemConfig.query.filter_by(config_key=data['config_key']).first()
        if existing_config:
            return jsonify({'error': f'La configuration "{data["config_key"]}" existe déjà'}), 409
        
        # Création de l'objet
        config = SystemConfig(
            config_key=data['config_key'],
            config_value=data['config_value'],
            config_type=data['config_type'],
            description=data.get('description'),
            is_active=data.get('is_active', True)
        )
        
        # Sauvegarde en base de données
        db.session.add(config)
        db.session.commit()
        
        # Retour de la configuration créée
        result = system_config_schema.dump(config)
        logger.info(f"Configuration système créée: {config.config_key}")
        
        return jsonify({
            'message': 'Configuration système créée avec succès',
            'data': result
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la création de la configuration: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@config_bp.route('/<int:config_id>', methods=['PUT'])
@jwt_required()
def update_system_config(config_id: int):
    """
    Met à jour une configuration système existante.
    
    Args:
        config_id: ID de la configuration à mettre à jour
        
    Body (JSON): Tous les champs sont optionnels sauf config_key qui ne peut pas être modifié
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Récupération de la configuration existante
        config = SystemConfig.query.get_or_404(config_id)
        
        # Mise à jour des champs fournis
        if 'config_value' in data:
            config.config_value = data['config_value']
        
        if 'config_type' in data:
            config.config_type = data['config_type']
        
        if 'description' in data:
            config.description = data['description']
        
        if 'is_active' in data:
            config.is_active = bool(data['is_active'])
        
        # Validation des données mises à jour
        validation_error = validate_config_data(config.to_dict())
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Sauvegarde des modifications
        config.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Retour de la configuration mise à jour
        result = system_config_schema.dump(config)
        logger.info(f"Configuration système mise à jour: {config.config_key}")
        
        return jsonify({
            'message': 'Configuration système mise à jour avec succès',
            'data': result
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la mise à jour de la configuration {config_id}: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@config_bp.route('/<int:config_id>', methods=['DELETE'])
@jwt_required()
def delete_system_config(config_id: int):
    """
    Supprime une configuration système.
    
    Args:
        config_id: ID de la configuration à supprimer
    """
    try:
        config = SystemConfig.query.get_or_404(config_id)
        
        # Suppression de la configuration
        db.session.delete(config)
        db.session.commit()
        
        logger.info(f"Configuration système supprimée: {config.config_key}")
        
        return jsonify({
            'message': 'Configuration système supprimée avec succès',
            'deleted_key': config.config_key
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression de la configuration {config_id}: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@config_bp.route('/key/<config_key>', methods=['PUT'])
@jwt_required()
def update_system_config_by_key(config_key: str):
    """
    Met à jour une configuration système par sa clé.
    
    Args:
        config_key: Clé de la configuration à mettre à jour
        
    Body (JSON): Même format que la mise à jour par ID
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Récupération de la configuration existante
        config = SystemConfig.query.filter_by(config_key=config_key).first()
        
        if not config:
            return jsonify({'error': f'Configuration "{config_key}" non trouvée'}), 404
        
        # Mise à jour des champs fournis
        if 'config_value' in data:
            config.config_value = data['config_value']
        
        if 'config_type' in data:
            config.config_type = data['config_type']
        
        if 'description' in data:
            config.description = data['description']
        
        if 'is_active' in data:
            config.is_active = bool(data['is_active'])
        
        # Validation des données mises à jour
        validation_error = validate_config_data(config.to_dict())
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Sauvegarde des modifications
        config.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Retour de la configuration mise à jour
        result = system_config_schema.dump(config)
        logger.info(f"Configuration système mise à jour par clé: {config_key}")
        
        return jsonify({
            'message': 'Configuration système mise à jour avec succès',
            'data': result
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la mise à jour de la configuration {config_key}: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@config_bp.route('/batch', methods=['POST'])
@jwt_required()
def create_batch_system_configs():
    """
    Crée plusieurs configurations système en lot.
    
    Body (JSON):
        - configs: Liste des configurations à créer
    """
    try:
        request_data = request.get_json()
        
        if not request_data or 'configs' not in request_data:
            return jsonify({'error': 'Champ "configs" avec liste des configurations requis'}), 400
        
        configs_list = request_data['configs']
        
        if not isinstance(configs_list, list):
            return jsonify({'error': 'Le champ "configs" doit être une liste'}), 400
        
        if len(configs_list) > 100:  # Limite de sécurité
            return jsonify({'error': 'Maximum 100 configurations par lot'}), 400
        
        created_configs = []
        errors = []
        
        for i, config_data in enumerate(configs_list):
            try:
                # Validation des données
                validation_error = validate_config_data(config_data)
                if validation_error:
                    errors.append({'index': i, 'error': validation_error})
                    continue
                
                # Vérification de l'unicité de la clé
                existing_config = SystemConfig.query.filter_by(config_key=config_data['config_key']).first()
                if existing_config:
                    errors.append({'index': i, 'error': f'La configuration "{config_data["config_key"]}" existe déjà'})
                    continue
                
                # Création de l'objet
                config = SystemConfig(
                    config_key=config_data['config_key'],
                    config_value=config_data['config_value'],
                    config_type=config_data['config_type'],
                    description=config_data.get('description'),
                    is_active=config_data.get('is_active', True)
                )
                
                db.session.add(config)
                created_configs.append(config)
                
            except Exception as e:
                errors.append({'index': i, 'error': str(e)})
        
        # Sauvegarde en base de données
        db.session.commit()
        
        # Sérialisation des configurations créées
        result = system_config_schemas.dump(created_configs)
        
        logger.info(f"Lot de configurations créé: {len(created_configs)} créées, {len(errors)} erreurs")
        
        return jsonify({
            'message': f'Lot traité: {len(created_configs)} créées, {len(errors)} erreurs',
            'created': result,
            'errors': errors,
            'summary': {
                'total_processed': len(configs_list),
                'successful': len(created_configs),
                'failed': len(errors)
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la création du lot de configurations: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@config_bp.route('/types', methods=['GET'])
@jwt_required()
def get_config_types():
    """
    Récupère la liste des types de configuration disponibles.
    """
    try:
        types = db.session.query(SystemConfig.config_type).distinct().all()
        type_list = [config_type[0] for config_type in types]
        
        return jsonify({
            'config_types': sorted(type_list),
            'available_types': ['string', 'int', 'float', 'bool', 'json'],
            'count': len(type_list)
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des types de configuration: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@config_bp.route('/export', methods=['GET'])
@jwt_required()
def export_system_configs():
    """
    Exporte toutes les configurations système au format JSON.
    
    Query Parameters:
        - active_only: Exporter seulement les configurations actives (true/false)
        - format: Format d'export (json, key_value)
    """
    try:
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        export_format = request.args.get('format', 'json')
        
        # Construction de la requête
        query = SystemConfig.query
        if active_only:
            query = query.filter(SystemConfig.is_active == True)
        
        configs = query.order_by(SystemConfig.config_key).all()
        
        if export_format == 'key_value':
            # Format clé-valeur simple
            result = {}
            for config in configs:
                # Conversion de la valeur selon le type
                if config.config_type == 'int':
                    result[config.config_key] = int(config.config_value)
                elif config.config_type == 'float':
                    result[config.config_key] = float(config.config_value)
                elif config.config_type == 'bool':
                    result[config.config_key] = config.config_value.lower() == 'true'
                elif config.config_type == 'json':
                    result[config.config_key] = json.loads(config.config_value)
                else:
                    result[config.config_key] = config.config_value
        else:
            # Format JSON complet
            result = system_config_schemas.dump(configs)
        
        return jsonify({
            'export': result,
            'metadata': {
                'total_configs': len(configs),
                'active_only': active_only,
                'format': export_format,
                'exported_at': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'export des configurations: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@config_bp.route('/import', methods=['POST'])
@jwt_required()
def import_system_configs():
    """
    Importe des configurations système depuis un fichier JSON.
    
    Body (JSON):
        - configs: Liste des configurations à importer
        - overwrite: Si les configurations existantes doivent être écrasées (défaut: false)
    """
    try:
        data = request.get_json()
        
        if not data or 'configs' not in data:
            return jsonify({'error': 'Champ "configs" avec liste des configurations requis'}), 400
        
        configs_list = data['configs']
        overwrite = data.get('overwrite', False)
        
        if not isinstance(configs_list, list):
            return jsonify({'error': 'Le champ "configs" doit être une liste'}), 400
        
        imported_configs = []
        updated_configs = []
        errors = []
        
        for i, config_data in enumerate(configs_list):
            try:
                # Validation des données
                validation_error = validate_config_data(config_data)
                if validation_error:
                    errors.append({'index': i, 'error': validation_error})
                    continue
                
                # Vérification de l'existence de la configuration
                existing_config = SystemConfig.query.filter_by(config_key=config_data['config_key']).first()
                
                if existing_config:
                    if overwrite:
                        # Mise à jour de la configuration existante
                        existing_config.config_value = config_data['config_value']
                        existing_config.config_type = config_data['config_type']
                        existing_config.description = config_data.get('description', existing_config.description)
                        existing_config.is_active = config_data.get('is_active', existing_config.is_active)
                        existing_config.updated_at = datetime.utcnow()
                        updated_configs.append(existing_config)
                    else:
                        errors.append({'index': i, 'error': f'La configuration "{config_data["config_key"]}" existe déjà'})
                        continue
                else:
                    # Création d'une nouvelle configuration
                    config = SystemConfig(
                        config_key=config_data['config_key'],
                        config_value=config_data['config_value'],
                        config_type=config_data['config_type'],
                        description=config_data.get('description'),
                        is_active=config_data.get('is_active', True)
                    )
                    db.session.add(config)
                    imported_configs.append(config)
                
            except Exception as e:
                errors.append({'index': i, 'error': str(e)})
        
        # Sauvegarde en base de données
        db.session.commit()
        
        # Sérialisation des résultats
        imported_result = system_config_schemas.dump(imported_configs)
        updated_result = system_config_schemas.dump(updated_configs)
        
        logger.info(f"Import de configurations: {len(imported_configs)} importées, {len(updated_configs)} mises à jour, {len(errors)} erreurs")
        
        return jsonify({
            'message': f'Import terminé: {len(imported_configs)} importées, {len(updated_configs)} mises à jour, {len(errors)} erreurs',
            'imported': imported_result,
            'updated': updated_result,
            'errors': errors,
            'summary': {
                'total_processed': len(configs_list),
                'imported': len(imported_configs),
                'updated': len(updated_configs),
                'failed': len(errors)
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'import des configurations: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500
