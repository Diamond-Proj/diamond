# Diamond infrastructure

```
terraform/
  bootstrap/        one-time: S3 state bucket (locking is S3-native, no DynamoDB)
  modules/          reusable building blocks (network, registry, database, cluster, db_admin, app)
  environments/
    prod/           own VPC, own RDS, own ECS cluster/ALB
    staging/        same as prod, smaller/cheaper
    dev/            own VPC/RDS/ECS cluster (shared by all branch envs) + a persistent "main" deploy
    dev-branch/     ephemeral -- one Terraform workspace per developer branch, plugged into dev's shared infra
  scripts/
    dev-up.sh       build+push your branch's images, create its DB, deploy it
    dev-down.sh     tear a branch environment down and drop its DB
```

State lives in the shared S3 bucket created by `bootstrap/`, one object per environment (workspaces get their own key automatically). Locking uses S3's native conditional-write locking (`use_lockfile`, requires Terraform >= 1.11) -- no DynamoDB table needed. This lets any machine (including CI) safely run `apply`/`destroy` against a given environment.

## One-time setup

```bash
cd bootstrap
terraform init
terraform apply -var="state_bucket_name=<something-globally-unique>"
```

Then apply `prod`, `staging`, and `dev` each once (see their `terraform.tfvars.example`):

```bash
cd environments/dev
terraform init
terraform apply
```

`dev` must exist before any branch environment can be created -- `dev-branch` reads its VPC/RDS/cluster/ECR details via `terraform_remote_state`.

## Day-to-day: testing a branch

```bash
./scripts/dev-up.sh              # uses your current git branch
./scripts/dev-up.sh some-branch  # or name one explicitly
```

This builds and pushes your branch's images to the shared dev ECR repos (tagged with the branch slug), creates a dedicated Postgres database for it on the shared dev RDS instance, and stands up its own ECS services + ALB. It prints a URL when done.

When you're finished:

```bash
./scripts/dev-down.sh
```

This destroys that branch's ECS services/ALB and drops its database, freeing the slug for the next person.

## Design notes

- **Isolation**: branch environments share the dev VPC and RDS *instance*, but each gets its own datbase and its own ECS services/ALB. This keeps spin-up to ~1-2 minutes (no VPC/RDS provisioning) at the cost of sharing one Postgres engine across everyone's branches.
- **Branch DB credentials**: branch databases are accessed with the shared instance's master user, scoped only by database name -- not a dedicated role per branch. Fine for throwaway test data; revisit before this holds anything sensitive.
- **prod/staging remain fully isolated** (own VPC, own RDS instance) -- only `dev`/`dev-branch` share infrastructure.

## CI/CD

Three workflows in `../.github/workflows/`, one trigger per environment:

| Environment | Trigger | What runs |
| --- | --- | --- |
| `prod` | push a tag matching `vMAJOR.MINOR.PATCH` (e.g. `v1.4.2`) | [`deploy-prod.yml`](../.github/workflows/deploy-prod.yml) rejects anything that isn't a plain release (no `-rc1`/`-alpha` etc.), then always rebuilds+pushes both images tagged with the release version and applies `environments/prod` |
| `staging` | push to `main` | [`deploy-staging.yml`](../.github/workflows/deploy-staging.yml) rebuilds+pushes only the image(s) whose path (`backend/**`/`frontend/**`) changed, tagged with the commit SHA; the other container keeps whatever's already applied. Skips entirely if the push touched neither app code nor `terraform/**` |
| `dev` (a branch) | manual -- [`deploy-dev-branch.yml`](../.github/workflows/deploy-dev-branch.yml) via `workflow_dispatch` | thin wrapper around `scripts/dev-up.sh`, same as running it locally. [`teardown-dev-branch.yml`](../.github/workflows/teardown-dev-branch.yml) wraps `scripts/dev-down.sh` the same way |

The persistent "main" deploy in `dev` itself (as opposed to per-branch environments) isn't wired to any of these -- it's still applied by hand as covered under one-time setup above.

**Required repo secrets**: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` for an IAM user with permission to push to ECR and manage the VPC/RDS/ECS/ALB/Secrets Manager resources each environment's `terraform apply` touches. Consider scoping `prod`'s deploy job behind a GitHub Environment protection rule (required reviewers) given it runs unattended off a tag push.