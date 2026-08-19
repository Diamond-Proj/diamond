FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.8.5"

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .

ENV GUNICORN_CMD_ARGS="--workers=2 --threads=4 --worker-class=gthread --bind=0.0.0.0:5328"
EXPOSE 5328

CMD ["uv", "run", "gunicorn", "diamond_backend.wsgi:app"]
