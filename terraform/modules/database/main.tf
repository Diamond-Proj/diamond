# The RDS instance, its security group, and its master-credentials secret
# are shared across all environments -- created once by
# terraform/bootstrap-data, not per environment. This module just looks
# them up, plus this environment's own connection-string secret (one per
# environment, also created by bootstrap-data).

data "aws_db_instance" "shared" {
  db_instance_identifier = "${var.shared_db_name}-postgres"
}

data "aws_security_group" "rds" {
  name = "${var.shared_db_name}-rds"
}

data "aws_secretsmanager_secret" "master_credentials" {
  name = "${var.shared_db_name}-db-master-credentials"
}

data "aws_secretsmanager_secret" "app_db_url" {
  name = "${var.name}-database-url"
}
