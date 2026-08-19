variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "vpc_cidr" {
  type    = string
  default = "10.22.0.0/16"
}

variable "backend_image" {
  description = "Full image ref (repo:tag), e.g. from CI after pushing a build. Required -- prod should never default to ':latest'."
  type        = string
}

variable "frontend_image" {
  type = string
}

variable "backend_desired_count" {
  type    = number
  default = 2
}

variable "frontend_desired_count" {
  type    = number
  default = 2
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.small"
}

variable "backend_extra_env" {
  type    = map(string)
  default = {}
}

variable "frontend_extra_env" {
  type    = map(string)
  default = {}
}
