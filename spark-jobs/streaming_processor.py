#!/usr/bin/env python3
"""
Spark Structured Streaming pour traitement temps réel des données financières
"""

import sys
import json
from datetime import datetime
from typing import Dict, Any

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, current_timestamp, window, avg, max as spark_max,
    min as spark_min, count, sum as spark_sum, when, lag, lead,
    stddev, round as spark_round, abs as spark_abs, lit
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    TimestampType, IntegerType, BooleanType
)
from pyspark.sql.window import Window
import boto3

class StreamingProcessor:
    """Processeur Spark Structured Streaming pour données temps réel"""
    
    def __init__(self, app_name: str = "FinancialStreamingProcessor"):
        """Initialisation du processeur streaming"""
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
        
        # Configuration Kinesis
        self.kinesis_stream_name = self._get_kinesis_stream()
        self.kinesis_region = "us-east-1"
        self.checkpoint_location = f"s3a://financial-pipeline-dev-data-lake/checkpoints/streaming/"
        
        print(f"🚀 Spark Streaming Session initialisée: {app_name}")
        print(f"📡 Stream Kinesis: {self.kinesis_stream_name}")
        print(f"⚙️ Configuration: Streaming temps réel activé")

    def _get_kinesis_stream(self) -> str:
        """Récupère le nom du stream Kinesis"""
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
                        if tag['Key'] == 'KinesisStream':
                            return tag['Value']
            
        except Exception as e:
            print(f"⚠️ Impossible de récupérer le stream depuis les métadonnées: {e}")
        
        # Fallback pour les tests
        return "financial-data-stream"

    def create_schema(self) -> StructType:
        """Schéma pour les données financières streaming"""
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

    def read_from_kinesis(self):
        """Lit les données depuis Kinesis Data Streams"""
        print(f"📡 Lecture depuis Kinesis: {self.kinesis_stream_name}")
        
        # Configuration Kinesis
        kinesis_options = {
            "streamName": self.kinesis_stream_name,
            "region": self.kinesis_region,
            "initialPosition": "latest",
            "maxRecordsPerBatch": "1000",
            "maxRecordsPerSecond": "100"
        }
        
        # Lecture streaming depuis Kinesis
        df = self.spark \
            .readStream \
            .format("kinesis") \
            .options(**kinesis_options) \
            .load()
        
        # Parsing des données JSON
        schema = self.create_schema()
        parsed_df = df.select(
            col("data").cast("string").alias("json_data"),
            col("approximateArrivalTimestamp").alias("kinesis_timestamp")
        ).select(
            from_json(col("json_data"), schema).alias("data"),
            col("kinesis_timestamp")
        ).select(
            col("data.*"),
            col("kinesis_timestamp")
        )
        
        return parsed_df

    def validate_streaming_data(self, df):
        """Validation des données streaming"""
        print("🔍 Validation des données streaming...")
        
        # Filtrage des données valides
        validated_df = df.filter(
            (col("symbol").isNotNull()) &
            (col("close") > 0) &
            (col("volume") >= 0) &
            (col("high") >= col("low")) &
            (col("close") <= col("high")) &
            (col("close") >= col("low"))
        )
        
        return validated_df

    def calculate_realtime_indicators(self, df):
        """Calcul des indicateurs techniques en temps réel"""
        print("📈 Calcul des indicateurs temps réel...")
        
        # Fenêtre de calcul par symbole
        window_symbol = Window.partitionBy("symbol").orderBy("kinesis_timestamp")
        window_20 = window_symbol.rowsBetween(-19, 0)
        
        # Calcul des indicateurs
        indicators_df = df.withColumn(
            "price_change", col("close") - lag("close", 1).over(window_symbol)
        ).withColumn(
            "price_change_pct", 
            when(lag("close", 1).over(window_symbol) > 0,
                 (col("price_change") / lag("close", 1).over(window_symbol)) * 100)
            .otherwise(0.0)
        ).withColumn(
            "sma_20", avg("close").over(window_20)
        ).withColumn(
            "volatility", stddev("close").over(window_20)
        ).withColumn(
            "volume_sma", avg("volume").over(window_20)
        )
        
        return indicators_df

    def detect_realtime_anomalies(self, df):
        """Détection d'anomalies en temps réel"""
        print("🚨 Détection d'anomalies temps réel...")
        
        window_symbol = Window.partitionBy("symbol").orderBy("kinesis_timestamp")
        window_stats = window_symbol.rowsBetween(-50, 0)
        
        # Calcul des statistiques pour détection d'anomalies
        anomalies_df = df.withColumn(
            "price_mean", avg("close").over(window_stats)
        ).withColumn(
            "price_stddev", stddev("close").over(window_stats)
        ).withColumn(
            "volume_mean", avg("volume").over(window_stats)
        ).withColumn(
            "volume_stddev", stddev("volume").over(window_stats)
        ).withColumn(
            "price_zscore", 
            (col("close") - col("price_mean")) / col("price_stddev")
        ).withColumn(
            "volume_zscore",
            (col("volume") - col("volume_mean")) / col("volume_stddev")
        ).withColumn(
            "is_anomaly", 
            (spark_abs(col("price_zscore")) > 3) | 
            (spark_abs(col("volume_zscore")) > 3)
        ).withColumn(
            "anomaly_severity",
            when(spark_abs(col("price_zscore")) > 5, "CRITICAL")
            .when(spark_abs(col("price_zscore")) > 3, "HIGH")
            .when(spark_abs(col("volume_zscore")) > 3, "MEDIUM")
            .otherwise("LOW")
        )
        
        return anomalies_df

    def aggregate_market_data(self, df):
        """Agrégation des données de marché en temps réel"""
        print("📊 Agrégation des données de marché...")
        
        # Agrégation par fenêtre de temps (1 minute)
        market_agg = df.groupBy(
            window(col("kinesis_timestamp"), "1 minute").alias("time_window"),
            col("market")
        ).agg(
            count("symbol").alias("symbol_count"),
            avg("close").alias("avg_price"),
            avg("volume").alias("avg_volume"),
            avg("price_change_pct").alias("avg_change_pct"),
            avg("volatility").alias("avg_volatility"),
            spark_sum(when(col("price_change_pct") > 0, 1).otherwise(0)).alias("gainers"),
            spark_sum(when(col("price_change_pct") < 0, 1).otherwise(0)).alias("losers"),
            spark_sum(when(col("is_anomaly"), 1).otherwise(0)).alias("anomalies")
        ).withColumn(
            "market_sentiment",
            when(col("avg_change_pct") > 1, "BULLISH")
            .when(col("avg_change_pct") < -1, "BEARISH")
            .otherwise("NEUTRAL")
        ).withColumn(
            "processing_timestamp", current_timestamp()
        )
        
        return market_agg

    def write_to_s3(self, df, table_name):
        """Écriture des données vers S3"""
        output_path = f"s3a://financial-pipeline-dev-data-lake/streaming/{table_name}/"
        
        query = df.writeStream \
            .outputMode("append") \
            .format("parquet") \
            .option("path", output_path) \
            .option("checkpointLocation", f"{self.checkpoint_location}{table_name}") \
            .trigger(processingTime="30 seconds") \
            .start()
        
        return query

    def write_to_console(self, df, table_name):
        """Écriture vers la console pour debug"""
        query = df.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", "false") \
            .trigger(processingTime="10 seconds") \
            .start()
        
        return query

    def run_streaming_processing(self):
        """Exécute le traitement streaming"""
        print("🔄 Début du traitement streaming...")
        
        try:
            # 1. Lecture depuis Kinesis
            raw_stream = self.read_from_kinesis()
            
            # 2. Validation des données
            validated_stream = self.validate_streaming_data(raw_stream)
            
            # 3. Calcul des indicateurs
            indicators_stream = self.calculate_realtime_indicators(validated_stream)
            
            # 4. Détection d'anomalies
            anomalies_stream = self.detect_realtime_anomalies(indicators_stream)
            
            # 5. Agrégation des données de marché
            market_stream = self.aggregate_market_data(anomalies_stream)
            
            # 6. Écriture des résultats
            queries = []
            
            # Écriture des indicateurs vers S3
            indicators_query = self.write_to_s3(indicators_stream, "realtime_indicators")
            queries.append(("Indicators", indicators_query))
            
            # Écriture des anomalies vers S3
            anomalies_query = self.write_to_s3(anomalies_stream, "realtime_anomalies")
            queries.append(("Anomalies", anomalies_query))
            
            # Écriture des agrégations vers S3
            market_query = self.write_to_s3(market_stream, "realtime_market")
            queries.append(("Market", market_query))
            
            # Console pour debug
            console_query = self.write_to_console(
                anomalies_stream.filter(col("is_anomaly") == True),
                "anomalies_console"
            )
            queries.append(("Console", console_query))
            
            print("✅ Streaming queries démarrées:")
            for name, query in queries:
                print(f"  - {name}: {query.id}")
            
            # Attente des queries
            print("⏳ Traitement streaming en cours... (Ctrl+C pour arrêter)")
            for name, query in queries:
                query.awaitTermination()
                
        except KeyboardInterrupt:
            print("\n🛑 Arrêt du streaming demandé...")
            for name, query in queries:
                query.stop()
            print("✅ Streaming arrêté proprement")
            
        except Exception as e:
            print(f"❌ Erreur durant le streaming: {e}")
            raise e

    def cleanup(self):
        """Nettoyage des ressources"""
        print("🧹 Nettoyage des ressources Spark...")
        self.spark.stop()

def main():
    """Fonction principale"""
    print("🚀 Démarrage du processeur streaming financier")
    
    processor = None
    try:
        # Initialisation
        processor = StreamingProcessor("FinancialStreamingProcessor-EMR")
        
        # Traitement streaming
        processor.run_streaming_processing()
        
    except Exception as e:
        print(f"💥 Erreur fatale: {e}")
        sys.exit(1)
        
    finally:
        if processor:
            processor.cleanup()
    
    print("🎉 Processeur streaming terminé")

if __name__ == "__main__":
    main()
