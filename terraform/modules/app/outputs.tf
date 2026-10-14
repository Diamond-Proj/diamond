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

output "acm_validation_records" {
  description = "DNS records to create by hand (this project's domains aren't in Route 53) so ACM can validate the cert: one per name on it (var.domain_name plus var.subject_alternative_names), keyed by that name. Empty until domain_name is set."
  value = {
    for dvo in flatten([for c in aws_acm_certificate.frontend : tolist(c.domain_validation_options)]) :
    dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  }
}
