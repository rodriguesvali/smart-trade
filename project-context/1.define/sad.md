# System Architecture Document - Smart Trade MVP

Status: Approved by Agentic Architect  
Persona: @system.arch  
Date: 2026-06-14  
Source PRD: `project-context/1.define/prd.md`  
Selected Backend Runtime: `native-python`  
Frontend Stack: Angular + PrimeNG  
Database: MySQL  
Database Versioning: Alembic

## 1. Architecture Philosophy and Principles

The Smart Trade MVP architecture is safety-first, process-isolated, and traceable by default. The system must prevent live or paper strategy execution unless the configured strategy, all strategy-required model roles, asset, timeframe, and operational parameters pass explicit compatibility and approval gates.

Core principles:

- Safety-first operational design: invalid configuration, missing credentials, incompatible model metadata, unsupported strategy compatibility, exchange validation failures, or persistence failures must stop operational startup or block the unsafe action.
- Approved-model gating: the execution process may use only models with status `APPROVED` or `ACTIVE` that match the configured asset, timeframe, feature schema, selected strategy ID/version, declared model role, and strategy parameters.
- Process isolation: training, inference/execution, Python backend/API, Angular frontend, MySQL, model artifacts, and logs are separate runtime concerns with explicit boundaries.
- Observable by default: training, validation, backtest, model approval, inference, strategy decisions, orders, fills, positions, errors, and operator commands must be persisted or logged.
- Configuration outside code: exchange, symbol, timeframe, strategy selection, risk parameters, model paths, credentials, mode, and approval criteria are externally configured.
- Backend-mediated frontend access: Angular + PrimeNG accesses operational data and commands only through Python backend APIs/read models.
- Versioned database schema changes: MySQL schema changes are managed through Alembic migrations.
- Minimal MVP before expansion: support multiple registered strategies as an extension point, but run only one selected strategy for one configured asset and one open position at a time in the MVP.

## 2. Stakeholders and Concerns

| Stakeholder | Primary Concerns |
| --- | --- |
| Agentic Architect/operator | Approved PRD traceability, safe MVP scope, clear gates, reviewable architecture, operational control. |
| Trading execution process | Low-latency minute loop, model compatibility, strategy selection, order idempotency, state consistency, exchange error handling. |
| Training/model lifecycle | Historical data integrity, feature reproducibility, holdout separation, walk-forward validation, backtest evidence, model status lifecycle. |
| Strategy implementation owners | Stable strategy contract, registration metadata, parameter schema, compatibility declarations, reuse across training/backtest/live operation. |
| Angular + PrimeNG frontend/operator console | Clear model, strategy, operation, position, metrics, chart, and log visibility through backend APIs. |
| Python backend/API | Read-model aggregation, controlled command mediation, no secret leakage, non-blocking frontend access. |
| Exchange/API boundary | Public historical/market data access, private spot order submission, rate-limit/timeouts/rejections handling. |
| MySQL storage | Durable structured state, schema versioning, consistency across processes, auditability. |
| Model artifact storage | Versioned serialized artifacts and metadata traceable to model IDs. |
| Log storage | Durable rotated operational logs and backend-mediated read access. |

## 3. Scope and Constraints

MVP constraints derived from the approved PRD:

- Market scope: crypto spot only.
- Asset scope: one configured exchange and symbol.
- Timeframe: M1.
- Direction: long-only.
- Strategy scope: multiple strategies can be registered, but only one compatible strategy is selected and active at a time.
- Position scope: one open position at a time.
- Explicit exclusions: margin, futures, leverage, short selling, hedge mode, multiple assets, concurrent strategies, multiple positions, position scaling, averaging down, pyramiding, martingale, and portfolio optimization.
- Runtime: Linux-native Python backend/trading services.
- Frontend: Angular + PrimeNG only.
- Persistence: MySQL for structured state; Alembic for schema versioning.
- Frontend restrictions: no direct database access, model artifact access, log-file access, exchange API access, or secret access.

The architecture must support paper mode before live readiness. Live operation remains gated by all strategy-required approved models, selected compatible strategy, valid exchange configuration, externalized credentials, and operator-controlled mode configuration.

## 4. Logical View

### Primary Presentation

