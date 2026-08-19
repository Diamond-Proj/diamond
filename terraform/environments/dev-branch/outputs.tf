output "alb_dns_name" {
  value = "http://${module.app.alb_dns_name}"
}

output "db_name" {
  value = local.db_name
}
