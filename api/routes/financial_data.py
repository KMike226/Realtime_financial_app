"""
Endpoints CRUD pour les données financières
===========================================
Routes Flask pour les opérations CRUD sur les données financières.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc, asc, and_, or_
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional

from app import db, FinancialData, financial_data_schema, financial_data_schemas, validate_financial_data

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du blueprint pour les données financières
financial_data_bp = Blueprint('financial_data', __name__, url_prefix='/api/financial-data')


@financial_data_bp.route('/', methods=['GET'])
@jwt_required()
def get_financial_data():
    """
    Récupère les données financières avec filtres et pagination.
    
    Query Parameters:
        - symbol: Filtre par symbole (ex: AAPL, BTC)
        - source: Filtre par source (ex: Alpha Vantage, CoinGecko)
        - start_date: Date de début (format ISO)
        - end_date: Date de fin (format ISO)
        - limit: Nombre maximum de résultats (défaut: 100)
        - offset: Décalage pour la pagination (défaut: 0)
        - sort: Ordre de tri (timestamp_asc, timestamp_desc, price_asc, price_desc)
    """
    try:
        # Récupération des paramètres de requête
        symbol = request.args.get('symbol')
        source = request.args.get('source')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = min(int(request.args.get('limit', 100)), 1000)  # Limite max de 1000
        offset = int(request.args.get('offset', 0))
        sort = request.args.get('sort', 'timestamp_desc')
        
        # Construction de la requête de base
        query = FinancialData.query
        
        # Application des filtres
        filters = []
        
        if symbol:
            filters.append(FinancialData.symbol == symbol.upper())
        
        if source:
            filters.append(FinancialData.source == source)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                filters.append(FinancialData.timestamp >= start_dt)
            except ValueError:
                return jsonify({'error': 'Format de date invalide pour start_date'}), 400
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                filters.append(FinancialData.timestamp <= end_dt)
            except ValueError:
                return jsonify({'error': 'Format de date invalide pour end_date'}), 400
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Application du tri
        if sort == 'timestamp_asc':
            query = query.order_by(asc(FinancialData.timestamp))
        elif sort == 'timestamp_desc':
            query = query.order_by(desc(FinancialData.timestamp))
        elif sort == 'price_asc':
            query = query.order_by(asc(FinancialData.price))
        elif sort == 'price_desc':
            query = query.order_by(desc(FinancialData.price))
        else:
            query = query.order_by(desc(FinancialData.timestamp))
        
        # Application de la pagination
        total_count = query.count()
        data = query.offset(offset).limit(limit).all()
        
        # Sérialisation des données
        result = financial_data_schemas.dump(data)
        
        return jsonify({
            'data': result,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'filters': {
                'symbol': symbol,
                'source': source,
                'start_date': start_date,
                'end_date': end_date,
                'sort': sort
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données financières: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@financial_data_bp.route('/<int:data_id>', methods=['GET'])
@jwt_required()
def get_financial_data_by_id(data_id: int):
    """
    Récupère une donnée financière spécifique par son ID.
    
    Args:
        data_id: ID de la donnée financière à récupérer
    """
    try:
        data = FinancialData.query.get_or_404(data_id)
        result = financial_data_schema.dump(data)
        return jsonify({'data': result})
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la donnée {data_id}: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@financial_data_bp.route('/', methods=['POST'])
@jwt_required()
def create_financial_data():
    """
    Crée une nouvelle donnée financière.
    
    Body (JSON):
        - symbol: Symbole de l'actif (requis)
        - timestamp: Timestamp de la donnée (requis)
        - price: Prix actuel (requis)
        - volume: Volume échangé (requis)
        - open_price: Prix d'ouverture (requis)
        - high_price: Prix le plus haut (requis)
        - low_price: Prix le plus bas (requis)
        - close_price: Prix de clôture (requis)
        - source: Source des données (requis)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Validation des données
        validation_error = validate_financial_data(data)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Conversion du timestamp
        try:
            timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Format de timestamp invalide'}), 400
        
        # Création de l'objet
        financial_data = FinancialData(
            symbol=data['symbol'].upper(),
            timestamp=timestamp,
            price=float(data['price']),
            volume=int(data['volume']),
            open_price=float(data['open_price']),
            high_price=float(data['high_price']),
            low_price=float(data['low_price']),
            close_price=float(data['close_price']),
            source=data['source']
        )
        
        # Sauvegarde en base de données
        db.session.add(financial_data)
        db.session.commit()
        
        # Retour de la donnée créée
        result = financial_data_schema.dump(financial_data)
        logger.info(f"Donnée financière créée: {financial_data.symbol} à {timestamp}")
        
        return jsonify({
            'message': 'Donnée financière créée avec succès',
            'data': result
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la création de la donnée financière: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@financial_data_bp.route('/<int:data_id>', methods=['PUT'])
@jwt_required()
def update_financial_data(data_id: int):
    """
    Met à jour une donnée financière existante.
    
    Args:
        data_id: ID de la donnée financière à mettre à jour
        
    Body (JSON): Mêmes champs que pour la création (tous optionnels)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Récupération de la donnée existante
        financial_data = FinancialData.query.get_or_404(data_id)
        
        # Mise à jour des champs fournis
        if 'symbol' in data:
            financial_data.symbol = data['symbol'].upper()
        
        if 'timestamp' in data:
            try:
                financial_data.timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Format de timestamp invalide'}), 400
        
        if 'price' in data:
            financial_data.price = float(data['price'])
        
        if 'volume' in data:
            financial_data.volume = int(data['volume'])
        
        if 'open_price' in data:
            financial_data.open_price = float(data['open_price'])
        
        if 'high_price' in data:
            financial_data.high_price = float(data['high_price'])
        
        if 'low_price' in data:
            financial_data.low_price = float(data['low_price'])
        
        if 'close_price' in data:
            financial_data.close_price = float(data['close_price'])
        
        if 'source' in data:
            financial_data.source = data['source']
        
        # Validation des données mises à jour
        validation_error = validate_financial_data(financial_data.to_dict())
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Sauvegarde des modifications
        financial_data.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Retour de la donnée mise à jour
        result = financial_data_schema.dump(financial_data)
        logger.info(f"Donnée financière mise à jour: ID {data_id}")
        
        return jsonify({
            'message': 'Donnée financière mise à jour avec succès',
            'data': result
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la mise à jour de la donnée {data_id}: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@financial_data_bp.route('/<int:data_id>', methods=['DELETE'])
@jwt_required()
def delete_financial_data(data_id: int):
    """
    Supprime une donnée financière.
    
    Args:
        data_id: ID de la donnée financière à supprimer
    """
    try:
        financial_data = FinancialData.query.get_or_404(data_id)
        
        # Suppression de la donnée
        db.session.delete(financial_data)
        db.session.commit()
        
        logger.info(f"Donnée financière supprimée: ID {data_id}")
        
        return jsonify({
            'message': 'Donnée financière supprimée avec succès',
            'deleted_id': data_id
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression de la donnée {data_id}: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@financial_data_bp.route('/batch', methods=['POST'])
@jwt_required()
def create_batch_financial_data():
    """
    Crée plusieurs données financières en lot.
    
    Body (JSON):
        - data: Liste des données financières à créer
    """
    try:
        request_data = request.get_json()
        
        if not request_data or 'data' not in request_data:
            return jsonify({'error': 'Champ "data" avec liste des données requis'}), 400
        
        data_list = request_data['data']
        
        if not isinstance(data_list, list):
            return jsonify({'error': 'Le champ "data" doit être une liste'}), 400
        
        if len(data_list) > 1000:  # Limite de sécurité
            return jsonify({'error': 'Maximum 1000 données par lot'}), 400
        
        created_data = []
        errors = []
        
        for i, data in enumerate(data_list):
            try:
                # Validation des données
                validation_error = validate_financial_data(data)
                if validation_error:
                    errors.append({'index': i, 'error': validation_error})
                    continue
                
                # Conversion du timestamp
                try:
                    timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                except ValueError:
                    errors.append({'index': i, 'error': 'Format de timestamp invalide'})
                    continue
                
                # Création de l'objet
                financial_data = FinancialData(
                    symbol=data['symbol'].upper(),
                    timestamp=timestamp,
                    price=float(data['price']),
                    volume=int(data['volume']),
                    open_price=float(data['open_price']),
                    high_price=float(data['high_price']),
                    low_price=float(data['low_price']),
                    close_price=float(data['close_price']),
                    source=data['source']
                )
                
                db.session.add(financial_data)
                created_data.append(financial_data)
                
            except Exception as e:
                errors.append({'index': i, 'error': str(e)})
        
        # Sauvegarde en base de données
        db.session.commit()
        
        # Sérialisation des données créées
        result = financial_data_schemas.dump(created_data)
        
        logger.info(f"Lot de données financières créé: {len(created_data)} créées, {len(errors)} erreurs")
        
        return jsonify({
            'message': f'Lot traité: {len(created_data)} créées, {len(errors)} erreurs',
            'created': result,
            'errors': errors,
            'summary': {
                'total_processed': len(data_list),
                'successful': len(created_data),
                'failed': len(errors)
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la création du lot de données: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@financial_data_bp.route('/symbols', methods=['GET'])
@jwt_required()
def get_available_symbols():
    """
    Récupère la liste des symboles disponibles dans la base de données.
    """
    try:
        symbols = db.session.query(FinancialData.symbol).distinct().all()
        symbol_list = [symbol[0] for symbol in symbols]
        
        return jsonify({
            'symbols': sorted(symbol_list),
            'count': len(symbol_list)
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des symboles: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@financial_data_bp.route('/sources', methods=['GET'])
@jwt_required()
def get_available_sources():
    """
    Récupère la liste des sources disponibles dans la base de données.
    """
    try:
        sources = db.session.query(FinancialData.source).distinct().all()
        source_list = [source[0] for source in sources]
        
        return jsonify({
            'sources': sorted(source_list),
            'count': len(source_list)
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des sources: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@financial_data_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_financial_data_stats():
    """
    Récupère des statistiques sur les données financières.
    """
    try:
        symbol = request.args.get('symbol')
        
        query = FinancialData.query
        if symbol:
            query = query.filter(FinancialData.symbol == symbol.upper())
        
        # Statistiques de base
        total_count = query.count()
        
        if total_count == 0:
            return jsonify({
                'message': 'Aucune donnée trouvée',
                'stats': {
                    'total_count': 0,
                    'symbol': symbol
                }
            })
        
        # Statistiques sur les prix
        price_stats = db.session.query(
            db.func.min(FinancialData.price).label('min_price'),
            db.func.max(FinancialData.price).label('max_price'),
            db.func.avg(FinancialData.price).label('avg_price')
        ).filter(query.whereclause).first()
        
        # Statistiques sur les volumes
        volume_stats = db.session.query(
            db.func.min(FinancialData.volume).label('min_volume'),
            db.func.max(FinancialData.volume).label('max_volume'),
            db.func.avg(FinancialData.volume).label('avg_volume')
        ).filter(query.whereclause).first()
        
        # Période des données
        date_range = db.session.query(
            db.func.min(FinancialData.timestamp).label('earliest'),
            db.func.max(FinancialData.timestamp).label('latest')
        ).filter(query.whereclause).first()
        
        return jsonify({
            'stats': {
                'total_count': total_count,
                'symbol': symbol,
                'price': {
                    'min': float(price_stats.min_price),
                    'max': float(price_stats.max_price),
                    'average': float(price_stats.avg_price)
                },
                'volume': {
                    'min': int(volume_stats.min_volume),
                    'max': int(volume_stats.max_volume),
                    'average': float(volume_stats.avg_volume)
                },
                'date_range': {
                    'earliest': date_range.earliest.isoformat(),
                    'latest': date_range.latest.isoformat()
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques: {str(e)}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500
