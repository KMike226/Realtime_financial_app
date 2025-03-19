# Module Kinesis avancé pour l'ingestion de données financières temps réel
# =====================================================================

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
  default     = 2
}

variable "retention_period" {
  description = "Période de rétention en heures (24-8760)"
  type        = number
  default     = 168  # 7 jours par défaut
}

variable "encryption_type" {
  description = "Type de chiffrement (KMS ou NONE)"
  type        = string
  default     = "KMS"
}

variable "kms_key_id" {
  description = "ID de la clé KMS pour le chiffrement"
  type        = string
  default     = "alias/aws/kinesis"
}

variable "enable_enhanced_monitoring" {
  description = "Active le monitoring avancé Kinesis"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags à appliquer aux ressources"
  type        = map(string)
  default     = {}
}

variable "enable_data_transformation" {
  description = "Active la transformation des données via Lambda"
  type        = bool
  default     = false
}

variable "s3_bucket_arn" {
  description = "ARN du bucket S3 pour l'archivage"
  type        = string
}

# Stream Kinesis principal pour données financières
resource "aws_kinesis_stream" "financial_data" {
  name             = "${var.project_name}-${var.environment}-${var.stream_name}"
  shard_count      = var.shard_count
  retention_period = var.retention_period

  # Métriques au niveau des shards pour monitoring avancé
  shard_level_metrics = var.enable_enhanced_monitoring ? [
    "IncomingRecords",
    "IncomingBytes", 
    "OutgoingRecords",
    "OutgoingBytes",
    "WriteProvisionedThroughputExceeded",
    "ReadProvisionedThroughputExceeded",
    "IteratorAgeMilliseconds"
  ] : [
    "IncomingRecords",
    "OutgoingRecords"
  ]

  # Configuration du mode de stream
  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  # Chiffrement des données
  dynamic "encryption_type" {
    for_each = var.encryption_type == "KMS" ? [1] : []
    content {
      encryption_type = var.encryption_type
      key_id         = var.kms_key_id
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.stream_name}"
      Environment = var.environment
      Purpose     = "Financial Data Ingestion"
      Type        = "Primary Stream"
      DataSource  = "Alpha Vantage, IEX Cloud"
    }
  )
}

# Stream Kinesis dédié aux données crypto
resource "aws_kinesis_stream" "crypto_data" {
  name             = "${var.project_name}-${var.environment}-crypto-stream"
  shard_count      = max(1, floor(var.shard_count / 2))  # Moins de shards pour crypto
  retention_period = var.retention_period

  # Métriques adaptées aux données crypto
  shard_level_metrics = var.enable_enhanced_monitoring ? [
    "IncomingRecords",
    "IncomingBytes",
    "OutgoingRecords", 
    "OutgoingBytes",
    "WriteProvisionedThroughputExceeded",
    "ReadProvisionedThroughputExceeded",
    "IteratorAgeMilliseconds"
  ] : [
    "IncomingRecords",
    "OutgoingRecords"
  ]

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  # Chiffrement des données crypto
  dynamic "encryption_type" {
    for_each = var.encryption_type == "KMS" ? [1] : []
    content {
      encryption_type = var.encryption_type
      key_id         = var.kms_key_id
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-crypto-stream"
      Environment = var.environment
      Purpose     = "Crypto Data Ingestion"
      Type        = "Crypto Stream"
      DataSource  = "CoinGecko, Binance"
    }
  )
}

# Stream Kinesis pour les événements et alertes
resource "aws_kinesis_stream" "events_alerts" {
  name             = "${var.project_name}-${var.environment}-events-stream"
  shard_count      = 1  # Un seul shard pour les événements
  retention_period = var.retention_period

  shard_level_metrics = [
    "IncomingRecords",
    "OutgoingRecords"
  ]

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  # Chiffrement des événements
  dynamic "encryption_type" {
    for_each = var.encryption_type == "KMS" ? [1] : []
    content {
      encryption_type = var.encryption_type
      key_id         = var.kms_key_id
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-events-stream"
      Environment = var.environment
      Purpose     = "Events and Alerts Processing"
      Type        = "Events Stream"
    }
  )
}