```text
Angular + PrimeNG Frontend
        |
        | HTTPS/API calls
        v
Python Backend/API
        |
        | read models / commands
        v
MySQL <---------------- Training Pipeline
  ^                         |
  |                         v
  |                 Feature Engineering
  |                         |
  |                         v
  |                 XGBoost Training
  |                         |
  |                         v
  |                 Validation + Backtest
  |                         |
  |                         v
  |                 Model Registry + Artifacts
  |
  +---------------- Inference/Execution Process
                            |
                            v
                    Strategy Registry
                            |
                            v
                    Selected Strategy Engine
                            |
                            v
                    CCXT Execution Adapter
                            |
                            v
                    Crypto Spot Exchange

Logs and model artifacts are shared backend/trading resources.
The frontend reaches them only through backend APIs/read models.
```

### Element Catalog

- Training Pipeline: collects historical M1 candles, generates features, separates holdout data, trains XGBoost candidates, validates with walk-forward analysis, runs selected-strategy backtests, and persists model metadata.
- Feature Engineering: produces reproducible feature sets from candle and volume data for training, validation, backtest, and live inference. TA-Lib is the selected MVP technical indicator library and must be encapsulated behind feature-engineering application/domain boundaries.
- Model Registry: stores model metadata, status lifecycle, feature schema, strategy identity, model role, approval evidence, artifact path, and compatibility fields.
- Model Artifact Store: stores serialized `.joblib` or `.pkl` model files and associated metadata files where required.
- Strategy Registry: exposes registered strategy metadata: stable ID, version, name, supported market type, supported direction, required parameters, required features, model role requirements, and operational status.
- Selected Strategy Engine: runs one configured strategy at a time for the MVP, initially the RSI/IFR oversold plus XGBoost binary confirmation strategy.
- Inference Engine: loads compatible approved/active model artifacts for each required strategy model role and produces role-scoped binary signals.
- Execution Adapter: isolates CCXT public/private exchange integration from domain/application logic.
- Persistence Layer: owns MySQL reads/writes for candles, features, model registry, strategy registry, validation/backtest records, decisions, orders, fills, positions, equity snapshots, and command records.
- Python Backend/API: mediates frontend reads and approved commands such as manual retraining request.
- Angular + PrimeNG Frontend: operator console for model, strategy, validation, operation, position, metrics, chart, and log visibility.
- Alembic Migration Layer: versions and applies schema changes for MySQL.
- Logging/Observability: records system events, warnings, exchange errors, rate limits, timeouts, order rejections, and operator-visible diagnostics.

### Rationale and Analysis

The logical view separates domain-critical trading behavior from UI and external adapters. The strategy registry is a domain/application extension point: adding a strategy should require implementing the strategy contract and registering metadata, not rewriting CCXT execution, backend read models, or frontend internals for each strategy. The MVP default strategy remains explicit so the initial build is small and testable.

## 5. Process and Runtime View

### Primary Presentation

The MVP runtime consists of the following independently startable processes:

1. Training process.
2. Inference/execution process.
3. Python backend/API process.
4. Angular frontend runtime or static build served by an approved web serving path.
5. MySQL database service.

Shared resources:

- MySQL database.
- Model artifact directory.
- Log directory.
- External configuration and non-versioned secrets.

### Startup Behavior

- MySQL must be available before backend/trading processes requiring persistence start.
- Alembic migrations must be applied before processes that depend on the new schema start.
- Training may run without exchange private credentials if only public historical data is required.
- Inference/execution startup must validate configuration, selected strategy compatibility, exchange limits, model metadata, feature schema, model status, credentials for the selected mode, and persistence availability.
- The frontend may start independently, but it must display backend/API unavailability rather than accessing shared resources directly.

### Shutdown Behavior

- Training shutdown must leave partial runs marked or inferable as incomplete.
- Inference/execution shutdown must not leave ambiguous open-position state. It must persist the latest known position/order state before stopping when possible.
- Backend/API shutdown must not affect running trading processes.
- Frontend shutdown has no effect on backend or trading execution.

### Restart and Recovery Behavior

- The inference/execution process reconstructs state from MySQL on restart: selected configuration, active model, latest position, pending/closed orders, and last known strategy state.
- Exchange responses and order IDs are persisted to support idempotency checks and avoid duplicate order submission after restart.
- Transient exchange failures are logged and handled without uncontrolled process termination where state can remain consistent.
- If state consistency cannot be established, execution fails safe and requires operator inspection.

