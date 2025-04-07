# Outputs pour le module Grafana
# ===============================

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

output "grafana_alb_arn" {
  description = "ARN de l'Application Load Balancer"
  value       = aws_lb.grafana_alb.arn
}

output "target_group_arn" {
  description = "ARN du Target Group"
  value       = aws_lb_target_group.grafana_tg.arn
}

output "ecs_cluster_name" {
  description = "Nom du cluster ECS"
  value       = aws_ecs_cluster.grafana_cluster.name
}

output "ecs_cluster_arn" {
  description = "ARN du cluster ECS"
  value       = aws_ecs_cluster.grafana_cluster.arn
}

output "ecs_service_name" {
  description = "Nom du service ECS"
  value       = aws_ecs_service.grafana_service.name
}

output "ecs_service_arn" {
  description = "ARN du service ECS"
  value       = aws_ecs_service.grafana_service.id
}

output "task_definition_arn" {
  description = "ARN de la définition de tâche ECS"
  value       = aws_ecs_task_definition.grafana_task.arn
}

output "grafana_admin_password" {
  description = "Mot de passe admin Grafana"
  value       = var.grafana_admin_password
  sensitive   = true
}

# EFS Outputs
output "efs_storage_id" {
  description = "ID du système de fichiers EFS pour le stockage"
  value       = aws_efs_file_system.grafana_storage.id
}

output "efs_storage_dns" {
  description = "DNS du système de fichiers EFS pour le stockage"
  value       = aws_efs_file_system.grafana_storage.dns_name
}

output "efs_config_id" {
  description = "ID du système de fichiers EFS pour la configuration"
  value       = aws_efs_file_system.grafana_config.id
}

output "efs_config_dns" {
  description = "DNS du système de fichiers EFS pour la configuration"
  value       = aws_efs_file_system.grafana_config.dns_name
}

output "efs_access_point_storage_id" {
  description = "ID de l'access point EFS pour le stockage"
  value       = aws_efs_access_point.grafana_access_point.id
}

output "efs_access_point_config_id" {
  description = "ID de l'access point EFS pour la configuration"
  value       = aws_efs_access_point.grafana_config_access_point.id
}

# Security Groups
output "security_group_id" {
  description = "ID du groupe de sécurité Grafana"
  value       = aws_security_group.grafana_sg.id
}

output "alb_security_group_id" {
  description = "ID du groupe de sécurité ALB"
  value       = aws_security_group.grafana_alb_sg.id
}

output "efs_security_group_id" {
  description = "ID du groupe de sécurité EFS"
  value       = aws_security_group.efs_sg.id
}

# IAM Roles
output "ecs_execution_role_arn" {
  description = "ARN du rôle d'exécution ECS"
  value       = aws_iam_role.ecs_execution_role.arn
}

output "grafana_task_role_arn" {
  description = "ARN du rôle de tâche Grafana"
  value       = aws_iam_role.grafana_task_role.arn
}

# CloudWatch
output "cloudwatch_log_group_name" {
  description = "Nom du groupe de logs CloudWatch"
  value       = aws_cloudwatch_log_group.grafana_logs.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN du groupe de logs CloudWatch"
  value       = aws_cloudwatch_log_group.grafana_logs.arn
}

# Auto Scaling
output "autoscaling_target_resource_id" {
  description = "Resource ID de l'auto scaling target"
  value       = var.enable_auto_scaling ? aws_appautoscaling_target.grafana_scale_target[0].resource_id : null
}

output "autoscaling_policy_arn" {
  description = "ARN de la politique d'auto scaling"
  value       = var.enable_auto_scaling ? aws_appautoscaling_policy.grafana_scale_up[0].arn : null
}

# Métriques et monitoring
output "monitoring_endpoints" {
  description = "Endpoints de monitoring"
  value = {
    grafana_health = "${var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.grafana_alb.dns_name}"}/api/health"
    grafana_metrics = "${var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.grafana_alb.dns_name}"}/metrics"
    alb_target_health = "AWS Console -> EC2 -> Target Groups -> ${aws_lb_target_group.grafana_tg.name}"
  }
}

# Configuration pour intégration avec d'autres modules
output "data_source_configs" {
  description = "Configurations des sources de données pour autres modules"
  value = {
    s3_bucket = var.s3_bucket_name
    athena_workgroup = var.athena_workgroup
    glue_database = var.glue_database_name
    cloudwatch_region = data.aws_region.current.name
  }
}

# Informations de connexion
output "connection_info" {
  description = "Informations de connexion Grafana"
  value = {
    url = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.grafana_alb.dns_name}"
    username = "admin"
    password_secret = "Stored in variable: grafana_admin_password"
    default_org = "Main Org."
  }
  sensitive = false
}

# Status et health checks
output "health_check_urls" {
  description = "URLs pour vérifier l'état de santé"
  value = {
    grafana_api_health = "${var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.grafana_alb.dns_name}"}/api/health"
    alb_health_check = aws_lb_target_group.grafana_tg.health_check[0].path
    ecs_service_status = "AWS Console -> ECS -> Clusters -> ${aws_ecs_cluster.grafana_cluster.name} -> Services"
  }
}

# Ressources pour backup et maintenance
output "backup_resources" {
  description = "Ressources pour backup et maintenance"
  value = {
    efs_storage_id = aws_efs_file_system.grafana_storage.id
    efs_config_id = aws_efs_file_system.grafana_config.id
    task_definition_family = aws_ecs_task_definition.grafana_task.family
    log_group_name = aws_cloudwatch_log_group.grafana_logs.name
  }
}
