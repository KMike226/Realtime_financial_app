# Module S3 Data Lake pour le pipeline financier
variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

variable "partition_lambda_arn" {
  description = "ARN de la fonction Lambda pour le partitioning automatique"
  type        = string
  default     = ""
}

variable "processing_role_arn" {
  description = "ARN du rôle IAM pour le traitement des données"
  type        = string
  default     = "*"
}

variable "analytics_role_arn" {
  description = "ARN du rôle IAM pour les analyses"
  type        = string
  default     = "*"
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

# Lifecycle rules pour optimiser les coûts avec partitioning intelligent
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  # Règle pour les données raw financières
  rule {
    id     = "raw_financial_data_lifecycle"
    status = "Enabled"

    filter {
      prefix = "raw/financial/"
    }

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
      days = 2555 # 7 ans de rétention
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  # Règle pour les données crypto avec cycle plus rapide
  rule {
    id     = "raw_crypto_data_lifecycle"
    status = "Enabled"

    filter {
      prefix = "raw/crypto/"
    }

    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    transition {
      days          = 180
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 1095 # 3 ans de rétention pour crypto
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  # Règle pour les données processées (plus longue rétention en Standard)
  rule {
    id     = "processed_data_lifecycle"
    status = "Enabled"

    filter {
      prefix = "processed/"
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    expiration {
      days = 3650 # 10 ans pour données processées
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

# Blocage des accès publics pour les données processées
resource "aws_s3_bucket_public_access_block" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket notification pour traitement automatique (conditionnel)
resource "aws_s3_bucket_notification" "data_lake_notifications" {
  count  = var.partition_lambda_arn != "" ? 1 : 0
  bucket = aws_s3_bucket.data_lake.id

  # Notification pour nouvelles données raw financières
  lambda_function {
    lambda_function_arn = var.partition_lambda_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/financial/"
    filter_suffix       = ".json"
  }

  # Notification pour nouvelles données crypto
  lambda_function {
    lambda_function_arn = var.partition_lambda_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/crypto/"
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}

# Permission pour S3 d'invoquer la Lambda de partitioning (conditionnel)
resource "aws_lambda_permission" "allow_s3_invoke" {
  count         = var.partition_lambda_arn != "" ? 1 : 0
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = var.partition_lambda_arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_lake.arn
}

# Politique d'accès pour le partitioning intelligent
resource "aws_s3_bucket_policy" "data_lake_policy" {
  bucket = aws_s3_bucket.data_lake.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowPartitioningService"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
          }
        }
      },
      {
        Sid    = "AllowProcessingAccess"
        Effect = "Allow"
        Principal = {
          AWS = var.processing_role_arn
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/processed/*"
        ]
      },
      {
        Sid    = "AllowAnalyticsAccess"
        Effect = "Allow"
        Principal = {
          AWS = var.analytics_role_arn
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/processed/*",
          "${aws_s3_bucket.data_lake.arn}/analytics/*"
        ]
      }
    ]
  })
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

output "bucket_domain_name" {
  description = "Nom de domaine du bucket Data Lake"
  value       = aws_s3_bucket.data_lake.bucket_domain_name
}

output "partition_structure" {
  description = "Structure de partitioning recommandée"
  value = {
    raw_financial = "raw/financial/year=YYYY/month=MM/day=DD/hour=HH/symbol=SYMBOL/"
    raw_crypto    = "raw/crypto/year=YYYY/month=MM/day=DD/hour=HH/symbol=SYMBOL/"
    processed     = "processed/data_type=TYPE/year=YYYY/month=MM/day=DD/"
    analytics     = "analytics/report_type=TYPE/year=YYYY/month=MM/"
  }
}

output "lifecycle_policies" {
  description = "Politiques de cycle de vie configurées"
  value = {
    financial_data = "Standard(0d) -> IA(30d) -> Glacier(90d) -> Deep Archive(365d) -> Delete(2555d)"
    crypto_data    = "Standard(0d) -> IA(7d) -> Glacier(30d) -> Deep Archive(180d) -> Delete(1095d)"
    processed_data = "Standard(0d) -> IA(90d) -> Glacier(365d) -> Delete(3650d)"
  }
}
