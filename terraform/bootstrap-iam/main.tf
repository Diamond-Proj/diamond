# One-time setup, run by whoever actually has iam:CreateRole/iam:PutRolePolicy
# (day-to-day applies of dev/staging/prod/bootstrap-data run as a user that
# deliberately does NOT have IAM permissions and never will). Creates the
# two ECS roles every environment's app/db_admin tasks share:
#
#   - diamond-ecs-execution: pulls images from ECR, writes CloudWatch logs
#     (via the AWS-managed AmazonECSTaskExecutionRolePolicy), and reads any
#     Secrets Manager secret named "diamond-*" (every secret this project
#     creates follows that naming convention -- see bootstrap-data).
#   - diamond-ecs-task: the task role containers themselves assume. No
#     permissions yet (nothing currently calls AWS APIs from inside a
#     container) -- exists so modules/app has something to attach to.
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
  name               = "diamond-ecs-execution"
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

resource "aws_iam_role_policy" "ecs_execution_read_secrets" {
  name   = "diamond-read-secrets"
  role   = aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.read_diamond_secrets.json
}

resource "aws_iam_role" "ecs_task" {
  name               = "diamond-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}