## 6. Data View

### MySQL Schema Ownership

MySQL is the authoritative store for structured application state. Schema ownership belongs to the backend/trading application codebase, with schema changes delivered as Alembic migrations.

Required entity areas:

- Asset configuration.
- Strategy registry.
- Selected strategy configuration.
- Candles.
- Features.
- Model registry.
- Validation runs.
- Backtest runs.
- Approval events.
- Inference signals.
- Strategy decisions.
- Positions.
- Orders.
- Fills/exchange responses.
- Equity snapshots.
- Operational events.
- Command requests.

### Alembic Versioning and Execution Policy

- Alembic is the required schema versioning mechanism.
- Migrations are reviewed as part of architecture/build changes before execution in shared or live environments.
- Alembic migrations are executed by the backend startup process before dependent backend/trading processes run.
- Trading execution must not auto-apply schema migrations while live or paper operation is running.
- Backend/API startup must fail fast if migrations fail or if the schema remains incompatible.
- Training and execution processes must check schema compatibility before writing records that rely on newly introduced fields.

### Rollback and Forward-Fix Policy

- For MVP, prefer forward-fix migrations over destructive rollback in environments containing trading history.
- Rollbacks may be defined only for safe metadata/schema changes where data loss is not expected.
- Destructive migrations require explicit Agentic Architect review and a backup/export plan.
- Migration failures must stop dependent process startup and surface a clear operator-visible error.

### Data Consistency Rules

- Every model-related operational record must include model ID and model role when a model participated in the decision.
- Every strategy-related validation, backtest, model, inference, and operational record must include strategy ID and strategy version.
- Records that use inference must include every participating model ID and model role.
- Every order/fill record must preserve exchange identifiers and raw response references where practical.
- Feature schema identifiers must match across model training and live inference.
- Position state transitions must be appendable/auditable, even if a current-state read model is also maintained.

## 7. Model Lifecycle View

### Lifecycle

```text
TRAINED -> VALIDATED -> APPROVED -> ACTIVE -> RETIRED
                  \          \          \
                   -> REJECTED -> EXPIRED
```

The exact transition enforcement can be implemented as application logic and persisted status changes. A model may not be used for strategy operation unless it is `APPROVED` or `ACTIVE`.

### Required Lifecycle Evidence

- Historical data collection window.
- Training window.
- Holdout window.
- Feature schema and feature list.
- Walk-forward validation metrics.
- Final out-of-sample backtest metrics.
- Strategy ID/version, model role, and strategy parameters used during validation/backtest.
- Approval event and approval criteria snapshot.
- Artifact path and serialization format.

### Compatibility Checks

Before activation, the system checks:

- Exchange and symbol match.
- M1 timeframe match.
- Feature schema match.
- Strategy ID/version and model role match.
- Strategy parameters match or are compatible by an approved compatibility rule.
- Model status is `APPROVED` or `ACTIVE`.
- Artifact exists and can be loaded.
- Model output contract is binary for each required binary model role.

### Traceability

Every inference record includes:

- Model ID.
- Model role.
- Strategy ID/version.
- Asset/timeframe.
- Input feature schema/version.
- Binary signal.
- Timestamp aligned to the evaluated candle.
- Downstream strategy decision reference where applicable.

## 8. Execution and Strategy View

### Minute-Aligned Loop

The inference/execution process runs a minute-aligned loop for M1 operation. The initial target is execution after the latest candle is expected to be closed, with the PRD target at second `01` of each minute.

Loop outline:

1. Confirm process mode and operational readiness.
2. Fetch or read the latest closed M1 candle.
3. Generate live features using the same feature contract as training.
4. Load or use the already loaded approved/active model.
5. Run selected strategy evaluation.
6. If required by strategy, request binary model inference for each declared model role needed by the decision.
7. Produce a strategy decision.
8. Submit authorized order through CCXT only when strategy and risk checks allow it.
9. Persist inference, decision, order, fill, position, and log records.

### Default MVP Strategy

The registered default strategy is:

