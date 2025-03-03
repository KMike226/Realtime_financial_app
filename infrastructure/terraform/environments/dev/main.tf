# Configuration Terraform pour l'environnement de développement
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

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
  
  vpc_cidr = "10.0.0.0/16"
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
  
  stream_name = "financial-data-stream"
  shard_count = 2
}

# Outputs
output "vpc_id" {
  description = "ID du VPC créé"
  value       = module.vpc.vpc_id
}

output "data_lake_bucket" {
  description = "Nom du bucket S3 Data Lake"
  value       = module.data_lake.bucket_name
}

output "kinesis_stream_name" {
  description = "Nom du stream Kinesis"
  value       = module.kinesis.stream_name
}
