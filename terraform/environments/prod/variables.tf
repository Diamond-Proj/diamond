variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "vpc_cidr" {
  type    = string
  default = "10.22.0.0/16"
}

variable "image_tag" {
  description = "Tag to deploy from both the backend and frontend repos, as pushed by build-and-push.yml (e.g. v1.4.2-abc1234). Required -- prod should never default to ':latest'."
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

variable "backend_desired_count" {
  type    = number
  default = 2
}

variable "frontend_desired_count" {
  type    = number
  default = 2
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
  description = "Custom domain for prod's frontend. See modules/app's variable of the same name. Defaulted (not left null) so a plain `terraform apply` without -var -- including the CI deploy -- can't accidentally destroy the ACM cert/HTTPS listener by reverting this to null."
  type        = string
  default     = "prod.diamondhpc.ai"
}

variable "subject_alternative_names" {
  description = "Extra names on prod's ACM cert. The public site is served at the apex (diamondhpc.ai) and at www.diamondhpc.ai, both Cloudflare-proxied to the same ALB as domain_name, so the cert has to cover all three. Defaulted for the same reason as domain_name: a CI apply without -var must not replace the cert with one missing a public name."
  type        = list(string)
  default     = ["diamondhpc.ai", "www.diamondhpc.ai"]
}

variable "db_url" {
  description = "TEST/experimental: pass the full postgres connection string directly (e.g. via TF_VAR_db_url) instead of reading it from Secrets Manager. See modules/app's variable of the same name for the tradeoffs. Leave unset for the normal path."
  type        = string
  default     = null
  sensitive   = true
}
