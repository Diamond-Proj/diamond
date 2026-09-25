# Diamond: Fine-tune and serve models from one workspace.

![Apache Licence V2.0](https://img.shields.io/badge/License-MIT-yellow.svg) [![NSF award info](https://img.shields.io/badge/NSF-1550588-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=2401245) <!-- TODO: add paper badge -->

[Diamond](https://diamondhpc.ai/) is a platform for training, fine-tuning and serving machine learning models
across [NSF](https://www.nsf.gov/)'s [ACCESS-CI](https://access-ci.org/) resources.

## Deployment

There are 3 modes for deployment and testing:
1. Launch the services independently: Ideal from local dev workflows
2. Launch the services with Docker Compose: Suitable for debugging deployment issues
3. TBD: Deploy to a staging env on AWS with terraform.

### Independent Launch

In this mode, the frontend and backend are launched on a local machine
with the majority of the details specified via `.env` files

Find details in [Frontend README](frontend/README.md) and [Backend README](backend/README.md)

## Launch with Docker Compose


Both services are defined in `docker-compose.yml` at the repo root. The backend
requires a populated `backend/.env` (copy from `backend/.env.example` and fill
in your Globus credentials and database URI). The frontend reads
`frontend/.env` for Globus client config; copy from `frontend/.env.example`.

**1. Prepare env files**

```bash
cp backend/.env.example backend/.env   # fill in credentials
cp frontend/.env.example frontend/.env # fill in Globus client ID/secret
```

**2. Build the images**

The frontend image bakes the backend URL at build time, so the build step is
required before the first launch and after any change to `FLASK_URL`.

```bash
docker compose build
```

**3. Launch**

Default (SQLite database):

```bash
# Set SQLALCHEMY_DATABASE_URI=sqlite:////data/diamond.db in backend/.env
docker compose up
```

With a local PostgreSQL container:

```bash
# Set SQLALCHEMY_DATABASE_URI=postgresql://diamond:diamond@db:5432/diamond in backend/.env
docker compose --profile postgres up
```

To inspect the SQLite database interactively:

```bash
docker compose --profile sqlite up -d
docker compose --profile sqlite exec sqlite sh
# inside: sqlite3 diamond.db
```
