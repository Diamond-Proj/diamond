variable "name" {
  description = "Unique, DNS-label-safe name for this app instance (e.g. diamond-prod, diamond-dev, diamond-dev-alice-feat123). Used to name the ALB, security groups, task defs, and this instance's service-discovery entry, so it must be unique within the shared cluster/namespace it's deployed into."
  type        = string

  validation {
    # ALB/target-group names cap at 32 chars; "-frontend" (9 chars) is the
    # longest suffix we append, so keep the base name well under that.
    condition     = length(var.name) <= 22
    error_message = "name must be 22 characters or fewer (ALB/target-group name limits)."
  }
}

variable "aws_region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "ecs_cluster_id" {
  type = string
}

variable "service_discovery_namespace_id" {
  type = string
}

variable "service_discovery_namespace_name" {
  type = string
}

variable "rds_security_group_id" {
  description = "The database module's RDS security group -- this module adds its own backend->rds ingress rule to it"
  type        = string
}

variable "db_url_secret_arn" {
  description = "Secrets Manager ARN holding the full postgres connection string this instance's backend should use. Ignored if var.db_url is set."
  type        = string
}

variable "db_url" {
  description = "TEST/experimental: the full postgres connection string, passed in directly (e.g. from a GitHub Actions secret via TF_VAR_db_url) instead of read from Secrets Manager at container startup. When set, this is injected as a plain ECS environment value rather than via `secrets`/valueFrom, so the execution role no longer needs secretsmanager:GetSecretValue for it -- but the value then lives in the task definition (visible via ecs:DescribeTaskDefinition) and in Terraform state, not just in Secrets Manager. Leave null to keep using db_url_secret_arn."
  type        = string
  default     = null
  sensitive   = true
}

variable "backend_image" {
  type = string
}

variable "frontend_image" {
  type = string
}

variable "service_discovery_name" {
  description = "Name this instance's backend registers under in the cluster's private DNS namespace, so the frontend reaches it at <this>.<namespace>:<backend_container_port> (e.g. backend.diamond.local:5328). Must be unique within the namespace -- fine to leave as \"backend\" for the one persistent deploy per environment, but branch environments sharing dev's namespace need their own."
  type        = string
  default     = "backend"
}

variable "backend_container_port" {
  type    = number
  default = 5328
}

variable "frontend_container_port" {
  type    = number
  default = 3000
}

variable "backend_cpu" {
  type    = number
  default = 512
}

variable "backend_memory" {
  type    = number
  default = 1024
}

variable "frontend_cpu" {
  type    = number
  default = 256
}

variable "frontend_memory" {
  type    = number
  default = 512
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
  description = "Custom domain for this instance's frontend (e.g. dev.diamondhpc.ai). When set, adds an ACM cert + HTTPS listener and redirects HTTP to HTTPS. DNS validation is manual since this project's domains aren't in Route 53 -- see the acm_validation_record output. Leave null to stay HTTP-only on the raw ALB DNS name (fine for throwaway branch environments)."
  type        = string
  default     = null
}