# Kinesis Firehose pour archivage automatique vers S3
resource "aws_kinesis_firehose_delivery_stream" "s3_delivery" {
  name        = "${var.project_name}-${var.environment}-s3-delivery"
  destination = "s3"

  s3_configuration {
    role_arn   = aws_iam_role.firehose_role.arn
    bucket_arn = var.s3_bucket_arn
    
    # Partitioning intelligent par source, type et temps
    prefix = "kinesis-raw/source=!{partitionKeyFromQuery:source}/data_type=!{partitionKeyFromQuery:data_type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
    error_output_prefix = "kinesis-errors/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
    
    # Configuration du buffering optimisée
    buffering_size     = 128  # 128 MB
    buffering_interval = 60   # 1 minute
    
    compression_format = "GZIP"

    # Transformation des données avec Lambda (optionnel)
    dynamic "processing_configuration" {
      for_each = var.enable_data_transformation ? [1] : []
      content {
        enabled = true
        
        processors {
          type = "Lambda"
          
          parameters {
            parameter_name  = "LambdaArn"
            parameter_value = aws_lambda_function.firehose_processor[0].arn
          }
          
          parameters {
            parameter_name  = "BufferSizeInMBs"
            parameter_value = "3"
          }
          
          parameters {
            parameter_name  = "BufferIntervalInSeconds"
            parameter_value = "60"
          }
        }
      }
    }

    # Configuration CloudWatch
    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose_logs.name
      log_stream_name = aws_cloudwatch_log_stream.firehose_logs.name
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-s3-delivery"
      Environment = var.environment
      Purpose     = "S3 Data Archival"
    }
  )
}

# Firehose séparé pour les données crypto
resource "aws_kinesis_firehose_delivery_stream" "s3_crypto_delivery" {
  name        = "${var.project_name}-${var.environment}-crypto-s3-delivery"
  destination = "s3"

  s3_configuration {
    role_arn   = aws_iam_role.firehose_role.arn
    bucket_arn = var.s3_bucket_arn
    
    prefix = "crypto-raw/source=!{partitionKeyFromQuery:source}/symbol=!{partitionKeyFromQuery:symbol}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
    error_output_prefix = "crypto-errors/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
    
    buffering_size     = 64   # Moins de données crypto
    buffering_interval = 120  # 2 minutes
    
    compression_format = "GZIP"

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose_crypto_logs.name
      log_stream_name = aws_cloudwatch_log_stream.firehose_crypto_logs.name
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-crypto-s3-delivery"
      Environment = var.environment
      Purpose     = "Crypto S3 Data Archival"
    }
  )
}

# CloudWatch Log Groups pour Firehose
resource "aws_cloudwatch_log_group" "firehose_logs" {
  name              = "/aws/kinesisfirehose/${var.project_name}-${var.environment}-s3-delivery"
  retention_in_days = 14

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-firehose-logs"
      Environment = var.environment
      Type        = "Firehose Logs"
    }
  )
}

resource "aws_cloudwatch_log_stream" "firehose_logs" {
  name           = "S3Delivery"
  log_group_name = aws_cloudwatch_log_group.firehose_logs.name
}

resource "aws_cloudwatch_log_group" "firehose_crypto_logs" {
  name              = "/aws/kinesisfirehose/${var.project_name}-${var.environment}-crypto-s3-delivery"
  retention_in_days = 14

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-firehose-crypto-logs"
      Environment = var.environment
      Type        = "Firehose Crypto Logs"
    }
  )
}

resource "aws_cloudwatch_log_stream" "firehose_crypto_logs" {
  name           = "CryptoS3Delivery"
  log_group_name = aws_cloudwatch_log_group.firehose_crypto_logs.name
}

# CloudWatch Alarms pour monitoring
resource "aws_cloudwatch_metric_alarm" "kinesis_iterator_age" {
  count               = var.enable_enhanced_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-kinesis-iterator-age-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "IteratorAgeMilliseconds"
  namespace           = "AWS/Kinesis"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "60000"  # 1 minute
  alarm_description   = "This metric monitors kinesis iterator age"
  alarm_actions       = [aws_sns_topic.kinesis_alerts[0].arn]

  dimensions = {
    StreamName = aws_kinesis_stream.financial_data.name
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-kinesis-iterator-age-alarm"
      Environment = var.environment
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "kinesis_write_throttled" {
  count               = var.enable_enhanced_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-kinesis-write-throttled"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "WriteProvisionedThroughputExceeded"
  namespace           = "AWS/Kinesis"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors kinesis write throttling"
  alarm_actions       = [aws_sns_topic.kinesis_alerts[0].arn]

  dimensions = {
    StreamName = aws_kinesis_stream.financial_data.name
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-kinesis-write-throttled-alarm"
      Environment = var.environment
    }
  )
}

# SNS Topic pour les alertes Kinesis
resource "aws_sns_topic" "kinesis_alerts" {
  count = var.enable_enhanced_monitoring ? 1 : 0
  name  = "${var.project_name}-${var.environment}-kinesis-alerts"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-kinesis-alerts"
      Environment = var.environment
      Purpose     = "Kinesis Monitoring Alerts"
    }
  )
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
          "s3:PutObject",
          "s3:PutObjectAcl"
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
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:DescribeStream",
          "kinesis:GetShardIterator",
          "kinesis:GetRecords",
          "kinesis:ListShards"
        ]
        Resource = [
          aws_kinesis_stream.financial_data.arn,
          aws_kinesis_stream.crypto_data.arn
        ]
      }
    ]
  })
}

