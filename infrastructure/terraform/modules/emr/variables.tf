# Variables du module EMR pour le pipeline financier

variable "project_name" {
  description = "Nom du projet pour le tagging des ressources"
  type        = string
  validation {
    condition     = length(var.project_name) > 0
    error_message = "Le nom du projet ne peut pas être vide."
  }
}

variable "environment" {
  description = "Environnement de déploiement (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "L'environnement doit être dev, staging ou prod."
  }
}

variable "vpc_id" {
  description = "ID du VPC où déployer le cluster EMR"
  type        = string
  validation {
    condition     = can(regex("^vpc-", var.vpc_id))
    error_message = "L'ID du VPC doit commencer par 'vpc-'."
  }
}

variable "private_subnet_ids" {
  description = "Liste des IDs des sous-réseaux privés pour le cluster EMR"
  type        = list(string)
  validation {
    condition     = length(var.private_subnet_ids) >= 1
    error_message = "Au moins un sous-réseau privé est requis."
  }
}

variable "s3_bucket_name" {
  description = "Nom du bucket S3 pour les données, logs et scripts EMR"
  type        = string
  validation {
    condition     = length(var.s3_bucket_name) > 0
    error_message = "Le nom du bucket S3 ne peut pas être vide."
  }
}

# Configuration des instances
variable "master_instance_type" {
  description = "Type d'instance EC2 pour le nœud master EMR"
  type        = string
  default     = "m5.xlarge"
  validation {
    condition = contains([
      "m5.large", "m5.xlarge", "m5.2xlarge", "m5.4xlarge",
      "m5a.large", "m5a.xlarge", "m5a.2xlarge", "m5a.4xlarge",
      "r5.large", "r5.xlarge", "r5.2xlarge", "r5.4xlarge",
      "c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge"
    ], var.master_instance_type)
    error_message = "Type d'instance master non supporté. Utilisez des instances m5, m5a, r5 ou c5."
  }
}

variable "core_instance_type" {
  description = "Type d'instance EC2 pour les nœuds core EMR"
  type        = string
  default     = "m5.large"
  validation {
    condition = contains([
      "m5.large", "m5.xlarge", "m5.2xlarge", "m5.4xlarge",
      "m5a.large", "m5a.xlarge", "m5a.2xlarge", "m5a.4xlarge",
      "r5.large", "r5.xlarge", "r5.2xlarge", "r5.4xlarge",
      "c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge"
    ], var.core_instance_type)
    error_message = "Type d'instance core non supporté. Utilisez des instances m5, m5a, r5 ou c5."
  }
}

variable "core_instance_count" {
  description = "Nombre initial d'instances core dans le cluster"
  type        = number
  default     = 2
  validation {
    condition     = var.core_instance_count >= 1 && var.core_instance_count <= 50
    error_message = "Le nombre d'instances core doit être entre 1 et 50."
  }
}

# Configuration de l'auto-scaling
variable "auto_scaling_min_capacity" {
  description = "Nombre minimum d'instances core pour l'auto-scaling"
  type        = number
  default     = 1
  validation {
    condition     = var.auto_scaling_min_capacity >= 1 && var.auto_scaling_min_capacity <= 10
    error_message = "La capacité minimale d'auto-scaling doit être entre 1 et 10."
  }
}

variable "auto_scaling_max_capacity" {
  description = "Nombre maximum d'instances core pour l'auto-scaling"
  type        = number
  default     = 10
  validation {
    condition     = var.auto_scaling_max_capacity >= 1 && var.auto_scaling_max_capacity <= 100
    error_message = "La capacité maximale d'auto-scaling doit être entre 1 et 100."
  }
}

# Configuration de sécurité
variable "key_name" {
  description = "Nom de la paire de clés EC2 pour l'accès SSH au cluster (optionnel)"
  type        = string
  default     = null
}

variable "allowed_cidr_blocks" {
  description = "Blocs CIDR autorisés à accéder aux interfaces web EMR"
  type        = list(string)
  default     = ["10.0.0.0/16"]
  validation {
    condition     = length(var.allowed_cidr_blocks) > 0
    error_message = "Au moins un bloc CIDR doit être spécifié."
  }
}

