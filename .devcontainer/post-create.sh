#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip pipx

if [ -f "backend/requirements-dev.txt" ]; then
  python -m pip install -r backend/requirements-dev.txt
elif [ -f "requirements-dev.txt" ]; then
  python -m pip install -r requirements-dev.txt
fi

if [ -f "frontend/package.json" ]; then
  npm --prefix frontend install
fi

npm --prefix .devcontainer/mcp install

python --version
node --version
npm --version
ng version
