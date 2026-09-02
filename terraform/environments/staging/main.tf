locals {
  name = "diamond-staging"
}

module "network" {
  source   = "../../modules/network"
  name     = local.name
  vpc_cidr = var.vpc_cidr
}

module "registry" {
  source = "../../modules/registry"
  name   = local.name
}

module "database" {
  source = "../../modules/database"
  name   = local.name
  vpc_id = module.network.vpc_id
}

module "cluster" {
  source = "../../modules/cluster"
  name   = local.name
  vpc_id = module.network.vpc_id
}

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

  backend_image  = var.backend_image
  frontend_image = var.frontend_image

  backend_desired_count  = var.backend_desired_count
  frontend_desired_count = var.frontend_desired_count

  backend_extra_env  = var.backend_extra_env
  frontend_extra_env = var.frontend_extra_env
}
