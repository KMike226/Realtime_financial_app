# Module ECS pour orchestration de conteneurs
# ===========================================
# Ce module configure un cluster ECS pour exécuter des applications conteneurisées
# comme Spark et d'autres services de traitement de données.

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Variables d'entrée
variable "cluster_name" {
  description = "Nom du cluster ECS"
  type        = string
  default     = "financial-app-cluster"
}

variable "environment" {
  description = "Environnement de déploiement"
  type        = string
  default     = "dev"
}

variable "vpc_id" {
  description = "ID du VPC où déployer le cluster"
  type        = string
}

variable "subnet_ids" {
  description = "IDs des sous-réseaux pour le cluster"
  type        = list(string)
}

variable "instance_type" {
  description = "Type d'instance EC2 pour les tâches"
  type        = string
  default     = "t3.medium"
}

variable "min_capacity" {
  description = "Capacité minimale du cluster"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Capacité maximale du cluster"
  type        = number
  default     = 10
}

variable "desired_capacity" {
  description = "Capacité désirée du cluster"
  type        = number
  default     = 2
}

# Rôle IAM pour le cluster ECS
resource "aws_iam_role" "ecs_cluster_role" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.cluster_name}-cluster-role"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Attachement de la politique ECS
resource "aws_iam_role_policy_attachment" "ecs_cluster_policy" {
  role       = aws_iam_role.ecs_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSClusterRole"
}

# Rôle IAM pour les tâches ECS
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.cluster_name}-task-role"

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

  tags = {
    Name        = "${var.cluster_name}-task-role"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Politique personnalisée pour les tâches ECS
resource "aws_iam_policy" "ecs_task_policy" {
  name        = "${var.cluster_name}-task-policy"
  description = "Politique pour les tâches ECS du projet financier"

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
          "arn:aws:s3:::financial-data-lake/*",
          "arn:aws:s3:::financial-data-lake"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:ListShards"
        ]
        Resource = "arn:aws:kinesis:*:*:stream/financial-data-stream"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "${var.cluster_name}-task-policy"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Attachement de la politique aux tâches
resource "aws_iam_role_policy_attachment" "ecs_task_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}

# Attachement de la politique ECS Task Execution
resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Cluster ECS
resource "aws_ecs_cluster" "main" {
  name = var.cluster_name

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs_cluster.name
      }
    }
  }

  tags = {
    Name        = var.cluster_name
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Groupe de logs CloudWatch pour le cluster
resource "aws_cloudwatch_log_group" "ecs_cluster" {
  name              = "/ecs/${var.cluster_name}"
  retention_in_days = 7

  tags = {
    Name        = "${var.cluster_name}-logs"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Groupe de logs pour les tâches
resource "aws_cloudwatch_log_group" "ecs_tasks" {
  name              = "/ecs/${var.cluster_name}/tasks"
  retention_in_days = 7

  tags = {
    Name        = "${var.cluster_name}-task-logs"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Groupe de capacité ECS (pour EC2)
resource "aws_ecs_capacity_provider" "main" {
  name = "${var.cluster_name}-capacity-provider"

  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.ecs.arn
    managed_termination_protection = "ENABLED"

    managed_scaling {
      maximum_scaling_step_size = 2
      minimum_scaling_step_size = 1
      status                    = "ENABLED"
      target_capacity           = 100
    }
  }

  tags = {
    Name        = "${var.cluster_name}-capacity-provider"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Association du groupe de capacité au cluster
resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = [aws_ecs_capacity_provider.main.name]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = aws_ecs_capacity_provider.main.name
  }
}

# Rôle IAM pour l'auto-scaling group
resource "aws_iam_role" "ecs_autoscaling_role" {
  name = "${var.cluster_name}-autoscaling-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "application-autoscaling.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.cluster_name}-autoscaling-role"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Attachement de la politique d'auto-scaling
resource "aws_iam_role_policy_attachment" "ecs_autoscaling_policy" {
  role       = aws_iam_role.ecs_autoscaling_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceAutoscaleRole"
}

# Rôle IAM pour les instances EC2
resource "aws_iam_role" "ecs_instance_role" {
  name = "${var.cluster_name}-instance-role"

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
    Name        = "${var.cluster_name}-instance-role"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Attachement des politiques pour les instances EC2
resource "aws_iam_role_policy_attachment" "ecs_instance_policy" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

# Instance profile pour les instances EC2
resource "aws_iam_instance_profile" "ecs_instance_profile" {
  name = "${var.cluster_name}-instance-profile"
  role = aws_iam_role.ecs_instance_role.name

  tags = {
    Name        = "${var.cluster_name}-instance-profile"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Launch template pour les instances EC2
resource "aws_launch_template" "ecs" {
  name_prefix   = "${var.cluster_name}-"
  image_id      = data.aws_ami.ecs_optimized.id
  instance_type = var.instance_type

  vpc_security_group_ids = [aws_security_group.ecs.id]

  iam_instance_profile {
    name = aws_iam_instance_profile.ecs_instance_profile.name
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    cluster_name = var.cluster_name
  }))

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "${var.cluster_name}-instance"
      Environment = var.environment
      Project     = "financial-app"
    }
  }

  tags = {
    Name        = "${var.cluster_name}-launch-template"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# AMI optimisée pour ECS
data "aws_ami" "ecs_optimized" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-ecs-hvm-*-x86_64-ebs"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Groupe de sécurité pour ECS
resource "aws_security_group" "ecs" {
  name        = "${var.cluster_name}-sg"
  description = "Groupe de sécurité pour le cluster ECS"
  vpc_id      = var.vpc_id

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Ports pour Spark (8080-8089)
  ingress {
    from_port   = 8080
    to_port     = 8089
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  # Tous les trafics sortants
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.cluster_name}-sg"
    Environment = var.environment
    Project     = "financial-app"
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "ecs" {
  name                = "${var.cluster_name}-asg"
  vpc_zone_identifier = var.subnet_ids
  target_group_arns   = []
  health_check_type   = "EC2"
  health_check_grace_period = 300

  min_size         = var.min_capacity
  max_size         = var.max_capacity
  desired_capacity = var.desired_capacity

  launch_template {
    id      = aws_launch_template.ecs.id
    version = "$Latest"
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = true
    propagate_at_launch = true
  }

  tag {
    key                 = "Name"
    value               = "${var.cluster_name}-asg"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  tag {
    key                 = "Project"
    value               = "financial-app"
    propagate_at_launch = true
  }
}

# Variables de sortie
output "cluster_id" {
  description = "ID du cluster ECS"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "Nom du cluster ECS"
  value       = aws_ecs_cluster.main.name
}

output "cluster_arn" {
  description = "ARN du cluster ECS"
  value       = aws_ecs_cluster.main.arn
}

output "task_role_arn" {
  description = "ARN du rôle des tâches ECS"
  value       = aws_iam_role.ecs_task_role.arn
}

output "task_execution_role_arn" {
  description = "ARN du rôle d'exécution des tâches ECS"
  value       = aws_iam_role.ecs_task_role.arn
}

output "security_group_id" {
  description = "ID du groupe de sécurité ECS"
  value       = aws_security_group.ecs.id
}

output "log_group_name" {
  description = "Nom du groupe de logs CloudWatch"
  value       = aws_cloudwatch_log_group.ecs_tasks.name
}
