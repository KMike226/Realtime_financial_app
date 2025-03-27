#!/bin/bash
# Script d'entrée pour les conteneurs Spark
# =========================================
# Gestion des différents modes d'exécution Spark

set -e

# Fonction d'aide
show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commandes disponibles:"
    echo "  spark-submit    Exécuter une application Spark"
    echo "  spark-shell     Démarrer le shell Spark interactif"
    echo "  spark-sql       Démarrer Spark SQL CLI"
    echo "  pyspark         Démarrer PySpark"
    echo "  help            Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0 spark-submit --class com.example.SparkApp /app/spark-jobs/app.jar"
    echo "  $0 pyspark"
}

# Fonction pour vérifier la configuration
check_config() {
    echo "Vérification de la configuration Spark..."
    
    # Vérifier que SPARK_HOME est défini
    if [ -z "$SPARK_HOME" ]; then
        echo "ERREUR: SPARK_HOME n'est pas défini"
        exit 1
    fi
    
    # Vérifier que les répertoires existent
    if [ ! -d "$SPARK_HOME" ]; then
        echo "ERREUR: SPARK_HOME ($SPARK_HOME) n'existe pas"
        exit 1
    fi
    
    # Vérifier les variables d'environnement AWS
    if [ -z "$AWS_DEFAULT_REGION" ]; then
        echo "ATTENTION: AWS_DEFAULT_REGION n'est pas défini"
    fi
    
    echo "Configuration Spark validée ✓"
}

# Fonction pour démarrer Spark en mode cluster
start_spark_cluster() {
    echo "Démarrage du cluster Spark..."
    
    # Démarrer le master
    $SPARK_HOME/sbin/start-master.sh
    
    # Attendre que le master soit prêt
    sleep 10
    
    # Démarrer les workers
    $SPARK_HOME/sbin/start-worker.sh spark://localhost:7077
    
    echo "Cluster Spark démarré ✓"
    echo "Master UI disponible sur: http://localhost:8080"
    echo "Worker UI disponible sur: http://localhost:8081"
}

# Fonction pour arrêter le cluster Spark
stop_spark_cluster() {
    echo "Arrêt du cluster Spark..."
    
    $SPARK_HOME/sbin/stop-worker.sh
    $SPARK_HOME/sbin/stop-master.sh
    
    echo "Cluster Spark arrêté ✓"
}

# Fonction pour exécuter une application Spark
run_spark_app() {
    local app_class="$1"
    local app_jar="$2"
    local app_args="${@:3}"
    
    echo "Exécution de l'application Spark: $app_class"
    echo "JAR: $app_jar"
    echo "Arguments: $app_args"
    
    $SPARK_HOME/bin/spark-submit \
        --class "$app_class" \
        --master k8s://https://kubernetes.default.svc.cluster.local:443 \
        --deploy-mode cluster \
        --conf spark.kubernetes.namespace=financial-app \
        --conf spark.kubernetes.container.image.pullPolicy=Always \
        --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark-driver \
        "$app_jar" \
        $app_args
}

# Fonction pour exécuter PySpark
run_pyspark() {
    echo "Démarrage de PySpark..."
    
    $SPARK_HOME/bin/pyspark \
        --master k8s://https://kubernetes.default.svc.cluster.local:443 \
        --deploy-mode cluster \
        --conf spark.kubernetes.namespace=financial-app \
        --conf spark.kubernetes.container.image.pullPolicy=Always \
        --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark-driver
}

# Fonction pour exécuter Spark SQL
run_spark_sql() {
    echo "Démarrage de Spark SQL CLI..."
    
    $SPARK_HOME/bin/spark-sql \
        --master k8s://https://kubernetes.default.svc.cluster.local:443 \
        --conf spark.kubernetes.namespace=financial-app \
        --conf spark.kubernetes.container.image.pullPolicy=Always \
        --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark-driver
}

# Fonction pour exécuter le shell Spark
run_spark_shell() {
    echo "Démarrage du shell Spark..."
    
    $SPARK_HOME/bin/spark-shell \
        --master k8s://https://kubernetes.default.svc.cluster.local:443 \
        --conf spark.kubernetes.namespace=financial-app \
        --conf spark.kubernetes.container.image.pullPolicy=Always \
        --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark-driver
}

# Gestion des signaux pour l'arrêt propre
trap 'stop_spark_cluster; exit 0' SIGTERM SIGINT

# Vérification de la configuration au démarrage
check_config

# Gestion des arguments
case "${1:-help}" in
    "spark-submit")
        if [ $# -lt 3 ]; then
            echo "ERREUR: spark-submit nécessite au moins --class et le JAR"
            echo "Usage: $0 spark-submit --class <class> <jar> [args...]"
            exit 1
        fi
        run_spark_app "${@:2}"
        ;;
    "pyspark")
        run_pyspark
        ;;
    "spark-sql")
        run_spark_sql
        ;;
    "spark-shell")
        run_spark_shell
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "Commande inconnue: $1"
        show_help
        exit 1
        ;;
esac
