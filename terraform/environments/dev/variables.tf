variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "backend_image" {
  description = "Image for the persistent dev deploy (main branch). Branch environments pass their own images directly, bypassing this."
  type        = string
  default     = ""
}

variable "frontend_image" {
  type    = string
  default = ""
}

variable "backend_extra_env" {
  type    = map(string)
  default = {}
}

variable "frontend_extra_env" {
  type    = map(string)
  default = {}
}
