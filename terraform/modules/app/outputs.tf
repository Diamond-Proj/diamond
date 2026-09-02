output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "backend_service_discovery_name" {
  value = "${aws_service_discovery_service.backend.name}.${var.service_discovery_namespace_name}"
}

output "backend_image" {
  value = var.backend_image
}

output "frontend_image" {
  value = var.frontend_image
}