- Spot long-only.
- One open position at a time.
- RSI/IFR oversold condition as the technical entry prerequisite.
- XGBoost binary signal `1` as entry/continuation confirmation for the default required model role.
- Mandatory stop loss.
- Mandatory take profit or configured profit handling.
- Break-even protection.
- Trailing stop that never moves downward for long positions.
- Profit realization or configured exit when favorable movement loses model confirmation.

### Strategy Registry Contract

Each registered strategy must declare:

- Stable strategy ID.
- Version.
- Display name and description.
- Supported market type.
- Supported direction.
- Required parameters and defaults.
- Required features.
- Model requirements by role.
- Position constraints.
- Compatibility with MVP spot long-only rules.

New strategies must be registerable as plugins. Plugin loading and registration must validate the strategy contract, metadata, parameter schema, model role requirements, compatibility declarations, and operational safety constraints before a strategy can be selected.

Strategy plugins are Python code-deployed backend plugins, not frontend-uploaded scripts. Each plugin must provide metadata (`id`, `name`, `version`, `description`, `supported_market`, `supported_direction`, `timeframes`, `required_features`, `model_requirements` by role), a typed parameter schema with defaults and limits, `validate_config(config)`, `required_features(config)`, `required_model_roles(config)`, `on_candle(context)`, `on_position_update(context)`, `risk_rules(config)`, and `compatibility_check(runtime_context)`. Strategy outputs must use standardized decisions such as `HOLD`, `ENTER_LONG`, `MOVE_STOP`, and `EXIT_POSITION`, with reason, signal/confidence where applicable, participating model roles/IDs, and risk updates.

The default MVP strategy uses one required model role for entry/continuation confirmation. The architecture supports future strategies that combine two or more approved models by role, such as entry confirmation, trend filter, volatility regime, or exit confirmation.

### Fail-Safe Behavior

The execution process must block startup or block action when:

- No compatible approved/active model exists for every required strategy model role.
- Selected strategy is missing, inactive, or incompatible.
- Feature schema does not match model metadata.
- Exchange limits or balance checks fail.
- Credentials required for the selected mode are missing.
- Persistence is unavailable for required operational records.
- Existing position/order state cannot be reconciled safely.

## 9. Integration View

### CCXT Boundaries

- Public CCXT methods are used for historical/market data collection.
- Private CCXT methods are used only by the execution adapter for authorized spot market orders.
- Domain and strategy logic must not depend directly on CCXT object shapes.
- Exchange rate limits, timeouts, rejected orders, and invalid responses are adapter concerns that are translated into application-level outcomes.

### Database Access Boundaries

- Training, execution, and backend/API processes may access MySQL through application persistence adapters.
- Angular frontend must never access MySQL directly.
- Backend/API should expose read models tailored for frontend needs rather than leaking internal table structure.

### Model Artifact Storage

- Training writes artifacts and metadata.
- Inference/execution reads artifacts only after model registry compatibility checks pass for every required strategy model role.
- Frontend receives model metadata and metrics through backend APIs only.

### Log Access

- Trading/backend processes write durable logs.
- Backend/API mediates frontend log views.
- Frontend does not tail files directly.

### Backend/API Contracts for Angular Frontend

Initial read/command contract areas:

- Registered strategies list and selected strategy detail.
- Asset/configuration summary.
- Model registry list/detail.
- Validation run detail.
- Backtest run detail.
- Current operation status.
- Latest inference and strategy decision.
- Current/open/closed position state.
- Orders and fills.
- Equity curve and metrics.
- Log stream/read endpoint.
- Manual retraining command request.

Commands that affect operation must be explicit, persisted as command requests, and surfaced with status.

### Environment and Configuration

Configuration is loaded from environment variables or local unversioned files. Secrets must not be committed, logged, returned through APIs, or embedded in frontend builds.

## 10. Deployment View

### Local Linux Layout

The MVP target is Linux-native execution, with Docker/container deployment preferred where useful. A minimal local layout contains:

- Python training service/process.
- Python inference/execution service/process.
- Python backend/API service/process.
- Angular + PrimeNG frontend build/runtime.
- TradingView Lightweight Charts used inside Angular for candlesticks, entry/exit markers, and equity curve.
- MySQL service.
- Shared model artifact volume/directory for backend/trading processes.
- Shared log volume/directory for backend/trading processes.
- Local unversioned environment configuration.

### Container Plan

Preferred containers:

