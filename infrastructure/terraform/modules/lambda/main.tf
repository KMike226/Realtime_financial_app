# Module Lambda pour traitement des données financières
# =====================================================

variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

variable "s3_bucket_name" {
  description = "Nom du bucket S3 pour le stockage"
  type        = string
}

variable "kinesis_stream_arn" {
  description = "ARN du stream Kinesis source"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Nom de la table DynamoDB"
  type        = string
  default     = ""
}

variable "sns_alerts_topic_arn" {
  description = "ARN du topic SNS pour les alertes"
  type        = string
  default     = ""
}

variable "lambda_memory_size" {
  description = "Taille de la mémoire pour la fonction Lambda (MB)"
  type        = number
  default     = 256
}

variable "lambda_timeout" {
  description = "Timeout de la fonction Lambda (secondes)"
  type        = number
  default     = 300
}

variable "lambda_reserved_concurrency" {
  description = "Concurrence réservée pour la fonction Lambda"
  type        = number
  default     = 10
}

variable "tags" {
  description = "Tags à appliquer aux ressources"
  type        = map(string)
  default     = {}
}

# Table DynamoDB pour le stockage rapide des données traitées
resource "aws_dynamodb_table" "processed_data" {
  name             = "${var.project_name}-${var.environment}-processed-data"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "symbol"
  range_key        = "timestamp"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  # Index global secondaire pour les requêtes par date
  global_secondary_index {
    name     = "TimestampIndex"
    hash_key = "timestamp"
    
    projection_type = "ALL"
  }

  # TTL pour auto-suppression des anciennes données
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-processed-data"
      Environment = var.environment
      Purpose     = "Processed Financial Data Storage"
    }
  )
}

# Package ZIP de la fonction Lambda
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_deployment.zip"
  
  source {
    content = templatefile("${path.module}/../../lambda-functions/kinesis-processor/lambda_function.py", {
      project_name = var.project_name
      environment  = var.environment
    })
    filename = "lambda_function.py"
  }
}

# Fonction Lambda principale
resource "aws_lambda_function" "kinesis_processor" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-kinesis-processor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = "python3.9"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size
  
  # Configuration de concurrence
  reserved_concurrent_executions = var.lambda_reserved_concurrency

  # Variables d'environnement
  environment {
    variables = {
      ENVIRONMENT       = var.environment
      PROJECT_NAME      = var.project_name
      S3_BUCKET        = var.s3_bucket_name
      DYNAMODB_TABLE   = aws_dynamodb_table.processed_data.name
      SNS_ALERTS_TOPIC = var.sns_alerts_topic_arn
    }
  }

  # Configuration de tracing
  tracing_config {
    mode = "Active"
  }

  # Configuration des logs
  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs,
    aws_cloudwatch_log_group.lambda_logs,
  ]

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-kinesis-processor"
      Environment = var.environment
      Purpose     = "Real-time Financial Data Processing"
    }
  )
}

# Trigger Kinesis pour la fonction Lambda
resource "aws_lambda_event_source_mapping" "kinesis_trigger" {
  event_source_arn  = var.kinesis_stream_arn
  function_name     = aws_lambda_function.kinesis_processor.arn
  starting_position = "LATEST"
  
  # Configuration du batch
  batch_size                         = 100
  maximum_batching_window_in_seconds = 5
  parallelization_factor            = 10
  
  # Gestion des erreurs
  maximum_record_age_in_seconds     = 604800  # 7 jours
  maximum_retry_attempts            = 3
  bisect_batch_on_function_error   = true
  
  # Configuration des destinations en cas d'erreur
  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.dlq.arn
    }
  }
}

# Dead Letter Queue pour les échecs de traitement
resource "aws_sqs_queue" "dlq" {
  name                       = "${var.project_name}-${var.environment}-lambda-dlq"
  message_retention_seconds  = 1209600  # 14 jours
  visibility_timeout_seconds = 300
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-lambda-dlq"
      Environment = var.environment
      Purpose     = "Lambda Dead Letter Queue"
    }
  )
}

# CloudWatch Log Group pour la fonction Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-kinesis-processor"
  retention_in_days = 14

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-lambda-logs"
      Environment = var.environment
    }
  )
}

# Rôle IAM pour la fonction Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-${var.environment}-lambda-processor-role"

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
      Name        = "${var.project_name}-${var.environment}-lambda-processor-role"
      Environment = var.environment
    }
  )
}

