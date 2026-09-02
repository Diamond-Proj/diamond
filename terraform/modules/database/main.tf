# The RDS instance, its security group, and its Secrets Manager secrets are
# all created and managed by hand -- this module only looks them up so the
# app/db_admin modules can wire into them. For a given environment `name`,
# the following must already exist:
#
#   - an RDS instance with identifier "${name}-postgres"
#   - a security group named "${name}-rds" in the environment's VPC (no
#     ingress rules required -- the app/db_admin modules add their own)
#   - a Secrets Manager secret "${name}-db-master-credentials": a JSON
#     object with keys username, password, host, port, database (used by
#     db_admin to create/drop per-branch databases)
#   - a Secrets Manager secret "${name}-database-url": a plain string, the
#     full postgresql:// connection string for this environment's own app
#     database (var.db_name)

data "aws_db_instance" "postgres" {
  db_instance_identifier = "${var.name}-postgres"
}

data "aws_security_group" "rds" {
  name   = "${var.name}-rds"
  vpc_id = var.vpc_id
}

data "aws_secretsmanager_secret" "master_credentials" {
  name = "${var.name}-db-master-credentials"
}

data "aws_secretsmanager_secret" "app_db_url" {
  name = "${var.name}-database-url"
}
