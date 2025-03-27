#!/bin/bash
# Configuration de l'environnement Spark
# ======================================
# Variables d'environnement pour Spark dans les conteneurs

export SPARK_HOME=/opt/spark
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin

# Configuration Java
export JAVA_HOME=/usr/local/openjdk-11
export JAVA_OPTS="-Xmx2g -XX:+UseG1GC"

# Configuration Spark
export SPARK_CONF_DIR=$SPARK_HOME/conf
export SPARK_LOG_DIR=/logs
export SPARK_WORKER_DIR=/tmp/spark-events

# Configuration AWS
export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
export AWS_REGION=${AWS_REGION:-us-east-1}

# Configuration des métriques
export SPARK_METRICS_CONF=$SPARK_HOME/conf/metrics.properties

# Configuration de sécurité
export SPARK_AUTHENTICATE_SECRET=${SPARK_AUTHENTICATE_SECRET:-spark-secret-key}

# Configuration des logs
export SPARK_LOG_LEVEL=${SPARK_LOG_LEVEL:-INFO}

# Configuration des applications financières
export FINANCIAL_DATA_BUCKET=${FINANCIAL_DATA_BUCKET:-financial-data-lake}
export KINESIS_STREAM_NAME=${KINESIS_STREAM_NAME:-financial-data-stream}

echo "Configuration Spark initialisée pour l'environnement: $ENVIRONMENT"
