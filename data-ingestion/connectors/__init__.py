"""
Data Ingestion Connectors Package
=================================

Ce package contient tous les connecteurs pour l'ingestion de données financières
en temps réel depuis diverses sources externes.

Connecteurs disponibles:
- Alpha Vantage: Données boursières et crypto
- IEX Cloud: Données de marché en temps réel
- CoinGecko: Données de cryptomonnaies
- Binance: Données de trading crypto

Author: Michée Project Team
"""

from .alpha_vantage_connector import AlphaVantageConnector, AlphaVantageConfig, DataType

__version__ = "1.0.0"
__author__ = "Michée Project Team"

__all__ = [
    'AlphaVantageConnector',
    'AlphaVantageConfig', 
    'DataType'
]
