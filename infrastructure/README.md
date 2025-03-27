# Orchestration de Conteneurs ECS/EKS
# ====================================
# Documentation pour l'orchestration de conteneurs avec ECS et EKS

## Vue d'ensemble

Ce module fournit une solution complète pour l'orchestration de conteneurs dans AWS, supportant à la fois ECS (Elastic Container Service) et EKS (Elastic Kubernetes Service) pour exécuter des applications Spark et d'autres services de traitement de données.

## Architecture

### ECS (Elastic Container Service)
- **Cluster ECS** avec auto-scaling
- **Capacity Provider** pour gestion automatique des instances
- **IAM Roles** pour sécurité et permissions
- **CloudWatch Logs** pour monitoring
- **Security Groups** configurés pour Spark

### EKS (Elastic Kubernetes Service)
- **Cluster EKS** avec version Kubernetes configurable
- **Node Groups** avec auto-scaling
- **IRSA** (IAM Roles for Service Accounts) pour sécurité
- **OIDC Provider** pour authentification
- **Namespaces** et **Service Accounts** pour Spark
- **ConfigMaps** pour configuration Spark

## Structure des fichiers

```
infrastructure/
├── terraform/
│   ├── modules/
│   │   ├── ecs/                 # Module Terraform ECS
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── user_data.sh
│   │   └── eks/                 # Module Terraform EKS
│   │       ├── main.tf
│   │       ├── variables.tf
│   │       └── outputs.tf
│   └── environments/
│       └── dev/                 # Configuration environnement dev
├── docker/
│   └── spark/                   # Configuration Docker Spark
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── conf/
│       │   ├── spark-defaults.conf
│       │   └── spark-env.sh
│       └── entrypoint.sh
└── scripts/
    └── deploy-containers.sh     # Script de déploiement
```

## Utilisation

### Prérequis

1. **AWS CLI** configuré avec les bonnes permissions
2. **Terraform** >= 1.0
3. **Docker** pour la construction des images
4. **kubectl** pour EKS (optionnel)

### Déploiement ECS

```bash
# Déploiement du cluster ECS
./scripts/deploy-containers.sh deploy-ecs --environment dev --region us-east-1

# Construction des images Docker
./scripts/deploy-containers.sh build-images

# Déploiement de Spark sur ECS
./scripts/deploy-containers.sh deploy-spark
```

### Déploiement EKS

```bash
# Déploiement du cluster EKS
./scripts/deploy-containers.sh deploy-eks --environment dev --region us-east-1

# Configuration de kubectl
aws eks update-kubeconfig --region us-east-1 --name financial-app-eks-dev

# Vérification du cluster
kubectl get nodes
```

### Développement local

```bash
# Démarrage de l'environnement de développement
cd infrastructure/docker/spark
docker-compose up -d

# Accès aux interfaces
# Master UI: http://localhost:8080
# Worker UI: http://localhost:8081
# Jupyter: http://localhost:8888
```

## Configuration

### Variables d'environnement

```bash
# Configuration AWS
export AWS_DEFAULT_REGION=us-east-1
export AWS_PROFILE=your-profile

# Configuration Spark
export SPARK_MASTER_URL=spark://localhost:7077
export FINANCIAL_DATA_BUCKET=financial-data-lake-dev
export KINESIS_STREAM_NAME=financial-data-stream
```

### Configuration Terraform

Les variables principales sont définies dans `variables.tf` :

- `cluster_name` : Nom du cluster
- `environment` : Environnement (dev, staging, prod)
- `vpc_id` : ID du VPC
- `subnet_ids` : IDs des sous-réseaux
- `instance_type` : Type d'instance EC2
- `min_capacity` / `max_capacity` : Limites d'auto-scaling

## Monitoring et Logs

### CloudWatch Logs

- **ECS** : `/ecs/financial-app-cluster`
- **EKS** : `/aws/eks/financial-app-eks/cluster`
- **Applications** : `/ecs/financial-app-cluster/tasks`

### Métriques importantes

- **ECS** : CPU/Mémoire utilisation, tâches actives
- **EKS** : Nœuds disponibles, pods en cours
- **Spark** : Jobs terminés, temps d'exécution

## Sécurité

### IAM Roles

- **ECS Cluster Role** : Permissions pour le cluster
- **ECS Task Role** : Permissions pour les tâches
- **EKS Node Role** : Permissions pour les nœuds
- **IRSA Roles** : Permissions pour les Service Accounts

### Security Groups

- **Ports ouverts** : 22 (SSH), 80/443 (HTTP/HTTPS), 8080-8089 (Spark)
- **Sources autorisées** : Sous-réseaux privés pour SSH, Internet pour HTTP

## Maintenance

### Mise à jour des images

```bash
# Reconstruction des images
./scripts/deploy-containers.sh build-images

# Redéploiement
./scripts/deploy-containers.sh deploy-spark
```

### Scaling

```bash
# ECS - Modification via Terraform
terraform apply -var="desired_capacity=5"

# EKS - Modification via kubectl
kubectl scale deployment spark-app --replicas=5
```

### Nettoyage

```bash
# Nettoyage complet
./scripts/deploy-containers.sh cleanup
```

## Dépannage

### Problèmes courants

1. **Cluster ECS ne démarre pas**
   - Vérifier les Security Groups
   - Vérifier les permissions IAM
   - Consulter les logs CloudWatch

2. **Cluster EKS inaccessible**
   - Vérifier la configuration kubectl
   - Vérifier les permissions AWS
   - Consulter les logs du cluster

3. **Spark ne démarre pas**
   - Vérifier la configuration des ports
   - Vérifier les variables d'environnement
   - Consulter les logs des conteneurs

### Commandes utiles

```bash
# Statut des clusters
./scripts/deploy-containers.sh status

# Logs ECS
aws logs describe-log-groups --log-group-name-prefix /ecs/

# Logs EKS
kubectl logs -n financial-app deployment/spark-app

# Statut des conteneurs Docker
docker ps
docker logs <container_name>
```

## Support

Pour toute question ou problème :
1. Consulter les logs CloudWatch
2. Vérifier la configuration Terraform
3. Tester en mode développement local
4. Consulter la documentation AWS ECS/EKS
