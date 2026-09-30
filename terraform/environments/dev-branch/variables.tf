variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "branch_name" {
  description = "A short, DNS-safe slug for this branch (scripts/dev-up.sh derives this from your git branch name -- lowercase, hyphens only, <=18 chars). Also used as the terraform workspace name."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,17}$", var.branch_name))
    error_message = "branch_name must be lowercase alphanumeric/hyphens, starting with a letter or digit, 18 characters or fewer."
  }
}

variable "backend_image" {
  description = "Image pushed by dev-up.sh, tagged with this branch"
  type        = string
}

variable "frontend_image" {
  type = string
}

variable "backend_cpu" {
  type    = number
  default = 256
}

variable "backend_memory" {
  type    = number
  default = 512
}

variable "frontend_cpu" {
  type    = number
  default = 256
}

variable "frontend_memory" {
  type    = number
  default = 512
}

variable "backend_extra_env" {
  type    = map(string)
  default = {}
}

variable "frontend_extra_env" {
  type    = map(string)
  default = {}
}
