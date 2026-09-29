variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "master_credentials_secret_arn" {
  description = "Secrets Manager ARN for the RDS master credentials (admin username/password/host)"
  type        = string
}

variable "rds_security_group_id" {
  description = "The database module's RDS security group -- this module adds its own ingress rule to it"
  type        = string
}
