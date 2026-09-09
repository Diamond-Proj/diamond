# One-time setup: a dedicated VPC holding a single shared RDS instance
# (separate prod/staging/dev databases on it) and an SSH bastion, peered to
# each of the dev/staging/prod VPCs so their ECS tasks can reach it.
#
# Apply order matters:
#   1. dev/staging/prod must already be applied (this reads their vpc_id and
#      vpc_cidr_block outputs via remote state).
#   2. Apply this:
#        cd terraform/bootstrap-data
#        terraform init
#        terraform apply -var="master_password=<something>"
#   3. Re-apply dev/staging/prod -- their own aws_route.to_shared_data (see
#      their main.tf) reads this module's outputs, so it only resolves once
#      this has been applied at least once.
#   4. SSH to the bastion and, using the master credentials in
#      diamond-shared-db-master-credentials, run `CREATE DATABASE dev;`,
#      `CREATE DATABASE staging;`, `CREATE DATABASE prod;`, then restore
#      each environment's data dump into its database.
#   5. Once traffic is confirmed flowing through the new instance, delete
#      the old manually-created RDS instance and bastion by hand.

data "aws_availability_zones" "available" {
  state = "available"
}

data "terraform_remote_state" "dev" {
  backend = "s3"
  config = {
    bucket = "diamond-hpc-terraform-state"
    key    = "diamond/dev/terraform.tfstate"
    region = "us-east-2"
  }
}

data "terraform_remote_state" "staging" {
  backend = "s3"
  config = {
    bucket = "diamond-hpc-terraform-state"
    key    = "diamond/staging/terraform.tfstate"
    region = "us-east-2"
  }
}

data "terraform_remote_state" "prod" {
  backend = "s3"
  config = {
    bucket = "diamond-hpc-terraform-state"
    key    = "diamond/prod/terraform.tfstate"
    region = "us-east-2"
  }
}

locals {
  peer_vpcs = {
    dev     = data.terraform_remote_state.dev.outputs
    staging = data.terraform_remote_state.staging.outputs
    prod    = data.terraform_remote_state.prod.outputs
  }
}

# --- Networking -------------------------------------------------------

resource "aws_vpc" "data" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "diamond-data" }
}

resource "aws_internet_gateway" "data" {
  vpc_id = aws_vpc.data.id
  tags   = { Name = "diamond-data" }
}

# Bastion only -- RDS has no reason to be publicly reachable.
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.data.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, 0)
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = { Name = "diamond-data-public-0" }
}

# RDS subnet group needs subnets in >= 2 AZs even for a single-AZ instance.
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.data.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 1)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = { Name = "diamond-data-private-${count.index}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.data.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.data.id
  }

  tags = { Name = "diamond-data-public" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# No default route -- RDS/bastion-to-internet isn't needed. Routes to each
# peered environment are added below.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.data.id
  tags   = { Name = "diamond-data-private" }
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# --- Peering to dev/staging/prod --------------------------------------

resource "aws_vpc_peering_connection" "this" {
  for_each    = local.peer_vpcs
  vpc_id      = aws_vpc.data.id
  peer_vpc_id = each.value.vpc_id
  auto_accept = true # same account/region, so no separate accepter needed

  tags = { Name = "diamond-data-to-${each.key}" }
}

resource "aws_route" "private_to_peer" {
  for_each                  = local.peer_vpcs
  route_table_id            = aws_route_table.private.id
  destination_cidr_block    = each.value.vpc_cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.this[each.key].id
}

# --- RDS ----------------------------------------------------------------

resource "aws_db_subnet_group" "shared" {
  name       = "diamond-shared-db"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "diamond-shared-db" }
}

# No ingress rules here -- the app/db_admin modules in each environment add
# their own aws_security_group_rule against this group's id (works
# cross-VPC once peered, same as it did within a single VPC before).
resource "aws_security_group" "rds" {
  name        = "diamond-shared-rds"
  description = "Shared Postgres instance (prod/staging/dev databases) -- ingress rules added by whichever module/env needs access"
  vpc_id      = aws_vpc.data.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "diamond-shared-rds" }
}

resource "aws_security_group_rule" "rds_from_bastion" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.bastion.id
}

resource "aws_db_instance" "shared" {
  identifier     = "diamond-shared-postgres"
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.db_instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.allocated_storage * 4
  storage_type          = "gp2"
  storage_encrypted     = true

  username = "postgres"
  password = var.master_password

  db_subnet_group_name   = aws_db_subnet_group.shared.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  multi_az                = false
  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true

  # prod/staging/dev databases are created by hand after the first apply
  # (see the file header) -- this resource only stands up the instance.
}

# Master credentials, for administrative use only (db_admin uses this to
# create/drop per-branch databases; also what you use from the bastion to
# create the prod/staging/dev databases initially).
resource "aws_secretsmanager_secret" "master_credentials" {
  name = "diamond-shared-db-master-credentials"
}

resource "aws_secretsmanager_secret_version" "master_credentials" {
  secret_id = aws_secretsmanager_secret.master_credentials.id
  secret_string = jsonencode({
    username = "postgres"
    password = var.master_password
    host     = aws_db_instance.shared.address
    port     = 5432
    database = "postgres" # the always-present admin database, not an app db
  })
}

# One connection-string secret per environment, all pointing at the same
# instance but a different database. modules/database looks these up by
# name ("<name>-database-url").
resource "aws_secretsmanager_secret" "app_db_url" {
  for_each = local.peer_vpcs
  name     = "diamond-${each.key}-database-url"
}

resource "aws_secretsmanager_secret_version" "app_db_url" {
  for_each      = local.peer_vpcs
  secret_id     = aws_secretsmanager_secret.app_db_url[each.key].id
  secret_string = "postgresql://postgres:${var.master_password}@${aws_db_instance.shared.address}:5432/${each.key}"
}

# --- Bastion --------------------------------------------------------------

data "aws_key_pair" "bastion" {
  key_name = var.bastion_key_name
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "bastion" {
  name        = "diamond-bastion"
  description = "SSH bastion for the shared RDS instance"
  vpc_id      = aws_vpc.data.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.bastion_ssh_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "diamond-bastion" }
}

resource "aws_instance" "bastion" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.bastion_instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.bastion.id]
  key_name                    = data.aws_key_pair.bastion.key_name
  associate_public_ip_address = true

  tags = { Name = "diamond-bastion" }
}
