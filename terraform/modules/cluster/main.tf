resource "aws_ecs_cluster" "main" {
  name = var.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Private DNS namespace so app instances (persistent + branch) can reach
# their own backend at a stable name without going through a public ALB.
# Each app instance registers "backend.<its-own-name>.<namespace>", so
# multiple app instances safely share one cluster + namespace.
resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "${var.name}.local"
  vpc  = var.vpc_id
}
