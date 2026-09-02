# This environment is meant to be run once per developer branch, via
# terraform workspaces (see ../../scripts/dev-up.sh). Each workspace gets its
# own state file automatically -- the local backend namespaces non-default
# workspaces under "terraform.tfstate.d/<workspace>/" without any extra
# config here.

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
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
