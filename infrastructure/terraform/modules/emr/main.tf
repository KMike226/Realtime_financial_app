# Module EMR pour le pipeline financier en temps réel
# Configuration du cluster EMR avec Spark pour le traitement des données

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}


# Rôle de service EMR
resource "aws_iam_role" "emr_service_role" {
  name = "${var.project_name}-${var.environment}-emr-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "elasticmapreduce.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-emr-service-role"
    Environment = var.environment
  }
}

# Attachement de la politique de service EMR
resource "aws_iam_role_policy_attachment" "emr_service_role_policy" {
  role       = aws_iam_role.emr_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
}

# Rôle d'instance EMR
resource "aws_iam_role" "emr_instance_role" {
  name = "${var.project_name}-${var.environment}-emr-instance-role"

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
    Name        = "${var.project_name}-${var.environment}-emr-instance-role"
    Environment = var.environment
  }
}

# Attachement de la politique d'instance EMR
resource "aws_iam_role_policy_attachment" "emr_instance_role_policy" {
  role       = aws_iam_role.emr_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
}

# Politique personnalisée pour accès S3 et Kinesis
resource "aws_iam_role_policy" "emr_instance_custom_policy" {
  name = "${var.project_name}-${var.environment}-emr-instance-custom-policy"
  role = aws_iam_role.emr_instance_role.id

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
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
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
        Resource = "*"
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

# Profil d'instance EMR
resource "aws_iam_instance_profile" "emr_instance_profile" {
  name = "${var.project_name}-${var.environment}-emr-instance-profile"
  role = aws_iam_role.emr_instance_role.name
}

# Security Group pour EMR
resource "aws_security_group" "emr_cluster" {
  name_prefix = "${var.project_name}-${var.environment}-emr-cluster"
  vpc_id      = var.vpc_id

  # Règles d'entrée pour communication interne EMR
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  # Règles de sortie pour accès internet
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-emr-cluster"
    Environment = var.environment
  }
}

# Security Group pour EMR Master
resource "aws_security_group" "emr_master" {
  name_prefix = "${var.project_name}-${var.environment}-emr-master"
  vpc_id      = var.vpc_id

  # SSH access (optionnel)
  dynamic "ingress" {
    for_each = var.key_name != null ? [1] : []
    content {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["10.0.0.0/16"]
    }
  }

  # Web interfaces (Hadoop, Spark)
  ingress {
    from_port   = 8088
    to_port     = 8088
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    from_port   = 4040
    to_port     = 4040
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-emr-master"
    Environment = var.environment
  }
}

