output "alb_dns_name" {
  value = "http://${module.app.alb_dns_name}"
}
