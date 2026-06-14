#!/usr/bin/env bash
set -euo pipefail

if [ -f "backend/pyproject.toml" ]; then
  uv sync --project backend --all-groups
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
uv --version
node --version
npm --version
ng version
