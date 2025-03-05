# Module IAM pour le pipeline financier
variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN du bucket S3 principal"
  type        = string
}

variable "kinesis_stream_arn" {
  description = "ARN du stream Kinesis principal"
  type        = string
}

variable "crypto_stream_arn" {
  description = "ARN du stream Kinesis crypto"
  type        = string
}

# Rôle IAM pour Lambda (traitement des données)
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-${var.environment}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-lambda-execution-role"
    Environment = var.environment
  }
}

# Politique IAM pour Lambda - accès aux services AWS
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-${var.environment}-lambda-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:DescribeStream",
          "kinesis:GetShardIterator",
          "kinesis:GetRecords",
          "kinesis:ListStreams",
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ]
        Resource = [
          var.kinesis_stream_arn,
          var.crypto_stream_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      }
    ]
  })
}

# Rôle IAM pour EC2 instances (si nécessaire pour Spark)
resource "aws_iam_role" "ec2_spark_role" {
  name = "${var.project_name}-${var.environment}-ec2-spark-role"

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
    Name        = "${var.project_name}-${var.environment}-ec2-spark-role"
    Environment = var.environment
  }
}

# Instance Profile pour EC2
resource "aws_iam_instance_profile" "ec2_spark_profile" {
  name = "${var.project_name}-${var.environment}-ec2-spark-profile"
  role = aws_iam_role.ec2_spark_role.name
}

# Politique IAM pour EC2 Spark
resource "aws_iam_role_policy" "ec2_spark_policy" {
  name = "${var.project_name}-${var.environment}-ec2-spark-policy"
  role = aws_iam_role.ec2_spark_role.id

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
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:DescribeStream",
          "kinesis:GetShardIterator",
          "kinesis:GetRecords",
          "kinesis:ListStreams"
        ]
        Resource = [
          var.kinesis_stream_arn,
          var.crypto_stream_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# Rôle IAM pour accès aux APIs externes (Alpha Vantage, CoinGecko)
resource "aws_iam_role" "api_access_role" {
  name = "${var.project_name}-${var.environment}-api-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-api-access-role"
    Environment = var.environment
  }
}

# Politique pour accès aux secrets (API keys)
resource "aws_iam_role_policy" "api_secrets_policy" {
  name = "${var.project_name}-${var.environment}-api-secrets-policy"
  role = aws_iam_role.api_access_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:*:*:secret:${var.project_name}/${var.environment}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ]
        Resource = [
          var.kinesis_stream_arn,
          var.crypto_stream_arn
        ]
      }
    ]
  })
}

# Outputs
output "lambda_execution_role_arn" {
  description = "ARN du rôle d'exécution Lambda"
  value       = aws_iam_role.lambda_execution_role.arn
}

output "lambda_execution_role_name" {
  description = "Nom du rôle d'exécution Lambda"
  value       = aws_iam_role.lambda_execution_role.name
}

output "ec2_spark_role_arn" {
  description = "ARN du rôle EC2 Spark"
  value       = aws_iam_role.ec2_spark_role.arn
}

output "ec2_spark_instance_profile_name" {
  description = "Nom du profil d'instance EC2 Spark"
  value       = aws_iam_instance_profile.ec2_spark_profile.name
}

output "api_access_role_arn" {
  description = "ARN du rôle d'accès aux APIs"
  value       = aws_iam_role.api_access_role.arn
}

output "api_access_role_name" {
  description = "Nom du rôle d'accès aux APIs"
  value       = aws_iam_role.api_access_role.name
}
