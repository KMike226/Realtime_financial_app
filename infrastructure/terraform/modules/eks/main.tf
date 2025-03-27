# Module EKS pour orchestration Kubernetes
# ========================================
# Ce module configure un cluster EKS pour exécuter des applications Kubernetes
# comme Spark, Grafana et d'autres services de traitement de données.

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
  }
}

# Variables d'entrée
variable "cluster_name" {
  description = "Nom du cluster EKS"
  type        = string
  default     = "financial-app-eks"
}

variable "environment" {
  description = "Environnement de déploiement"
  type        = string
  default     = "dev"
}

variable "vpc_id" {
  description = "ID du VPC où déployer le cluster"
  type        = string
}

variable "subnet_ids" {
  description = "IDs des sous-réseaux pour le cluster"
  type        = list(string)
}

variable "kubernetes_version" {
  description = "Version de Kubernetes"
  type        = string
  default     = "1.28"
}

variable "node_group_instance_types" {
  description = "Types d'instances pour les nœuds"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_group_min_size" {
  description = "Taille minimale du groupe de nœuds"
  type        = number
  default     = 1
}

variable "node_group_max_size" {
  description = "Taille maximale du groupe de nœuds"
  type        = number
  default     = 5
}

variable "node_group_desired_size" {
  description = "Taille désirée du groupe de nœuds"
  type        = number
  default     = 2
}

variable "enable_irsa" {
  description = "Activer IAM Roles for Service Accounts"
  type        = bool
  default     = true
}