- `mysql`: MySQL database.
- `backend-api`: Python backend/API.
- `trainer`: Python training pipeline entrypoint.
- `executor`: Python inference/execution entrypoint.
- `frontend`: Angular production build served by an approved static/web server path.

The exact build tooling and package managers remain open until Build setup.

### Angular Build and Serving Strategy

Angular + PrimeNG should be built as a frontend artifact and served separately from trading execution. It communicates only with backend/API endpoints. The architecture permits serving the built frontend through the Python backend or a separate static server, but the frontend must remain logically decoupled from trading processes.

TradingView Lightweight Charts is the selected charting library for the MVP operational charts. Angular components should wrap the library at the component boundary, keeping chart-specific imperative code isolated from PrimeNG layout components and frontend application state.

### MySQL Initialization and Alembic

- MySQL initialization provisions the database and connection credentials outside source control.
- Alembic applies schema migrations before application processes requiring the schema start.
- The migration execution point is a deployment/operator command for the MVP.
- Runtime services check schema compatibility and fail fast on mismatch.

### Operational Modes

- Training mode: collect data, train model, validate, backtest, persist evidence.
- Paper mode: run selected strategy and model gates without live capital execution, according to implementation policy.
- Live mode: submit authorized spot orders through CCXT only after all readiness gates pass.

## 11. Quality Attributes

| Attribute | Architecture Response |
| --- | --- |
| Latency | Inference/execution process keeps model loaded and follows minute-aligned loop; frontend is isolated from execution path. |
| Reliability | Process boundaries prevent frontend/backend UI issues from directly stopping execution; startup checks fail safe. |
| Resilience | Exchange errors are handled in adapters and persisted/logged; inconsistent state blocks unsafe continuation. |
| Observability | Model, strategy, inference, decision, order, fill, position, equity, command, and log records are traceable. |
| Security | Secrets are externalized and never exposed to frontend, logs, source, or API responses. |
| Data integrity | MySQL is authoritative for structured state; Alembic versions schema; state transitions are auditable. |
| Migration safety | Migrations are explicit, reviewed, and not auto-applied by live trading loops. |
| Reproducibility | Feature schema and strategy parameters are persisted with model/validation/backtest records. |
| Maintainability | Strategy registry and adapter boundaries limit changes needed for new strategies and external integrations. |

TA-Lib introduces a native C dependency. Build and deployment definitions must install and verify the native TA-Lib library before backend services that calculate indicators are considered ready.

## 12. Key Architectural Decisions

### Decision 1: Native Python Backend and Trading Runtime

- Context: PRD requires Linux-native Python backend/trading services.
- Options considered: native Python; chat/agent runtime; frontend-centric execution.
- Chosen approach: native Python processes for training, inference/execution, and backend/API.
- Consequences: direct control over CCXT, XGBoost artifacts, persistence, and operational loops; agent personas remain methodology roles only.
- PRD traceability: Executive Summary, Scope, RNF5.1.

### Decision 1.1: Python 3.14 and uv Dependency Management

- Context: Backend services require a standardized Python version, reproducible dependency resolution, and reliable Docker/CI installation.
- Options considered: `uv`; Poetry; pip-tools; Hatch; manual `pip` plus `requirements.txt`.
- Chosen approach: Python 3.14 with `uv` as the backend dependency and environment manager. Dependencies are declared in `pyproject.toml` and locked in `uv.lock`.
- Consequences: Builds are fast and reproducible; TA-Lib still requires native C library installation in the Linux/Docker image before the Python wrapper can be used.
- PRD traceability: OQ9.1 resolution, RNF5.1, RNF5.8.

### Decision 2: Angular + PrimeNG as Decoupled Frontend

- Context: PRD fixes Angular + PrimeNG frontend and forbids frontend direct execution access.
- Options considered: Angular + PrimeNG; Streamlit/Dash; Next.js.
- Chosen approach: Angular + PrimeNG operator console using Python backend APIs/read models.
- Consequences: UI failures cannot directly block trading execution; backend must provide frontend-oriented contracts.
- PRD traceability: RF3.1-RF3.7, RF4.1-RF4.9, RNF5.12.

### Decision 2.1: TradingView Lightweight Charts for Operational Charts