# Configuration de coût et optimisation
variable "auto_termination_timeout" {
  description = "Délai d'inactivité (en secondes) avant arrêt automatique du cluster"
  type        = number
  default     = 3600 # 1 heure
  validation {
    condition     = var.auto_termination_timeout >= 300 && var.auto_termination_timeout <= 86400
    error_message = "Le délai d'arrêt automatique doit être entre 300 secondes (5 min) et 86400 secondes (24h)."
  }
}

variable "enable_termination_protection" {
  description = "Activer la protection contre la terminaison du cluster"
  type        = bool
  default     = false
}

variable "spot_instance_percentage" {
  description = "Pourcentage d'instances Spot à utiliser pour les nœuds core (0-100)"
  type        = number
  default     = 0
  validation {
    condition     = var.spot_instance_percentage >= 0 && var.spot_instance_percentage <= 100
    error_message = "Le pourcentage d'instances Spot doit être entre 0 et 100."
  }
}

# Configuration EMR et Spark
variable "emr_release_label" {
  description = "Version d'EMR à utiliser"
  type        = string
  default     = "emr-6.15.0"
  validation {
    condition     = can(regex("^emr-[0-9]+\\.[0-9]+\\.[0-9]+$", var.emr_release_label))
    error_message = "Le label de release EMR doit suivre le format 'emr-X.Y.Z'."
  }
}

variable "applications" {
  description = "Applications EMR à installer sur le cluster"
  type        = list(string)
  default     = ["Spark", "Hadoop", "Hive", "Zeppelin"]
  validation {
    condition = alltrue([
      for app in var.applications : contains([
        "Spark", "Hadoop", "Hive", "Zeppelin", "JupyterHub",
        "Livy", "HBase", "Phoenix", "Presto", "Flink"
      ], app)
    ])
    error_message = "Applications non supportées détectées."
  }
}

# Configuration de monitoring
variable "enable_cloudwatch_monitoring" {
  description = "Activer le monitoring CloudWatch pour le cluster EMR"
  type        = bool
  default     = true
}

variable "cpu_alarm_threshold" {
  description = "Seuil d'alarme CPU en pourcentage"
  type        = number
  default     = 80
  validation {
    condition     = var.cpu_alarm_threshold >= 50 && var.cpu_alarm_threshold <= 100
    error_message = "Le seuil d'alarme CPU doit être entre 50 et 100."
  }
}

variable "memory_alarm_threshold" {
  description = "Seuil d'alarme mémoire en pourcentage"
  type        = number
  default     = 85
  validation {
    condition     = var.memory_alarm_threshold >= 50 && var.memory_alarm_threshold <= 100
    error_message = "Le seuil d'alarme mémoire doit être entre 50 et 100."
  }
}

# Configuration Spark avancée
variable "spark_dynamic_allocation" {
  description = "Activer l'allocation dynamique des executors Spark"
  type        = bool
  default     = true
}

variable "spark_max_executors" {
  description = "Nombre maximum d'executors Spark"
  type        = number
  default     = 8
  validation {
    condition     = var.spark_max_executors >= 1 && var.spark_max_executors <= 100
    error_message = "Le nombre maximum d'executors doit être entre 1 et 100."
  }
}

variable "spark_executor_memory" {
  description = "Mémoire allouée à chaque executor Spark (ex: '2g', '4g')"
  type        = string
  default     = "2g"
  validation {
    condition     = can(regex("^[0-9]+[gmGM]$", var.spark_executor_memory))
    error_message = "La mémoire executor doit être au format '2g' ou '2048m'."
  }
}

variable "spark_executor_cores" {
  description = "Nombre de cœurs CPU par executor Spark"
  type        = number
  default     = 2
  validation {
    condition     = var.spark_executor_cores >= 1 && var.spark_executor_cores <= 16
    error_message = "Le nombre de cœurs par executor doit être entre 1 et 16."
  }
}

# Tags personnalisés
variable "additional_tags" {
  description = "Tags supplémentaires à appliquer aux ressources EMR"
  type        = map(string)
  default     = {}
}
