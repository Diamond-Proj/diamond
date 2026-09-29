output "alb_dns_name" {
  value = "http://${module.app.alb_dns_name}"
}

output "vpc_id" {
  value = module.network.vpc_id
}

output "vpc_cidr_block" {
  value = module.network.vpc_cidr_block
}

output "alb_hostname" {
  description = "Bare ALB hostname (no scheme) -- this is the CNAME target for a custom domain."
  value       = module.app.alb_dns_name
}

output "acm_validation_record" {
  description = "DNS record to create by hand so ACM can validate var.domain_name's cert. Null until domain_name is set."
  value       = module.app.acm_validation_record
}

output "backend_ecr_repository_url" {
  value = data.aws_ecr_repository.backend.repository_url
}

output "frontend_ecr_repository_url" {
  value = data.aws_ecr_repository.frontend.repository_url
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
