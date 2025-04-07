#!/usr/bin/env python3
"""
Processeur de données financières pour EMR Spark
Pipeline de traitement en temps réel des données de marché
"""

import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, lit, when, avg, stddev, max as spark_max, min as spark_min,
    lag, lead, window, expr, current_timestamp, to_timestamp,
    regexp_replace, split, explode, struct, collect_list,
    round as spark_round, abs as spark_abs
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    TimestampType, IntegerType, BooleanType
)
from pyspark.sql.window import Window
import boto3

class FinancialDataProcessor:
    """Processeur principal pour les données financières"""
    
    def __init__(self, app_name: str = "FinancialDataProcessor"):
        """Initialisation du processeur Spark"""
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
            .config("spark.hadoop.fs.s3a.aws.credentials.provider", 
                   "com.amazonaws.auth.InstanceProfileCredentialsProvider") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
        
        # Configuration S3
        self.s3_bucket = self._get_s3_bucket()
        self.input_path = f"s3a://{self.s3_bucket}/raw-data/"
        self.output_path = f"s3a://{self.s3_bucket}/processed-data/"
        self.checkpoint_path = f"s3a://{self.s3_bucket}/checkpoints/"
        
        print(f"🚀 Spark Session initialisée: {app_name}")
        print(f"📁 Bucket S3: {self.s3_bucket}")
        print(f"⚙️ Configuration: Adaptive Query Execution activé")

    def _get_s3_bucket(self) -> str:
        """Récupère le nom du bucket S3 depuis les tags EMR"""
        try:
            # En production, récupérer depuis les métadonnées EMR
            import requests
            metadata_url = "http://169.254.169.254/latest/meta-data/instance-id"
            instance_id = requests.get(metadata_url, timeout=5).text
            
            ec2 = boto3.client('ec2')
            response = ec2.describe_instances(InstanceIds=[instance_id])
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'S3Bucket':
                            return tag['Value']
            
        except Exception as e:
            print(f"⚠️ Impossible de récupérer le bucket depuis les métadonnées: {e}")
        
        # Fallback pour les tests
        return "financial-pipeline-dev-data-lake"

    def create_schema(self) -> StructType:
        """Définit le schéma pour les données financières"""
        return StructType([
            StructField("symbol", StringType(), True),
            StructField("timestamp", StringType(), True),
            StructField("open", DoubleType(), True),
            StructField("high", DoubleType(), True),
            StructField("low", DoubleType(), True),
            StructField("close", DoubleType(), True),
            StructField("volume", IntegerType(), True),
            StructField("source", StringType(), True),
            StructField("market", StringType(), True)
        ])

    def read_raw_data(self, date_filter: str = None) -> DataFrame:
        """Lit les données brutes depuis S3"""
        print(f"📖 Lecture des données depuis: {self.input_path}")
        
        try:
            # Lecture des données avec schéma défini
            df = self.spark.read \
                .option("multiline", "true") \
                .option("mode", "PERMISSIVE") \
                .json(self.input_path)
            
            print(f"📊 Données lues: {df.count():,} lignes")
            
            if date_filter:
                df = df.filter(col("timestamp").contains(date_filter))
                print(f"🔍 Filtré par date {date_filter}: {df.count():,} lignes")
            
            return df
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture: {e}")
            # Retourner un DataFrame vide avec le bon schéma
            return self.spark.createDataFrame([], self.create_schema())

    def clean_and_validate(self, df: DataFrame) -> DataFrame:
        """Nettoie et valide les données"""
        print("🧹 Nettoyage et validation des données...")
        
        # Conversion du timestamp
        df_clean = df.withColumn(
            "timestamp_parsed",
            to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss")
        ).withColumn(
            "timestamp_parsed",
            when(col("timestamp_parsed").isNull(),
                 to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss'Z'"))
            .otherwise(col("timestamp_parsed"))
        )
        
        # Filtrage des données valides
        df_valid = df_clean.filter(
            (col("timestamp_parsed").isNotNull()) &
            (col("symbol").isNotNull()) &
            (col("close") > 0) &
            (col("volume") >= 0) &
            (col("high") >= col("low")) &
            (col("close") <= col("high")) &
            (col("close") >= col("low"))
        )
        
        # Suppression des doublons
        df_dedupe = df_valid.dropDuplicates(["symbol", "timestamp_parsed"])
        
        print(f"✅ Données nettoyées: {df_dedupe.count():,} lignes valides")
        
        return df_dedupe.select(
            col("symbol"),
            col("timestamp_parsed").alias("timestamp"),
            col("open"),
            col("high"),
            col("low"),
            col("close"),
            col("volume"),
            col("source"),
            col("market")
        )

    def calculate_technical_indicators(self, df: DataFrame) -> DataFrame:
        """Calcule les indicateurs techniques"""
        print("📈 Calcul des indicateurs techniques...")
        
        # Fenêtre pour les calculs par symbole
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        window_20 = window_symbol.rowsBetween(-19, 0)
        window_50 = window_symbol.rowsBetween(-49, 0)
        
        df_indicators = df.withColumn(
            # Moyennes mobiles
            "sma_20", avg("close").over(window_20)
        ).withColumn(
            "sma_50", avg("close").over(window_50)
        ).withColumn(
            # Volatilité (écart-type sur 20 périodes)
            "volatility_20", stddev("close").over(window_20)
        ).withColumn(
            # Prix précédent pour calculer les changements
            "prev_close", lag("close", 1).over(window_symbol)
        ).withColumn(
            # Calcul des changements
            "price_change", col("close") - col("prev_close")
        ).withColumn(
            "price_change_pct", 
            when(col("prev_close") > 0,
                 (col("price_change") / col("prev_close")) * 100)
            .otherwise(0.0)
        ).withColumn(
            # Indicateurs de tendance
            "trend_short", when(col("sma_20") > lag("sma_20", 1).over(window_symbol), "UP").otherwise("DOWN")
        ).withColumn(
            "trend_long", when(col("sma_50") > lag("sma_50", 1).over(window_symbol), "UP").otherwise("DOWN")
        ).withColumn(
            # Signal de croisement des moyennes mobiles
            "ma_crossover", when(
                (col("sma_20") > col("sma_50")) & 
                (lag("sma_20", 1).over(window_symbol) <= lag("sma_50", 1).over(window_symbol)),
                "GOLDEN_CROSS"
            ).when(
                (col("sma_20") < col("sma_50")) & 
                (lag("sma_20", 1).over(window_symbol) >= lag("sma_50", 1).over(window_symbol)),
                "DEATH_CROSS"
            ).otherwise("NONE")
        )
        
        # Calcul du RSI simplifié
        df_rsi = self._calculate_rsi(df_indicators)
        
        print("✅ Indicateurs techniques calculés")
        return df_rsi

    def _calculate_rsi(self, df: DataFrame, period: int = 14) -> DataFrame:
        """Calcule l'indice de force relative (RSI)"""
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        window_rsi = window_symbol.rowsBetween(-period + 1, 0)
        
        df_rsi = df.withColumn(
            # Gains et pertes
            "gain", when(col("price_change") > 0, col("price_change")).otherwise(0)
        ).withColumn(
            "loss", when(col("price_change") < 0, spark_abs(col("price_change"))).otherwise(0)
        ).withColumn(
            # Moyennes mobiles des gains et pertes
            "avg_gain", avg("gain").over(window_rsi)
        ).withColumn(
            "avg_loss", avg("loss").over(window_rsi)
        ).withColumn(
            # RSI
            "rs", col("avg_gain") / col("avg_loss")
        ).withColumn(
            "rsi", 100 - (100 / (1 + col("rs")))
        ).withColumn(
            # Signaux RSI
            "rsi_signal", when(col("rsi") > 70, "OVERBOUGHT")
                         .when(col("rsi") < 30, "OVERSOLD")
                         .otherwise("NEUTRAL")
        )
        
        return df_rsi

    def detect_anomalies(self, df: DataFrame) -> DataFrame:
        """Détecte les anomalies dans les données"""
        print("🔍 Détection d'anomalies...")
        
        # Fenêtre pour calculs statistiques
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        window_stats = window_symbol.rowsBetween(-100, 0)  # 100 périodes
        
        df_anomalies = df.withColumn(
            # Statistiques pour la détection d'anomalies
            "price_mean", avg("close").over(window_stats)
        ).withColumn(
            "price_stddev", stddev("close").over(window_stats)
        ).withColumn(
            "volume_mean", avg("volume").over(window_stats)
        ).withColumn(
            "volume_stddev", stddev("volume").over(window_stats)
        ).withColumn(
            # Z-scores
            "price_zscore", 
            (col("close") - col("price_mean")) / col("price_stddev")
        ).withColumn(
            "volume_zscore",
            (col("volume") - col("volume_mean")) / col("volume_stddev")
        ).withColumn(
            # Détection d'anomalies (Z-score > 3 ou < -3)
            "price_anomaly", spark_abs(col("price_zscore")) > 3
        ).withColumn(
            "volume_anomaly", spark_abs(col("volume_zscore")) > 3
        ).withColumn(
            # Classification des anomalies
            "anomaly_type", when(
                col("price_anomaly") & col("volume_anomaly"), "PRICE_VOLUME"
            ).when(
                col("price_anomaly"), "PRICE"
            ).when(
                col("volume_anomaly"), "VOLUME"
            ).otherwise("NONE")
        ).withColumn(
            # Niveau de risque
            "risk_level", when(
                col("anomaly_type") == "PRICE_VOLUME", "HIGH"
            ).when(
                col("anomaly_type").isin(["PRICE", "VOLUME"]), "MEDIUM"
            ).otherwise("LOW")
        )
        
        anomaly_count = df_anomalies.filter(col("anomaly_type") != "NONE").count()
        print(f"⚠️ Anomalies détectées: {anomaly_count}")
        
        return df_anomalies

    def generate_market_summary(self, df: DataFrame) -> DataFrame:
        """Génère un résumé du marché"""
        print("📊 Génération du résumé de marché...")
        
        # Dernière timestamp pour chaque symbole
        latest_data = df.groupBy("symbol").agg(
            spark_max("timestamp").alias("latest_timestamp")
        )
        
        # Jointure pour obtenir les dernières données
        df_latest = df.join(
            latest_data,
            (df.symbol == latest_data.symbol) & 
            (df.timestamp == latest_data.latest_timestamp)
        ).select(df["*"])
        
        # Résumé par marché
        market_summary = df_latest.groupBy("market").agg(
            spark_round(avg("close"), 2).alias("avg_price"),
            spark_round(avg("volume"), 0).alias("avg_volume"),
            spark_round(avg("price_change_pct"), 2).alias("avg_change_pct"),
            spark_round(avg("volatility_20"), 2).alias("avg_volatility"),
            spark_round(avg("rsi"), 2).alias("avg_rsi"),
            count("symbol").alias("symbol_count"),
            sum(when(col("price_change_pct") > 0, 1).otherwise(0)).alias("gainers"),
            sum(when(col("price_change_pct") < 0, 1).otherwise(0)).alias("losers"),
            sum(when(col("anomaly_type") != "NONE", 1).otherwise(0)).alias("anomalies")
        ).withColumn(
            "market_sentiment", when(
                col("avg_change_pct") > 1, "BULLISH"
            ).when(
                col("avg_change_pct") < -1, "BEARISH"
            ).otherwise("NEUTRAL")
        ).withColumn(
            "timestamp", current_timestamp()
        )
        
        print("✅ Résumé de marché généré")
        return market_summary

    def save_processed_data(self, df: DataFrame, table_name: str):
        """Sauvegarde les données traitées"""
        output_path = f"{self.output_path}{table_name}/"
        print(f"💾 Sauvegarde vers: {output_path}")
        
        try:
            df.coalesce(10) \
              .write \
              .mode("overwrite") \
              .option("compression", "snappy") \
              .parquet(output_path)
            
            print(f"✅ Données sauvegardées: {table_name}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {e}")

    def run_batch_processing(self, date_filter: str = None):
        """Exécute le traitement en batch"""
        print("🔄 Début du traitement en batch...")
        start_time = datetime.now()
        
        try:
            # 1. Lecture des données
            raw_data = self.read_raw_data(date_filter)
            
            if raw_data.count() == 0:
                print("⚠️ Aucune donnée à traiter")
                return
            
            # 2. Nettoyage et validation
            clean_data = self.clean_and_validate(raw_data)
            
            # 3. Calcul des indicateurs techniques
            indicators_data = self.calculate_technical_indicators(clean_data)
            
            # 4. Détection d'anomalies
            anomalies_data = self.detect_anomalies(indicators_data)
            
            # 5. Génération du résumé de marché
            market_summary = self.generate_market_summary(anomalies_data)
            
            # 6. Sauvegarde
            self.save_processed_data(anomalies_data, "financial_indicators")
            self.save_processed_data(market_summary, "market_summary")
            
            # 7. Statistiques finales
            end_time = datetime.now()
            duration = end_time - start_time
            
            print("\n" + "="*50)
            print("📊 RÉSUMÉ DU TRAITEMENT")
            print("="*50)
            print(f"⏱️ Durée: {duration}")
            print(f"📈 Données traitées: {anomalies_data.count():,} lignes")
            print(f"🏪 Marchés: {market_summary.count()} résumés générés")
            
            # Affichage des anomalies critiques
            critical_anomalies = anomalies_data.filter(
                col("risk_level") == "HIGH"
            ).select("symbol", "timestamp", "close", "anomaly_type", "risk_level")
            
            if critical_anomalies.count() > 0:
                print(f"🚨 Anomalies critiques: {critical_anomalies.count()}")
                print("Top 5 anomalies:")
                critical_anomalies.show(5, truncate=False)
            
            print("✅ Traitement terminé avec succès")
            
        except Exception as e:
            print(f"❌ Erreur durant le traitement: {e}")
            raise e

    def cleanup(self):
        """Nettoyage des ressources"""
        print("🧹 Nettoyage des ressources Spark...")
        self.spark.stop()


def main():
    """Fonction principale"""
    print("🚀 Démarrage du processeur de données financières EMR")
    
    # Parse des arguments
    date_filter = sys.argv[1] if len(sys.argv) > 1 else None
    
    processor = None
    try:
        # Initialisation
        processor = FinancialDataProcessor("FinancialDataProcessor-EMR")
        
        # Traitement
        processor.run_batch_processing(date_filter)
        
    except Exception as e:
        print(f"💥 Erreur fatale: {e}")
        sys.exit(1)
        
    finally:
        if processor:
            processor.cleanup()
    
    print("🎉 Processeur de données financières terminé")


if __name__ == "__main__":
    main()
