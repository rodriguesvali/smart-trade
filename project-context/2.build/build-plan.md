# Build Plan - Smart Trade MVP

Status: Draft for Agentic Architect review  
Persona: @system.arch  
Date: 2026-06-14  
Source artifacts: `project-context/1.define/prd.md`, `project-context/1.define/sad.md`, `.codex/aamad/state.md`

## 1. Build Objective

Build the MVP in controlled increments that keep the system executable and observable from the beginning, while deferring real trading execution until training, validation, model approval, paper readiness, and operational safety gates are implemented.

The recommended Build strategy is:

1. Create a minimal backend/API and minimal Angular + PrimeNG frontend first.
2. Establish MySQL/Alembic schema, configuration, logs, and read contracts early.
3. Implement historical data and training/validation/backtest before any operational execution.
4. Implement strategy/plugin/model-role contracts before the live loop.
5. Implement paper operation before live operation.
6. Add live execution last, behind all gates.

This sequence is intentionally conservative. It prevents the project from building a trading loop before the system can explain, validate, persist, and display what it is doing.

## 2. Guiding Constraints

- Backend runtime: Python 3.14, `uv`, native Python.
- Frontend: Angular + PrimeNG, TradingView Lightweight Charts.
- Database: MySQL with Alembic migrations executed by backend startup.
- Exchange: Bybit spot `BTC/USDT` through CCXT.
- Strategy: one selected strategy active at a time in MVP.
- Strategy extensibility: Python code-deployed plugins.
- Model extensibility: strategy-declared model roles; default strategy uses one model role.
- Indicators: TA-Lib.
- Execution: spot long-only, one open position, no position scaling.
- Live mode: last increment only, manual enablement, after paper readiness.

## 3. Build Increments

### B0 - Project Bootstrap and Runtime Skeleton

Goal: create the runnable project foundation without business behavior.

Scope:

- Python backend workspace using Python 3.14 and `uv`.
- Angular + PrimeNG frontend workspace.
- Docker/local development layout for backend, frontend, MySQL.
- Base configuration loading from environment/local unversioned files.
- Basic logging setup.
- Alembic initialized and wired to backend startup.
- Health endpoints for backend and database connectivity.

Exit criteria:

- Developer can start backend, frontend, and MySQL locally.
- Backend health endpoint reports service and database status.
- Alembic migration path runs during backend startup and fails fast on migration failure.
- Frontend shows a minimal operational shell and backend connectivity status.

Primary persona handoff:

- `@project.mgr` owns structure, dependency plan, environment files, Docker/local setup.
- `@backend.eng` validates backend skeleton.
- `@frontend.eng` validates Angular shell.
- `@qa.eng` validates startup smoke checks.

### B1 - Core Domain, Persistence, and API Contracts

Goal: establish stable domain boundaries and data contracts before feature-specific implementation.

Scope:

- Domain model for asset configuration, strategy registry, model registry, model roles, model lifecycle, strategy decisions, positions, orders, fills, equity snapshots, command requests, and operational events.
- Initial MySQL schema via Alembic.
- Backend read APIs for frontend shell:
  - configuration summary;
  - registered strategies;
  - model registry summaries;
  - operation status;
  - logs/events summary.
- Command request framework for controlled operations.
- No real training or trading logic yet.

Exit criteria:

- MySQL schema supports MVP entity areas from PRD/SAD.
- Frontend can display configuration, empty strategy/model state, and service status through backend APIs.
- Command requests are persisted and auditable.
- No frontend direct database, log-file, artifact, exchange, or secret access exists.

Primary persona handoff:

- `@backend.eng` owns domain/persistence/API boundaries.
- `@frontend.eng` consumes backend read contracts.
- `@qa.eng` validates traceability and API contract evidence.

### B2 - Minimal Frontend Operational Console

Goal: create the operator surface early enough to guide backend contracts and avoid blind processes.

Scope:

- Angular + PrimeNG layout for:
  - system status;
  - strategy registry/selected strategy;
  - model registry;
  - training/backtest placeholders;
  - operation placeholders;
  - log/event view.
- TradingView Lightweight Charts wrapper component with mocked or backend-provided placeholder candle/equity data.
- No live exchange credentials or execution commands.

Exit criteria:

