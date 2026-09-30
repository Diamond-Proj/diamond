variable "name" {
  description = "This environment's name (e.g. diamond-dev) -- used to find its own \"<name>-database-url\" connection-string secret."
  type        = string
}

variable "shared_db_name" {
  description = "Name of the shared RDS instance/security group/master-credentials secret that every environment's database lives on (created by terraform/bootstrap-data)."
  type        = string
  default     = "diamond-shared"
}

variable "db_name" {
  description = "Name of this environment's own database on the shared instance. Must match whatever's embedded in the manually-created \"<name>-database-url\" secret -- this module doesn't derive it, just passes it through."
  type        = string
  default     = "diamond"
}