# Politique IAM pour les logs CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Politique IAM pour X-Ray tracing
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Politique IAM personnalisée pour accès aux services AWS
resource "aws_iam_role_policy" "lambda_custom_policy" {
  name = "${var.project_name}-${var.environment}-lambda-custom-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Accès Kinesis
      {
        Effect = "Allow"
        Action = [
          "kinesis:DescribeStream",
          "kinesis:GetShardIterator",
          "kinesis:GetRecords",
          "kinesis:ListShards"
        ]
        Resource = [var.kinesis_stream_arn]
      },
      # Accès S3
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      # Accès DynamoDB
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.processed_data.arn,
          "${aws_dynamodb_table.processed_data.arn}/*"
        ]
      },
      # Accès SNS pour les alertes
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.sns_alerts_topic_arn != "" ? [var.sns_alerts_topic_arn] : []
      },
      # Accès SQS pour la DLQ
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [aws_sqs_queue.dlq.arn]
      }
    ]
  })
}

# CloudWatch Alarms pour monitoring
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = var.sns_alerts_topic_arn != "" ? [var.sns_alerts_topic_arn] : []

  dimensions = {
    FunctionName = aws_lambda_function.kinesis_processor.function_name
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-lambda-errors-alarm"
      Environment = var.environment
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.project_name}-${var.environment}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "240000"  # 4 minutes (seuil d'alerte avant timeout)
  alarm_description   = "This metric monitors lambda duration"
  alarm_actions       = var.sns_alerts_topic_arn != "" ? [var.sns_alerts_topic_arn] : []

  dimensions = {
    FunctionName = aws_lambda_function.kinesis_processor.function_name
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-lambda-duration-alarm"
      Environment = var.environment
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.project_name}-${var.environment}-lambda-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors lambda throttles"
  alarm_actions       = var.sns_alerts_topic_arn != "" ? [var.sns_alerts_topic_arn] : []

  dimensions = {
    FunctionName = aws_lambda_function.kinesis_processor.function_name
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-lambda-throttles-alarm"
      Environment = var.environment
    }
  )
}

# Fonction Lambda pour traitement par batch (usage séparé)
resource "aws_lambda_function" "batch_processor" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-batch-processor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = "python3.9"
  timeout         = 900  # 15 minutes pour traitement batch
  memory_size     = 512  # Plus de mémoire pour les batches

  environment {
    variables = {
      ENVIRONMENT       = var.environment
      PROJECT_NAME      = var.project_name
      S3_BUCKET        = var.s3_bucket_name
      DYNAMODB_TABLE   = aws_dynamodb_table.processed_data.name
      SNS_ALERTS_TOPIC = var.sns_alerts_topic_arn
      PROCESSING_MODE  = "batch"
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-batch-processor"
      Environment = var.environment
      Purpose     = "Batch Financial Data Processing"
    }
  )
}

# EventBridge rule pour traitement batch programmé
resource "aws_cloudwatch_event_rule" "batch_schedule" {
  name                = "${var.project_name}-${var.environment}-batch-schedule"
  description         = "Trigger batch processing every hour"
  schedule_expression = "rate(1 hour)"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-batch-schedule"
      Environment = var.environment
    }
  )
}

resource "aws_cloudwatch_event_target" "batch_lambda_target" {
  rule      = aws_cloudwatch_event_rule.batch_schedule.name
  target_id = "BatchProcessorTarget"
  arn       = aws_lambda_function.batch_processor.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.batch_processor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.batch_schedule.arn
}

# ==============================================
# OUTPUTS
# ==============================================

output "lambda_function_name" {
  description = "Nom de la fonction Lambda de traitement"
  value       = aws_lambda_function.kinesis_processor.function_name
}

output "lambda_function_arn" {
  description = "ARN de la fonction Lambda de traitement"
  value       = aws_lambda_function.kinesis_processor.arn
}

output "batch_processor_name" {
  description = "Nom de la fonction Lambda de traitement batch"
  value       = aws_lambda_function.batch_processor.function_name
}

output "batch_processor_arn" {
  description = "ARN de la fonction Lambda de traitement batch"
  value       = aws_lambda_function.batch_processor.arn
}

output "dynamodb_table_name" {
  description = "Nom de la table DynamoDB"
  value       = aws_dynamodb_table.processed_data.name
}

output "dynamodb_table_arn" {
  description = "ARN de la table DynamoDB"
  value       = aws_dynamodb_table.processed_data.arn
}

output "dlq_url" {
  description = "URL de la Dead Letter Queue"
  value       = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  description = "ARN de la Dead Letter Queue"
  value       = aws_sqs_queue.dlq.arn
}

output "lambda_role_arn" {
  description = "ARN du rôle IAM Lambda"
  value       = aws_iam_role.lambda_role.arn
}

output "cloudwatch_log_group" {
  description = "Nom du groupe de logs CloudWatch"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}
