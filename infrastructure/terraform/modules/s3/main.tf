# Module S3 Data Lake pour le pipeline financier
variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

# Bucket principal pour le Data Lake
resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.project_name}-${var.environment}-data-lake-${random_string.suffix.result}"

  tags = {
    Name        = "${var.project_name}-${var.environment}-data-lake"
    Environment = var.environment
    Purpose     = "Data Lake"
  }
}

# Génération d'un suffixe aléatoire pour garantir l'unicité
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Configuration du versioning
resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Configuration du chiffrement
resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Blocage des accès publics
resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rules pour optimiser les coûts
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "financial_data_lifecycle"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 2555  # 7 ans de rétention
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# Bucket pour les données processées
resource "aws_s3_bucket" "processed_data" {
  bucket = "${var.project_name}-${var.environment}-processed-${random_string.suffix.result}"

  tags = {
    Name        = "${var.project_name}-${var.environment}-processed"
    Environment = var.environment
    Purpose     = "Processed Data"
  }
}

# Configuration du versioning pour les données processées
resource "aws_s3_bucket_versioning" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Chiffrement pour les données processées
resource "aws_s3_bucket_server_side_encryption_configuration" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Outputs
output "bucket_name" {
  description = "Nom du bucket Data Lake"
  value       = aws_s3_bucket.data_lake.id
}

output "bucket_arn" {
  description = "ARN du bucket Data Lake"
  value       = aws_s3_bucket.data_lake.arn
}

output "processed_bucket_name" {
  description = "Nom du bucket pour données processées"
  value       = aws_s3_bucket.processed_data.id
}

output "processed_bucket_arn" {
  description = "ARN du bucket pour données processées"
  value       = aws_s3_bucket.processed_data.arn
}
