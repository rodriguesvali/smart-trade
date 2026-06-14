# syntax=docker/dockerfile:1

FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        default-mysql-client \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml ./
COPY uv.lock ./
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src

RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "smart_trade_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
