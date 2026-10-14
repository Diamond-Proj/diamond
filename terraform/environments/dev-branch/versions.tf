# This environment is meant to be run once per developer branch, via
# terraform workspaces (see ../../scripts/dev-up.sh). Each workspace gets its
# own state file automatically -- the S3 backend namespaces non-default
# workspaces under "env:/<workspace>/<key>" without any extra config here.

terraform {
  required_version = ">= 1.11.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket       = "diamond-hpc-terraform-state" # must match bootstrap's state_bucket_name
    key          = "diamond/dev-branch/terraform.tfstate"
    region       = "us-east-2"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "diamond"
      Environment = "dev-branch"
      Branch      = var.branch_name
      ManagedBy   = "terraform"
    }
  }
}
