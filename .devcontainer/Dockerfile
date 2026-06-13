# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS node

FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

ARG ANGULAR_CLI_VERSION=21.2.15

COPY --from=node /usr/local /usr/local

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIPX_HOME=/usr/local/py-utils/pipx \
    PIPX_BIN_DIR=/usr/local/py-utils/bin

RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        default-mysql-client \
        git \
        pkg-config \
    && npm install -g @angular/cli@${ANGULAR_CLI_VERSION} \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER root
