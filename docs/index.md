# Introduction

[Diamond](https://diamondhpc.ai/) is a web platform for training, fine-tuning, and serving machine learning models on High-Performance Computing (HPC) infrastructure. It provides a user-friendly interface for submitting jobs to clusters, monitoring their progress, and managing resources — all without writing batch scripts by hand.

## Project Overview

Key components of Diamond:

- **Diamond Web UI**: A web interface that allows users to authenticate, submit jobs, monitor their progress, and manage resources.
- **Diamond API**: A RESTful API that powers the Web UI for job submission, monitoring, and resource management.
- **Globus Compute**: A distributed Function as a Service (FaaS) platform that enables reliable, scalable, and high performance remote function execution.
- **Globus Auth**: A web service that allows users to authenticate and authorize access to resources.
- **Globus Transfer**: A web service that allows users to transfer files to and from remote servers.

## Project Infrastructure

- **Diamond API**: A gunicorn server hosted on AWS.
- **Diamond Web UI**: A NextJS application hosted on AWS.
- **Data**: Data is stored in a [PostgreSQL](https://www.postgresql.org/) database hosted on AWS RDS.
- **Services**:
    - Jobs are executed on [Globus Compute](https://www.globus.org/globus-compute).
    - Files are transferred using [Globus Transfer](https://www.globus.org/globus-transfer).
    - Authentication is handled by [Globus Auth](https://www.globus.org/globus-auth).

---

# User Guide

This section gets you started with Diamond as a user: sign in, connect a cluster, prepare data, and launch your first workload.

## Sign In

1. Open the Diamond website.
2. Click **Sign in** — you are redirected to [Globus Auth](https://www.globus.org/globus-auth).
3. Authenticate with your institutional credentials (for example, your university login) and approve the consent screen.

Diamond requests the Globus scopes it needs (profile, email, transfer, and any registered flow scopes) automatically. 
## The Workspace

After signing in you land in the workspace, which is organized into pages:

| Page | What you do there |
| ---- | ----------------- |
| **Dashboard** | Overview of your account activity and resource usage. |
| **Endpoints** | Connect and manage HPC clusters, pick partitions, and set your Diamond working directory. |
| **Datasets** | Register and manage datasets used for training. |
| **Tasks** | Submit, monitor, and inspect jobs; chat with served models. |
| **Images** | Browse available container images and build new ones. |
| **Profile** | View your account details and sign out. |

## Connect an HPC Endpoint

Before running anything, connect a cluster (for example [Delta@NCSA](https://delta.ncsa.illinois.edu/)):

1. Go to **Endpoints**. A short onboarding walkthrough highlights the key controls the first time.
2. Find your cluster under available endpoints and add it as a managed endpoint. For NCSA Delta, use the **NCSA Delta MEP** — the shared multi-user Globus Compute endpoint — so you don't need to deploy and run your own endpoint on the cluster.
3. In the endpoint settings, update the endpoint config with your **account** (your Slurm allocation, for example `bcrc-delta-cpu`) and **partition** (for example `cpu-interactive`). 
4. Set the Diamond working directory — the directory on the cluster where datasets are staged, tasks run, and outputs are written.

## Manage Datasets

Go to **Datasets** to register a dataset for training jobs. A dataset entry points at data on the cluster (or transferred there via Globus) and is referenced by fine-tuning tasks. The page also shows per-dataset statistics.

## Run a Task

Go to **Tasks** and click **Submit Task**. Choose a template; each one is a guided form with sensible defaults for the target cluster:

| Template | Category | Description |
| -------- | -------- | ----------- |
| **DeepSpeed Finetuning** | Fine-tuning | Fine-tune a model using DeepSpeed on a dataset. |
| **SAM3 Finetuning** | Fine-tuning | Fine-tune SAM3 for image segmentation on a labeled dataset. |
| **SAM3 Image Segmentation** | Inference | Run SAM3 (base or fine-tuned) to segment an image. |
| **AlphaFold Structure Prediction** | Inference | Predict a protein structure or complex with AlphaFold2 (ColabFold); inspect the 3D model, pLDDT and PAE in the viewer. |
| **Launch vLLM Chat Service** | Inference | Launch an OpenAI-compatible vLLM service on a compute node for interactive chat. |

A typical fine-tuning workflow:

1. Select the **DeepSpeed Finetuning** template.
2. Pick the endpoint, dataset, and base container image.
3. Set resources (nodes, walltime, GPUs) — defaults are provided.
4. Submit. The task appears in the task list with live status.
5. Open the task to follow its log, view output files, and download artifacts.

You can also launch your own tasks without a template. Clear the template selection (or just leave it unset) and fill in the form directly:

1. If the workload needs your own software stack, build a container image for it first on the **Images** page (see [Manage Container Images](#manage-container-images)); otherwise pick one of the available images.
2. Select your image from the container dropdown — images available on the chosen endpoint are listed automatically.
3. Enter the task command to run inside the container, and set resources and Slurm options as needed.
4. Submit and monitor it like any other task.

Notes:

- Files you upload through a task form (for example a FASTA/A3M for AlphaFold) are limited to 5 MB each and are staged on the cluster before the job starts.
- Larger data should be placed on the cluster directly (or registered as a dataset) and referenced by path.

## Chat with a Served Model

After launching the **Launch vLLM Chat Service** template, open the task to get an interactive chat interface backed by the vLLM endpoint running on your compute node. The service is OpenAI-compatible, so it can also be used from your own tools.

## Manage Container Images

Go to **Images** to browse the container images available on your endpoints and to build new ones with the image builder. When a build is in progress you can stream its build log from the same page.

---

# Technical Documentation

This section describes how Diamond is built and how to run and develop it.

## Architecture

```
Browser ── Next.js Web UI (port 3000) ── /api rewrite ── Flask API (port 5328, gunicorn)
                                                        ├── SQLAlchemy ── SQLite / PostgreSQL
                                                        ├── Globus Auth (login, tokens)
                                                        ├── Globus Compute (job execution on HPC)
                                                        └── Globus Transfer (file staging)
```

- The **Web UI** (Next.js App Router, React, TypeScript, Tailwind CSS) proxies `/api/:path*` requests to the backend via `FLASK_URL`.
- The **API** is a Flask application served by gunicorn. It authenticates users with Globus Auth tokens, stores state in a relational database, and dispatches jobs to clusters through Globus Compute. Job scripts are rendered from templates and submitted to Slurm on the remote endpoint; file staging uses Globus Transfer.
- The **database** holds accounts, datasets, endpoints, containers, tasks, functions, and flows. Schema migrations are managed with Alembic (via Flask-Migrate).

## Repository Layout

```
diamond/
├── backend/          # Flask API (Python 3.11, uv, gunicorn, SQLAlchemy)
│   ├── diamond_backend/
│   │   ├── app/      # routes: base, tasks, datasets, endpoints, containers, transfers, profiles
│   │   │   ├── database/   # SQLAlchemy models + migrations
│   │   │   └── utils/      # auth decorators, script rendering, Globus helpers
│   │   └── wsgi.py / run.py / gunicorn.conf.py
│   ├── migrations/   # Alembic migration scripts
│   └── tests/
├── frontend/         # Next.js App Router web UI (React, TypeScript, Tailwind, pnpm)
│   └── src/
│       ├── app/(workspace)/   # dashboard, tasks, datasets, endpoints, images, profile
│       ├── components/        # shared UI, onboarding, landing, layout
│       └── lib/
├── terraform/        # AWS staging infrastructure
├── docker-compose.yml
└── docs/             # this documentation site
```

## Backend

- **Stack**: Python 3.11, Flask, gunicorn, SQLAlchemy, Alembic, Globus SDKs; dependencies managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`).
- **Run (dev)**: `uv run flask --app diamond_backend.run:app run --debug` — serves on `http://localhost:5328`.
- **Run (prod)**: `uv run gunicorn diamond_backend.wsgi:app`, configured through `GUNICORN_CMD_ARGS`.
- **Configuration**: copy `backend/.env.example` to `backend/.env` and set `SECRET_KEY`, Globus credentials (`PORTAL_CLIENT_ID`, `PORTAL_CLIENT_SECRET`), and `SQLALCHEMY_DATABASE_URI` (SQLite locally, PostgreSQL in production).
- **Migrations**:
  ```bash
  uv run flask --app diamond_backend.run:app db upgrade    # apply pending migrations
  uv run flask --app diamond_backend.run:app db migrate -m "describe the change"
  uv run flask --app diamond_backend.run:app db downgrade  # roll back one migration
  ```

## Frontend

- **Stack**: Next.js (App Router), React, TypeScript, Tailwind CSS; Node.js pinned in `.nvmrc`, pnpm pinned in `package.json`.
- **Run (dev)**:
  ```bash
  cd frontend
  nvm install && nvm use
  corepack enable && corepack prepare pnpm@12.3.4 --activate
  pnpm install --frozen-lockfile
  cp .env.example .env    # set FLASK_URL and Globus client config
  pnpm dev                # http://localhost:3000
  ```
- **Key environment variables**: `FLASK_URL` (backend base URL), `NEXT_PUBLIC_GLOBUS_CLIENT_ID`, `NEXT_PUBLIC_GLOBUS_SCOPES`, `GLOBUS_CLIENT_SECRET`. `NEXT_PUBLIC_*` values are baked into the browser bundle, so rebuild after changing them.

## REST API Overview

All routes are prefixed with `/api`. Authentication uses Globus tokens checked by the `@authenticated` decorator.

| Group | Representative routes | Purpose |
| ----- | --------------------- | ------- |
| Base | `GET /api/healthcheck`, `GET /api/is_authenticated`, `GET /api/stats`, `GET /api/globus_login_scopes` | Service health, auth state, usage stats, dynamic login scopes. |
| Tasks | `POST /api/submit_task`, `GET /api/get_task_status`, `GET /api/get_task_log`, `GET /api/task_output_files`, `POST /api/delete_task`, `POST /api/vllm_chat` | Submit and manage jobs, read logs and output artifacts, chat with a vLLM service. |
| Datasets | `GET/POST /api/datasets` | List and register datasets. |
| Endpoints | `GET /api/list_all_endpoints`, `PUT /api/manage_endpoint/<uuid>`, `POST /api/list_partitions`, `POST /api/set_diamond_work_path` | Discover clusters, manage endpoints, choose partitions, set the working directory. |
| Images | `POST /api/image_builder`, `GET /api/get_build_log`, `GET /api/get_all_containers` | Build container images and list/publish/delete them. |
| Transfers | `GET/POST /api/transfers` | List and start Globus transfer tasks (labelled `Diamond:*`). |
| Profile | `GET/POST /api/profile` | Read and update the user profile. |

## Deployment

There are three modes for deployment and testing:

1. **Independent launch** — run the backend and frontend separately on your machine (see Backend and Frontend above). Ideal for local development.
2. **Docker Compose** — both services from the root `docker-compose.yml`; suitable for debugging deployment issues:
   ```bash
   cp backend/.env.example backend/.env    # fill in credentials + database URI
   cp frontend/.env.example frontend/.env  # fill in Globus client config
   docker compose build
   docker compose up                        # frontend :3000, backend :5328
   ```
   Profiles: default (database URI supplied via `backend/.env`), `--profile postgres` (adds a PostgreSQL container), and `--profile sqlite` (adds a sqlite3 CLI sidecar sharing `/data` with the backend). Note that `NEXT_PUBLIC_*` values must be present at frontend build time.
3. **AWS staging** — infrastructure defined in `terraform/`.

## Testing and CI

- **Backend** (via `tox`): `uv run tox -e py311` (tests), `-e lint`, `-e type`, `-e format`, or `uv run tox` for everything.
- **Frontend**: `pnpm lint`, `pnpm build`, `pnpm typecheck`, and `pnpm test` (Playwright UI regression tests with mocked auth and API).
- **Git hooks**: installing frontend dependencies sets the shared pre-commit hook, which runs frontend typecheck and UI tests when frontend files are staged (`SKIP_PRECOMMIT=1` to skip).
- **CI workflows** (`.github/workflows/`): `backend-ci.yml`, `frontend-ui-regression.yml`, `build-and-push.yml` (container images), and `health-check.yml`.