# Politique IAM additionnelle pour transformation Lambda
resource "aws_iam_role_policy" "firehose_lambda_policy" {
  count = var.enable_data_transformation ? 1 : 0
  name  = "${var.project_name}-${var.environment}-firehose-lambda-policy"
  role  = aws_iam_role.firehose_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
          "lambda:GetFunctionConfiguration"
        ]
        Resource = [
          aws_lambda_function.firehose_processor[0].arn
        ]
      }
    ]
  })
}

# Fonction Lambda pour transformation des données Firehose
resource "aws_lambda_function" "firehose_processor" {
  count            = var.enable_data_transformation ? 1 : 0
  filename         = "firehose_processor.zip"
  function_name    = "${var.project_name}-${var.environment}-firehose-processor"
  role            = aws_iam_role.lambda_firehose_role[0].arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.firehose_processor_zip[0].output_base64sha256
  runtime         = "python3.9"
  timeout         = 60

  environment {
    variables = {
      ENVIRONMENT = var.environment
      PROJECT_NAME = var.project_name
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-firehose-processor"
      Environment = var.environment
      Purpose     = "Firehose Data Transformation"
    }
  )
}

# Création du ZIP pour la fonction Lambda
data "archive_file" "firehose_processor_zip" {
  count       = var.enable_data_transformation ? 1 : 0
  type        = "zip"
  output_path = "firehose_processor.zip"
  
  source {
    content = templatefile("${path.module}/lambda/firehose_processor.py", {
      project_name = var.project_name
      environment  = var.environment
    })
    filename = "lambda_function.py"
  }
}

# Rôle IAM pour la fonction Lambda
resource "aws_iam_role" "lambda_firehose_role" {
  count = var.enable_data_transformation ? 1 : 0
  name  = "${var.project_name}-${var.environment}-lambda-firehose-role"

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

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-lambda-firehose-role"
      Environment = var.environment
    }
  )
}

# Politique pour la fonction Lambda
resource "aws_iam_role_policy_attachment" "lambda_firehose_basic" {
  count      = var.enable_data_transformation ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_firehose_role[0].name
}

# ==============================================
# OUTPUTS
# ==============================================

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

output "events_stream_name" {
  description = "Nom du stream Kinesis événements"
  value       = aws_kinesis_stream.events_alerts.name
}

output "events_stream_arn" {
  description = "ARN du stream Kinesis événements"
  value       = aws_kinesis_stream.events_alerts.arn
}

output "firehose_delivery_stream" {
  description = "Nom du Kinesis Firehose delivery stream"
  value       = aws_kinesis_firehose_delivery_stream.s3_delivery.name
}

output "firehose_crypto_delivery_stream" {
  description = "Nom du Kinesis Firehose crypto delivery stream"
  value       = aws_kinesis_firehose_delivery_stream.s3_crypto_delivery.name
}

output "firehose_role_arn" {
  description = "ARN du rôle IAM Firehose"
  value       = aws_iam_role.firehose_role.arn
}

output "sns_topic_arn" {
  description = "ARN du topic SNS pour les alertes"
  value       = var.enable_enhanced_monitoring ? aws_sns_topic.kinesis_alerts[0].arn : null
}

output "lambda_processor_function_name" {
  description = "Nom de la fonction Lambda de transformation"
  value       = var.enable_data_transformation ? aws_lambda_function.firehose_processor[0].function_name : null
}

output "cloudwatch_log_groups" {
  description = "Noms des groupes de logs CloudWatch"
  value = {
    firehose_main   = aws_cloudwatch_log_group.firehose_logs.name
    firehose_crypto = aws_cloudwatch_log_group.firehose_crypto_logs.name
  }
}

output "monitoring_config" {
  description = "Configuration du monitoring"
  value = {
    enhanced_monitoring_enabled = var.enable_enhanced_monitoring
    data_transformation_enabled = var.enable_data_transformation
    encryption_enabled          = var.encryption_type == "KMS"
    retention_period_hours      = var.retention_period
  }
}
