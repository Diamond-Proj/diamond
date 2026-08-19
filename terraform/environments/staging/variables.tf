variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "vpc_cidr" {
  type    = string
  default = "10.21.0.0/16"
}

variable "backend_image" {
  type = string
}

variable "frontend_image" {
  type = string
}

variable "backend_desired_count" {
  type    = number
  default = 1
}

variable "frontend_desired_count" {
  type    = number
  default = 1
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "backend_extra_env" {
  type    = map(string)
  default = {}
}

variable "frontend_extra_env" {
  type    = map(string)
  default = {}
}
