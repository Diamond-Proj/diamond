variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "vpc_cidr" {
  description = "CIDR for the shared data VPC. Must not overlap dev/staging/prod (10.20.0.0/16, 10.21.0.0/16, 10.22.0.0/16)."
  type        = string
  default     = "10.23.0.0/16"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "engine_version" {
  type    = string
  default = "18.3"
}

variable "allocated_storage" {
  type    = number
  default = 20
}

variable "master_password" {
  description = "Master (postgres user) password for the shared RDS instance. Provide at apply time (-var or TF_VAR_master_password) -- deliberately not generated or defaulted."
  type        = string
  sensitive   = true
}

variable "bastion_instance_type" {
  type    = string
  default = "t2.micro"
}

variable "bastion_key_name" {
  description = "Name of an existing EC2 key pair (looked up, not created) -- private key material never touches Terraform."
  type        = string
  default     = "minum-devdb"
}

variable "bastion_ssh_cidr_blocks" {
  description = "CIDRs allowed to SSH to the bastion. Defaults to open, matching the current manually-created bastion -- tighten this once a fixed IP range is available."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
