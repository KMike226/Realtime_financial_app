# Variables de sortie pour le module EKS
# ======================================
# Définition des outputs du module EKS

output "cluster_id" {
  description = "ID du cluster EKS"
  value       = aws_eks_cluster.main.id
}

output "cluster_name" {
  description = "Nom du cluster EKS"
  value       = aws_eks_cluster.main.name
}

output "cluster_arn" {
  description = "ARN du cluster EKS"
  value       = aws_eks_cluster.main.arn
}

output "cluster_endpoint" {
  description = "Endpoint du cluster EKS"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_certificate_authority_data" {
  description = "Données du certificat d'autorité du cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
}

output "cluster_security_group_id" {
  description = "ID du groupe de sécurité du cluster EKS"
  value       = aws_security_group.eks_cluster.id
}

output "node_security_group_id" {
  description = "ID du groupe de sécurité des nœuds EKS"
  value       = aws_security_group.eks_nodes.id
}

output "node_group_arn" {
  description = "ARN du groupe de nœuds EKS"
  value       = aws_eks_node_group.main.arn
}

output "node_group_name" {
  description = "Nom du groupe de nœuds EKS"
  value       = aws_eks_node_group.main.node_group_name
}

output "node_role_arn" {
  description = "ARN du rôle des nœuds EKS"
  value       = aws_iam_role.eks_node_role.arn
}

output "cluster_role_arn" {
  description = "ARN du rôle du cluster EKS"
  value       = aws_iam_role.eks_cluster_role.arn
}

output "oidc_provider_arn" {
  description = "ARN du fournisseur OIDC pour IRSA"
  value       = var.enable_irsa ? aws_iam_openid_connect_provider.eks[0].arn : null
}

output "oidc_provider_url" {
  description = "URL du fournisseur OIDC"
  value       = var.enable_irsa ? aws_iam_openid_connect_provider.eks[0].url : null
}

output "kms_key_id" {
  description = "ID de la clé KMS pour l'encryption"
  value       = aws_kms_key.eks.key_id
}

output "kms_key_arn" {
  description = "ARN de la clé KMS pour l'encryption"
  value       = aws_kms_key.eks.arn
}

output "log_group_name" {
  description = "Nom du groupe de logs CloudWatch"
  value       = aws_cloudwatch_log_group.eks_cluster.name
}

output "log_group_arn" {
  description = "ARN du groupe de logs CloudWatch"
  value       = aws_cloudwatch_log_group.eks_cluster.arn
}

output "namespace_name" {
  description = "Nom du namespace Kubernetes pour l'application financière"
  value       = kubernetes_namespace.financial_app.metadata[0].name
}

output "spark_driver_service_account" {
  description = "Nom du service account Spark Driver"
  value       = kubernetes_service_account.spark_driver.metadata[0].name
}

output "spark_executor_service_account" {
  description = "Nom du service account Spark Executor"
  value       = kubernetes_service_account.spark_executor.metadata[0].name
}

output "spark_driver_role_arn" {
  description = "ARN du rôle IAM pour Spark Driver (si IRSA activé)"
  value       = var.enable_irsa ? aws_iam_role.spark_driver_role[0].arn : null
}

output "spark_executor_role_arn" {
  description = "ARN du rôle IAM pour Spark Executor (si IRSA activé)"
  value       = var.enable_irsa ? aws_iam_role.spark_executor_role[0].arn : null
}

output "config_map_name" {
  description = "Nom du ConfigMap pour la configuration Spark"
  value       = kubernetes_config_map.spark_config.metadata[0].name
}

output "kubectl_config_command" {
  description = "Commande pour configurer kubectl"
  value       = "aws eks update-kubeconfig --region ${data.aws_region.current.name} --name ${aws_eks_cluster.main.name}"
}

# Data source pour la région actuelle
data "aws_region" "current" {}
