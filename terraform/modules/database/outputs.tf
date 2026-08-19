output "address" {
  value = aws_db_instance.postgres.address
}

output "security_group_id" {
  value = aws_security_group.rds.id
}

output "master_credentials_secret_arn" {
  value = aws_secretsmanager_secret.master_credentials.arn
}

output "app_db_url_secret_arn" {
  value = aws_secretsmanager_secret.app_db_url.arn
}

output "db_name" {
  value = var.db_name
}
