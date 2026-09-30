variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "vpc_cidr" {
  type    = string
  default = "10.21.0.0/16"
}

variable "image_tag" {
  description = "Tag to deploy from both the backend and frontend repos, as pushed by build-and-push.yml (e.g. main-94d9b3e)."
  type        = string

  validation {
    condition     = var.image_tag != "" && var.image_tag != "latest"
    error_message = "image_tag must be a specific, already-pushed tag (not empty or 'latest')."
  }
}

variable "backend_repository_name" {
  description = "Shared ECR repo for backend images (managed outside Terraform, see build-and-push.yml)."
  type        = string
  default     = "backend"
}

variable "frontend_repository_name" {
  type    = string
  default = "frontend"
}

variable "db_url" {
  description = "TEST/experimental: pass the full postgres connection string directly (e.g. via TF_VAR_db_url) instead of reading it from Secrets Manager. See modules/app's variable of the same name for the tradeoffs. Leave unset for the normal path."
  type        = string
  default     = null
  sensitive   = true
}

variable "backend_desired_count" {
  type    = number
  default = 1
}

variable "frontend_desired_count" {
  type    = number
  default = 1
}

variable "backend_extra_env" {
  type    = map(string)
  default = {}
}

variable "frontend_extra_env" {
  type    = map(string)
  default = {}
}

variable "domain_name" {
  description = "Custom domain for staging's frontend. See modules/app's variable of the same name. Once set and validated, keep it as this default (as dev/prod do) so a CI apply can't revert it to null and destroy the cert/HTTPS listener."
  type        = string
  default     = null
}
