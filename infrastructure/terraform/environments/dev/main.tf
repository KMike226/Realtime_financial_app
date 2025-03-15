# Configuration Terraform pour l'environnement de développement

# Configuration du provider AWS
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "dev"
      Project     = "financial-pipeline"
      ManagedBy   = "terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "Région AWS pour le déploiement"
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Nom du projet"
  type        = string
  default     = "financial-pipeline"
}

# Module VPC
module "vpc" {
  source = "../../modules/vpc"

  project_name = var.project_name
  environment  = "dev"

  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["eu-west-1a", "eu-west-1b"]

  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets = ["10.0.11.0/24", "10.0.12.0/24"]
}

# Module S3 Data Lake
module "data_lake" {
  source = "../../modules/s3"

  project_name = var.project_name
  environment  = "dev"
}

# Module Kinesis
module "kinesis" {
  source = "../../modules/kinesis"

  project_name = var.project_name
  environment  = "dev"

  stream_name   = "financial-data-stream"
  shard_count   = 2
  s3_bucket_arn = module.data_lake.bucket_arn
}

# Module Security Groups
module "security" {
  source = "../../modules/security"

  project_name = var.project_name
  environment  = "dev"
  vpc_id       = module.vpc.vpc_id
  vpc_cidr     = "10.0.0.0/16"
}

# Module IAM
module "iam" {
  source = "../../modules/iam"

  project_name       = var.project_name
  environment        = "dev"
  s3_bucket_arn      = module.data_lake.bucket_arn
  kinesis_stream_arn = module.kinesis.stream_arn
  crypto_stream_arn  = module.kinesis.crypto_stream_arn
}

# Outputs
output "vpc_id" {
  description = "ID du VPC créé"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "IDs des sous-réseaux publics"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs des sous-réseaux privés"
  value       = module.vpc.private_subnet_ids
}

output "data_lake_bucket" {
  description = "Nom du bucket S3 Data Lake"
  value       = module.data_lake.bucket_name
}

output "processed_data_bucket" {
  description = "Nom du bucket S3 pour données processées"
  value       = module.data_lake.processed_bucket_name
}

output "kinesis_stream_name" {
  description = "Nom du stream Kinesis principal"
  value       = module.kinesis.stream_name
}

output "crypto_stream_name" {
  description = "Nom du stream Kinesis crypto"
  value       = module.kinesis.crypto_stream_name
}

output "lambda_execution_role_arn" {
  description = "ARN du rôle d'exécution Lambda"
  value       = module.iam.lambda_execution_role_arn
}

output "ec2_spark_instance_profile" {
  description = "Nom du profil d'instance EC2 Spark"
  value       = module.iam.ec2_spark_instance_profile_name
}

output "lambda_security_group_id" {
  description = "ID du security group Lambda"
  value       = module.security.lambda_security_group_id
}

output "ec2_spark_security_group_id" {
  description = "ID du security group EC2 Spark"
  value       = module.security.ec2_spark_security_group_id
}
