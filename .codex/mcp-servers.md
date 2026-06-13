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

Version note: Context7 is pinned to `@upstash/context7-mcp@2.3.0` because the current host runtime is Node 18. The newer 3.x package requires newer web APIs not available in this host Node runtime.

PrimeNG runtime note: the devcontainer post-create step installs the PrimeNG MCP package into `.devcontainer/mcp`, whose `node_modules/` directory is ignored by Git.
