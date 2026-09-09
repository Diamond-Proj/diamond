output "alb_dns_name" {
  value = "http://${module.app.alb_dns_name}"
}

output "vpc_id" {
  value = module.network.vpc_id
}

output "vpc_cidr_block" {
  value = module.network.vpc_cidr_block
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

output "backend_image" {
  value = module.app.backend_image
}

output "frontend_image" {
  value = module.app.frontend_image
}
