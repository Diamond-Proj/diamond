variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "namespace_name" {
  description = "Private DNS namespace for service discovery. Keep this identical across environments -- see main.tf."
  type        = string
  default     = "diamond.local"
}