- Frontend can render core screens using backend APIs.
- Chart wrapper can render candlesticks, entry/exit markers, and equity curve from test/read-model data.
- UI clearly distinguishes unavailable, empty, paper, and live states.

Primary persona handoff:

- `@frontend.eng` owns Angular implementation.
- `@backend.eng` supports read-model/API shape.
- `@qa.eng` checks frontend evidence and no unsafe command exposure.

## 4. Data, Training, and Validation Increments

### B3 - Historical Data and Feature Pipeline

Goal: collect and persist data needed for model training.

Scope:

- CCXT public Bybit spot data adapter for `BTC/USDT` M1 candles.
- Candle persistence and idempotent historical ingestion.
- TA-Lib feature generation behind feature-engineering boundary.
- Feature schema/versioning.
- Retention behavior for candles/features.
- Frontend visibility for data collection status.

Exit criteria:

- System can collect and persist M1 candles for `BTC/USDT`.
- Feature generation is reproducible and schema-versioned.
- Ingestion can resume without duplicating candle rows.
- Frontend shows data availability and latest collection status.

Primary persona handoff:

- `@backend.eng` owns ingestion/features/persistence.
- `@frontend.eng` exposes status.
- `@qa.eng` validates no look-ahead in feature generation.

### B4 - Strategy Plugin Contract and Default Strategy

Goal: implement strategy extensibility before model training binds to a specific hard-coded strategy.

Scope:

- Python code-deployed plugin discovery/registration.
- Strategy metadata and parameter schema validation.
- `required_features(config)`.
- `required_model_roles(config)`.
- `validate_config(config)`.
- `risk_rules(config)`.
- `compatibility_check(runtime_context)`.
- Default MVP strategy plugin: RSI/IFR oversold + one XGBoost model role for entry/continuation confirmation.
- Persisted strategy registry and selected strategy configuration.

Exit criteria:

- Default strategy registers through the same plugin mechanism expected for future strategies.
- Strategy cannot be selected if compatibility or safety validation fails.
- Strategy model role requirements are visible through backend API/frontend.

Primary persona handoff:

- `@backend.eng` owns plugin contract and default strategy.
- `@frontend.eng` renders strategy metadata/config.
- `@qa.eng` validates plugin rejection and selection gates.

### B5 - Model Training, Walk-Forward Validation, Backtest, and Manual Approval

Goal: produce approved model artifacts before operational execution exists.

Scope:

- XGBoost training for declared strategy model roles.
- Training window and final holdout separation.
- Walk-forward validation.
- Out-of-sample backtest of selected strategy using required model roles.
- Metrics persistence:
  - precision class 1;
  - trade count;
  - net PnL after fee/slippage assumptions;
  - profit factor;
  - max drawdown;
  - win rate;
  - max losing streak;
  - acceptable walk-forward windows.
- Model artifact persistence with metadata.
- Model lifecycle statuses.
- Manual approval workflow.
- Frontend training/model/backtest views.

Exit criteria:

- Candidate model can be trained for default strategy model role.
- Holdout data is excluded from training.
- Walk-forward and final backtest results are persisted.
- Manual approval is blocked unless minimum thresholds are met.
- Approved/active model is traceable by model ID, model role, strategy ID/version, feature schema, and parameters.

Primary persona handoff:

- `@backend.eng` owns training/validation/backtest/model registry.
- `@frontend.eng` owns model evidence UI.
- `@qa.eng` validates leakage prevention, metrics, threshold gates, and artifact traceability.

## 5. Operation Increments

### B6 - Paper Inference and Strategy Runtime

Goal: run the operational loop without live capital.

Scope:

- Minute-aligned M1 loop.
- Approved model-role loading for selected strategy.
- Live feature generation.
- Strategy decision execution in paper mode.
- Simulated orders/fills/positions/equity.
- Stop loss, take profit, break even, trailing stop, and inference-conditioned exit behavior.
- Full persistence of model IDs/roles, decisions, simulated orders, positions, equity, and logs.
- Frontend operation view with chart markers and equity curve.

Exit criteria:

- Paper loop runs with no live order submission.
- Strategy cannot start unless every required model role has a compatible `APPROVED` or `ACTIVE` model.
- Paper records are traceable and visible in frontend.
- State can recover after restart without duplicate simulated orders.

Primary persona handoff:

