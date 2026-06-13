# Smart Trade Dev Container

This dev container uses Docker Compose with:

- `app`: Python 3.12 devcontainer image plus Node.js 22 and Angular CLI 21.
- `mysql`: MySQL 8.4 with UTF-8 defaults and a healthcheck.

Open the repository with "Dev Containers: Reopen in Container".

Forwarded ports:

- `4200`: Angular development server.
- `8000`: Python API.
- `3306`: MySQL.

Development database defaults are intentionally local-only:

- Database: `smart_trade`
- User: `smart_trade`
- Password: `smart_trade`
- Root password: `smart_trade_root`

Do not use these credentials outside local development.