- Context: The frontend requires candlestick charts, visual markers for long entries/exits, and equity curve display.
- Options considered: TradingView Lightweight Charts; Apache ECharts; Highcharts Stock; ApexCharts; PrimeNG Chart/Chart.js financial plugin.
- Chosen approach: TradingView Lightweight Charts for MVP candlesticks, entry/exit markers, and equity curve.
- Consequences: The charting choice is optimized for financial time series and trading annotations; Angular integration requires a thin local wrapper component because the library is not a native PrimeNG component.
- PRD traceability: RF4.3, RF4.4, AC8.13.

### Decision 3: MySQL as Structured State Store

- Context: PRD requires MySQL for structured state.
- Options considered: MySQL; SQLite; PostgreSQL.
- Chosen approach: MySQL as authoritative structured persistence.
- Consequences: multi-process persistence and operational queries are supported; schema discipline is required.
- PRD traceability: DR6.1-DR6.10.

### Decision 4: Alembic-Owned Schema Versioning

- Context: PRD and AAMAD alignment require Alembic.
- Options considered: manual SQL; ORM auto-create; Alembic migrations.
- Chosen approach: Alembic migration history and explicit migration execution before dependent services start.
- Consequences: schema changes are auditable; live trading loop does not mutate schema at runtime.
- PRD traceability: DR6.2, OQ9.9.

### Decision 5: Migration Rollback/Forward-Fix Policy

- Context: Trading history and model evidence are operationally valuable.
- Options considered: automatic rollback; manual destructive rollback; forward-fix first.
- Chosen approach: prefer forward-fix migrations; destructive rollback requires explicit review and backup/export plan.
- Consequences: lower risk of accidental trading data loss; migration mistakes require controlled correction.
- PRD traceability: DR6.2, DR6.8-DR6.10.

### Decision 6: Strategy Registry as Domain Extension Point

- Context: PRD now requires multiple strategies to be implementable and registered, while MVP runs one active strategy.
- Options considered: hard-coded strategy only; code-deployed registry; plugin-based strategy registration.
- Chosen approach: stable strategy registry contract with plugin-based strategy registration.
- Consequences: future strategies can be added as plugins, but plugin discovery/activation must validate contract compliance, metadata, parameter schema, compatibility, and safety gates before selection.
- PRD traceability: RF2.5.1-RF2.5.20, AC8.16-AC8.17, OQ9.11-OQ9.12.

### Decision 6.1: TA-Lib for Technical Indicators

- Context: The MVP requires RSI/IFR, Bollinger Bands, volatility, momentum, and derived technical indicators for training, validation, backtest, and live inference.
- Options considered: TA-Lib; pandas-ta/pandas-ta-classic; custom indicator implementations.
- Chosen approach: TA-Lib as the MVP technical indicator library, wrapped behind a feature-engineering boundary.
- Consequences: Indicator calculations use a mature native technical-analysis library, but Linux/Docker builds must install and verify the TA-Lib C dependency.
- PRD traceability: RF1.3, DR6.5.

### Decision 7: Approved Model Role Compatibility Gate

- Context: Strategy must not run without approved compatible model.
- Options considered: load latest model; operator-selected file path; one global active model; registry-compatible model role gate.
- Chosen approach: execution loads only `APPROVED` or `ACTIVE` models for every model role declared by the selected strategy, matching asset, timeframe, feature schema, strategy ID/version, model role, and parameters.
- Consequences: reduces model mismatch and accidental live use of invalid artifacts; future strategies can combine multiple approved models without replacing the execution platform.
- PRD traceability: RF1.10-RF1.12, RF2.2-RF2.3, AC8.6.

### Decision 8: CCXT Isolated Behind Execution Adapter

- Context: PRD requires direct CCXT integration but maintainable boundaries.
- Options considered: CCXT calls inside strategy; dedicated execution adapter.
- Chosen approach: CCXT public/private calls are adapter responsibilities.
- Consequences: strategy/domain logic stays testable and independent from exchange library details.
- PRD traceability: RF2.5-RF2.7, AC8.11-AC8.12.

### Decision 9: Backend Read Models for Frontend

- Context: Frontend needs operational views but must not access database/artifacts/logs directly.
- Options considered: frontend direct DB/log access; backend read models.
- Chosen approach: backend API aggregates frontend-specific read models and command statuses.
- Consequences: frontend remains decoupled; backend owns authorization, filtering, and safe exposure.
- PRD traceability: RF3.1-RF3.7, RF4.1-RF4.9.

