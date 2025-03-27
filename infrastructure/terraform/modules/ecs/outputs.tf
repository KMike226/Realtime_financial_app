# Variables de sortie pour le module ECS
# ======================================
# Définition des outputs du module ECS

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
  description = "Nom du groupe de logs CloudWatch pour les tâches"
  value       = aws_cloudwatch_log_group.ecs_tasks.name
}

output "log_group_arn" {
  description = "ARN du groupe de logs CloudWatch pour les tâches"
  value       = aws_cloudwatch_log_group.ecs_tasks.arn
}

output "cluster_log_group_name" {
  description = "Nom du groupe de logs CloudWatch pour le cluster"
  value       = aws_cloudwatch_log_group.ecs_cluster.name
}

output "capacity_provider_name" {
  description = "Nom du fournisseur de capacité ECS"
  value       = aws_ecs_capacity_provider.main.name
}

output "autoscaling_group_name" {
  description = "Nom du groupe d'auto-scaling"
  value       = aws_autoscaling_group.ecs.name
}

output "launch_template_id" {
  description = "ID du template de lancement"
  value       = aws_launch_template.ecs.id
}

output "launch_template_latest_version" {
  description = "Version la plus récente du template de lancement"
  value       = aws_launch_template.ecs.latest_version
}

output "instance_profile_name" {
  description = "Nom du profil d'instance IAM"
  value       = aws_iam_instance_profile.ecs_instance_profile.name
}

output "task_policy_arn" {
  description = "ARN de la politique personnalisée des tâches"
  value       = aws_iam_policy.ecs_task_policy.arn
}
