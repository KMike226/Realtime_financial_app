# Module Security Groups pour le pipeline financier
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

variable "vpc_cidr" {
  description = "CIDR block du VPC"
  type        = string
}

# Security Group pour Lambda Functions
resource "aws_security_group" "lambda_sg" {
  name_prefix = "${var.project_name}-${var.environment}-lambda-"
  vpc_id      = var.vpc_id
  description = "Security group pour les Lambda functions"

  # Règles sortantes - HTTPS pour API calls
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS sortant pour appels API externes"
  }

  # HTTP pour API calls (si nécessaire)
  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP sortant pour appels API"
  }

  # Communication interne VPC
  egress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Communication interne VPC"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-lambda-sg"
    Environment = var.environment
  }
}

# Security Group pour EC2 Instances (Spark)
resource "aws_security_group" "ec2_spark_sg" {
  name_prefix = "${var.project_name}-${var.environment}-spark-"
  vpc_id      = var.vpc_id
  description = "Security group pour les instances EC2 Spark"

  # SSH access (seulement depuis VPC)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "SSH depuis VPC"
  }

  # Spark UI
  ingress {
    from_port   = 4040
    to_port     = 4050
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Spark UI"
  }

  # Communication Spark cluster
  ingress {
    from_port = 7000
    to_port   = 7999
    protocol  = "tcp"
    self      = true
    description = "Communication Spark cluster"
  }

  # Tous les ports sortants
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Tout le trafic sortant"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-spark-sg"
    Environment = var.environment
  }
}

# Security Group pour Load Balancer (si utilisé)
resource "aws_security_group" "alb_sg" {
  name_prefix = "${var.project_name}-${var.environment}-alb-"
  vpc_id      = var.vpc_id
  description = "Security group pour Application Load Balancer"

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS depuis Internet"
  }

  # HTTP (redirection vers HTTPS)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP depuis Internet"
  }

  # Tout le trafic sortant
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Tout le trafic sortant"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-alb-sg"
    Environment = var.environment
  }
}

# Security Group pour RDS (si utilisé pour métadonnées)
resource "aws_security_group" "rds_sg" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  vpc_id      = var.vpc_id
  description = "Security group pour base de données RDS"

  # PostgreSQL/MySQL depuis les resources internes
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id, aws_security_group.ec2_spark_sg.id]
    description     = "PostgreSQL depuis Lambda et Spark"
  }

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id, aws_security_group.ec2_spark_sg.id]
    description     = "MySQL depuis Lambda et Spark"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-sg"
    Environment = var.environment
  }
}

# Security Group pour ElastiCache (Redis/Memcached)
resource "aws_security_group" "elasticache_sg" {
  name_prefix = "${var.project_name}-${var.environment}-cache-"
  vpc_id      = var.vpc_id
  description = "Security group pour ElastiCache"

  # Redis
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id, aws_security_group.ec2_spark_sg.id]
    description     = "Redis depuis Lambda et Spark"
  }

  # Memcached
  ingress {
    from_port       = 11211
    to_port         = 11211
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id, aws_security_group.ec2_spark_sg.id]
    description     = "Memcached depuis Lambda et Spark"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-cache-sg"
    Environment = var.environment
  }
}

# Outputs
output "lambda_security_group_id" {
  description = "ID du security group Lambda"
  value       = aws_security_group.lambda_sg.id
}

output "ec2_spark_security_group_id" {
  description = "ID du security group EC2 Spark"
  value       = aws_security_group.ec2_spark_sg.id
}

output "alb_security_group_id" {
  description = "ID du security group ALB"
  value       = aws_security_group.alb_sg.id
}

output "rds_security_group_id" {
  description = "ID du security group RDS"
  value       = aws_security_group.rds_sg.id
}

output "elasticache_security_group_id" {
  description = "ID du security group ElastiCache"
  value       = aws_security_group.elasticache_sg.id
}
