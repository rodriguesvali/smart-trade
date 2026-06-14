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

---

# B4 Backend - Strategy Plugin Contract and Default Strategy

Status: Draft for Agentic Architect review  
Persona: @backend.eng  
Date: 2026-06-14  
Source artifacts: `project-context/1.define/prd.md`, `project-context/1.define/sad.md`, `project-context/2.build/build-plan.md`, `project-context/2.build/backend.md`

## 1. Scope Completed

B4 implemented the code-deployed strategy plugin contract and the default MVP strategy registration/selection path.

Implemented:

- Strategy plugin domain contract with metadata, parameter schema, required features, required model roles, risk rules, config validation, and runtime compatibility checks.
- Code-deployed plugin discovery through `smart_trade_backend.strategies.discover_strategy_plugins`.
- Default MVP strategy plugin:
  - `default_rsi_xgboost_long`;
  - spot-only;
  - long-only;
  - M1/`1m`;
  - RSI/IFR oversold setup;
  - one XGBoost binary model role: `entry_confirmation`.
- Strategy registry application service:
  - idempotent registration/upsert into `strategy_registry`;
  - persisted model-role and required-feature declarations;
  - selected strategy persistence in `selected_strategies`;
  - rejection when config validation or runtime compatibility fails.
- Runtime compatibility requires the B3 feature schema to expose all default strategy features before selection.
- FastAPI strategy endpoints:
  - `GET /api/strategies`;
  - `POST /api/strategies/register`;
  - `POST /api/strategies/select`.
- `SELECT_STRATEGY` command handling now completes or fails auditably instead of only creating a requested command.
- Startup strategy registration is enabled when startup migrations are enabled.

## 2. Documentation Consulted

Context7 was consulted before backend implementation:

- Pydantic `/pydantic/pydantic`: `model_validate`, `Field` constraints, and validation error handling.
- FastAPI `/fastapi/fastapi`: request body schemas, response models, and `HTTPException` patterns.
- SQLAlchemy `/websites/sqlalchemy_en_20`: ORM `select`, `update`, session commit/refresh patterns.

## 3. API Contract Updates

`GET /api/strategies` now returns registered strategy items including:

- `parameter_schema`;
- `required_features`;
- `model_roles`;
- `default_parameters`;
- `compatibility.compatible`;
- `compatibility.reasons`;
- `compatibility.risk_rules`.

`POST /api/strategies/select` requires:

- `strategy_registry_id`;
- optional `parameters`.

Selection fails with HTTP 400 when:

- the strategy is not deployed in code;
- the parameter config is invalid;
- market type, direction, or timeframe is incompatible;
- required B3 features are missing.

## 4. Verification

Executed successfully:

```bash
cd backend
uv run pytest
uv run ruff check .
```

Result:

- `10 passed`.
- Existing FastAPI/Starlette TestClient deprecation warning remains unchanged.
- Ruff returned `All checks passed.`

## 5. Intentional Non-Scope

B4 did not implement:

- XGBoost training;
- model registry approval behavior;
- inference;
- strategy signal execution;
- order submission;
- paper/live operation start;
- frontend strategy parameter editing.

---

# B3 Backend - Historical Data and Feature Pipeline

Status: Draft for Agentic Architect review  
Persona: @backend.eng  
Date: 2026-06-14  
Source artifacts: `project-context/1.define/prd.md`, `project-context/1.define/sad.md`, `project-context/2.build/build-plan.md`, `project-context/2.build/setup.md`, `project-context/2.build/backend.md`, `project-context/2.build/frontend.md`

## 1. Scope Completed

B3 implemented historical market-data persistence and feature generation needed before model training.

Implemented:

- CCXT public market-data adapter for spot OHLCV candles.
- Candle domain model and persistence table with unique market/time key.
- Idempotent historical ingestion service with pagination by `since_ms`.
- Data ingestion run audit table.
- Feature schema table and candle feature table.
- TA-Lib feature calculator adapter for B3 basic features:
  - `rsi_14`;
  - `bb_upper_20_2`;
  - `bb_middle_20`;
  - `bb_lower_20_2`;
  - `return_1`;
  - `log_return_1`;
  - `volume_change_1`;
  - `atr_14`;
  - `body_pct`.
- Deterministic Python fallback feature calculator for local/test startup when the `training` dependency group is not installed.
- Retention hooks for candles/features using configurable retention days.
- B3 FastAPI read/operation endpoints:
  - `GET /api/data/status`;
  - `GET /api/data/candles?limit=...`;
  - `POST /api/data/ingestion-runs`;
  - `POST /api/data/features/generate`.

## 2. Documentation Consulted

Context7 was consulted before backend implementation:

- SQLAlchemy `/websites/sqlalchemy_en_20`: ORM-compatible upsert patterns, SQLite `ON CONFLICT`, and MySQL `ON DUPLICATE KEY UPDATE` references. B3 chose portable select/update/insert upserts for SQLite/MySQL parity in the current repository.
- FastAPI `/fastapi/fastapi`: query parameter and Pydantic response model patterns.

