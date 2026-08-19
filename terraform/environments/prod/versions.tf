terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket         = "diamond-terraform-state" # must match bootstrap's state_bucket_name
    key            = "diamond/prod/terraform.tfstate"
    region         = "us-east-2"
    dynamodb_table = "diamond-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "diamond"
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}
