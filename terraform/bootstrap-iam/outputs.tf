output "ecs_execution_role_name" {
  value = aws_iam_role.ecs_execution.name
}

output "ecs_task_role_name" {
  value = aws_iam_role.ecs_task.name
}

output "read_diamond_secrets_policy_arn" {
  description = "Give this ARN to whoever manages the deploying user's IAM policy -- adding it to their AttachApprovedPoliciesOnly allowlist lets them self-serve manage these roles without this module being re-run by an admin."
  value       = aws_iam_policy.read_diamond_secrets.arn
}
