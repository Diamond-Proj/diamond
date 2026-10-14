#!/usr/bin/env bash
# Build + push your branch's images, create its database on the shared dev
# RDS instance, and stand up its ECS services + ALB.
#
# Usage: ./dev-up.sh [branch-name]
#   Defaults to your current git branch, sanitized to a DNS-safe slug.
#
# Prerequisite: someone has already applied terraform/environments/dev once
# (it creates the shared VPC/RDS/cluster/ECR repos this plugs into).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEV_DIR="$SCRIPT_DIR/../environments/dev"
BRANCH_DIR="$SCRIPT_DIR/../environments/dev-branch"
AWS_REGION="${AWS_REGION:-us-east-2}"

RAW_BRANCH="${1:-$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)}"
# lowercase, non-alnum -> hyphen, collapse/trim hyphens, cap at 18 chars
BRANCH=$(echo "$RAW_BRANCH" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g' | cut -c1-18 | sed -E 's/-+$//')
if [ -z "$BRANCH" ]; then
  echo "Couldn't derive a usable slug from branch name '$RAW_BRANCH'" >&2
  exit 1
fi
DB_NAME="branch_${BRANCH//-/_}"

echo "==> Branch slug: $BRANCH  (db: $DB_NAME)"

echo "==> Reading shared dev infra outputs..."
BACKEND_REPO=$(terraform -chdir="$DEV_DIR" output -raw backend_ecr_repository_url)
FRONTEND_REPO=$(terraform -chdir="$DEV_DIR" output -raw frontend_ecr_repository_url)
CLUSTER_NAME=$(terraform -chdir="$DEV_DIR" output -raw ecs_cluster_name)
SUBNET_ID=$(terraform -chdir="$DEV_DIR" output -json private_subnet_ids | python3 -c 'import json,sys; print(json.load(sys.stdin)[0])')
DB_ADMIN_TASK_DEF=$(terraform -chdir="$DEV_DIR" output -raw db_admin_task_definition_arn)
DB_ADMIN_SG=$(terraform -chdir="$DEV_DIR" output -raw db_admin_security_group_id)

# The shared backend/frontend repos are IMMUTABLE, so a tag can only be
# pushed once. Tag with the branch slug plus the commit (same shape as
# build-and-push.yml's <ref>-<sha7>), and skip any image that's already
# been pushed for this commit -- re-running on the same commit is a no-op,
# a new commit gets new tags.
TAG="$BRANCH-$(git -C "$REPO_ROOT" rev-parse --short=7 HEAD)"
if [ -n "$(git -C "$REPO_ROOT" status --porcelain -- backend frontend)" ]; then
  echo "WARNING: uncommitted changes under backend/ or frontend/ -- they'll be built into '$TAG' now, but a later run on this commit will skip the build and keep this image." >&2
fi

image_exists() {
  aws ecr describe-images --region "$AWS_REGION" --repository-name "${1##*/}" \
    --image-ids imageTag="$TAG" >/dev/null 2>&1
}

echo "==> Logging in to ECR and building images tagged '$TAG'..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${BACKEND_REPO%%/*}"
if image_exists "$BACKEND_REPO"; then
  echo "    $BACKEND_REPO:$TAG already exists, skipping build"
else
  docker build -t "$BACKEND_REPO:$TAG" "$REPO_ROOT/backend"
  docker push "$BACKEND_REPO:$TAG"
fi
if image_exists "$FRONTEND_REPO"; then
  echo "    $FRONTEND_REPO:$TAG already exists, skipping build"
else
  # FLASK_URL is baked into the frontend at build time (Next.js rewrites), so
  # it has to name this branch's own backend -- dev-branch registers it as
  # "dev-<branch>-backend" in dev's shared diamond.local namespace.
  # NEXT_PUBLIC_GLOBUS_CLIENT_ID is passed through from your environment.
  docker build -t "$FRONTEND_REPO:$TAG" \
    --build-arg FLASK_URL="$FLASK_URL" \
    --build-arg NEXT_PUBLIC_GLOBUS_CLIENT_ID="$NEXT_PUBLIC_GLOBUS_CLIENT_ID" \
    "$REPO_ROOT/frontend"
  docker push "$FRONTEND_REPO:$TAG"
fi

echo "==> Creating database '$DB_NAME' on the shared dev instance (if it doesn't already exist)..."
TASK_ARN=$(aws ecs run-task \
  --region "$AWS_REGION" \
  --cluster "$CLUSTER_NAME" \
  --task-definition "$DB_ADMIN_TASK_DEF" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$DB_ADMIN_SG],assignPublicIp=DISABLED}" \
  --overrides "{\"containerOverrides\":[{\"name\":\"db-admin\",\"environment\":[{\"name\":\"ACTION\",\"value\":\"create\"},{\"name\":\"DB_NAME\",\"value\":\"$DB_NAME\"}]}]}" \
  --query 'tasks[0].taskArn' --output text)
aws ecs wait tasks-stopped --region "$AWS_REGION" --cluster "$CLUSTER_NAME" --tasks "$TASK_ARN"
EXIT_CODE=$(aws ecs describe-tasks --region "$AWS_REGION" --cluster "$CLUSTER_NAME" --tasks "$TASK_ARN" --query 'tasks[0].containers[0].exitCode' --output text)
if [ "$EXIT_CODE" != "0" ]; then
  echo "db-admin create task failed (exit $EXIT_CODE) -- check CloudWatch log group $(terraform -chdir="$DEV_DIR" output -raw db_admin_log_group_name)" >&2
  exit 1
fi

echo "==> Applying terraform/environments/dev-branch (workspace: $BRANCH)..."
terraform -chdir="$BRANCH_DIR" init -input=false
terraform -chdir="$BRANCH_DIR" workspace select "$BRANCH" 2>/dev/null || terraform -chdir="$BRANCH_DIR" workspace new "$BRANCH"
terraform -chdir="$BRANCH_DIR" apply -input=false \
  -var="branch_name=$BRANCH" \
  -var="backend_image=$BACKEND_REPO:$TAG" \
  -var="frontend_image=$FRONTEND_REPO:$TAG"

echo "==> Done. URL:"
terraform -chdir="$BRANCH_DIR" output -raw alb_dns_name
echo
