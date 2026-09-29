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

output "acm_validation_record" {
  description = "DNS record to create by hand (this project's domains aren't in Route 53) so ACM can validate the cert for var.domain_name. Null until domain_name is set."
  value = var.domain_name != null ? {
    name  = tolist(aws_acm_certificate.frontend[0].domain_validation_options)[0].resource_record_name
    type  = tolist(aws_acm_certificate.frontend[0].domain_validation_options)[0].resource_record_type
    value = tolist(aws_acm_certificate.frontend[0].domain_validation_options)[0].resource_record_value
  } : null
}
