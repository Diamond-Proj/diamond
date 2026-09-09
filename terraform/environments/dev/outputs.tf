output "alb_dns_name" {
  value = "http://${module.app.alb_dns_name}"
}

output "vpc_id" {
  value = module.network.vpc_id
}

output "vpc_cidr_block" {
  value = module.network.vpc_cidr_block
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "backend_ecr_repository_url" {
  value = module.registry.backend_repository_url
}

output "frontend_ecr_repository_url" {
  value = module.registry.frontend_repository_url
}

output "ecs_cluster_id" {
  value = module.cluster.cluster_id
}

output "ecs_cluster_name" {
  value = module.cluster.cluster_name
}

output "service_discovery_namespace_id" {
  value = module.cluster.namespace_id
}

output "service_discovery_namespace_name" {
  value = module.cluster.namespace_name
}

output "rds_address" {
  value = module.database.address
}

output "rds_security_group_id" {
  value = module.database.security_group_id
}

output "db_master_credentials_secret_arn" {
  value = module.database.master_credentials_secret_arn
}

output "db_admin_task_definition_arn" {
  value = module.db_admin.task_definition_arn
}

output "db_admin_security_group_id" {
  value = module.db_admin.security_group_id
}

output "db_admin_log_group_name" {
  value = module.db_admin.log_group_name
}
