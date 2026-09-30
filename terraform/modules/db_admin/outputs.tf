output "task_definition_arn" {
  value = aws_ecs_task_definition.db_admin.arn
}

output "security_group_id" {
  value = aws_security_group.db_admin.id
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.db_admin.name
}
