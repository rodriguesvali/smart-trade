# Project MCP Servers

Status: configured for project-local Codex usage.

Configuration file: `.codex/config.toml`

## Servers

- `context7`: current documentation for backend and frontend technologies.
- `primeng`: PrimeNG-specific component, theme, layout, and API documentation.

## Usage Rules

- `backend-eng` must use `context7` before backend implementation or backend code changes.
- `frontend-eng` must use `context7` before Angular or adjacent frontend implementation/code changes.
- `frontend-eng` must use `primeng` for PrimeNG-specific work.

## Secrets

Do not commit MCP credentials.

If Context7 authentication is required in the local environment, export `CONTEXT7_API_KEY` outside the repository before starting Codex.