# Configuration du cluster EMR
resource "aws_emr_cluster" "financial_data_cluster" {
  name          = "${var.project_name}-${var.environment}-cluster"
  release_label = "emr-6.15.0"
  applications  = ["Spark", "Hadoop", "Hive", "Zeppelin"]

  # Configuration des logs
  log_uri = "s3://${var.s3_bucket_name}/emr-logs/"

  # Rôles IAM
  service_role     = aws_iam_role.emr_service_role.arn
  autoscaling_role = aws_iam_role.emr_autoscaling_role.arn

  # Configuration réseau
  ec2_attributes {
    subnet_id                         = var.private_subnet_ids[0]
    emr_managed_master_security_group = aws_security_group.emr_master.id
    emr_managed_slave_security_group  = aws_security_group.emr_cluster.id
    instance_profile                  = aws_iam_instance_profile.emr_instance_profile.arn
    key_name                          = var.key_name
  }

  # Configuration du master node
  master_instance_group {
    instance_type = var.master_instance_type
  }

  # Configuration des core nodes avec auto-scaling
  core_instance_group {
    instance_type  = var.core_instance_type
    instance_count = var.core_instance_count

    ebs_config {
      size                 = 40
      type                 = "gp3"
      volumes_per_instance = 1
    }

    autoscaling_policy = jsonencode({
      Constraints = {
        MinCapacity = var.auto_scaling_min_capacity
        MaxCapacity = var.auto_scaling_max_capacity
      }
      Rules = [
        {
          Name        = "ScaleOutMemoryPercentage"
          Description = "Scale out if memory utilization > 75%"
          Action = {
            Market = "ON_DEMAND"
            SimpleScalingPolicyConfiguration = {
              AdjustmentType    = "CHANGE_IN_CAPACITY"
              ScalingAdjustment = 1
              CoolDown          = 300
            }
          }
          Trigger = {
            CloudWatchAlarmDefinition = {
              ComparisonOperator = "GREATER_THAN"
              EvaluationPeriods  = 1
              MetricName         = "MemoryPercentage"
              Namespace          = "AWS/ElasticMapReduce"
              Period             = 300
              Statistic          = "AVERAGE"
              Threshold          = 75.0
              Unit               = "PERCENT"
              Dimensions = [
                {
                  Key   = "JobFlowId"
                  Value = "$${emr.clusterId}"
                }
              ]
            }
          }
        },
        {
          Name        = "ScaleInMemoryPercentage"
          Description = "Scale in if memory utilization < 25%"
          Action = {
            SimpleScalingPolicyConfiguration = {
              AdjustmentType    = "CHANGE_IN_CAPACITY"
              ScalingAdjustment = -1
              CoolDown          = 300
            }
          }
          Trigger = {
            CloudWatchAlarmDefinition = {
              ComparisonOperator = "LESS_THAN"
              EvaluationPeriods  = 1
              MetricName         = "MemoryPercentage"
              Namespace          = "AWS/ElasticMapReduce"
              Period             = 300
              Statistic          = "AVERAGE"
              Threshold          = 25.0
              Unit               = "PERCENT"
              Dimensions = [
                {
                  Key   = "JobFlowId"
                  Value = "$${emr.clusterId}"
                }
              ]
            }
          }
        }
      ]
    })
  }

  # Configuration Spark
  configurations_json = jsonencode([
    {
      Classification = "spark-env"
      Properties     = {}
      Configurations = [
        {
          Classification = "export"
          Properties = {
            PYSPARK_PYTHON = "/usr/bin/python3"
          }
        }
      ]
    },
    {
      Classification = "spark-defaults"
      Properties = {
        "spark.dynamicAllocation.enabled"               = "true"
        "spark.dynamicAllocation.minExecutors"          = "1"
        "spark.dynamicAllocation.maxExecutors"          = "8"
        "spark.sql.adaptive.enabled"                    = "true"
        "spark.sql.adaptive.coalescePartitions.enabled" = "true"
        "spark.serializer"                              = "org.apache.spark.serializer.KryoSerializer"
        "spark.sql.execution.arrow.pyspark.enabled"     = "true"
        "spark.hadoop.fs.s3a.impl"                      = "org.apache.hadoop.fs.s3a.S3AFileSystem"
        "spark.hadoop.fs.s3a.aws.credentials.provider"  = "com.amazonaws.auth.InstanceProfileCredentialsProvider"
      }
    },
    {
      Classification = "yarn-site"
      Properties = {
        "yarn.resourcemanager.am.max-attempts" = "1"
        "yarn.nodemanager.vmem-check-enabled"  = "false"
        "yarn.nodemanager.pmem-check-enabled"  = "false"
      }
    }
  ])

  # Steps de bootstrap pour installer des packages supplémentaires
  bootstrap_action {
    path = "s3://${var.s3_bucket_name}/emr-bootstrap/install-python-packages.sh"
    name = "Install Python packages"
  }

  # Optimisations de coût
  auto_termination_policy {
    idle_timeout = 3600 # Arrêt automatique après 1 heure d'inactivité
  }

  # Activer la terminaison protégée en production
  termination_protection            = var.environment == "prod" ? true : false
  keep_job_flow_alive_when_no_steps = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-cluster"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "financial-data-processing"
  }
}

# Rôle d'auto-scaling EMR
resource "aws_iam_role" "emr_autoscaling_role" {
  name = "${var.project_name}-${var.environment}-emr-autoscaling-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "application-autoscaling.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "elasticmapreduce.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-emr-autoscaling-role"
    Environment = var.environment
  }
}

# Politique d'auto-scaling EMR
resource "aws_iam_role_policy_attachment" "emr_autoscaling_role_policy" {
  role       = aws_iam_role.emr_autoscaling_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforAutoScalingRole"
}

# Script de bootstrap pour installer les packages Python
resource "aws_s3_object" "bootstrap_script" {
  bucket  = var.s3_bucket_name
  key     = "emr-bootstrap/install-python-packages.sh"
  content = <<-EOF
#!/bin/bash
# Script de bootstrap pour installer les packages Python requis

# Mise à jour du système
sudo yum update -y

# Installation des packages Python pour le traitement financier
sudo pip3 install \
  pandas \
  numpy \
  boto3 \
  pyspark \
  requests \
  yfinance \
  alpha_vantage \
  plotly \
  seaborn \
  scikit-learn

# Configuration des variables d'environnement
echo "export PYTHONPATH=/usr/lib/spark/python/lib/pyspark.zip:/usr/lib/spark/python/lib/py4j-*.zip" >> ~/.bashrc
echo "export SPARK_HOME=/usr/lib/spark" >> ~/.bashrc

# Redémarrer les services Spark pour appliquer les configurations
sudo systemctl restart spark-history-server
EOF

  tags = {
    Name        = "${var.project_name}-${var.environment}-emr-bootstrap"
    Environment = var.environment
  }
}

# CloudWatch Alarmes pour monitoring
resource "aws_cloudwatch_metric_alarm" "emr_cluster_cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-emr-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElasticMapReduce"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors EMR cluster CPU utilization"
  alarm_actions       = []

  dimensions = {
    JobFlowId = aws_emr_cluster.financial_data_cluster.id
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-emr-cpu-alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "emr_cluster_memory_high" {
  alarm_name          = "${var.project_name}-${var.environment}-emr-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryPercentage"
  namespace           = "AWS/ElasticMapReduce"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors EMR cluster memory utilization"
  alarm_actions       = []

  dimensions = {
    JobFlowId = aws_emr_cluster.financial_data_cluster.id
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-emr-memory-alarm"
    Environment = var.environment
  }
}
