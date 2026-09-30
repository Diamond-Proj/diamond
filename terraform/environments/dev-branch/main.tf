locals {
  # e.g. branch_name "alice-feat123" -> "dev-alice-feat123" (fits the app
  # module's 22-char name limit since branch_name is capped at 18).
  name    = "dev-${var.branch_name}"
  db_name = "branch_${replace(var.branch_name, "-", "_")}"
}

data "terraform_remote_state" "dev" {
  backend = "s3"
  config = {
    bucket = "diamond-hpc-terraform-state"
    key    = "diamond/dev/terraform.tfstate"
    region = "us-east-2"
  }
}

# Read the shared instance's master credentials to build this branch's own
# connection string. scripts/dev-up.sh is responsible for actually having
# created the `db_name` database first (via the db_admin one-off task) --
# this environment only wires up the connection string and the app, it
# doesn't create the database itself.
data "aws_secretsmanager_secret_version" "master" {
  secret_id = data.terraform_remote_state.dev.outputs.db_master_credentials_secret_arn
}

locals {
  master = jsondecode(data.aws_secretsmanager_secret_version.master.secret_string)
}

resource "aws_secretsmanager_secret" "branch_db_url" {
  name = "diamond-dev-${var.branch_name}-database-url"
}

resource "aws_secretsmanager_secret_version" "branch_db_url" {
  secret_id     = aws_secretsmanager_secret.branch_db_url.id
  secret_string = "postgresql://${local.master.username}:${local.master.password}@${local.master.host}:${local.master.port}/${local.db_name}"
}

module "app" {
  source = "../../modules/app"

  name       = local.name
  aws_region = var.aws_region

  vpc_id             = data.terraform_remote_state.dev.outputs.vpc_id
  public_subnet_ids  = data.terraform_remote_state.dev.outputs.public_subnet_ids
  private_subnet_ids = data.terraform_remote_state.dev.outputs.private_subnet_ids

  ecs_cluster_id                   = data.terraform_remote_state.dev.outputs.ecs_cluster_id
  service_discovery_namespace_id   = data.terraform_remote_state.dev.outputs.service_discovery_namespace_id
  service_discovery_namespace_name = data.terraform_remote_state.dev.outputs.service_discovery_namespace_name
  # Shares dev's namespace with the persistent deploy (which takes plain
  # "backend"), so needs a unique name of its own.
  service_discovery_name = "${local.name}-backend"

  rds_security_group_id = data.terraform_remote_state.dev.outputs.rds_security_group_id
  db_url_secret_arn     = aws_secretsmanager_secret.branch_db_url.arn

  backend_image  = var.backend_image
  frontend_image = var.frontend_image

  backend_cpu           = var.backend_cpu
  backend_memory        = var.backend_memory
  backend_desired_count = 1

  frontend_cpu           = var.frontend_cpu
  frontend_memory        = var.frontend_memory
  frontend_desired_count = 1

  backend_extra_env  = merge({ FLASK_ENV = "development" }, var.backend_extra_env)
  frontend_extra_env = var.frontend_extra_env
}
