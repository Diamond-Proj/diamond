output "cluster_id" {
  value = aws_ecs_cluster.main.id
}

output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "namespace_id" {
  value = aws_service_discovery_private_dns_namespace.main.id
}

output "namespace_name" {
  value = aws_service_discovery_private_dns_namespace.main.name
}
