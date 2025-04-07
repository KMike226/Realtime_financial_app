# Outputs du module EMR

output "cluster_id" {
  description = "ID du cluster EMR"
  value       = aws_emr_cluster.financial_data_cluster.id
}

output "cluster_name" {
  description = "Nom du cluster EMR"
  value       = aws_emr_cluster.financial_data_cluster.name
}

output "cluster_arn" {
  description = "ARN du cluster EMR"
  value       = aws_emr_cluster.financial_data_cluster.arn
}

output "master_public_dns" {
  description = "DNS public du nœud master EMR"
  value       = aws_emr_cluster.financial_data_cluster.master_public_dns
}

output "cluster_state" {
  description = "État du cluster EMR"
  value       = aws_emr_cluster.financial_data_cluster.state
}

output "log_uri" {
  description = "URI des logs du cluster EMR"
  value       = aws_emr_cluster.financial_data_cluster.log_uri
}

output "emr_service_role_arn" {
  description = "ARN du rôle de service EMR"
  value       = aws_iam_role.emr_service_role.arn
}

output "emr_instance_role_arn" {
  description = "ARN du rôle d'instance EMR"
  value       = aws_iam_role.emr_instance_role.arn
}

output "emr_instance_profile_arn" {
  description = "ARN du profil d'instance EMR"
  value       = aws_iam_instance_profile.emr_instance_profile.arn
}

output "emr_autoscaling_role_arn" {
  description = "ARN du rôle d'auto-scaling EMR"
  value       = aws_iam_role.emr_autoscaling_role.arn
}

output "emr_master_security_group_id" {
  description = "ID du security group EMR master"
  value       = aws_security_group.emr_master.id
}

output "emr_cluster_security_group_id" {
  description = "ID du security group EMR cluster"
  value       = aws_security_group.emr_cluster.id
}

output "bootstrap_script_s3_path" {
  description = "Chemin S3 du script de bootstrap"
  value       = "s3://${var.s3_bucket_name}/${aws_s3_object.bootstrap_script.key}"
}

# Informations utiles pour la connexion et le monitoring
output "spark_ui_url" {
  description = "URL de l'interface Spark (accessible via un tunnel SSH)"
  value       = aws_emr_cluster.financial_data_cluster.master_public_dns != "" ? "http://${aws_emr_cluster.financial_data_cluster.master_public_dns}:4040" : "Cluster not ready"
}

output "yarn_ui_url" {
  description = "URL de l'interface YARN (accessible via un tunnel SSH)"
  value       = aws_emr_cluster.financial_data_cluster.master_public_dns != "" ? "http://${aws_emr_cluster.financial_data_cluster.master_public_dns}:8088" : "Cluster not ready"
}

output "zeppelin_url" {
  description = "URL de Zeppelin pour le développement interactif"
  value       = aws_emr_cluster.financial_data_cluster.master_public_dns != "" ? "http://${aws_emr_cluster.financial_data_cluster.master_public_dns}:8890" : "Cluster not ready"
}

# Instructions pour la connexion SSH
output "ssh_command" {
  description = "Commande SSH pour se connecter au nœud master (si key_name est fourni)"
  value       = var.key_name != null && aws_emr_cluster.financial_data_cluster.master_public_dns != "" ? "ssh -i ~/.ssh/${var.key_name}.pem hadoop@${aws_emr_cluster.financial_data_cluster.master_public_dns}" : "SSH key not configured or cluster not ready"
}

# CloudWatch Alarms
output "cpu_alarm_arn" {
  description = "ARN de l'alarme CloudWatch pour CPU"
  value       = aws_cloudwatch_metric_alarm.emr_cluster_cpu_high.arn
}

output "memory_alarm_arn" {
  description = "ARN de l'alarme CloudWatch pour mémoire"
  value       = aws_cloudwatch_metric_alarm.emr_cluster_memory_high.arn
}
