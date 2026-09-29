resource "aws_ecs_cluster" "main" {
  name = var.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Private DNS namespace so app instances (persistent + branch) can reach
# their own backend at a stable name without going through a public ALB.
# Deliberately the same name ("diamond.local") in every environment: the
# frontend's FLASK_URL is baked in at image build time (see
# frontend/next.config.ts), so one frontend image can only be promoted
# across dev/staging/prod if its backend resolves at the same hostname
# everywhere. Each environment's namespace is private to its own VPC, so
# the identical names don't collide.
resource "aws_service_discovery_private_dns_namespace" "main" {
  name = var.namespace_name
  vpc  = var.vpc_id
}
