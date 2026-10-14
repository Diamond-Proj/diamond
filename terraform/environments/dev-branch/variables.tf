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

variable "db_url" {
  description = "Full postgres connection string for the shared dev database (the same DEV_DB_URL the persistent dev deploy uses), e.g. via TF_VAR_db_url. See modules/app's variable of the same name."
  type        = string
  sensitive   = true
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
