FROM ubuntu:24.04

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