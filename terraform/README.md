# Diamond infrastructure

```
terraform/
  bootstrap/        one-time: S3 state bucket (locking is S3-native, no DynamoDB)
  bootstrap-data/    one-time: shared RDS instance + SSH bastion, VPC-peered to dev/staging/prod
  bootstrap-iam/     one-time: shared ECS execution/task roles, applied by whoever actually has IAM permissions
  modules/          reusable building blocks (network, registry, database, cluster, db_admin, app)
  environments/
    prod/           own VPC, own ECS cluster/ALB, uses its own database on the shared RDS instance
    staging/        same as prod, smaller/cheaper
    dev/            own VPC/ECS cluster (shared by all branch envs) + a persistent "main" deploy, uses its own database on the shared RDS instance
    dev-branch/     ephemeral -- one Terraform workspace per developer branch, plugged into dev's shared infra
  scripts/
    dev-up.sh       build+push your branch's images, create its DB, deploy it
    dev-down.sh     tear a branch environment down and drop its DB
```

**RDS is provisioned once, by `bootstrap-data/`, and shared.** A single Postgres instance holds separate `dev`/`staging`/`prod` databases (plus one per active branch environment, same as before). Each environment's `database` module ([`modules/database`](modules/database/main.tf)) just looks up that shared instance, its security group, and its master-credentials secret -- all named `diamond-shared-*` -- plus its own environment-specific connection-string secret (`<name>-database-url`, one per environment). The instance itself lives in a dedicated VPC (`bootstrap-data`), peered to each environment's VPC so their ECS tasks can reach it; an SSH bastion in that same VPC gives admin access to the instance directly.

**IAM roles are provisioned once too, by `bootstrap-iam/`, and shared.** The day-to-day AWS principal running `terraform apply` for dev/staging/prod (and CI) deliberately has no IAM permissions -- `iam:CreateRole` is denied by design, not a gap to fix. Since every environment's ECS execution/task role needs identical permissions (the AWS-managed `AmazonECSTaskExecutionRolePolicy`, plus read access to any `diamond-*` Secrets Manager secret), one shared `diamond-ecs-execution`/`diamond-ecs-task` role pair, created once by someone who *does* have IAM permissions, covers every environment and the `db_admin` one-off task. [`modules/app`](modules/app/ecs.tf) and [`modules/db_admin`](modules/db_admin/main.tf) look these up by name via `data "aws_iam_role"` rather than creating their own.

State lives in the shared S3 bucket created by `bootstrap/`, one object per environment (workspaces get their own key automatically). Locking uses S3's native conditional-write locking (`use_lockfile`, requires Terraform >= 1.11) -- no DynamoDB table needed. This lets any machine (including CI) safely run `apply`/`destroy` against a given environment.

## One-time setup

```bash
cd bootstrap
terraform init
terraform apply -var="state_bucket_name=<something-globally-unique>"
```

Have someone who actually has IAM permissions apply the shared ECS roles -- this only needs to happen once, ever, regardless of how many environments get added later:

```bash
cd bootstrap-iam
terraform init
terraform apply
```

Apply `prod`, `staging`, and `dev` each once (see their `terraform.tfvars.example`) -- this creates their VPCs, which `bootstrap-data` needs to peer against. This will fail on `module.app`/`module.db_admin` if `bootstrap-iam` hasn't been applied yet (they look up its roles by name), so do that first.

```bash
cd environments/dev
terraform init
terraform apply
```

Then set up the shared database and bastion:

```bash
cd bootstrap-data
terraform init
terraform apply -var="master_password=<something>"
```

...and **re-apply `prod`/`staging`/`dev`** so each one picks up its `aws_route` to the new peering connection (this only resolves once `bootstrap-data` has been applied at least once, so it's a required second pass, not optional).

Finally, SSH to the bastion (`terraform -chdir=bootstrap-data output bastion_public_ip`) and, using the master credentials in Secrets Manager (`diamond-shared-db-master-credentials`), run `CREATE DATABASE dev;` / `CREATE DATABASE staging;` / `CREATE DATABASE prod;`, then restore each environment's data into its database however you're migrating it in. Once traffic is confirmed flowing through the new instance, delete whatever RDS instance/bastion you'd created manually before -- `bootstrap-data` fully replaces them.

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
- **prod/staging/dev now share one RDS instance too** (see `bootstrap-data/`), each with its own database but *all three connection strings currently use the instance's own master (`postgres`) user* -- there's no narrower per-environment role. That means a leaked staging or dev secret is a leaked prod credential. Fine to start, but worth revisiting (e.g. per-database roles created by hand, or via the `hashicorp/postgresql` Terraform provider) before this holds anything sensitive in prod.
- **Network isolation is now peering, not separate VPCs**: prod/staging/dev each still have their own VPC, but all three are peered to the shared data VPC so their ECS tasks can reach the one RDS instance. A compromised backend task in any one environment has network-level line of sight to the RDS security group that fronts all three databases (though not to the other environments' VPCs directly -- peering is data-VPC-hub-and-spoke, not mesh).

## CI/CD

Three workflows in `../.github/workflows/`, one trigger per environment:

| Environment | Trigger | What runs |
| --- | --- | --- |
| `prod` | push a tag matching `vMAJOR.MINOR.PATCH` (e.g. `v1.4.2`) | [`deploy-prod.yml`](../.github/workflows/deploy-prod.yml) rejects anything that isn't a plain release (no `-rc1`/`-alpha` etc.), then always rebuilds+pushes both images tagged with the release version and applies `environments/prod` |
| `staging` | push to `main` | [`deploy-staging.yml`](../.github/workflows/deploy-staging.yml) rebuilds+pushes only the image(s) whose path (`backend/**`/`frontend/**`) changed, tagged with the commit SHA; the other container keeps whatever's already applied. Skips entirely if the push touched neither app code nor `terraform/**` |
| `dev` (a branch) | manual -- [`deploy-dev-branch.yml`](../.github/workflows/deploy-dev-branch.yml) via `workflow_dispatch` | thin wrapper around `scripts/dev-up.sh`, same as running it locally. [`teardown-dev-branch.yml`](../.github/workflows/teardown-dev-branch.yml) wraps `scripts/dev-down.sh` the same way |

The persistent "main" deploy in `dev` itself (as opposed to per-branch environments) isn't wired to any of these -- it's still applied by hand as covered under one-time setup above.

**Required repo secrets**: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` for an IAM user with permission to push to ECR and manage the VPC/RDS/ECS/ALB/Secrets Manager resources each environment's `terraform apply` touches. It does **not** need any `iam:*` permissions -- see `bootstrap-iam/` above, the ECS roles it uses are looked up, not created. Consider scoping `prod`'s deploy job behind a GitHub Environment protection rule (required reviewers) given it runs unattended off a tag push.