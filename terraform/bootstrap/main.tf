# One-time setup: creates the S3 bucket that every other environment's
# remote state lives in. Locking uses S3's native conditional-write locking
# (`use_lockfile` in each environment's backend block) -- no DynamoDB table
# needed. Apply this once, by hand, with local state, before touching
# prod/staging/dev/dev-branch:
#
#   cd terraform/bootstrap
#   terraform init
#   terraform apply -var="state_bucket_name=<something-globally-unique>"
#
# S3 bucket names are globally unique across ALL AWS accounts, so the default
# below will likely be taken -- pass your own.

terraform {
  required_version = ">= 1.11.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "state_bucket_name" {
  type    = string
  default = "diamond-hpc-terraform-state"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "state" {
  bucket = var.state_bucket_name

  # Early draft: nothing stops someone from deleting this bucket out from
  # under every environment's state. Consider a bucket policy / SCP that
  # denies deletion once this is load-bearing.
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "state_bucket_name" {
  value = aws_s3_bucket.state.bucket
}
