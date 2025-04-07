# Variables pour le module Grafana
# ===================================

variable "project_name" {
  description = "Nom du projet"
  type        = string
  default     = "financial-platform"
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "vpc_id" {
  description = "ID du VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs des sous-réseaux privés"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "IDs des sous-réseaux publics"
  type        = list(string)
}

variable "s3_bucket_name" {
  description = "Nom du bucket S3 data lake"
  type        = string
}

variable "rds_endpoint" {
  description = "Endpoint de la base de données RDS"
  type        = string
  default     = ""
}

variable "grafana_admin_password" {
  description = "Mot de passe admin Grafana"
  type        = string
  sensitive   = true
  default     = "admin123!"
}

variable "certificate_arn" {
  description = "ARN du certificat SSL"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Nom de domaine pour Grafana"
  type        = string
  default     = ""
}

variable "enable_auto_scaling" {
  description = "Activer l'auto-scaling pour ECS"
  type        = bool
  default     = true
}

variable "min_capacity" {
  description = "Capacité minimale ECS"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Capacité maximale ECS"
  type        = number
  default     = 3
}

variable "cpu_target" {
  description = "Cible CPU pour auto-scaling (%)"
  type        = number
  default     = 70
}

variable "memory_target" {
  description = "Cible mémoire pour auto-scaling (%)"
  type        = number
  default     = 80
}

variable "log_retention_days" {
  description = "Rétention des logs CloudWatch (jours)"
  type        = number
  default     = 14
}

variable "grafana_version" {
  description = "Version de Grafana à déployer"
  type        = string
  default     = "10.2.0"
}

variable "cpu_units" {
  description = "Unités CPU pour ECS (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 512
}

variable "memory_mb" {
  description = "Mémoire en MB pour ECS"
  type        = number
  default     = 1024
}

variable "health_check_grace_period" {
  description = "Période de grâce pour health check (secondes)"
  type        = number
  default     = 60
}

variable "enable_monitoring" {
  description = "Activer Container Insights"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Rétention des backups EFS (jours)"
  type        = number
  default     = 7
}

variable "enable_encryption" {
  description = "Activer le chiffrement pour EFS"
  type        = bool
  default     = true
}

variable "performance_mode" {
  description = "Mode de performance EFS (generalPurpose|maxIO)"
  type        = string
  default     = "generalPurpose"
  
  validation {
    condition     = contains(["generalPurpose", "maxIO"], var.performance_mode)
    error_message = "Performance mode must be 'generalPurpose' or 'maxIO'."
  }
}

variable "throughput_mode" {
  description = "Mode de débit EFS (bursting|provisioned)"
  type        = string
  default     = "provisioned"
  
  validation {
    condition     = contains(["bursting", "provisioned"], var.throughput_mode)
    error_message = "Throughput mode must be 'bursting' or 'provisioned'."
  }
}

variable "provisioned_throughput_mibps" {
  description = "Débit provisionné EFS en MiB/s (si throughput_mode=provisioned)"
  type        = number
  default     = 10
}

variable "tags" {
  description = "Tags à appliquer aux ressources"
  type        = map(string)
  default = {
    Project   = "Financial Platform"
    ManagedBy = "Terraform"
    Component = "Grafana"
  }
}

# Variables pour intégration avec d'autres services
variable "cloudwatch_log_groups" {
  description = "Groupes de logs CloudWatch à surveiller"
  type        = list(string)
  default     = []
}

variable "kinesis_stream_names" {
  description = "Noms des streams Kinesis à surveiller"
  type        = list(string)
  default     = []
}

variable "lambda_function_names" {
  description = "Noms des fonctions Lambda à surveiller"
  type        = list(string)
  default     = []
}

variable "enable_athena_integration" {
  description = "Activer l'intégration Athena pour queries S3"
  type        = bool
  default     = true
}

variable "athena_workgroup" {
  description = "Nom du workgroup Athena"
  type        = string
  default     = "primary"
}

variable "glue_database_name" {
  description = "Nom de la base de données Glue"
  type        = string
  default     = "financial_data"
}
