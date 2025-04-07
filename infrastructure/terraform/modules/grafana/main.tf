# Module Grafana pour visualisation des données financières temps réel
# ============================================================

variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
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

variable "tags" {
  description = "Tags à appliquer aux ressources"
  type        = map(string)
  default     = {}
}

# Application Load Balancer pour Grafana
resource "aws_lb" "grafana_alb" {
  name               = "${var.project_name}-${var.environment}-grafana-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.grafana_alb_sg.id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = false

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-alb"
      Environment = var.environment
      Purpose     = "Grafana Load Balancer"
    }
  )
}

# Target Group pour Grafana
resource "aws_lb_target_group" "grafana_tg" {
  name     = "${var.project_name}-${var.environment}-grafana-tg"
  port     = 3000
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200,302"
    path                = "/api/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-tg"
      Environment = var.environment
    }
  )
}

# Listener HTTPS pour ALB
resource "aws_lb_listener" "grafana_https" {
  count             = var.certificate_arn != "" ? 1 : 0
  load_balancer_arn = aws_lb.grafana_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana_tg.arn
  }
}

# Listener HTTP pour ALB (redirection vers HTTPS)
resource "aws_lb_listener" "grafana_http" {
  load_balancer_arn = aws_lb.grafana_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = var.certificate_arn != "" ? "redirect" : "forward"

    dynamic "redirect" {
      for_each = var.certificate_arn != "" ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }

    dynamic "forward" {
      for_each = var.certificate_arn == "" ? [1] : []
      content {
        target_group_arn = aws_lb_target_group.grafana_tg.arn
      }
    }
  }
}

# ECS Cluster pour Grafana
resource "aws_ecs_cluster" "grafana_cluster" {
  name = "${var.project_name}-${var.environment}-grafana-cluster"

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight           = 1
  }

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-cluster"
      Environment = var.environment
    }
  )
}

# Task Definition pour Grafana
resource "aws_ecs_task_definition" "grafana_task" {
  family                   = "${var.project_name}-${var.environment}-grafana"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = aws_iam_role.grafana_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "grafana"
      image = "grafana/grafana:10.2.0"
      
      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "GF_SECURITY_ADMIN_PASSWORD"
          value = var.grafana_admin_password
        },
        {
          name  = "GF_INSTALL_PLUGINS"
          value = "grafana-athena-datasource,grafana-s3-datasource,grafana-cloudwatch-datasource"
        },
        {
          name  = "GF_SERVER_ROOT_URL"
          value = var.domain_name != "" ? "https://${var.domain_name}" : "http://localhost:3000"
        },
        {
          name  = "GF_SECURITY_ALLOW_EMBEDDING"
          value = "true"
        },
        {
          name  = "GF_AUTH_ANONYMOUS_ENABLED"
          value = "false"
        },
        {
          name  = "GF_USERS_ALLOW_SIGN_UP"
          value = "false"
        },
        {
          name  = "GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH"
          value = "/etc/grafana/provisioning/dashboards/financial-overview.json"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "grafana-storage"
          containerPath = "/var/lib/grafana"
        },
        {
          sourceVolume  = "grafana-config"
          containerPath = "/etc/grafana/provisioning"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.grafana_logs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "grafana"
        }
      }

      healthCheck = {
        command = [
          "CMD-SHELL",
          "curl -f http://localhost:3000/api/health || exit 1"
        ]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  volume {
    name = "grafana-storage"
    
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.grafana_storage.id
      root_directory = "/"
      
      authorization_config {
        access_point_id = aws_efs_access_point.grafana_access_point.id
      }
      
      transit_encryption = "ENABLED"
    }
  }

  volume {
    name = "grafana-config"
    
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.grafana_config.id
      root_directory = "/"
      
      authorization_config {
        access_point_id = aws_efs_access_point.grafana_config_access_point.id
      }
      
      transit_encryption = "ENABLED"
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-task"
      Environment = var.environment
    }
  )
}

# ECS Service pour Grafana
resource "aws_ecs_service" "grafana_service" {
  name            = "${var.project_name}-${var.environment}-grafana-service"
  cluster         = aws_ecs_cluster.grafana_cluster.id
  task_definition = aws_ecs_task_definition.grafana_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.grafana_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.grafana_tg.arn
    container_name   = "grafana"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.grafana_http]

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 50
  }

  enable_execute_command = true

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-service"
      Environment = var.environment
    }
  )
}

# EFS pour stockage persistant Grafana
resource "aws_efs_file_system" "grafana_storage" {
  creation_token = "${var.project_name}-${var.environment}-grafana-storage"
  encrypted      = true

  performance_mode = "generalPurpose"
  throughput_mode  = "provisioned"
  provisioned_throughput_in_mibps = 10

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-storage"
      Environment = var.environment
      Purpose     = "Grafana Data Storage"
    }
  )
}

resource "aws_efs_file_system" "grafana_config" {
  creation_token = "${var.project_name}-${var.environment}-grafana-config"
  encrypted      = true

  performance_mode = "generalPurpose"
  throughput_mode  = "provisioned"
  provisioned_throughput_in_mibps = 5

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-config"
      Environment = var.environment
      Purpose     = "Grafana Configuration"
    }
  )
}

