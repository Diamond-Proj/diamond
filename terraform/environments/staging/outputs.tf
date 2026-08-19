output "alb_dns_name" {
  value = "http://${module.app.alb_dns_name}"
}

output "backend_ecr_repository_url" {
  value = module.registry.backend_repository_url
}

output "frontend_ecr_repository_url" {
  value = module.registry.frontend_repository_url
}

output "rds_endpoint" {
  value = module.database.address
}
