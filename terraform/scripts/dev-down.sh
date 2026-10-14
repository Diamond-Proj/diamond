#!/usr/bin/env bash
# Tear down a branch environment created by dev-up.sh: destroys its ECS
# services/ALB and removes the terraform workspace so the slug is free for
# the next person. The shared dev database is left alone.
#
# Usage: ./dev-down.sh [branch-name]
#   Defaults to your current git branch, using the same sanitization as
#   dev-up.sh -- pass the same argument you used there.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BRANCH_DIR="$SCRIPT_DIR/../environments/dev-branch"
AWS_REGION="${AWS_REGION:-us-east-2}"

RAW_BRANCH="${1:-$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)}"
BRANCH=$(echo "$RAW_BRANCH" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g' | cut -c1-18 | sed -E 's/-+$//')

echo "==> Tearing down branch: $BRANCH"

terraform -chdir="$BRANCH_DIR" init -input=false
if ! terraform -chdir="$BRANCH_DIR" workspace select "$BRANCH" 2>/dev/null; then
  echo "No workspace named '$BRANCH' -- nothing to tear down." >&2
  exit 0
fi

# Grab the current images so `terraform destroy` has valid required vars
# (their values don't matter for a destroy, just that they're set).
# GitHub Actions sets CI=true; nobody's there to answer the prompt.
terraform -chdir="$BRANCH_DIR" destroy -input=false ${CI:+-auto-approve} \
  -var="branch_name=$BRANCH" \
  -var="backend_image=unused" \
  -var="frontend_image=unused" \
  -var="db_url=unused"

terraform -chdir="$BRANCH_DIR" workspace select default
terraform -chdir="$BRANCH_DIR" workspace delete "$BRANCH"

echo "==> Done."
