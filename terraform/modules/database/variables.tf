variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "db_name" {
  description = "Name of the default database this environment's own app instance connects to. Must match whatever's embedded in the manually-created \"<name>-database-url\" secret -- this module doesn't derive it, just passes it through."
  type        = string
  default     = "diamond"
}
