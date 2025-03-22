#!/usr/bin/env python3
"""
Lambda Function: Alert Processor
================================

Cette fonction Lambda traite les alertes financières intelligentes
et envoie des notifications multi-canal selon les préférences utilisateur.

Fonctionnalités:
- Traitement des alertes de prix et volumes
- Notifications multi-canal (Email, SMS, Slack, Discord)
- Gestion des préférences utilisateur
- Rate limiting pour éviter le spam
- Escalade automatique pour alertes critiques

Author: Michée Project Team
Date: 2025-03-22
"""

import json
import logging
import boto3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal
import requests
from urllib.parse import quote

# Configuration du logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clients AWS
sns_client = boto3.client('sns')
ses_client = boto3.client('ses')
dynamodb = boto3.resource('dynamodb')

# Configuration depuis les variables d'environnement
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'realtime-financial')
USER_PREFERENCES_TABLE = os.environ.get('USER_PREFERENCES_TABLE', f'{PROJECT_NAME}-{ENVIRONMENT}-user-preferences')
ALERT_HISTORY_TABLE = os.environ.get('ALERT_HISTORY_TABLE', f'{PROJECT_NAME}-{ENVIRONMENT}-alert-history')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'alerts@realtime-financial.com')

# Configuration des seuils d'alerte
CRITICAL_PRICE_CHANGE = 15.0  # 15% de changement critique
MAJOR_PRICE_CHANGE = 10.0     # 10% de changement majeur
VOLUME_SPIKE_CRITICAL = 10.0  # 10x le volume normal


