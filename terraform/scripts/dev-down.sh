#!/usr/bin/env bash
# Tear down a branch environment created by dev-up.sh: destroys its ECS
# services/ALB, drops its database on the shared dev RDS instance, and
# removes the terraform workspace so the slug is free for the next person.
#
# Usage: ./dev-down.sh [branch-name]
#   Defaults to your current git branch, using the same sanitization as
#   dev-up.sh -- pass the same argument you used there.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEV_DIR="$SCRIPT_DIR/../environments/dev"
BRANCH_DIR="$SCRIPT_DIR/../environments/dev-branch"
AWS_REGION="${AWS_REGION:-us-east-2}"

RAW_BRANCH="${1:-$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)}"
BRANCH=$(echo "$RAW_BRANCH" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g' | cut -c1-18 | sed -E 's/-+$//')
DB_NAME="branch_${BRANCH//-/_}"

echo "==> Tearing down branch: $BRANCH  (db: $DB_NAME)"

terraform -chdir="$BRANCH_DIR" init -input=false
if ! terraform -chdir="$BRANCH_DIR" workspace select "$BRANCH" 2>/dev/null; then
  echo "No workspace named '$BRANCH' -- nothing to tear down." >&2
  exit 0
fi

# Grab the current images so `terraform destroy` has valid required vars
# (their values don't matter for a destroy, just that they're set).
terraform -chdir="$BRANCH_DIR" destroy -input=false \
  -var="branch_name=$BRANCH" \
  -var="backend_image=unused" \
  -var="frontend_image=unused"

terraform -chdir="$BRANCH_DIR" workspace select default
terraform -chdir="$BRANCH_DIR" workspace delete "$BRANCH"

echo "==> Dropping database '$DB_NAME' on the shared dev instance..."
CLUSTER_NAME=$(terraform -chdir="$DEV_DIR" output -raw ecs_cluster_name)
SUBNET_ID=$(terraform -chdir="$DEV_DIR" output -json private_subnet_ids | python3 -c 'import json,sys; print(json.load(sys.stdin)[0])')
DB_ADMIN_TASK_DEF=$(terraform -chdir="$DEV_DIR" output -raw db_admin_task_definition_arn)
DB_ADMIN_SG=$(terraform -chdir="$DEV_DIR" output -raw db_admin_security_group_id)

TASK_ARN=$(aws ecs run-task \
  --region "$AWS_REGION" \
  --cluster "$CLUSTER_NAME" \
  --task-definition "$DB_ADMIN_TASK_DEF" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$DB_ADMIN_SG],assignPublicIp=DISABLED}" \
  --overrides "{\"containerOverrides\":[{\"name\":\"db-admin\",\"environment\":[{\"name\":\"ACTION\",\"value\":\"drop\"},{\"name\":\"DB_NAME\",\"value\":\"$DB_NAME\"}]}]}" \
  --query 'tasks[0].taskArn' --output text)
aws ecs wait tasks-stopped --region "$AWS_REGION" --cluster "$CLUSTER_NAME" --tasks "$TASK_ARN"
EXIT_CODE=$(aws ecs describe-tasks --region "$AWS_REGION" --cluster "$CLUSTER_NAME" --tasks "$TASK_ARN" --query 'tasks[0].containers[0].exitCode' --output text)
if [ "$EXIT_CODE" != "0" ]; then
  echo "db-admin drop task failed (exit $EXIT_CODE) -- check CloudWatch log group $(terraform -chdir="$DEV_DIR" output -raw db_admin_log_group_name)" >&2
  exit 1
fi

echo "==> Done."
