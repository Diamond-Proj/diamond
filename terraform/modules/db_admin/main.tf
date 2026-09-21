# Ad-hoc "run a one-off psql command against the shared RDS instance" task,
# used by scripts/dev-up.sh and scripts/dev-down.sh to create/drop a
# per-branch database. Not a long-running service -- invoked via
# `aws ecs run-task` with containerOverrides setting ACTION/DB_NAME.
#
# Early-draft simplification: branch databases are created/owned by the same
# master user as the RDS instance itself, so app containers for a branch run
# with admin-level DB credentials scoped only by which database they connect
# to, not by role permissions. A more careful setup would create a
# per-branch role with a real password and GRANT it access to just its own
# database.

resource "aws_security_group" "db_admin" {
  name        = "${var.name}-db-admin"
  description = "One-off db-admin task -- egress only, no inbound needed"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-db-admin" }
}

resource "aws_security_group_rule" "db_admin_to_rds" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = var.rds_security_group_id
  source_security_group_id = aws_security_group.db_admin.id
  description              = "db-admin one-off task"
}

resource "aws_cloudwatch_log_group" "db_admin" {
  name              = "/ecs/${var.name}/db-admin"
  retention_in_days = 14
}

# Shared across every environment, created once by terraform/bootstrap-iam.
# Name must stay exactly "ecsTaskExecutionRole" -- the deploying user's own
# IAM policy scopes GetRole/PassRole to "role/ecsTask*", so anything else
# will 403. Already grants secretsmanager:GetSecretValue on every
# "diamond-*" secret, which covers var.master_credentials_secret_arn.
data "aws_iam_role" "execution" {
  name = "ecsTaskExecutionRole"
}

resource "aws_ecs_task_definition" "db_admin" {
  family                   = "${var.name}-db-admin"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = data.aws_iam_role.execution.arn

  container_definitions = jsonencode([
    {
      name      = "db-admin"
      image     = "postgres:16-alpine"
      essential = true
      # The create/drop logic lives here, permanently, so `run-task` callers
      # only need to override plain environment variables (ACTION, DB_NAME)
      # instead of trying to shell-escape a script through CLI JSON.
      command = [
        "sh", "-c",
        <<-EOT
        set -eu
        case "$${ACTION:-}" in
          create)
            EXISTS=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'")
            if [ "$EXISTS" != "1" ]; then
              PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\""
            fi
            ;;
          drop)
            PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\" WITH (FORCE)"
            ;;
          *)
            echo "set ACTION=create or ACTION=drop via run-task containerOverrides, along with DB_NAME" >&2
            exit 1
            ;;
        esac
        EOT
      ]
      secrets = [
        { name = "DB_HOST", valueFrom = "${var.master_credentials_secret_arn}:host::" },
        { name = "DB_PORT", valueFrom = "${var.master_credentials_secret_arn}:port::" },
        { name = "DB_USER", valueFrom = "${var.master_credentials_secret_arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${var.master_credentials_secret_arn}:password::" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.db_admin.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "db-admin"
        }
      }
    }
  ])
}

data "aws_region" "current" {}