class AlertProcessor:
    """Processeur principal pour les alertes financières intelligentes"""
    
    def __init__(self):
        """Initialise le processeur d'alertes"""
        self.user_preferences_table = dynamodb.Table(USER_PREFERENCES_TABLE) if USER_PREFERENCES_TABLE else None
        self.alert_history_table = dynamodb.Table(ALERT_HISTORY_TABLE) if ALERT_HISTORY_TABLE else None
        
        # Cache pour les préférences utilisateur
        self.preferences_cache = {}
        
        logger.info(f"Processeur d'alertes initialisé - Env: {ENVIRONMENT}")
    
    def process_alert_event(self, alert_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un événement d'alerte
        
        Args:
            alert_event: Événement d'alerte à traiter
            
        Returns:
            Résultats du traitement
        """
        try:
            logger.info(f"Traitement alerte: {alert_event.get('alert_type', 'unknown')}")
            
            # Classification de l'alerte
            alert_classification = self._classify_alert(alert_event)
            
            # Enrichissement de l'alerte
            enriched_alert = self._enrich_alert(alert_event, alert_classification)
            
            # Récupération des utilisateurs concernés
            target_users = self._get_target_users(enriched_alert)
            
            # Vérification rate limiting
            filtered_users = self._apply_rate_limiting(target_users, enriched_alert)
            
            # Envoi des notifications
            notification_results = self._send_notifications(filtered_users, enriched_alert)
            
            # Enregistrement de l'historique
            self._record_alert_history(enriched_alert, notification_results)
            
            return {
                'success': True,
                'alert_id': enriched_alert.get('alert_id'),
                'classification': alert_classification,
                'users_notified': len(notification_results.get('successful_notifications', [])),
                'notifications_sent': notification_results.get('total_sent', 0),
                'notifications_failed': notification_results.get('total_failed', 0)
            }
            
        except Exception as e:
            logger.error(f"Erreur traitement alerte: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'alert_data': alert_event
            }
    
    def _classify_alert(self, alert_event: Dict[str, Any]) -> Dict[str, Any]:
        """Classifie la sévérité et le type d'alerte"""
        classification = {
            'severity': 'info',
            'urgency': 'low',
            'category': 'price_movement',
            'requires_immediate_action': False
        }
        
        alert_type = alert_event.get('alert_type', '')
        
        # Classification par type d'alerte
        if alert_type == 'financial_anomaly':
            anomalies = alert_event.get('anomalies', [])
            derived_metrics = alert_event.get('derived_metrics', {})
            
            # Analyse des changements de prix
            price_change_percent = abs(derived_metrics.get('price_change_percent', 0))
            
            if price_change_percent >= CRITICAL_PRICE_CHANGE:
                classification.update({
                    'severity': 'critical',
                    'urgency': 'high',
                    'requires_immediate_action': True
                })
            elif price_change_percent >= MAJOR_PRICE_CHANGE:
                classification.update({
                    'severity': 'warning',
                    'urgency': 'medium'
                })
            else:
                classification.update({
                    'severity': 'info',
                    'urgency': 'low'
                })
            
            # Analyse des anomalies spécifiques
            if any('volume_spike' in anomaly for anomaly in anomalies):
                volume_ratio = derived_metrics.get('volume_ratio', 1)
                if volume_ratio >= VOLUME_SPIKE_CRITICAL:
                    classification['severity'] = 'critical'
                    classification['urgency'] = 'high'
            
            if any('extreme_price_change' in anomaly for anomaly in anomalies):
                classification['category'] = 'extreme_movement'
                classification['requires_immediate_action'] = True
        
        elif alert_type == 'system_event':
            classification.update({
                'category': 'system',
                'severity': 'warning',
                'urgency': 'medium'
            })
        
        elif alert_type == 'user_threshold_alert':
            classification.update({
                'category': 'user_defined',
                'severity': 'info',
                'urgency': 'medium'
            })
        
        return classification
    
    def _enrich_alert(self, alert_event: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """Enrichit l'alerte avec des informations supplémentaires"""
        enriched = {
            **alert_event,
            'alert_id': self._generate_alert_id(),
            'processed_at': datetime.utcnow().isoformat(),
            'classification': classification,
            'environment': ENVIRONMENT
        }
        
        # Ajout de contexte selon le type d'alerte
        if alert_event.get('alert_type') == 'financial_anomaly':
            symbol = alert_event.get('symbol', 'unknown')
            current_data = alert_event.get('current_data', {})
            
            enriched.update({
                'display_title': f"Anomalie détectée: {symbol}",
                'formatted_message': self._format_financial_anomaly_message(alert_event),
                'action_items': self._generate_action_items(alert_event, classification),
                'market_context': self._get_market_context(symbol)
            })
        
        # Ajout d'URLs et liens utiles
        enriched['links'] = self._generate_useful_links(alert_event)
        
        return enriched
    
    def _format_financial_anomaly_message(self, alert_event: Dict[str, Any]) -> str:
        """Formate un message d'anomalie financière"""
        symbol = alert_event.get('symbol', 'unknown')
        current_data = alert_event.get('current_data', {})
        derived_metrics = alert_event.get('derived_metrics', {})
        anomalies = alert_event.get('anomalies', [])
        
        price = current_data.get('price', 0)
        volume = current_data.get('volume', 0)
        price_change_percent = derived_metrics.get('price_change_percent', 0)
        
        message_parts = [
            f"🚨 Anomalie détectée pour {symbol}",
            f"💰 Prix actuel: ${price:.2f}",
            f"📊 Changement: {price_change_percent:+.2f}%",
            f"📈 Volume: {volume:,}"
        ]
        
        if anomalies:
            message_parts.append(f"⚠️ Anomalies: {', '.join(anomalies)}")
        
        return '\n'.join(message_parts)
    
    def _generate_action_items(self, alert_event: Dict[str, Any], classification: Dict[str, Any]) -> List[str]:
        """Génère des éléments d'action recommandés"""
        actions = []
        
        if classification['severity'] == 'critical':
            actions.extend([
                "Vérifier les actualités récentes pour ce symbole",
                "Examiner les volumes de trading anormaux",
                "Considérer une révision de position si applicable"
            ])
        elif classification['severity'] == 'warning':
            actions.extend([
                "Surveiller l'évolution dans les prochaines heures",
                "Vérifier les indicateurs techniques"
            ])
        else:
            actions.append("Information à noter pour analyse future")
        
        return actions
    
    def _get_market_context(self, symbol: str) -> Dict[str, Any]:
        """Récupère le contexte de marché (simulé pour l'instant)"""
        # En production, ceci pourrait interroger des APIs de marché
        return {
            'market_session': 'regular_hours',  # regular_hours, pre_market, after_hours
            'sector': 'technology',  # Simulé
            'market_cap': 'large_cap'  # Simulé
        }
    
    def _generate_useful_links(self, alert_event: Dict[str, Any]) -> Dict[str, str]:
        """Génère des liens utiles pour l'alerte"""
        symbol = alert_event.get('symbol', '')
        
        links = {
            'yahoo_finance': f"https://finance.yahoo.com/quote/{symbol}",
            'google_finance': f"https://www.google.com/finance/quote/{symbol}:NASDAQ",
            'news_search': f"https://www.google.com/search?q={quote(symbol)}+stock+news"
        }
        
        return links
    
    def _get_target_users(self, enriched_alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Détermine les utilisateurs à notifier"""
        # En production, ceci interrogerait une base de données d'utilisateurs
        # Pour l'instant, retourne des utilisateurs simulés
        
        symbol = enriched_alert.get('symbol', '')
        severity = enriched_alert.get('classification', {}).get('severity', 'info')
        
        # Simulation d'utilisateurs intéressés
        simulated_users = [
            {
                'user_id': 'user_1',
                'email': 'admin@realtime-financial.com',
                'phone': '+1234567890',
                'preferred_channels': ['email', 'slack'],
                'alert_preferences': {
                    'severity_threshold': 'info',
                    'symbols_of_interest': [symbol, 'AAPL', 'GOOGL'],
                    'notification_hours': {'start': '09:00', 'end': '17:00'}
                }
            },
            {
                'user_id': 'user_2', 
                'email': 'trader@realtime-financial.com',
                'phone': '+1234567891',
                'preferred_channels': ['email', 'sms'],
                'alert_preferences': {
                    'severity_threshold': 'warning',
                    'symbols_of_interest': [symbol],
                    'notification_hours': {'start': '06:00', 'end': '20:00'}
                }
            }
        ]
        
        # Filtrage selon les préférences
        target_users = []
        for user in simulated_users:
            if self._should_notify_user(user, enriched_alert):
                target_users.append(user)
        
        return target_users
    
    def _should_notify_user(self, user: Dict[str, Any], alert: Dict[str, Any]) -> bool:
        """Détermine si un utilisateur doit être notifié"""
        preferences = user.get('alert_preferences', {})
        
        # Vérification du seuil de sévérité
        severity_threshold = preferences.get('severity_threshold', 'info')
        alert_severity = alert.get('classification', {}).get('severity', 'info')
        
        severity_levels = {'info': 1, 'warning': 2, 'critical': 3}
        if severity_levels.get(alert_severity, 1) < severity_levels.get(severity_threshold, 1):
            return False
        
        # Vérification des symboles d'intérêt
        symbol = alert.get('symbol', '')
        symbols_of_interest = preferences.get('symbols_of_interest', [])
        if symbols_of_interest and symbol not in symbols_of_interest:
            return False
        
        # Vérification des heures de notification
        current_hour = datetime.utcnow().strftime('%H:%M')
        notification_hours = preferences.get('notification_hours', {})
        
        if notification_hours:
            start_hour = notification_hours.get('start', '00:00')
            end_hour = notification_hours.get('end', '23:59')
            
            if not (start_hour <= current_hour <= end_hour):
                # Exception pour les alertes critiques
                if alert_severity != 'critical':
                    return False
        
        return True
    
    def _apply_rate_limiting(self, users: List[Dict[str, Any]], alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Applique le rate limiting pour éviter le spam"""
        # Implémentation simplifiée - en production, utiliserait DynamoDB/Redis
        filtered_users = []
        
        for user in users:
            user_id = user.get('user_id', '')
            symbol = alert.get('symbol', '')
            
            # Simulation de vérification rate limiting
            # En production: vérifier les dernières notifications pour cet utilisateur/symbole
            last_notification_key = f"{user_id}_{symbol}"
            
            # Pour l'instant, on accepte tous les utilisateurs
            # En production: implémenter une vraie logique de rate limiting
            filtered_users.append(user)
        
        return filtered_users
    
    def _send_notifications(self, users: List[Dict[str, Any]], alert: Dict[str, Any]) -> Dict[str, Any]:
        """Envoie les notifications aux utilisateurs"""
        results = {
            'total_sent': 0,
            'total_failed': 0,
            'successful_notifications': [],
            'failed_notifications': []
        }
        
        for user in users:
            user_id = user.get('user_id', '')
            preferred_channels = user.get('preferred_channels', ['email'])
            
            user_results = []
            
            for channel in preferred_channels:
                try:
                    if channel == 'email':
                        self._send_email_notification(user, alert)
                        user_results.append({'channel': 'email', 'status': 'success'})
                    
                    elif channel == 'sms':
                        self._send_sms_notification(user, alert)
                        user_results.append({'channel': 'sms', 'status': 'success'})
                    
                    elif channel == 'slack':
                        self._send_slack_notification(user, alert)
                        user_results.append({'channel': 'slack', 'status': 'success'})
                    
                    elif channel == 'discord':
                        self._send_discord_notification(user, alert)
                        user_results.append({'channel': 'discord', 'status': 'success'})
                    
                    results['total_sent'] += 1
                    
                except Exception as e:
                    logger.error(f"Erreur envoi notification {channel} pour {user_id}: {str(e)}")
                    user_results.append({'channel': channel, 'status': 'failed', 'error': str(e)})
                    results['total_failed'] += 1
            
            # Enregistrement des résultats par utilisateur
            results['successful_notifications'].append({
                'user_id': user_id,
                'channels': user_results
            })
        
        return results
    
    def _send_email_notification(self, user: Dict[str, Any], alert: Dict[str, Any]):
        """Envoie une notification email"""
        email = user.get('email', '')
        if not email:
            raise ValueError("Email address not provided")
        
        subject = f"Alerte Financière: {alert.get('symbol', 'Unknown')}"
        
        # Génération du contenu HTML
        html_content = self._generate_email_html(alert)
        text_content = alert.get('formatted_message', 'Nouvelle alerte financière')
        
        try:
            response = ses_client.send_email(
                Source=FROM_EMAIL,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {
                        'Text': {'Data': text_content},
                        'Html': {'Data': html_content}
                    }
                }
            )
            
            logger.info(f"Email envoyé à {email}: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Erreur envoi email à {email}: {str(e)}")
            raise
    
    def _send_sms_notification(self, user: Dict[str, Any], alert: Dict[str, Any]):
        """Envoie une notification SMS"""
        phone = user.get('phone', '')
        if not phone:
            raise ValueError("Phone number not provided")
        
        # Message SMS court
        message = f"Alerte {alert.get('symbol', '')}: {alert.get('classification', {}).get('severity', 'info').upper()}\n"
        message += alert.get('formatted_message', '')[:150] + "..."  # Limitation SMS
        
        try:
            response = sns_client.publish(
                PhoneNumber=phone,
                Message=message
            )
            
            logger.info(f"SMS envoyé à {phone}: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Erreur envoi SMS à {phone}: {str(e)}")
            raise
    
    def _send_slack_notification(self, user: Dict[str, Any], alert: Dict[str, Any]):
        """Envoie une notification Slack"""
        if not SLACK_WEBHOOK_URL:
            raise ValueError("Slack webhook URL not configured")
        
        # Formatage pour Slack
        slack_payload = {
            "text": f"Alerte Financière: {alert.get('symbol', 'Unknown')}",
            "attachments": [
                {
                    "color": self._get_slack_color(alert.get('classification', {}).get('severity', 'info')),
                    "fields": [
                        {
                            "title": "Symbole",
                            "value": alert.get('symbol', 'Unknown'),
                            "short": True
                        },
                        {
                            "title": "Sévérité", 
                            "value": alert.get('classification', {}).get('severity', 'info').upper(),
                            "short": True
                        },
                        {
                            "title": "Prix",
                            "value": f"${alert.get('current_data', {}).get('price', 0):.2f}",
                            "short": True
                        },
                        {
                            "title": "Changement",
                            "value": f"{alert.get('derived_metrics', {}).get('price_change_percent', 0):+.2f}%",
                            "short": True
                        }
                    ],
                    "footer": f"Alerte {alert.get('alert_id', '')}"
                }
            ]
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=slack_payload)
        response.raise_for_status()
        
        logger.info(f"Notification Slack envoyée pour {user.get('user_id', '')}")
    
    def _send_discord_notification(self, user: Dict[str, Any], alert: Dict[str, Any]):
        """Envoie une notification Discord"""
        if not DISCORD_WEBHOOK_URL:
            raise ValueError("Discord webhook URL not configured")
        
        # Formatage pour Discord
        discord_payload = {
            "content": f"🚨 **Alerte Financière: {alert.get('symbol', 'Unknown')}**",
            "embeds": [
                {
                    "title": alert.get('display_title', 'Alerte Financière'),
                    "description": alert.get('formatted_message', ''),
                    "color": self._get_discord_color(alert.get('classification', {}).get('severity', 'info')),
                    "fields": [
                        {
                            "name": "Sévérité",
                            "value": alert.get('classification', {}).get('severity', 'info').upper(),
                            "inline": True
                        },
                        {
                            "name": "Catégorie",
                            "value": alert.get('classification', {}).get('category', 'unknown'),
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": f"Alerte ID: {alert.get('alert_id', '')}"
                    },
                    "timestamp": alert.get('processed_at', datetime.utcnow().isoformat())
                }
            ]
        }
        
        response = requests.post(DISCORD_WEBHOOK_URL, json=discord_payload)
        response.raise_for_status()
        
        logger.info(f"Notification Discord envoyée pour {user.get('user_id', '')}")
    
    def _generate_email_html(self, alert: Dict[str, Any]) -> str:
        """Génère le contenu HTML pour l'email"""
        symbol = alert.get('symbol', 'Unknown')
        severity = alert.get('classification', {}).get('severity', 'info')
        formatted_message = alert.get('formatted_message', '')
        action_items = alert.get('action_items', [])
        links = alert.get('links', {})
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
                .severity-{severity} {{ border-left: 5px solid {'#ff4444' if severity == 'critical' else '#ff8800' if severity == 'warning' else '#4444ff'}; }}
                .actions {{ background-color: #f9f9f9; padding: 10px; margin: 10px 0; }}
                .links {{ margin: 15px 0; }}
                .links a {{ margin-right: 15px; }}
            </style>
        </head>
        <body>
            <div class="header severity-{severity}">
                <h2>Alerte Financière: {symbol}</h2>
                <p><strong>Sévérité:</strong> {severity.upper()}</p>
            </div>
            
            <div class="content">
                <h3>Détails de l'alerte</h3>
                <pre>{formatted_message}</pre>
            </div>
        """
        
        if action_items:
            html += """
            <div class="actions">
                <h3>Actions recommandées</h3>
                <ul>
            """
            for action in action_items:
                html += f"<li>{action}</li>"
            html += "</ul></div>"
        
        if links:
            html += '<div class="links"><h3>Liens utiles</h3>'
            for name, url in links.items():
                html += f'<a href="{url}" target="_blank">{name.replace("_", " ").title()}</a>'
            html += "</div>"
        
        html += """
            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                Cette alerte a été générée automatiquement par le système de monitoring financier.
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _get_slack_color(self, severity: str) -> str:
        """Retourne la couleur Slack selon la sévérité"""
        colors = {
            'critical': 'danger',
            'warning': 'warning', 
            'info': 'good'
        }
        return colors.get(severity, 'good')
    
    def _get_discord_color(self, severity: str) -> int:
        """Retourne la couleur Discord selon la sévérité"""
        colors = {
            'critical': 0xff4444,  # Rouge
            'warning': 0xff8800,   # Orange
            'info': 0x4444ff       # Bleu
        }
        return colors.get(severity, 0x4444ff)
    
    def _record_alert_history(self, alert: Dict[str, Any], notification_results: Dict[str, Any]):
        """Enregistre l'historique des alertes"""
        if not self.alert_history_table:
            return
        
        try:
            history_item = {
                'alert_id': alert.get('alert_id', ''),
                'timestamp': alert.get('processed_at', ''),
                'symbol': alert.get('symbol', ''),
                'alert_type': alert.get('alert_type', ''),
                'severity': alert.get('classification', {}).get('severity', 'info'),
                'users_notified': notification_results.get('total_sent', 0),
                'notification_failures': notification_results.get('total_failed', 0),
                'alert_data': json.dumps(alert, default=str),
                'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())  # TTL de 90 jours
            }
            
            self.alert_history_table.put_item(Item=history_item)
            logger.debug(f"Historique enregistré pour alerte {alert.get('alert_id', '')}")
            
        except Exception as e:
            logger.error(f"Erreur enregistrement historique: {str(e)}")
    
    def _generate_alert_id(self) -> str:
        """Génère un ID unique pour l'alerte"""
        import uuid
        return f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"


def lambda_handler(event, context):
    """
    Handler principal de la fonction Lambda d'alertes
    
    Args:
        event: Événement SNS ou autre contenant l'alerte
        context: Contexte d'exécution Lambda
        
    Returns:
        Résultats du traitement des alertes
    """
    logger.info(f"Début traitement des alertes - Records: {len(event.get('Records', []))}")
    
    try:
        processor = AlertProcessor()
        results = []
        
        # Traitement des enregistrements SNS
        for record in event.get('Records', []):
            if record.get('EventSource') == 'aws:sns':
                # Décodage du message SNS
                sns_message = json.loads(record['Sns']['Message'])
                
                # Traitement de l'alerte
                result = processor.process_alert_event(sns_message)
                results.append(result)
            
            else:
                # Traitement direct de l'événement
                result = processor.process_alert_event(record)
                results.append(result)
        
        # Statistiques globales
        total_processed = len(results)
        successful_processing = sum(1 for r in results if r.get('success', False))
        total_notifications = sum(r.get('notifications_sent', 0) for r in results)
        
        logger.info(f"Traitement terminé: {successful_processing}/{total_processed} alertes traitées, {total_notifications} notifications envoyées")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Alert processing completed',
                'total_processed': total_processed,
                'successful_processing': successful_processing,
                'total_notifications_sent': total_notifications,
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Erreur critique dans le handler d'alertes: {str(e)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Alert processing failed',
                'message': str(e)
            })
        }
