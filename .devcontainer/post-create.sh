#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip pipx

if [ -f "backend/requirements-dev.txt" ]; then
  python -m pip install -r backend/requirements-dev.txt
elif [ -f "requirements-dev.txt" ]; then
  python -m pip install -r requirements-dev.txt
fi

if [ -f "frontend/package-lock.json" ]; then
  npm --prefix frontend ci
elif [ -f "frontend/package.json" ]; then
  npm --prefix frontend install
fi

MCP_RUNTIME_DIR=".devcontainer/mcp"
if [ -f "${MCP_RUNTIME_DIR}/package-lock.json" ]; then
  npm --prefix "${MCP_RUNTIME_DIR}" ci
else
  npm --prefix "${MCP_RUNTIME_DIR}" install
fi

python --version
node --version
npm --version
ng version
