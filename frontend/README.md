# Diamond Frontend

The web interface for Diamond, a platform for training, fine-tuning, and serving
machine learning models on HPC resources. It includes Globus sign-in and
workspaces for tasks, datasets, container images, endpoints, and user profiles.

Built with Next.js App Router, React, TypeScript, and Tailwind CSS. This directory
is the frontend of the Diamond monorepo; the Python/Flask API lives in
[`../backend`](../backend/README.md).

## Requirements

- **Node.js 24.21.0 LTS**, pinned in [`.nvmrc`](.nvmrc).
- **pnpm 12.3.4**, pinned in [`package.json`](package.json).
- A configured backend and Globus application credentials for normal application use.
  UI regression tests use mocks and do not require these services.

Frontend dependencies and `pnpm-lock.yaml` are managed in this directory.
Backend Python dependencies are managed separately with uv.

## Quick start

From the repository root:

```bash
cd frontend
```

All subsequent commands run from `frontend/` unless stated otherwise.

With nvm installed, select Node and activate the pinned pnpm version:

```bash
nvm install
nvm use
corepack enable
corepack prepare pnpm@12.3.4 --activate
pnpm install --frozen-lockfile
```

If you use another Node version manager, select the version recorded in `.nvmrc`.

Create the local environment file if it does not already exist:

```bash
cp .env.example .env
```

Fill in the values below, start the backend using its
[setup instructions](../backend/README.md), then start the frontend:

```bash
pnpm dev
```

Open [localhost:3000](http://localhost:3000). The default backend URL is
`http://localhost:5328`.

## Environment variables

Use [`.env.example`](.env.example) as a starting point.

| Variable                       | Purpose                                                                                         |
| ------------------------------ | ----------------------------------------------------------------------------------------------- |
| `FLASK_URL`                    | Backend base URL for the `/api/:path*` rewrite. Use a full URL such as `http://localhost:5328`. |
| `NEXT_PUBLIC_GLOBUS_CLIENT_ID` | Globus application client ID used for sign-in.                                                  |
| `NEXT_PUBLIC_GLOBUS_SCOPES`    | Space-separated Globus scopes required by the application.                                      |
| `GLOBUS_CLIENT_SECRET`         | Server-side credential for token exchange and refresh.                                          |
| `VERCEL_GIT_COMMIT_SHA`        | Optional revision identifier returned by the healthcheck.                                       |

The template also contains `NEXT_PUBLIC_VERCEL_URL` and `DATABASE_URL`; neither is
currently read by the frontend source. Configure the backend database in the
backend environment instead.

Keep credentials in local environment files or your deployment platform's secret
configuration. `NEXT_PUBLIC_*` values are public browser configuration and must be
available when building the frontend. Rebuild after changing these values or
`FLASK_URL`; setting them only when starting an existing image is insufficient.

## Common commands

| Command                 | Purpose                                          |
| ----------------------- | ------------------------------------------------ |
| `pnpm dev`              | Start the development server on port 3000.       |
| `pnpm build`            | Create the production build.                     |
| `pnpm start`            | Serve an existing production build on port 3000. |
| `pnpm lint`             | Run ESLint.                                      |
| `pnpm lint:fix`         | Apply available ESLint fixes.                    |
| `pnpm typecheck`        | Check TypeScript without emitting JavaScript.    |
| `pnpm format`           | Format project files with Prettier.              |
| `pnpm test`             | Run Playwright UI regression tests.              |
| `pnpm test:interactive` | Open Playwright's interactive test UI.           |
| `pnpm test:report`      | Open the saved HTML test report.                 |

## Validation and UI tests

Install the Chromium browser used by Playwright:

```bash
pnpm exec playwright install chromium
```

On Linux machines that also need browser system dependencies, use
`pnpm exec playwright install --with-deps chromium`.

Run the checks before opening a pull request:

```bash
pnpm lint
pnpm build
pnpm typecheck
pnpm test
```

Playwright starts a development server automatically and reuses an existing server
on port 3000 outside CI. Stop your existing server first if you need an isolated
run. UI tests exercise the development server; `pnpm build` validates production
compilation separately.

The test suite uses mocked authentication and backend responses:

- [`tests/public.spec.ts`](tests/public.spec.ts): sign-in and unauthenticated route access.
- [`tests/authenticated/`](tests/authenticated/): authenticated workspace interactions.
- [`tests/auth.setup.ts`](tests/auth.setup.ts): generated mock authentication state.
- [`tests/mocks/mock-api.ts`](tests/mocks/mock-api.ts): backend API mocks.

Generated authentication state is stored in `tests/.auth/user.json` and is
Git-ignored. Test reports are written to `playwright-report/`.

The [frontend CI workflow](../.github/workflows/frontend-ui-regression.yml) runs a
frozen dependency install, lint, production build, typecheck, and UI tests. It
reads Node from `.nvmrc` and pnpm from `package.json`.

### Git hooks

The current `prepare` script sets `core.hooksPath` to `.githooks`, but the existing
hook lives in `frontend/.githooks/` and assumes frontend commands run from the
repository root. This setup has not been adapted to the monorepo. Use the checks
above and CI rather than relying on automatic pre-commit validation.

## Production and Docker

To build and serve the frontend locally:

```bash
pnpm build
pnpm start
```

The [Dockerfile](Dockerfile) uses the same pinned Node and pnpm versions as local
development. Its build context is `frontend/`. See the root
[Compose configuration](../docker-compose.yml) for service and environment settings.

See the [repository README](../README.md#launch-with-docker-compose) for the
multi-service Compose workflow.

**Current Docker limitation:** `.dockerignore` excludes local environment files,
and the Dockerfile does not yet pass public Globus configuration into the build
or consume the `frontend_build_env` secret mentioned in its header comment.
Build-time delivery of the required `NEXT_PUBLIC_*` values needs to be configured
for a working sign-in deployment. Runtime `env_file` configuration alone does not
supply those values to the browser bundle.

## Troubleshooting

- **Wrong Node or pnpm version:** run `nvm use`, then check `node --version` and
  `pnpm --version` against the versions above.
- **API requests fail:** check that the backend is running and `FLASK_URL` is
  reachable from the frontend server. Restart development or rebuild production
  after changing it.
- **Globus sign-in fails:** check client credentials, scopes, and the callback URL
  registered for your environment.
- **Typecheck references a removed page under `.next/`:** stop Next.js, remove the
  generated `.next` directory, then run `pnpm build` and `pnpm typecheck` again.
- **Playwright cannot launch Chromium:** run the browser installation command above
  and check that port 3000 is available.

## License

Copyright (c) 2024 University of Illinois and others. All rights reserved.

This program and the accompanying materials are made available under the terms
of the [Mozilla Public License v2.0](https://www.mozilla.org/en-US/MPL/2.0/).
