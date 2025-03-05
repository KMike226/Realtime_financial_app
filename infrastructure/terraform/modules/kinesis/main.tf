# Module Kinesis pour l'ingestion de données financières
variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

variable "stream_name" {
  description = "Nom du stream Kinesis"
  type        = string
}

variable "shard_count" {
  description = "Nombre de shards pour le stream"
  type        = number
  default     = 1
}

variable "retention_period" {
  description = "Période de rétention en heures"
  type        = number
  default     = 24
}

# Stream Kinesis principal
resource "aws_kinesis_stream" "financial_data" {
  name             = "${var.project_name}-${var.environment}-${var.stream_name}"
  shard_count      = var.shard_count
  retention_period = var.retention_period

  shard_level_metrics = [
    "IncomingRecords",
    "OutgoingRecords",
  ]

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-${var.stream_name}"
    Environment = var.environment
    Purpose     = "Financial Data Ingestion"
  }
}

# Stream Kinesis pour les données crypto
resource "aws_kinesis_stream" "crypto_data" {
  name             = "${var.project_name}-${var.environment}-crypto-stream"
  shard_count      = var.shard_count
  retention_period = var.retention_period

  shard_level_metrics = [
    "IncomingRecords",
    "OutgoingRecords",
  ]

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-crypto-stream"
    Environment = var.environment
    Purpose     = "Crypto Data Ingestion"
  }
}

# Kinesis Firehose pour archivage automatique vers S3
resource "aws_kinesis_firehose_delivery_stream" "s3_delivery" {
  name        = "${var.project_name}-${var.environment}-s3-delivery"
  destination = "s3"

  s3_configuration {
    role_arn   = aws_iam_role.firehose_role.arn
    bucket_arn = var.s3_bucket_arn
    
    prefix = "financial-data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
    error_output_prefix = "errors/"
    
    buffering_size     = 5
    buffering_interval = 300
    
    compression_format = "GZIP"

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose_logs.name
      log_stream_name = aws_cloudwatch_log_stream.firehose_logs.name
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-s3-delivery"
    Environment = var.environment
  }
}

# CloudWatch Log Group pour Firehose
resource "aws_cloudwatch_log_group" "firehose_logs" {
  name              = "/aws/kinesisfirehose/${var.project_name}-${var.environment}-s3-delivery"
  retention_in_days = 14

  tags = {
    Name        = "${var.project_name}-${var.environment}-firehose-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_stream" "firehose_logs" {
  name           = "S3Delivery"
  log_group_name = aws_cloudwatch_log_group.firehose_logs.name
}

# Rôle IAM pour Kinesis Firehose
resource "aws_iam_role" "firehose_role" {
  name = "${var.project_name}-${var.environment}-firehose-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "firehose.amazonaws.com"
        }
      }
    ]
  })
}

# Politique IAM pour Kinesis Firehose
resource "aws_iam_role_policy" "firehose_policy" {
  name = "${var.project_name}-${var.environment}-firehose-policy"
  role = aws_iam_role.firehose_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:AbortMultipartUpload",
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads",
          "s3:PutObject"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:*:*:log-group:/aws/kinesisfirehose/*"
        ]
      }
    ]
  })
}

# Variable pour le bucket S3 (à passer depuis le module parent)
variable "s3_bucket_arn" {
  description = "ARN du bucket S3 pour l'archivage"
  type        = string
  default     = ""
}

# Outputs
output "stream_name" {
  description = "Nom du stream Kinesis principal"
  value       = aws_kinesis_stream.financial_data.name
}

output "stream_arn" {
  description = "ARN du stream Kinesis principal"
  value       = aws_kinesis_stream.financial_data.arn
}

output "crypto_stream_name" {
  description = "Nom du stream Kinesis crypto"
  value       = aws_kinesis_stream.crypto_data.name
}

output "crypto_stream_arn" {
  description = "ARN du stream Kinesis crypto"
  value       = aws_kinesis_stream.crypto_data.arn
}

output "firehose_delivery_stream" {
  description = "Nom du Kinesis Firehose delivery stream"
  value       = aws_kinesis_firehose_delivery_stream.s3_delivery.name
}
