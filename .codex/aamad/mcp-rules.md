# MCP Rules

Status: approved by Agentic Architect for backend and frontend engineering.

Project-local MCP configuration: `.codex/config.toml`

Detected/PRD-implied technologies: Python, Angular, PrimeNG, TypeScript, CCXT, XGBoost, TA-Lib or pandas-ta, MySQL, Alembic, Docker.

Suggested MCP servers:
- context7: required for `backend-eng` before backend implementation or backend code changes, to obtain current documentation for relevant libraries, frameworks, and architectural patterns.
- context7: required for `frontend-eng` before Angular or adjacent frontend implementation/code changes, including Angular, TypeScript, RxJS, Angular HTTP, forms, routing, testing, charting, and build tooling.
- primeng: required for `frontend-eng` whenever implementing or changing PrimeNG components, themes, layout, tables, charts, forms, menus, overlays, or PrimeNG component APIs.

Rule: additional MCP-specific rules outside `backend-eng` and `frontend-eng` still require Agentic Architect approval.

Secrets rule: do not commit MCP credentials. If Context7 authentication is required, provide `CONTEXT7_API_KEY` through the local environment.