### Decision 10: Idempotency Through Persisted Order/State Records

- Context: Exchange retries and restarts can create duplicate order risk.
- Options considered: in-memory tracking only; persisted order intent/response/state records.
- Chosen approach: persist strategy decisions, order requests, exchange responses, fills, and position transitions.
- Consequences: restart/recovery can reconcile state and block duplicate unsafe submissions.
- PRD traceability: RF2.6-RF2.7, AC8.12.

### Decision 11: MySQL Connection and Pooling Strategy

- Context: Multiple Python processes require MySQL access.
- Options considered: one global connection; per-process pools; ad hoc connections.
- Chosen approach: each Python process owns its own bounded MySQL connection pool through its persistence adapter.
- Consequences: process isolation is preserved; pool sizing must be configured conservatively for MVP.
- PRD traceability: RNF5.3, DR6.1.

### Decision 12: Schema Compatibility Expectations

- Context: Training, execution, and frontend read models share schema-backed records.
- Options considered: tolerate missing fields; fail fast on incompatible schema.
- Chosen approach: services check expected schema/migration version at startup and fail fast on mismatch.
- Consequences: avoids silent corruption or incomplete records; requires explicit migration step.
- PRD traceability: DR6.2, RNF5.11.

## 13. Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Market/exchange volatility | Slippage, rejected orders, unexpected fills. | Validate exchange limits, persist exchange responses, use paper mode before live. |
| Model overfitting | False confidence and poor live results. | Walk-forward validation, holdout backtest, approval gates, metrics persistence. |
| Data leakage/look-ahead bias | Invalid validation evidence. | Explicit holdout separation and reproducible feature generation. |
| Model/feature mismatch | Invalid live inference. | Feature schema compatibility checks before model activation. |
| Strategy incompatibility | Unsafe operation with unsupported market/direction. | Strategy registry compatibility declarations and selection gate. |
| Duplicate orders after retry/restart | Capital loss or unintended exposure. | Persist order intents/responses and reconcile state on restart. |
| Exchange/API failure | Missed entries/exits or inconsistent state. | Adapter-level error handling, durable logs, fail-safe state blocking. |
| Schema drift | Runtime failures or corrupted records. | Alembic migrations, schema version checks, explicit migration execution. |
| Secret leakage | Account compromise. | Environment/local secret injection, no secrets in logs/API/frontend/source. |
| Frontend/API load on database | Interference with trading writes. | Backend read models and isolated frontend process; avoid direct frontend DB access. |
| TA-Lib native dependency failure | Training or inference feature generation fails at startup/runtime. | Install TA-Lib C library in Docker/Linux build; add startup health checks for indicator calculation. |

## 14. Future Work and Explicit Deferrals

Explicitly deferred unless later approved:

- Multi-asset concurrent operation.
- Multiple strategies running concurrently.
- Short selling, futures, margin, leverage, hedge mode, and derivatives execution.
- Position scaling, averaging down, pyramiding, martingale.
- Cloud deployment and managed infrastructure.
- Advanced alerting and incident automation.
- Additional model families beyond XGBoost.
- Alternative frontend stacks.
- Fully autonomous model approval.
- Portfolio optimization.

## 15. Sources

- `project-context/1.define/prd.md`
- `docs/proposed-solution.md`
- `AGENTS.md`
- `.codex/aamad/state.md`
- `.codex/aamad/workflow.md`
- `.codex/aamad/templates/sad-template.md`
- `.codex/aamad/agents/system-arch.md`

## 16. Assumptions