# EFS Mount Targets
resource "aws_efs_mount_target" "grafana_storage_mount" {
  count           = length(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.grafana_storage.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [aws_security_group.efs_sg.id]
}

resource "aws_efs_mount_target" "grafana_config_mount" {
  count           = length(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.grafana_config.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [aws_security_group.efs_sg.id]
}

# EFS Access Points
resource "aws_efs_access_point" "grafana_access_point" {
  file_system_id = aws_efs_file_system.grafana_storage.id

  posix_user {
    gid = 472  # Grafana GID
    uid = 472  # Grafana UID
  }

  root_directory {
    path = "/grafana"
    creation_info {
      owner_gid   = 472
      owner_uid   = 472
      permissions = "755"
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-access-point"
      Environment = var.environment
    }
  )
}

resource "aws_efs_access_point" "grafana_config_access_point" {
  file_system_id = aws_efs_file_system.grafana_config.id

  posix_user {
    gid = 472
    uid = 472
  }

  root_directory {
    path = "/config"
    creation_info {
      owner_gid   = 472
      owner_uid   = 472
      permissions = "755"
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-config-access-point"
      Environment = var.environment
    }
  )
}

# Security Groups
resource "aws_security_group" "grafana_alb_sg" {
  name_prefix = "${var.project_name}-${var.environment}-grafana-alb-"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-alb-sg"
      Environment = var.environment
    }
  )
}

resource "aws_security_group" "grafana_sg" {
  name_prefix = "${var.project_name}-${var.environment}-grafana-"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Grafana from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.grafana_alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-sg"
      Environment = var.environment
    }
  )
}

resource "aws_security_group" "efs_sg" {
  name_prefix = "${var.project_name}-${var.environment}-efs-"
  vpc_id      = var.vpc_id

  ingress {
    description     = "NFS from Grafana"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.grafana_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-efs-sg"
      Environment = var.environment
    }
  )
}

# CloudWatch Log Group pour Grafana
resource "aws_cloudwatch_log_group" "grafana_logs" {
  name              = "/aws/ecs/${var.project_name}-${var.environment}-grafana"
  retention_in_days = 14

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-logs"
      Environment = var.environment
    }
  )
}

# IAM Roles
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.project_name}-${var.environment}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-ecs-execution-role"
      Environment = var.environment
    }
  )
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "grafana_task_role" {
  name = "${var.project_name}-${var.environment}-grafana-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-grafana-task-role"
      Environment = var.environment
    }
  )
}

# Politique IAM pour accès aux données
resource "aws_iam_role_policy" "grafana_data_access" {
  name = "${var.project_name}-${var.environment}-grafana-data-access"
  role = aws_iam_role.grafana_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Accès S3 pour les données
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      # Accès CloudWatch pour les métriques
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:GetMetricData",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      },
      # Accès Athena pour les requêtes
      {
        Effect = "Allow"
        Action = [
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StartQueryExecution",
          "athena:StopQueryExecution",
          "athena:GetWorkGroup"
        ]
        Resource = "*"
      },
      # Accès Glue pour le catalog
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartitions"
        ]
        Resource = "*"
      }
    ]
  })
}

# Route 53 Record (optionnel)
resource "aws_route53_record" "grafana_dns" {
  count   = var.domain_name != "" ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.grafana_alb.dns_name
    zone_id                = aws_lb.grafana_alb.zone_id
    evaluate_target_health = true
  }
}

# Auto Scaling pour ECS
resource "aws_appautoscaling_target" "grafana_scale_target" {
  max_capacity       = 3
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.grafana_cluster.name}/${aws_ecs_service.grafana_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "grafana_scale_up" {
  name               = "${var.project_name}-${var.environment}-grafana-scale-up"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.grafana_scale_target.resource_id
  scalable_dimension = aws_appautoscaling_target.grafana_scale_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.grafana_scale_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# Data sources
data "aws_region" "current" {}

data "aws_route53_zone" "main" {
  count = var.domain_name != "" ? 1 : 0
  name  = split(".", var.domain_name)[1]  # Assume domain format: grafana.example.com
}

# ==============================================
# OUTPUTS
# ==============================================

output "grafana_url" {
  description = "URL d'accès à Grafana"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.grafana_alb.dns_name}"
}

output "grafana_alb_dns" {
  description = "DNS de l'Application Load Balancer"
  value       = aws_lb.grafana_alb.dns_name
}

output "grafana_alb_zone_id" {
  description = "Zone ID de l'Application Load Balancer"
  value       = aws_lb.grafana_alb.zone_id
}

output "ecs_cluster_name" {
  description = "Nom du cluster ECS"
  value       = aws_ecs_cluster.grafana_cluster.name
}

output "ecs_service_name" {
  description = "Nom du service ECS"
  value       = aws_ecs_service.grafana_service.name
}

output "grafana_admin_password" {
  description = "Mot de passe admin Grafana"
  value       = var.grafana_admin_password
  sensitive   = true
}

output "efs_storage_id" {
  description = "ID du système de fichiers EFS pour le stockage"
  value       = aws_efs_file_system.grafana_storage.id
}

output "efs_config_id" {
  description = "ID du système de fichiers EFS pour la configuration"
  value       = aws_efs_file_system.grafana_config.id
}

output "security_group_id" {
  description = "ID du groupe de sécurité Grafana"
  value       = aws_security_group.grafana_sg.id
}
