# B0 Setup - Project Bootstrap and Runtime Skeleton

Status: Draft for Agentic Architect review  
Persona: @project.mgr  
Date: 2026-06-14  
Source artifacts: `project-context/1.define/prd.md`, `project-context/1.define/sad.md`, `project-context/2.build/build-plan.md`

## 1. Scope Completed

B0 created the runnable project foundation without trading, training, strategy, exchange, or dashboard business logic.

Created/updated:

- Backend Python workspace under `backend/`.
- Frontend Angular workspace under `frontend/`.
- Root `.env.example`.
- Backend `.env.example`.
- Root `compose.yaml`.
- Backend and frontend Dockerfile skeletons.
- Devcontainer updated to Python 3.14 and `uv`.
- Minimal FastAPI health endpoints.
- Alembic startup migration wiring.
- Minimal Angular + PrimeNG shell.
- Frontend proxy from `/api` to backend `http://localhost:8000`.

## 2. Backend Setup

Backend decisions implemented:

- Python: 3.14.
- Dependency manager: `uv`.
- API framework selected for B0: FastAPI.
- Server: Uvicorn.
- Database access skeleton: SQLAlchemy + PyMySQL.
- Migrations: Alembic.
- Settings: `pydantic-settings`.

Important files:

- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/src/smart_trade_backend/main.py`
- `backend/src/smart_trade_backend/config.py`
- `backend/src/smart_trade_backend/db.py`
- `backend/src/smart_trade_backend/migrations.py`
- `backend/alembic.ini`
- `backend/migrations/`
- `backend/tests/test_health.py`

Backend commands:

```bash
cd backend
uv sync
uv run pytest
uv run uvicorn smart_trade_backend.main:app --host 0.0.0.0 --port 8000
```

Runtime behavior:

- `GET /health` reports API health without checking MySQL.
- `GET /health/db` checks MySQL connectivity.
- Alembic migrations run during FastAPI startup by default.
- Tests set `SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP=false` so health tests do not require MySQL.

## 3. Frontend Setup

Frontend decisions implemented:

- Angular CLI workspace in `frontend/`.
- PrimeNG installed.
- Theme package uses `@primeuix/themes`.
- TradingView Lightweight Charts package installed.
- `@angular/animations` is not a direct dependency and is not used in code.
- Angular animation providers/modules are intentionally absent because `@angular/animations` is deprecated in current Angular documentation.
- The Angular app uses a minimal operational shell only.

Important files:

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/angular.json`
- `frontend/proxy.conf.json`
- `frontend/src/app/app.config.ts`
- `frontend/src/app/app.ts`
- `frontend/src/app/app.html`
- `frontend/src/app/app.scss`
- `frontend/src/styles.scss`

Frontend commands:

```bash
cd frontend
npm install
npm start
npm run build
```

The development server proxies `/api/*` to `http://localhost:8000/*`.

## 4. Local Environment

Root `.env.example` documents local-only environment values:

- `SMART_TRADE_ENVIRONMENT`
- `SMART_TRADE_DATABASE_URL`
- `SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP`
- `SMART_TRADE_EXCHANGE`
- `SMART_TRADE_SYMBOL`
- `SMART_TRADE_TIMEFRAME`
- `SMART_TRADE_INITIAL_CAPITAL_USD`
- `SMART_TRADE_MODE`
- `BYBIT_API_KEY`
- `BYBIT_API_SECRET`
- `SMART_TRADE_MODEL_ARTIFACT_DIR`
- `SMART_TRADE_LOG_DIR`

No real credentials were added.

## 5. Containers

Root `compose.yaml` defines:

- `backend`: FastAPI container.
- `frontend`: Angular production build served through nginx.
- `mysql`: MySQL 8.4.

The existing devcontainer was also updated:

- Python 3.14 devcontainer image.
- Node.js 22.
- Angular CLI 21.
- `uv` copied from the official Astral image.
- MySQL 8.4 service remains in `.devcontainer/docker-compose.yml`.

## 6. Verification

Executed successfully:

```bash
npm --prefix frontend run build
```

Result:

- Angular production build completed successfully.
- Output: `frontend/dist/smart-trade-frontend`.

