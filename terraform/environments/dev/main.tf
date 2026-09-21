locals {
  name = "diamond-dev"
}

module "network" {
  source   = "../../modules/network"
  name     = local.name
  vpc_cidr = var.vpc_cidr
}

# Shared by both the persistent "main" deploy below and every ephemeral
# branch environment (see ../dev-branch).
module "registry" {
  source = "../../modules/registry"
  name   = local.name
}

module "database" {
  source  = "../../modules/database"
  name    = local.name
  db_name = "dev"
}

# The shared RDS instance/bastion (terraform/bootstrap-data) live in their
# own VPC, peered to this one. Route traffic to it through that peering
# connection -- the reverse routes (this VPC's CIDR, from the data VPC) are
# created on bootstrap-data's side.
data "terraform_remote_state" "shared_data" {
  backend = "s3"
  config = {
    bucket = "diamond-hpc-terraform-state"
    key    = "diamond/bootstrap-data/terraform.tfstate"
    region = "us-east-2"
  }
}

resource "aws_route" "to_shared_data" {
  route_table_id            = module.network.private_route_table_id
  destination_cidr_block    = data.terraform_remote_state.shared_data.outputs.vpc_cidr_block
  vpc_peering_connection_id = data.terraform_remote_state.shared_data.outputs.peering_connection_ids["dev"]
}

module "cluster" {
  source = "../../modules/cluster"
  name   = local.name
  vpc_id = module.network.vpc_id
}

# Lets scripts/dev-up.sh and scripts/dev-down.sh create/drop a database per
# branch on this same RDS instance.
module "db_admin" {
  source = "../../modules/db_admin"

  name                          = local.name
  vpc_id                        = module.network.vpc_id
  master_credentials_secret_arn = module.database.master_credentials_secret_arn
  rds_security_group_id         = module.database.security_group_id
}

# The persistent dev deploy -- always tracks main, always up. Branch
# environments (../dev-branch) are separate app instances layered on top of
# the same vpc/cluster/database via terraform_remote_state.
module "app" {
  source = "../../modules/app"

  name       = local.name
  aws_region = var.aws_region

  vpc_id             = module.network.vpc_id
  public_subnet_ids  = module.network.public_subnet_ids
  private_subnet_ids = module.network.private_subnet_ids

  ecs_cluster_id                   = module.cluster.cluster_id
  service_discovery_namespace_id   = module.cluster.namespace_id
  service_discovery_namespace_name = module.cluster.namespace_name

  rds_security_group_id = module.database.security_group_id
  db_url_secret_arn     = module.database.app_db_url_secret_arn
  db_url                = var.db_url

  backend_image  = coalesce(var.backend_image, "${module.registry.backend_repository_url}:latest")
  frontend_image = coalesce(var.frontend_image, "${module.registry.frontend_repository_url}:latest")

  backend_extra_env  = var.backend_extra_env
  frontend_extra_env = var.frontend_extra_env

  domain_name = var.domain_name
}
