#!/usr/bin/env python3
"""
Configuration pour Spark Structured Streaming
"""

import os
from typing import Dict, Any

class StreamingConfig:
    """Configuration pour le traitement streaming"""
    
    # Configuration Kinesis
    KINESIS_STREAM_NAME = os.getenv("KINESIS_STREAM_NAME", "financial-data-stream")
    KINESIS_REGION = os.getenv("KINESIS_REGION", "us-east-1")
    
    # Configuration Spark
    SPARK_APP_NAME = "FinancialStreamingProcessor"
    SPARK_MASTER = os.getenv("SPARK_MASTER", "yarn")
    
    # Configuration S3
    S3_BUCKET = os.getenv("S3_BUCKET", "financial-pipeline-dev-data-lake")
    CHECKPOINT_LOCATION = f"s3a://{S3_BUCKET}/checkpoints/streaming/"
    
    # Configuration streaming
    TRIGGER_INTERVAL = "30 seconds"
    MAX_RECORDS_PER_BATCH = 1000
    MAX_RECORDS_PER_SECOND = 100
    
    # Configuration fenêtres
    WINDOW_SIZE = "1 minute"
    SLIDE_SIZE = "30 seconds"
    
    # Configuration indicateurs
    SMA_PERIOD = 20
    VOLATILITY_PERIOD = 20
    ANOMALY_THRESHOLD = 3.0
    
    @classmethod
    def get_spark_config(cls) -> Dict[str, str]:
        """Retourne la configuration Spark"""
        return {
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
            "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
            "spark.sql.execution.arrow.pyspark.enabled": "true",
            "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
            "spark.hadoop.fs.s3a.aws.credentials.provider": 
                "com.amazonaws.auth.InstanceProfileCredentialsProvider",
            "spark.sql.streaming.checkpointLocation": cls.CHECKPOINT_LOCATION,
            "spark.sql.streaming.stateStore.providerClass": 
                "org.apache.spark.sql.execution.streaming.state.HDFSBackedStateStoreProvider"
        }
    
    @classmethod
    def get_kinesis_options(cls) -> Dict[str, str]:
        """Retourne les options Kinesis"""
        return {
            "streamName": cls.KINESIS_STREAM_NAME,
            "region": cls.KINESIS_REGION,
            "initialPosition": "latest",
            "maxRecordsPerBatch": str(cls.MAX_RECORDS_PER_BATCH),
            "maxRecordsPerSecond": str(cls.MAX_RECORDS_PER_SECOND)
        }
