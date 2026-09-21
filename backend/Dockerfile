# Backend Dockerfile
# Docker build command : cd diamond/backend && docker build -t diamond_backend:0.1.0 .
# Docker run command : docker run --env-file .env -e FLASK_ENV=production -p 5328:5328 diamond_backend:0.1.0

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV UV_PYTHON=3.13.9 \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY diamond_backend/ diamond_backend/

EXPOSE 5328

ENV GUNICORN_CMD_ARGS="--bind=0.0.0.0:5328"

CMD ["uv", "run", "gunicorn", "diamond_backend.wsgi:app"]

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv python install 3.13.0 \
    && uv sync --no-dev --frozen --no-install-project

COPY diamond_backend/ diamond_backend/
RUN uv sync --no-dev --frozen

EXPOSE 5328

ENV GUNICORN_CMD_ARGS="--bind=0.0.0.0:5328"

CMD ["uv", "run", "gunicorn", "diamond_backend.wsgi:app"]