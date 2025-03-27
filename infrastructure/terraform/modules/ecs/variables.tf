# Variables pour le module ECS
# ============================
# Définition des variables d'entrée pour le module ECS

variable "cluster_name" {
  description = "Nom du cluster ECS"
  type        = string
  default     = "financial-app-cluster"
  
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
  description = "ID du VPC où déployer le cluster ECS"
  type        = string
}

variable "subnet_ids" {
  description = "Liste des IDs des sous-réseaux pour le cluster ECS"
  type        = list(string)
  
  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "Au moins 2 sous-réseaux sont requis pour la haute disponibilité."
  }
}

variable "instance_type" {
  description = "Type d'instance EC2 pour les tâches ECS"
  type        = string
  default     = "t3.medium"
  
  validation {
    condition     = can(regex("^[a-z][0-9]+\\.[a-z]+$", var.instance_type))
    error_message = "Le type d'instance doit être valide (ex: t3.medium, m5.large)."
  }
}

variable "min_capacity" {
  description = "Capacité minimale du cluster ECS"
  type        = number
  default     = 1
  
  validation {
    condition     = var.min_capacity >= 0
    error_message = "La capacité minimale doit être >= 0."
  }
}

variable "max_capacity" {
  description = "Capacité maximale du cluster ECS"
  type        = number
  default     = 10
  
  validation {
    condition     = var.max_capacity >= var.min_capacity
    error_message = "La capacité maximale doit être >= à la capacité minimale."
  }
}

variable "desired_capacity" {
  description = "Capacité désirée du cluster ECS"
  type        = number
  default     = 2
  
  validation {
    condition     = var.desired_capacity >= var.min_capacity && var.desired_capacity <= var.max_capacity
    error_message = "La capacité désirée doit être entre min et max."
  }
}

variable "enable_container_insights" {
  description = "Activer Container Insights pour le monitoring"
  type        = bool
  default     = true
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