Context7 did not return snippets for CCXT or TA-Lib in this session, so official primary docs were used as fallback:

- CCXT manual: `fetch_ohlcv(symbol, timeframe, since, limit)` returns chronological OHLCV arrays using UTC timestamps in milliseconds.
- TA-Lib Python wrapper/function list: RSI, BBANDS, ROC/returns-adjacent functions, and ATR are available indicator families; TA-Lib Python requires the native/wheel dependency.

## 3. Backend Structure

New backend modules:

- `smart_trade_backend.domain.market_data`
  - Pure `Candle`, `FeatureSchema`, and `FeatureRow` dataclasses.
- `smart_trade_backend.application.market_data.ports`
  - Ports for historical market data and feature calculation.
- `smart_trade_backend.application.market_data.ingestion`
  - Ingestion orchestration, idempotent candle upsert, feature generation, retention, and data status read model.
- `smart_trade_backend.application.market_data.features`
  - B3 feature schema constants and deterministic fallback calculator.
- `smart_trade_backend.adapters.exchange.ccxt_public`
  - CCXT public OHLCV adapter.
- `smart_trade_backend.adapters.features.talib`
  - TA-Lib feature calculator adapter.

Updated persistence:

- `candles`
- `feature_schemas`
- `candle_features`
- `data_ingestion_runs`

Migration:

- `20260614_0002_b3_market_data_features.py`

The B1 migration was stabilized to create only B1 tables, because `Base.metadata.create_all()` would otherwise create B3 tables before the B3 migration when running against a fresh database.

## 4. API Contracts

Read endpoints:

- `GET /api/data/status`
- `GET /api/data/candles?limit=200`

Operation endpoints:

- `POST /api/data/ingestion-runs`
  - Public market-data only.
  - No exchange credentials.
  - No trading execution.
- `POST /api/data/features/generate`
  - Regenerates B3 features from persisted candles.

Frontend access remains backend-mediated only.

## 5. Safety and Scope Boundaries

B3 did not add:

- private exchange credentials;
- private exchange API calls;
- order submission;
- inference;
- model training;
- model approval;
- strategy selection;
- paper/live operation controls.

The CCXT adapter uses public OHLCV only. Feature generation uses current/prior candle windows and does not use future candles for any row.

## 6. Verification

Executed successfully:

```bash
cd backend
uv run pytest
```

Result:

- `7 passed`.
- Existing FastAPI/Starlette TestClient deprecation warning remains unchanged.

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
SMART_TRADE_DATABASE_URL=sqlite+pysqlite:////tmp/smart_trade_b3_migration.db uv run alembic upgrade head
SMART_TRADE_DATABASE_URL=sqlite+pysqlite:////tmp/smart_trade_b3_migration.db uv run alembic current
```

Result:

- Alembic upgraded to `20260614_0002 (head)`.

Executed successfully:

```bash
cd backend
uv run --group exchange python -c "import ccxt; print(ccxt.__version__)"
uv run --group training python -c "import talib; import numpy; print(talib.__version__)"
```

Result:

- `ccxt 4.5.58`
- `ta-lib 0.6.8`

Runtime smoke checks executed successfully with a temporary SQLite database:

- `GET http://127.0.0.1:8000/api/data/status`
- `GET http://127.0.0.1:8000/api/data/candles?limit=3`
- `GET http://127.0.0.1:4200/api/data/status`
- `HEAD http://127.0.0.1:4200/`

Public Bybit ingestion smoke executed successfully:

```bash
curl -X POST http://127.0.0.1:8000/api/data/ingestion-runs \
  -H 'content-type: application/json' \
  -d '{"limit":40,"page_size":40}'
```

Result:

- `status`: `COMPLETED`
- `fetched_count`: `40`
- `inserted_count`: `40`
- `feature_rows_upserted`: `21`
- Feature schema: `b3-talib-basic-v1`

## 7. Intentional Non-Scope

B3 did not implement:

- model training;
- walk-forward validation;
- backtest;
- model registry lifecycle changes;
- strategy plugin/default strategy registration;
- paper inference;
- live execution;
- frontend chart replacement with live candle read models.

## 8. Next Agent Handoffs

Recommended next step after Agentic Architect approval: B4.

`@backend.eng`:

- Implement strategy plugin contract and default RSI/IFR + XGBoost model-role strategy.
- Bind strategy-required features to the B3 feature schema.

`@frontend.eng`:

- Continue using `/api/data/status` for data availability.
- Replace operational chart sample data with backend candle/equity/marker read models when the relevant B6 APIs exist.

`@qa.eng`:

- Validate ingestion idempotency, feature schema reproducibility, no look-ahead behavior, migration ordering, and public-only exchange access.
