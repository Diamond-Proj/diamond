output "vpc_id" {
  value = aws_vpc.data.id
}

output "vpc_cidr_block" {
  value = aws_vpc.data.cidr_block
}

output "peering_connection_ids" {
  description = "Map of environment name -> VPC peering connection ID. Each environment's own aws_route back to this VPC reads its entry here."
  value       = { for k, v in aws_vpc_peering_connection.this : k => v.id }
}

output "rds_address" {
  value = aws_db_instance.shared.address
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}

output "master_credentials_secret_arn" {
  value = aws_secretsmanager_secret.master_credentials.arn
}

output "bastion_public_ip" {
  value = aws_instance.bastion.public_ip
}
