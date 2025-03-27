# Variables pour le module EKS
# =============================
# Définition des variables d'entrée pour le module EKS

variable "cluster_name" {
  description = "Nom du cluster EKS"
  type        = string
  default     = "financial-app-eks"
  
  validation {
    condition     = length(var.cluster_name) > 0 && length(var.cluster_name) <= 32
    error_message = "Le nom du cluster doit être entre 1 et 32 caractères."
  }
}

variable "environment" {
  description = "Environnement de déploiement (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "L'environnement doit être dev, staging ou prod."
  }
}

variable "vpc_id" {
  description = "ID du VPC où déployer le cluster EKS"
  type        = string
}

variable "subnet_ids" {
  description = "Liste des IDs des sous-réseaux pour le cluster EKS"
  type        = list(string)
  
  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "Au moins 2 sous-réseaux sont requis pour la haute disponibilité."
  }
}

variable "kubernetes_version" {
  description = "Version de Kubernetes"
  type        = string
  default     = "1.28"
  
  validation {
    condition     = can(regex("^1\\.(2[0-9]|3[0-9])$", var.kubernetes_version))
    error_message = "La version Kubernetes doit être valide (ex: 1.28)."
  }
}

variable "node_group_instance_types" {
  description = "Types d'instances pour les nœuds EKS"
  type        = list(string)
  default     = ["t3.medium"]
  
  validation {
    condition     = length(var.node_group_instance_types) > 0
    error_message = "Au moins un type d'instance doit être spécifié."
  }
}

variable "node_group_min_size" {
  description = "Taille minimale du groupe de nœuds"
  type        = number
  default     = 1
  
  validation {
    condition     = var.node_group_min_size >= 0
    error_message = "La taille minimale doit être >= 0."
  }
}

variable "node_group_max_size" {
  description = "Taille maximale du groupe de nœuds"
  type        = number
  default     = 5
  
  validation {
    condition     = var.node_group_max_size >= var.node_group_min_size
    error_message = "La taille maximale doit être >= à la taille minimale."
  }
}

variable "node_group_desired_size" {
  description = "Taille désirée du groupe de nœuds"
  type        = number
  default     = 2
  
  validation {
    condition     = var.node_group_desired_size >= var.node_group_min_size && var.node_group_desired_size <= var.node_group_max_size
    error_message = "La taille désirée doit être entre min et max."
  }
}

variable "enable_irsa" {
  description = "Activer IAM Roles for Service Accounts"
  type        = bool
  default     = true
}

variable "enable_cluster_logging" {
  description = "Activer le logging du cluster EKS"
  type        = bool
  default     = true
}

variable "cluster_log_types" {
  description = "Types de logs à activer pour le cluster"
  type        = list(string)
  default     = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  
  validation {
    condition = alltrue([
      for log_type in var.cluster_log_types : contains([
        "api", "audit", "authenticator", "controllerManager", "scheduler"
      ], log_type)
    ])
    error_message = "Les types de logs doivent être valides."
  }
}

variable "log_retention_days" {
  description = "Nombre de jours de rétention des logs CloudWatch"
  type        = number
  default     = 7
  
  validation {
    condition     = var.log_retention_days >= 1 && var.log_retention_days <= 3653
    error_message = "La rétention des logs doit être entre 1 et 3653 jours."
  }
}

variable "enable_encryption" {
  description = "Activer l'encryption des secrets Kubernetes"
  type        = bool
  default     = true
}

variable "node_disk_size" {
  description = "Taille du disque pour les nœuds EKS (en GB)"
  type        = number
  default     = 20
  
  validation {
    condition     = var.node_disk_size >= 20 && var.node_disk_size <= 1000
    error_message = "La taille du disque doit être entre 20 et 1000 GB."
  }
}

variable "tags" {
  description = "Tags additionnels à appliquer aux ressources"
  type        = map(string)
  default     = {}
}

variable "allowed_cidr_blocks" {
  description = "Blocs CIDR autorisés pour l'accès SSH"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}

variable "spark_ports" {
  description = "Ports utilisés par Spark (début et fin)"
  type        = object({
    start = number
    end   = number
  })
  default = {
    start = 8080
    end   = 8089
  }
}

variable "max_unavailable_percentage" {
  description = "Pourcentage maximum de nœuds indisponibles lors des mises à jour"
  type        = number
  default     = 25
  
  validation {
    condition     = var.max_unavailable_percentage >= 1 && var.max_unavailable_percentage <= 100
    error_message = "Le pourcentage doit être entre 1 et 100."
  }
}