- Backend runtime remains `native-python`.
- Python 3.14 is the standardized backend Python version.
- `uv` is the standardized backend dependency and environment manager, with dependencies declared in `pyproject.toml` and locked in `uv.lock`.
- Angular + PrimeNG remains the frontend stack.
- MySQL remains the target structured database.
- Alembic remains the schema migration/versioning tool.
- The MVP default strategy is RSI/IFR oversold plus XGBoost binary confirmation.
- TA-Lib is the selected MVP technical indicator library.
- Strategy registry is required and new strategies must be registerable as plugins.
- Strategies may declare one or more model roles. The default MVP strategy declares one model role for entry/continuation confirmation.
- One selected strategy is active at a time in the MVP.
- Model approval is manual-only for the MVP.
- Alembic migrations are executed by the backend startup process before dependent backend/trading processes run, with failure causing fail-fast startup.
- Paper mode is expected before live operation.
- Bybit is the initial MVP exchange.
- Bitcoin is the initial MVP asset, with `BTC/USDT` as the default CCXT spot symbol and Bybit-native symbol formatting handled by the CCXT adapter.
- Initial operational capital is 1,000 USD.
- Backtest/paper default cost assumptions are taker fee 0.15% per side and base slippage 0.05% per side for `BTC/USDT` market orders. Stress simulation uses 0.15% slippage per side. Live/paper operation should prefer account-specific Bybit fee rates from API when available.
- Bybit activation must validate account/jurisdiction availability, spot API availability, fee tier, minimum order size, precision, liquidity, and CCXT support before paper or live operation.
- MVP manual model approval minimum thresholds are: `precision_class_1 >= 0.55`, `trade_count >= 30`, `net_pnl > 0` after fee/slippage assumptions, `profit_factor >= 1.20`, `max_drawdown <= 8%`, `win_rate >= 45%`, `max_losing_streak <= 5`, and at least 60% of walk-forward windows non-negative or with profit factor above 1.0.
- Paper mode is mandatory for at least 7 consecutive days before live operation. Live readiness requires at least 30 simulated trades or a full 7-day run if fewer signals occur, no unresolved critical failures, consistent position/order state, complete model and strategy traceability, exchange limit validation, and paper results within approved risk thresholds. Final live enablement remains manual.
- MVP retention policy: retain raw M1 candles for 180 days; derived features for 90 days; validation/backtest reports, inference records, strategy decisions, orders, fills, positions, equity snapshots, approval events, and command audit trail for at least 365 days; application logs for 30 days online with rotation; critical execution/error logs for 180 days; approved/active model artifacts indefinitely while operationally relevant; rejected model artifacts for 30 days. Features may be regenerated from retained candle data when needed.
- The MVP operational frontend has no authentication.

## 17. Open Questions

No open architecture questions remain.

## 18. Audit

- Generated by: @system.arch
- Action: Created System Architecture Document from approved PRD.
- Date: 2026-06-13
- Backend runtime: `native-python`
- Python version: 3.14
- Dependency manager: `uv`
- Frontend stack: Angular + PrimeNG
- Charting library: TradingView Lightweight Charts
- Indicator library: TA-Lib
- Initial exchange: Bybit
- Initial asset: Bitcoin (`BTC/USDT` default CCXT spot symbol)
- Initial operational capital: 1,000 USD
- Fee/slippage assumptions: 0.15% taker fee per side, 0.05% base slippage per side, 0.15% stress slippage per side; prefer account-specific Bybit fee API when available.
- Model approval thresholds: precision class 1 >= 0.55, trade count >= 30, net PnL > 0, profit factor >= 1.20, max drawdown <= 8%, win rate >= 45%, max losing streak <= 5, and >= 60% acceptable walk-forward windows.
- Paper/live readiness: at least 7 consecutive paper days; at least 30 simulated trades or full 7-day run if fewer signals occur; no unresolved critical failures; consistent state and traceability; manual live enablement.
- Retention policy: raw candles 180 days; derived features 90 days; validation/backtest, inference, strategy decisions, orders, fills, positions, equity, approvals, and commands at least 365 days; application logs 30 days; critical logs 180 days; approved/active model artifacts indefinitely while relevant; rejected model artifacts 30 days.
- Frontend authentication: none for MVP.
- Strategy plugin contract: Python code-deployed backend plugins with metadata, typed parameter schema, validation hooks, feature declarations, model role declarations, candle/position handlers, risk rules, compatibility checks, and standardized decisions.
- Database: MySQL
- Database versioning: Alembic
- Source inputs: `project-context/1.define/prd.md`, `.codex/aamad/templates/sad-template.md`, `.codex/aamad/agents/system-arch.md`, `.codex/aamad/state.md`
- Review status: Final approved by Agentic Architect after collaborative Define review.
- Handoff gate: SAD final approved. Define phase architecture is closed.
