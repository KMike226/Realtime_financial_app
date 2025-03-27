# Dockerfile pour Spark sur ECS/EKS
# ==================================
# Image Docker optimisée pour exécuter Spark dans des conteneurs
# Compatible avec ECS et Kubernetes

FROM openjdk:11-jre-slim

# Métadonnées de l'image
LABEL maintainer="Financial App Team"
LABEL description="Image Spark pour applications financières"
LABEL version="1.0.0"

# Variables d'environnement
ENV SPARK_VERSION=3.4.0
ENV HADOOP_VERSION=3
ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.5-src.zip:$PYTHONPATH

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Création de l'utilisateur spark
RUN groupadd -r spark && useradd -r -g spark spark

# Téléchargement et installation de Spark
RUN wget -q https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
    && tar -xzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
    && mv spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} ${SPARK_HOME} \
    && rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz

# Installation des dépendances Python pour Spark
RUN pip3 install --no-cache-dir \
    pyspark==${SPARK_VERSION} \
    pandas \
    numpy \
    boto3 \
    requests \
    py4j

# Configuration des permissions
RUN chown -R spark:spark ${SPARK_HOME}

# Création des répertoires de travail
RUN mkdir -p /app /logs /tmp/spark-events \
    && chown -R spark:spark /app /logs /tmp/spark-events

# Copie des scripts d'application
COPY --chown=spark:spark scripts/ /app/scripts/
COPY --chown=spark:spark spark-jobs/ /app/spark-jobs/

# Configuration Spark pour conteneurs
COPY --chown=spark:spark conf/spark-defaults.conf ${SPARK_HOME}/conf/
COPY --chown=spark:spark conf/spark-env.sh ${SPARK_HOME}/conf/

# Script d'entrée
COPY --chown=spark:spark entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Exposition des ports Spark
EXPOSE 8080 8081 4040 7077

# Utilisateur par défaut
USER spark

# Répertoire de travail
WORKDIR /app

# Point d'entrée
ENTRYPOINT ["/app/entrypoint.sh"]

# Commande par défaut
CMD ["spark-submit", "--help"]
