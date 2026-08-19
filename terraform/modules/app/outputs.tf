output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "backend_service_discovery_name" {
  value = "${aws_service_discovery_service.backend.name}.${var.service_discovery_namespace_name}"
}
