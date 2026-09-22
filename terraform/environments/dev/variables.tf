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

variable "db_url" {
  description = "TEST/experimental: pass the full postgres connection string directly (e.g. via TF_VAR_db_url) instead of reading it from Secrets Manager. See modules/app's variable of the same name for the tradeoffs. Leave unset for the normal path."
  type        = string
  default     = null
  sensitive   = true
}

variable "frontend_extra_env" {
  type    = map(string)
  default = {}
}

variable "domain_name" {
  description = "Custom domain for the persistent dev deploy's frontend. See modules/app's variable of the same name. Defaulted (not left null) so a plain `terraform apply` without -var can't accidentally destroy the ACM cert/HTTPS listener by reverting this to null."
  type        = string
  default     = "dev.diamondhpc.ai"
}
