resource "random_password" "master" {
  length  = 24
  special = false # keep it simple to embed in a connection-string env var
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.name}-db"
  subnet_ids = var.private_subnet_ids

  tags = { Name = "${var.name}-db" }
}

# Deliberately has no ingress rules -- callers (the app module, the db_admin
# module) add their own aws_security_group_rule pointing at this SG's id.
# That avoids a cycle: this module doesn't need to know about client
# security groups that are created elsewhere.
resource "aws_security_group" "rds" {
  name        = "${var.name}-rds"
  description = "Postgres -- ingress rules added by whichever module/env needs access"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-rds" }
}

resource "aws_db_instance" "postgres" {
  identifier     = "${var.name}-postgres"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.allocated_storage * 4
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.master.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  multi_az                = var.multi_az
  backup_retention_period = var.backup_retention_period
  skip_final_snapshot     = var.skip_final_snapshot
  deletion_protection     = var.deletion_protection
  apply_immediately       = true
}

# Master credentials, for administrative use only (the db_admin module uses
# this to create/drop per-branch databases). Application containers should
# get the narrower app_db_url secret below instead.
resource "aws_secretsmanager_secret" "master_credentials" {
  name = "${var.name}-db-master-credentials"
}

resource "aws_secretsmanager_secret_version" "master_credentials" {
  secret_id = aws_secretsmanager_secret.master_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.master.result
    host     = aws_db_instance.postgres.address
    port     = 5432
    database = "postgres" # the always-present admin database, not the app db
  })
}

# Full connection string for this environment's own app database (var.db_name).
# Branch environments do NOT use this -- they build their own secret pointing
# at their own per-branch database (see environments/dev-branch).
resource "aws_secretsmanager_secret" "app_db_url" {
  name = "${var.name}-database-url"
}

resource "aws_secretsmanager_secret_version" "app_db_url" {
  secret_id     = aws_secretsmanager_secret.app_db_url.id
  secret_string = "postgresql://${var.db_username}:${random_password.master.result}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
}
