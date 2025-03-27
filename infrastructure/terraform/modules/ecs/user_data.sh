#!/bin/bash
# Script d'initialisation pour les instances ECS
# ==============================================
# Ce script configure l'instance EC2 pour rejoindre le cluster ECS

# Mise à jour du système
yum update -y

# Installation de Docker
yum install -y docker
systemctl start docker
systemctl enable docker

# Installation de l'agent ECS
echo "ECS_CLUSTER=${cluster_name}" >> /etc/ecs/ecs.config
echo "ECS_ENABLE_TASK_IAM_ROLE=true" >> /etc/ecs/ecs.config
echo "ECS_ENABLE_TASK_ENI=true" >> /etc/ecs/ecs.config

# Redémarrage de l'agent ECS
systemctl restart ecs

# Installation d'outils supplémentaires pour Spark
yum install -y java-1.8.0-openjdk python3 pip3

# Configuration de Java pour Spark
export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk
echo "export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk" >> /etc/environment

# Installation de Spark (optionnel, peut être dans le conteneur)
# wget https://archive.apache.org/dist/spark/spark-3.4.0/spark-3.4.0-bin-hadoop3.tgz
# tar -xzf spark-3.4.0-bin-hadoop3.tgz
# mv spark-3.4.0-bin-hadoop3 /opt/spark

# Log de fin d'initialisation
echo "Initialisation ECS terminée pour le cluster: ${cluster_name}" >> /var/log/ecs-init.log