Executed successfully:

```bash
cd backend
uv run pytest
```

Result:

- `1 passed`.
- Python used by `uv`: CPython 3.14.6.
- Warning observed: FastAPI/Starlette TestClient currently emits a deprecation warning recommending `httpx2`; this does not fail B0.

Executed successfully:

```bash
cd backend
uv run ruff check .
```

Result:

- `All checks passed`.

Dependency checks:

```bash
npm --prefix frontend audit --omit=dev
```

Result:

- `found 0 vulnerabilities`.

Known dev dependency audit issue:

```bash
npm --prefix frontend audit
```

Result:

- 4 high severity advisories reported through Angular build tooling dependencies (`esbuild`/`vite` path).
- npm reported no fix available at the time of this B0 setup.
- This affects development/build dependencies, not production runtime dependencies under `--omit=dev`.

Angular animations check:

```bash
npm --prefix frontend ls @angular/animations
rg -n "@angular/animations|provideAnimations|BrowserAnimationsModule|NoopAnimationsModule" frontend/package.json frontend/src frontend/.npmrc
```

Result:

- `(empty)` with exit code 1 from `npm ls`, which is npm's normal result when the package is absent.
- No active frontend source/package references were found by `rg`.

Note:

- `@angular/animations` still appears in `package-lock.json` as optional peer metadata from Angular packages, but it is not installed, not imported, and not configured in application code.
- `frontend/.npmrc` sets `omit=peer` so `npm ci` does not install optional peer packages such as `@angular/animations`.

Local runtime smoke checks:

```bash
cd backend
SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP=false uv run uvicorn smart_trade_backend.main:app --host 0.0.0.0 --port 8000
```

Result:

- FastAPI started successfully on `http://localhost:8000`.
- `GET /health` returned `{"status":"ok","service":"Smart Trade API","environment":"development"}`.

```bash
npm --prefix frontend start -- --host 0.0.0.0 --port 4200
```

Result:

- Angular development server started successfully on `http://localhost:4200`.
- `HEAD /` returned HTTP 200.
- `GET /api/health` through the Angular proxy returned the backend health payload.

Docker validation:

```bash
docker compose config
```

Result:

- Not executed successfully in this workspace because Docker CLI is not installed (`docker: command not found`).
- `compose.yaml`, `backend/Dockerfile`, and `frontend/Dockerfile` were created as skeletons and should be validated in a Docker-enabled environment.

## 7. Intentional Non-Scope

B0 did not implement:

- CCXT calls.
- Bybit API integration.
- Candle ingestion.
- TA-Lib feature generation.
- XGBoost training.
- Strategy plugin discovery beyond setup documentation.
- Model registry behavior.
- Trading loop.
- Paper execution.
- Live execution.
- Operational dashboard behavior beyond a minimal shell.

## 8. Next Agent Handoffs

Recommended next step: B1.

`@backend.eng`:

- Define core domain boundaries and persistence models.
- Create first real Alembic schema migration.
- Implement read-model API contracts for configuration, strategy registry, model registry, operation status, and logs/events.

`@frontend.eng`:

- Replace placeholder shell sections with API-backed read views from B1 contracts.
- Keep PrimeNG layout and no-auth MVP constraint.
- Keep chart wrapper isolated.

`@qa.eng`:

- Add startup smoke checks for backend/frontend/MySQL.
- Validate migration startup behavior.
- Validate frontend has no direct DB/artifact/log/exchange/secret access.

`@project.mgr`:

- Resolve frontend package manager if npm is not the desired final choice.
- Expand local setup documentation only if Agentic Architect requests it.

## 9. Open B0 Questions

- Should npm remain the frontend package manager for the MVP, or should the project switch to pnpm before B1?
- Should the root `compose.yaml` be treated as the canonical local runtime, or should `.devcontainer/docker-compose.yml` remain the primary local runtime during development?

## 10. Audit

- Generated by: @project.mgr
- Action: Completed B0 project bootstrap and runtime skeleton.
- Date: 2026-06-14
- Review status: Pending Agentic Architect review.
- Handoff gate: Do not proceed to B1 until the Agentic Architect approves or requests changes to B0.