# Rôle IAM pour le cluster EKS
resource "aws_iam_role" "eks_cluster_role" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.cluster_name}-cluster-role"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Attachement des politiques EKS
resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# Rôle IAM pour les nœuds EKS
resource "aws_iam_role" "eks_node_role" {
  name = "${var.cluster_name}-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.cluster_name}-node-role"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Attachement des politiques pour les nœuds EKS
resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "eks_container_registry_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Politique personnalisée pour les nœuds EKS
resource "aws_iam_policy" "eks_node_policy" {
  name        = "${var.cluster_name}-node-policy"
  description = "Politique personnalisée pour les nœuds EKS du projet financier"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::financial-data-lake/*",
          "arn:aws:s3:::financial-data-lake"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:ListShards"
        ]
        Resource = "arn:aws:kinesis:*:*:stream/financial-data-stream"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "${var.cluster_name}-node-policy"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Attachement de la politique personnalisée
resource "aws_iam_role_policy_attachment" "eks_node_custom_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = aws_iam_policy.eks_node_policy.arn
}

# Groupe de sécurité pour le cluster EKS
resource "aws_security_group" "eks_cluster" {
  name        = "${var.cluster_name}-cluster-sg"
  description = "Groupe de sécurité pour le cluster EKS"
  vpc_id      = var.vpc_id

  # Communication entre les nœuds
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  # Communication depuis les nœuds vers le cluster
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.cluster_name}-cluster-sg"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Groupe de sécurité pour les nœuds EKS
resource "aws_security_group" "eks_nodes" {
  name        = "${var.cluster_name}-nodes-sg"
  description = "Groupe de sécurité pour les nœuds EKS"
  vpc_id      = var.vpc_id

  # Communication depuis le cluster vers les nœuds
  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_cluster.id]
  }

  # Communication entre les nœuds
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  # SSH depuis les sous-réseaux privés
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  # Ports pour Spark (8080-8089)
  ingress {
    from_port   = 8080
    to_port     = 8089
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.cluster_name}-nodes-sg"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Cluster EKS
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    security_group_ids      = [aws_security_group.eks_cluster.id]
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs    = ["0.0.0.0/0"]
  }

  # Configuration du logging
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # Configuration de l'encryption
  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_cloudwatch_log_group.eks_cluster
  ]

  tags = {
    Name        = var.cluster_name
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Clé KMS pour l'encryption du cluster EKS
resource "aws_kms_key" "eks" {
  description             = "Clé KMS pour l'encryption du cluster EKS ${var.cluster_name}"
  deletion_window_in_days = 7

  tags = {
    Name        = "${var.cluster_name}-kms-key"
    Environment = var.environment
    Project     = "financial-app"
  }
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${var.cluster_name}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

# Groupe de logs CloudWatch pour le cluster EKS
resource "aws_cloudwatch_log_group" "eks_cluster" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = 7

  tags = {
    Name        = "${var.cluster_name}-cluster-logs"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Groupe de nœuds EKS
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-nodes"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = var.subnet_ids

  instance_types = var.node_group_instance_types

  scaling_config {
    desired_size = var.node_group_desired_size
    max_size     = var.node_group_max_size
    min_size     = var.node_group_min_size
  }

  update_config {
    max_unavailable_percentage = 25
  }

  # Configuration du disque
  disk_size = 20

  # Labels pour les nœuds
  labels = {
    Environment = var.environment
    Project     = "financial-app"
    NodeType    = "general"
  }

  # Taints pour les nœuds (optionnel)
  # taint {
  #   key    = "dedicated"
  #   value  = "spark"
  #   effect = "NO_SCHEDULE"
  # }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
    aws_iam_role_policy_attachment.eks_node_custom_policy
  ]

  tags = {
    Name        = "${var.cluster_name}-nodes"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Configuration OIDC pour IRSA (IAM Roles for Service Accounts)
data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  count = var.enable_irsa ? 1 : 0

  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer

  tags = {
    Name        = "${var.cluster_name}-oidc"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Provider Kubernetes pour les ressources Kubernetes
provider "kubernetes" {
  host                   = aws_eks_cluster.main.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.main.name]
  }
}

# Namespace pour les applications financières
resource "kubernetes_namespace" "financial_app" {
  metadata {
    name = "financial-app"
    labels = {
      name        = "financial-app"
      environment = var.environment
      project     = "financial-app"
    }
  }
}

# ConfigMap pour la configuration Spark
resource "kubernetes_config_map" "spark_config" {
  metadata {
    name      = "spark-config"
    namespace = kubernetes_namespace.financial_app.metadata[0].name
  }

  data = {
    "spark-defaults.conf" = <<-EOT
      spark.master                     k8s://https://${aws_eks_cluster.main.endpoint}
      spark.submit.deployMode          cluster
      spark.kubernetes.namespace      financial-app
      spark.kubernetes.container.image.pullPolicy Always
      spark.kubernetes.authenticate.driver.serviceAccountName spark-driver
      spark.kubernetes.executor.deleteOnTermination true
      spark.sql.adaptive.enabled true
      spark.sql.adaptive.coalescePartitions.enabled true
    EOT
  }
}

# Service Account pour Spark Driver
resource "kubernetes_service_account" "spark_driver" {
  metadata {
    name      = "spark-driver"
    namespace = kubernetes_namespace.financial_app.metadata[0].name
    annotations = var.enable_irsa ? {
      "eks.amazonaws.com/role-arn" = aws_iam_role.spark_driver_role[0].arn
    } : {}
  }
}

# Service Account pour Spark Executor
resource "kubernetes_service_account" "spark_executor" {
  metadata {
    name      = "spark-executor"
    namespace = kubernetes_namespace.financial_app.metadata[0].name
    annotations = var.enable_irsa ? {
      "eks.amazonaws.com/role-arn" = aws_iam_role.spark_executor_role[0].arn
    } : {}
  }
}

# Rôle IAM pour Spark Driver (avec IRSA)
resource "aws_iam_role" "spark_driver_role" {
  count = var.enable_irsa ? 1 : 0

  name = "${var.cluster_name}-spark-driver-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks[0].arn
        }
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.eks[0].url, "https://", "")}:sub" = "system:serviceaccount:financial-app:spark-driver"
            "${replace(aws_iam_openid_connect_provider.eks[0].url, "https://", "")}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${var.cluster_name}-spark-driver-role"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Rôle IAM pour Spark Executor (avec IRSA)
resource "aws_iam_role" "spark_executor_role" {
  count = var.enable_irsa ? 1 : 0

  name = "${var.cluster_name}-spark-executor-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks[0].arn
        }
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.eks[0].url, "https://", "")}:sub" = "system:serviceaccount:financial-app:spark-executor"
            "${replace(aws_iam_openid_connect_provider.eks[0].url, "https://", "")}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${var.cluster_name}-spark-executor-role"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Attachement des politiques pour Spark Driver
resource "aws_iam_role_policy_attachment" "spark_driver_policy" {
  count      = var.enable_irsa ? 1 : 0
  role       = aws_iam_role.spark_driver_role[0].name
  policy_arn = aws_iam_policy.eks_node_policy.arn
}

# Attachement des politiques pour Spark Executor
resource "aws_iam_role_policy_attachment" "spark_executor_policy" {
  count      = var.enable_irsa ? 1 : 0
  role       = aws_iam_role.spark_executor_role[0].name
  policy_arn = aws_iam_policy.eks_node_policy.arn
}