- `@backend.eng` owns inference/strategy runtime/paper execution.
- `@frontend.eng` owns operational console.
- `@qa.eng` validates paper state consistency and safety gates.

### B7 - Live Readiness Gate

Goal: prove the system is operationally ready before live execution is enabled.

Scope:

- Paper readiness evidence:
  - at least 7 consecutive paper days;
  - at least 30 simulated trades or full 7-day run if fewer signals occur;
  - no unresolved critical failures;
  - consistent position/order state;
  - complete model/strategy traceability;
  - exchange limit validation;
  - paper results within approved risk thresholds.
- Manual live enablement gate.
- Frontend readiness status and evidence view.

Exit criteria:

- Live mode cannot be enabled until all readiness checks pass.
- Manual live enablement is auditable.
- Failure reasons are visible to operator.

Primary persona handoff:

- `@qa.eng` owns readiness evidence criteria.
- `@backend.eng` owns gate enforcement.
- `@frontend.eng` owns readiness display.

### B8 - Live Spot Execution

Goal: enable real Bybit spot execution only after readiness gates pass.

Scope:

- CCXT private Bybit spot adapter.
- Credential loading from unversioned local configuration/environment.
- Exchange limit, precision, balance, and fee-rate validation.
- Market buy/sell order submission for authorized strategy decisions.
- Exchange response/fill persistence.
- Idempotency and restart reconciliation.
- Fail-safe stop on inconsistent state.

Exit criteria:

- Live mode cannot run without manual enablement and passing readiness gates.
- Orders are submitted only through execution adapter after strategy/risk authorization.
- Exchange responses and fills are persisted.
- Failures preserve consistent state or stop safely.

Primary persona handoff:

- `@backend.eng` owns CCXT private execution.
- `@qa.eng` validates live safety behavior in controlled/paper-equivalent tests before any real capital exposure.
- `@frontend.eng` displays live state without direct execution access.

## 6. Recommended Build Order

The recommended order is:

1. `B0 - Project Bootstrap and Runtime Skeleton`
2. `B1 - Core Domain, Persistence, and API Contracts`
3. `B2 - Minimal Frontend Operational Console`
4. `B3 - Historical Data and Feature Pipeline`
5. `B4 - Strategy Plugin Contract and Default Strategy`
6. `B5 - Model Training, Walk-Forward Validation, Backtest, and Manual Approval`
7. `B6 - Paper Inference and Strategy Runtime`
8. `B7 - Live Readiness Gate`
9. `B8 - Live Spot Execution`

This matches the architectural risk order:

- First make the system runnable and observable.
- Then make persistence/contracts stable.
- Then prove data and model lifecycle.
- Then run paper operation.
- Only then enable live execution.

## 7. Why Not Start With Trading Execution

Starting with live or paper execution before training/backtest creates avoidable risk:

- Strategy decisions would have no approved model evidence.
- Frontend would not yet expose enough diagnostic evidence.
- Persistence and model-role traceability would be retrofitted later.
- Exchange order handling could be implemented before state/idempotency is stable.
- QA would be forced to validate safety gates after the most dangerous surface already exists.

The safer path is backend/frontend skeleton first, training second, paper third, live last.

## 8. Stage Gates

Each Build increment must stop for Agentic Architect review before the next risk level begins.

Minimum gates:

- Gate B0/B1: bootstrap and persistence/API contracts approved.
- Gate B2: frontend operational shell approved.
- Gate B3: data/feature pipeline approved.
- Gate B4: strategy plugin/default strategy contract approved.
- Gate B5: training/validation/backtest/model approval approved.
- Gate B6/B7: paper operation and readiness gate approved.
- Gate B8: live execution explicitly approved.

## 9. Open Planning Questions

- Frontend package manager remains to be selected.
- Backend web framework remains to be selected during `@project.mgr` or `@backend.eng` planning.
- Exact process runner/deployment layout remains to be selected during Build setup.
- Test framework choices remain to be selected during Build setup.

## 10. Audit

- Generated by: @system.arch
- Action: Created Build phase architecture plan from approved PRD/SAD.
- Date: 2026-06-14
- Review status: Pending Agentic Architect review.
- Handoff gate: Do not proceed to project scaffolding, dependency installation, code generation, or implementation until the Agentic Architect approves or revises this Build plan.
