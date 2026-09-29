# One-time setup, run by whoever actually has IAM permissions (day-to-day
# applies of dev/staging/prod/bootstrap-data run as a user with a much more
# restricted, resource-scoped IAM policy -- see below). Creates the two ECS
# roles every environment's app/db_admin tasks share:
#
#   - ecsTaskExecutionRole: pulls images from ECR, writes CloudWatch logs
#     (via the AWS-managed AmazonECSTaskExecutionRolePolicy), and reads any
#     Secrets Manager secret named "diamond-*" (via the standalone
#     DiamondReadSecrets policy below).
#   - ecsTaskRole: the task role containers themselves assume. No
#     permissions yet (nothing currently calls AWS APIs from inside a
#     container) -- exists so modules/app has something to attach to.
#
# Naming matters here: the day-to-day deploying user's IAM policy scopes
# every action (CreateRole, GetRole, AttachRolePolicy, PassRole, ...) to
# `role/ecsTask*`. These names were picked to match that constraint --
# rename them and that user's GetRole/PassRole calls will start failing
# again, same as when they were "diamond-ecs-execution"/"diamond-ecs-task".
#
# DiamondReadSecrets is deliberately a standalone customer-managed policy
# rather than an inline one: that user's policy can only ever attach a
# pre-approved managed policy by ARN (no iam:PutRolePolicy at all), so if
# this policy's ARN is ever added to their AttachApprovedPoliciesOnly
# allowlist, they can fully self-serve these roles without needing this
# module re-run by an admin again.
#
# Since the permissions needed are identical for every environment (there's
# nothing environment-specific about "read a diamond-* secret"), one shared
# pair of roles covers dev/staging/prod and the db_admin one-off task alike.
# modules/app and modules/db_admin look these up by name via `data
# "aws_iam_role"` rather than creating their own.
#
#   cd terraform/bootstrap-iam
#   terraform init
#   terraform apply

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = "ecsTaskExecutionRole"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "read_diamond_secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = ["arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:diamond-*"]
  }
}

resource "aws_iam_policy" "read_diamond_secrets" {
  name   = "DiamondReadSecrets"
  policy = data.aws_iam_policy_document.read_diamond_secrets.json
}

resource "aws_iam_role_policy_attachment" "ecs_execution_read_secrets" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = aws_iam_policy.read_diamond_secrets.arn
}

resource "aws_iam_role" "ecs_task" {
  name               = "ecsTaskRole"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}
