# B1 Backend - Core Domain, Persistence, and API Contracts

Status: Draft for Agentic Architect review  
Persona: @backend.eng  
Date: 2026-06-14  
Source artifacts: `project-context/1.define/prd.md`, `project-context/1.define/sad.md`, `project-context/2.build/build-plan.md`, `project-context/2.build/setup.md`

## 1. Scope Completed

B1 established the first backend domain, persistence, and frontend API contracts without implementing training, plugin loading, inference, exchange access, or trading execution.

Implemented:

- Domain enums and dataclasses for asset configuration, strategy registration, model registry entries, command requests, and operational events.
- SQLAlchemy persistence adapter models for MVP traceability areas:
  - asset configurations;
  - strategy registry;
  - selected strategies;
  - model registry;
  - strategy decisions;
  - positions;
  - orders;
  - fills;
  - equity snapshots;
  - command requests;
  - operational events.
- Alembic initial migration: `20260614_0001_b1_core_schema.py`.
- FastAPI `/api/*` read contracts for the Angular frontend.
- Persisted command request endpoint for auditable operator commands.
- Angular shell updated to consume B1 read contracts through the backend API.

## 2. Documentation Consulted

Context7 was consulted before backend implementation:

- FastAPI `/fastapi/fastapi`: lifespan, `APIRouter`, response models, SQLAlchemy session dependency pattern.
- SQLAlchemy `/websites/sqlalchemy_en_20`: SQLAlchemy 2.0 declarative ORM, `DeclarativeBase`, `Mapped`, `mapped_column`, relationships/typed mappings.
- Alembic `/websites/alembic_sqlalchemy`: migration context, target metadata, schema creation patterns.

PrimeNG MCP was consulted before the Angular shell adjustment:

- PrimeNG guide list, confirming current PrimeNG v21 documentation set and component guidance availability.

## 3. Backend Structure

New backend packages:

- `smart_trade_backend.domain`
  - Pure domain enums and dataclasses.
  - No FastAPI, SQLAlchemy, CCXT, file, or frontend dependency.
- `smart_trade_backend.adapters.persistence`
  - SQLAlchemy ORM records and schema mapping.
- `smart_trade_backend.application`
  - Read-model aggregation and command request application service.
- `smart_trade_backend.api`
  - FastAPI route contracts and Pydantic response/request schemas.

Updated runtime wiring:

- FastAPI app now creates a SQLAlchemy engine and session factory during lifespan startup.
- Alembic env now points to SQLAlchemy metadata for migration support.
- `/api/health` was added so the frontend can use the same `/api` proxy namespace for all backend calls.
- `frontend/proxy.conf.json` no longer strips `/api`, because B1 backend contracts are mounted under `/api/*`.

## 4. API Contracts

Read endpoints:

- `GET /api/health`
- `GET /api/configuration/summary`
- `GET /api/strategies`
- `GET /api/models`
- `GET /api/operation/status`
- `GET /api/events?limit=50`

Command endpoint:

- `POST /api/commands`

B1 enabled command request types:

- `RETRAIN_MODEL`
- `SELECT_STRATEGY`
- `APPROVE_MODEL`

Other command types are persisted as rejected if requested in B1. No command triggers training, approval, strategy selection, paper mode, or live operation yet.

## 5. Operational Status Behavior

With no selected strategy and no approved/active model, the operation status intentionally returns:

- `state`: `NOT_READY`
- blockers:
  - `No selected strategy.`
  - `No approved or active model.`

This matches the approved safety-first design: operation is visible but blocked until later increments implement strategy registration, training, validation, backtest, and manual approval.

## 6. Frontend Contract Use

The Angular shell now reads:

- backend health;
- configuration summary;
- strategy registry summary;
- model registry summary;
- operation status;
- recent operational events.

The frontend still has no direct database, log-file, model artifact, exchange, or secret access.

## 7. Verification

Executed successfully:

```bash
cd backend
uv run pytest
```

Result:

- `4 passed`.
- Warning observed: FastAPI/Starlette TestClient emits a deprecation warning recommending `httpx2`; this does not fail B1.

Executed successfully:

```bash
cd backend
uv run ruff check .
```

Result:

- `All checks passed.`

Executed successfully:

```bash
cd backend
SMART_TRADE_DATABASE_URL=sqlite+pysqlite:////tmp/smart_trade_b1.db uv run alembic upgrade head
```

Result:

- Alembic upgraded to `20260614_0001`.

Executed successfully:

```bash
npm --prefix frontend run build
```

Result:

- Angular production build completed successfully.

Runtime smoke checks executed successfully with a temporary SQLite database:

- `GET http://127.0.0.1:8000/api/configuration/summary`
- `GET http://127.0.0.1:8000/api/operation/status`
- startup migration through Uvicorn on a fresh temporary database, verified with `GET http://127.0.0.1:8001/api/health` and Alembic `current`.
- `GET http://127.0.0.1:4200/api/health`
- `GET http://127.0.0.1:4200/api/configuration/summary`
- `GET http://127.0.0.1:4200/api/operation/status`
- `HEAD http://127.0.0.1:4200/`

## 8. Intentional Non-Scope

B1 did not implement:

- default strategy plugin registration;
- strategy plugin discovery;
- CCXT exchange calls;
- historical data ingestion;
- TA-Lib feature generation;
- XGBoost training;
- model artifact writing/loading;
- model approval workflow behavior;
- inference;
- paper trading;
- live trading;
- real order submission;
- frontend charting or full operational console workflows.

## 9. Next Agent Handoffs

Recommended next step: B2.

`@frontend.eng`:

- Build the minimal operational console on top of B1 contracts.
- Keep the chart wrapper isolated.
- Preserve no-auth MVP constraints and backend-mediated access only.

`@backend.eng`:

- Support frontend contract refinements if B2 exposes missing read-model needs.
- Do not implement training/trading behavior until B3/B4/B5 sequencing reaches those areas.

`@qa.eng`:

- Validate B1 API response shape, empty-state behavior, command request auditability, and absence of frontend direct access to restricted resources.
