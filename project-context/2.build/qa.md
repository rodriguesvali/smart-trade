# QA Test Scenarios - Smart Trade MVP

Status: Draft for Agentic Architect review  
Persona: @qa.eng  
Date: 2026-06-14  
Source artifacts: `project-context/1.define/prd.md`, `project-context/1.define/sad.md`, `project-context/2.build/build-plan.md`, `project-context/2.build/setup.md`, `project-context/2.build/backend.md`, `project-context/2.build/frontend.md`

## 1. QA Scope

This artifact defines the Smart Trade MVP test scenarios from the QA perspective.

The scenarios are split into:

- **Executable now**: B0-B5 behavior currently implemented.
- **Prepared for later increments**: B6-B8 behavior required by PRD/SAD but not implemented yet.

QA must not validate with real capital unless the Agentic Architect explicitly approves a live-readiness test window. B8 live tests must be preceded by B6 paper evidence and B7 readiness approval.

## 2. Current Test Baseline

Current implemented increments:

- B0: project skeleton, FastAPI health, Alembic startup, Angular shell.
- B1: domain/persistence/API read contracts and command request audit.
- B2: minimal Angular + PrimeNG operational console.
- B3: public CCXT OHLCV ingestion and feature pipeline.
- B4: strategy plugin contract, default strategy registration, strategy selection gate, frontend strategy requirements visibility.
- B5: model training, walk-forward validation, holdout backtest, model artifact persistence, and manual approval gate.

Current automated baseline:

```bash
cd backend
uv run pytest
uv run ruff check .

npm --prefix frontend run build
```

Expected current result:

- Backend tests pass.
- Backend lint passes.
- Frontend production build passes.
- Known frontend warnings may remain for bundle/style warning budgets while below error budgets.

## 3. Scenario Conventions

Severity:

- **Critical**: unsafe trading behavior, secret leakage, model approval bypass, state corruption.
- **High**: incorrect gate behavior, traceability loss, data leakage/look-ahead, broken operator evidence.
- **Medium**: degraded diagnostics, missing UI evidence, recoverable API/contract defect.
- **Low**: cosmetic or non-blocking quality issue.

Evidence:

- Automated test name, curl output, screenshot path, migration output, log excerpt, or database assertion.
- Any failure must include reproduction steps and affected requirement IDs.

## 4. Executable Now - B0/B1 Platform and API Contracts

| ID | Scenario | Requirements | Steps | Expected Result | Severity |
| --- | --- | --- | --- | --- | --- |
| QA-B0-001 | Backend health reports service status | RF3.1 | Start backend and call `GET /health` and `GET /api/health`. | Both return `status=ok` without exposing secrets. | Medium |
| QA-B0-002 | DB health fails safely when DB is unavailable | RNF5.11, DR6.2 | Configure invalid `SMART_TRADE_DATABASE_URL`, start/call DB health. | DB check fails clearly; no partial trading behavior starts. | High |
| QA-B0-003 | Startup migrations run before API readiness | DR6.2, SAD migration policy | Start backend against fresh SQLite/MySQL test DB. | Alembic reaches head before dependent read endpoints are used. | High |
| QA-B1-001 | Empty read models return safe NOT_READY state | AC8.6, RF3.1 | Call config, strategies, models, operation, events on fresh DB. | Operation state is `NOT_READY`; blockers include missing selected strategy and missing approved/active model where applicable. | High |
| QA-B1-002 | Command request is persisted and auditable | RF3.3, DR6.9 | POST `RETRAIN_MODEL` command. | Command row is persisted with requestor, payload, timestamp, and `REQUESTED` status. | Medium |
| QA-B1-003 | Unsupported command does not execute behavior | RF3.3, RNF5.11 | POST command outside enabled command set. | Command is rejected/audited; no training/trading starts. | High |
| QA-B1-004 | Frontend does not access forbidden resources | RF3.2, RF3.4, RF4.8, RNF5.5 | Inspect frontend source/build and browser network calls. | UI calls only backend `/api/*`; no DB, log file, artifact, credentials, CCXT, or private exchange access. | Critical |

## 5. Executable Now - B2 Frontend Console

| ID | Scenario | Requirements | Steps | Expected Result | Severity |
| --- | --- | --- | --- | --- | --- |
| QA-B2-001 | Dashboard renders with backend available | RF4.7, RF4.9 | Start backend/frontend and open `/`. | Console renders shell, mode, readiness, strategy/model/event areas. | Medium |
| QA-B2-002 | Dashboard handles backend unavailable | RF3.5, RNF5.12 | Stop backend, keep frontend running. | UI shows backend unavailable state; no direct fallback to restricted resources. | High |
| QA-B2-003 | Paper/live mode is visually distinct | RF4.7 | Set mode config to paper/live in controlled environment. | UI clearly displays mode value; live must not imply execution is enabled by UI alone. | High |
| QA-B2-004 | Registry and log empty states are usable | RF4.6, RF4.9 | Use fresh DB with no events/models. | Tables show empty states without misleading operational readiness. | Medium |
| QA-B2-005 | Chart placeholder cannot be mistaken for real market evidence | RF4.3, RF4.4 | Inspect operation view before B6 chart data exists. | UI labels placeholder/sample data clearly. | Medium |

## 6. Executable Now - B3 Market Data and Feature Pipeline

| ID | Scenario | Requirements | Steps | Expected Result | Severity |
| --- | --- | --- | --- | --- | --- |
| QA-B3-001 | Public OHLCV ingestion persists candles | RF1.1, AC8.1 | POST `/api/data/ingestion-runs` with small limit against Bybit public data or fake adapter. | Candles are persisted for configured exchange/symbol/timeframe; run status is completed. | High |
| QA-B3-002 | Ingestion is idempotent | RF1.2, AC8.1 | Run same ingestion twice. | Second run does not duplicate candle rows; inserted count is zero or only new rows. | High |
| QA-B3-003 | Feature generation creates versioned schema | RF1.3, AC8.2, DR6.5 | Generate features after enough candles. | `b3-talib-basic-v1` exists; feature rows reference that schema. | High |
| QA-B3-004 | Feature generation does not use future candles | RF1.6, AC8.3, DR6.5 | Use deterministic candle fixture and validate feature row windows. | Each feature row depends only on current/prior candle values. | Critical |
| QA-B3-005 | Data status read model reflects latest state | RF3.1, RF4.1 | Call `GET /api/data/status` after ingestion. | Candle count, feature count, latest candle, schema, and latest run match DB state. | Medium |
| QA-B3-006 | CCXT public failure is surfaced safely | RF2.7, RNF5.11 | Simulate adapter timeout/rate limit/unavailable dependency. | API returns controlled error; no partial success is reported as completed. | High |
| QA-B3-007 | Public data path does not require private credentials | RF3.4, RNF5.5 | Unset exchange credentials and run B3 ingestion. | Public ingestion works or fails for public reasons only; no credential leak. | Critical |

## 7. Executable Now - B4 Strategy Plugin and Selection Gates

| ID | Scenario | Requirements | Steps | Expected Result | Severity |
| --- | --- | --- | --- | --- | --- |
| QA-B4-001 | Default strategy registers through plugin discovery | RF2.5.1, RF2.5.2, RF2.5.3, AC8.16 | Start backend or call registration service/API. | `default_rsi_xgboost_long` is persisted with metadata, schema, features, and model roles. | High |
| QA-B4-002 | Strategy API exposes model role requirements | RF2.5.2.2, RF3.7, RF4.9 | Call `GET /api/strategies`. | Response includes role `entry_confirmation`, model type `xgboost`, binary output contract, and required statuses. | High |
| QA-B4-003 | Strategy API exposes required feature contract | RF2.5.1, DR6.5, RF3.7 | Call `GET /api/strategies`. | Response includes B3 feature names required by the default strategy. | High |
| QA-B4-004 | Strategy cannot be selected without required features | RF2.5.5, RF2.5.20, AC8.17 | Fresh DB with no B3 feature schema, call `POST /api/strategies/select`. | API rejects selection with missing required features. | Critical |
| QA-B4-005 | Strategy can be selected when B3 features are compatible | RF2.5.4, AC8.16 | Insert/generate compatible B3 schema, then select strategy. | One selected strategy row exists with status `SELECTED`; operation blocker for missing selected strategy clears. | High |
| QA-B4-006 | Only one strategy can be selected at a time | RF2.5.4 | Select a strategy, then select again or select another compatible strategy fixture. | Previous selected record becomes inactive; only latest row is `SELECTED`. | High |
| QA-B4-007 | Invalid parameters are rejected | RF2.5.2.1, RF2.5.20 | Submit invalid thresholds or invalid risk relationships. | API rejects selection; no selected strategy changes. | High |
| QA-B4-008 | Incompatible market/timeframe/direction is rejected | RF2.5.5, AC8.17 | Override runtime context in service-level test. | Compatibility fails for non-spot, non-long-only, or non-`1m` runtime. | Critical |
| QA-B4-009 | Risk rules are visible to backend/frontend | RF2.5.10-RF2.5.17, RF3.7, RF4.9 | Call strategy API and inspect dashboard registry. | API returns stop-loss, one-position, take-profit/protected-exit rules; frontend shows strategy readiness/requirements. | High |
| QA-B4-010 | Strategy registration does not bypass model approval | RF2.5.20, AC8.6 | Select compatible strategy without approved model. | Operation remains `NOT_READY` with missing compatible approved/active model blocker. | Critical |

## 8. Executable Now - B5 Training, Validation, Backtest, Approval

| ID | Scenario | Requirements | Steps | Expected Result | Severity |
| --- | --- | --- | --- | --- | --- |
| QA-B5-001 | Training window excludes final holdout | RF1.5, AC8.3 | Run training with known time windows. | No holdout timestamps appear in training rows or fitted data. | Critical |
| QA-B5-002 | Walk-forward validation uses only past-to-future folds | RF1.6, AC8.4 | Inspect validation fold boundaries. | Each fold trains on earlier data and validates on later data only. | Critical |
| QA-B5-003 | Model role matches selected strategy requirements | RF1.7, RF2.5.2.2 | Train for default strategy. | Model metadata has strategy ID/version and role `entry_confirmation`. | High |
| QA-B5-004 | Backtest uses complete selected strategy logic | RF1.8, AC8.4 | Run holdout backtest. | RSI/IFR, model confirmation, stops, take profit, break even, trailing stop, and exits are included. | Critical |
| QA-B5-005 | Metrics are persisted with model candidate | RF1.9, AC8.5 | Complete validation/backtest. | Precision class 1, trade count, net PnL, profit factor, max drawdown, win rate, losing streak, and walk-forward evidence are persisted. | High |
| QA-B5-006 | Approval is blocked below thresholds | RF1.11, DR6.6 | Attempt approval with failing metrics. | Model remains non-approved; rejection/failure reason is auditable. | Critical |
| QA-B5-007 | Approval succeeds only with matching evidence | RF1.12, AC8.6 | Approve model that passes thresholds and metadata checks. | Status becomes `APPROVED`; approval timestamp/event is persisted. | High |
| QA-B5-008 | Corrupt or missing artifact cannot be approved/loaded | RF2.3, RNF5.11 | Delete/corrupt artifact after metadata exists. | Approval/loading fails safe with clear operator evidence. | Critical |
| QA-B5-009 | Feature schema mismatch blocks model compatibility | DR6.7, RF2.2 | Change live feature schema after training. | Model is not considered compatible for operation. | Critical |

Current B5 automated coverage:

- `tests/test_model_training.py::test_training_creates_backtested_model_with_temporal_evidence`
  - validates chronological training/holdout separation;
  - validates walk-forward validation boundaries;
  - validates strategy/model-role/feature-schema traceability;
  - validates persisted walk-forward windows and backtest trades;
  - validates persisted backtested model metrics and artifact file.
- `tests/test_model_training.py::test_model_approval_is_blocked_until_thresholds_pass`
  - validates approval threshold blocking for weak metrics.
- `tests/test_model_training.py::test_model_approval_succeeds_with_valid_artifact_and_metrics`
  - validates positive approval path, `APPROVED` status, and approval timestamp.
- `tests/test_model_training.py::test_model_approval_is_blocked_when_artifact_is_missing_or_corrupt`
  - validates approval blocking for missing artifact and invalid JSON artifact.

Current B5 verification evidence:

```bash
cd backend
uv run pytest
uv run ruff check .
SMART_TRADE_DATABASE_URL=sqlite+pysqlite:////tmp/smart_trade_b5_migration.db uv run alembic upgrade head
SMART_TRADE_DATABASE_URL=sqlite+pysqlite:////tmp/smart_trade_b5_migration.db uv run alembic current
uv run --group training python -c "import xgboost; print(xgboost.__version__)"

npm --prefix frontend run build
```

Results:

- Backend: `14 passed`, ruff `All checks passed`.
- Alembic: upgraded to `20260614_0003 (head)`.
- XGBoost import: `3.2.0`.
- Frontend: production build succeeded with known warning-level budgets.

## 9. Prepared for B6 - Paper Inference and Strategy Runtime

| ID | Scenario | Requirements | Steps | Expected Result | Severity |
| --- | --- | --- | --- | --- | --- |
| QA-B6-001 | Paper loop cannot start without selected strategy | AC8.6 | Attempt paper start with no selected strategy. | Start is blocked and audited. | Critical |
| QA-B6-002 | Paper loop cannot start without approved matching model role | RF1.12, RF2.3, AC8.6 | Select strategy but provide no approved model. | Start is blocked with missing role reason. | Critical |
| QA-B6-003 | Inference is minute-aligned after closed candle | RF2.1, AC8.7 | Run paper loop with controlled clock/candles. | Inference runs after expected M1 close and does not use incomplete candle. | High |
| QA-B6-004 | Binary model output contract is enforced | RF2.4 | Model returns invalid non-binary output. | Decision fails safe; no entry/exit order is simulated from invalid signal. | Critical |
| QA-B6-005 | Default strategy enters long only under complete conditions | RF2.5.7, RF2.5.8, AC8.8 | Simulate oversold RSI, signal `1`, balance and limits valid. | One paper long entry is created and persisted. | Critical |
| QA-B6-006 | Additional entry signals do not scale position | RF2.5.9, AC8.9 | Emit repeated entry conditions while position open. | No additional position quantity is added. | Critical |
| QA-B6-007 | Initial stop and take-profit/profit handling are set | RF2.5.10, RF2.5.11 | Open a paper position. | Position has initial stop and take-profit/protected-exit state. | Critical |
| QA-B6-008 | Break-even and trailing stop never move protection downward | RF2.5.12-RF2.5.15, AC8.10 | Simulate favorable then adverse movement. | Stop only moves upward for long position after protection activation. | Critical |
| QA-B6-009 | Loss of confirmation exits according to configured behavior | RF2.5.16, RF2.5.17 | Simulate favorable price then model signal `0`. | Strategy exits or triggers configured protected exit behavior. | High |
| QA-B6-010 | Restart recovers state without duplicate simulated orders | SAD restart behavior, B6 exit criteria | Stop/restart paper runtime with open/pending state. | State reconstructs from DB; no duplicate order/position records are created. | Critical |

## 10. Prepared for B7 - Live Readiness Gate

| ID | Scenario | Requirements | Steps | Expected Result | Severity |
| --- | --- | --- | --- | --- | --- |
| QA-B7-001 | Seven-day paper gate is enforced | PRD assumptions, B7 scope | Attempt live enablement before 7 consecutive paper days. | Live enablement is blocked. | Critical |
| QA-B7-002 | Trade count/readiness alternative is enforced | PRD assumptions, B7 scope | Provide fewer than 30 trades before full 7-day run. | Gate follows approved rule: 30 trades or full 7-day run if fewer signals occur. | High |
| QA-B7-003 | Critical unresolved failures block live readiness | RNF5.11, B7 scope | Create unresolved critical operational event. | Live readiness remains blocked and reason visible. | Critical |
| QA-B7-004 | Model/strategy traceability is required for readiness | RNF5.10, DR6.10 | Remove/invalidate traceability fields in paper records. | Readiness fails. | Critical |
| QA-B7-005 | Manual enablement is auditable | B7 scope | Approve live readiness manually. | Command/event records include operator, time, evidence snapshot, and result. | Critical |

## 11. Prepared for B8 - Live Spot Execution

| ID | Scenario | Requirements | Steps | Expected Result | Severity |
| --- | --- | --- | --- | --- | --- |
| QA-B8-001 | Missing credentials fail safe without secret exposure | RF3.4, AC8.15, RNF5.5 | Attempt live startup with missing credentials. | Live does not start; API/logs do not expose secrets. | Critical |
| QA-B8-002 | Exchange limits and precision are validated before order | RF2.5.6, B8 scope | Use mocked exchange limits and invalid order size/precision. | Order is blocked before private submission. | Critical |
| QA-B8-003 | Authorized long entry submits one spot buy order | RF2.5, RF2.6, AC8.8 | In controlled sandbox/mock, emit authorized entry. | Exactly one spot buy request is submitted and persisted with raw response reference. | Critical |
| QA-B8-004 | Authorized exit submits one spot sell order | RF2.5, AC8.11 | In controlled sandbox/mock, trigger exit. | Exactly one spot sell request is submitted and persisted. | Critical |
| QA-B8-005 | Exchange timeout/rate limit preserves state consistency | RF2.7, AC8.12, RNF5.7 | Mock timeout/rate limit during order submission. | Error is logged, order/position state is not falsely marked filled, retry/reconciliation policy is followed. | Critical |
| QA-B8-006 | Restart reconciliation prevents duplicate live orders | SAD restart behavior, B8 scope | Restart after submitted/pending exchange order. | Runtime reconciles exchange/order state before any new order. | Critical |
| QA-B8-007 | Frontend cannot directly execute live trades | RF4.8, RNF5.12 | Inspect frontend bundle and network during live mode. | UI still calls backend commands/read APIs only; no exchange private calls or credentials. | Critical |

## 12. Regression Smoke Suite

Run before every Agentic Architect build gate:

```bash
cd backend
uv run pytest
uv run ruff check .

npm --prefix frontend run build
```

When the local app is running:

```bash
curl -sS http://127.0.0.1:8000/api/health
curl -sS http://127.0.0.1:8000/api/operation/status
curl -sS http://127.0.0.1:8000/api/strategies
curl -sS http://127.0.0.1:8000/api/data/status
curl -sS -I http://127.0.0.1:4200/
```

Minimum smoke expectations through B4:

- API health is ok.
- Frontend returns HTTP 200.
- Default strategy is registered.
- Operation is not ready until a compatible selected strategy and approved/active model exist.
- With selected B4 strategy but no approved/active model, blocker remains for missing compatible approved/active model evidence.

## 13. Current Residual Risks

- B5 training and approval gates are implemented, including artifact existence/JSON integrity checks, but the runtime inference loader and paper operation loop are not implemented until B6.
- Operation remains intentionally blocked without compatible approved/active model evidence.
- B3 feature no-look-ahead behavior has deterministic coverage but should be expanded with explicit boundary fixtures before B6.
- Frontend selection controls and strategy parameter editing are not implemented in B4; selection is API/command mediated.
- Live readiness and live execution must remain untested with real capital until B6/B7 evidence is approved.

## 14. Playwright Execution - 2026-06-14

Executor: @qa.eng  
Tooling: Playwright via temporary Node package at `/tmp/smart-trade-pw`, without changing project dependencies.  
Main backend: `http://127.0.0.1:8000`  
Frontend: `http://127.0.0.1:4200`  
Temporary fresh backend: `http://127.0.0.1:8011`, SQLite `/tmp/smart_trade_qa_pw_fresh.db`

Execution report:

- `/tmp/smart-trade-qa-playwright-results.json`

Screenshots:

- `/tmp/smart-trade-qa-pw-operation.png`
- `/tmp/smart-trade-qa-pw-strategy-registry.png`
- `/tmp/smart-trade-qa-pw-data-pipeline.png`
- `/tmp/smart-trade-qa-pw-backend-unavailable.png`

Result summary:

- Passed: 20
- Failed: 0
- Skipped/not executed in Playwright: B6-B8 future scenarios and selected B0-B5 scenarios that require infrastructure fault injection, exchange variability, or service-level runtime-context overrides.

Executed scenarios:

| ID | Result | Evidence |
| --- | --- | --- |
| QA-B0-001 | PASS | `GET /health` and `GET /api/health` returned `ok`. |
| QA-B0-003 | PASS | Fresh DB backend migrated and registered default strategy. |
| QA-B1-001 | PASS | Fresh operation state returned `NOT_READY` with missing strategy and missing model blockers. |
| QA-B1-002 | PASS | `RETRAIN_MODEL` command persisted as `REQUESTED`. |
| QA-B1-003 | PASS | `START_PAPER` command persisted as `REJECTED`; no operation started. |
| QA-B1-004 | PASS | Browser request capture found no DB, artifact, credential, secret, Bybit, or private exchange access from frontend. |
| QA-B2-001 | PASS | Dashboard rendered with backend online; screenshot captured. |
| QA-B2-002 | PASS | `/api/**` requests were blocked in browser; UI showed backend unavailable state. |
| QA-B2-003 | PASS | Paper mode and read-only state were visible. |
| QA-B2-005 | PASS | Chart placeholder/sample-data warning was visible. |
| QA-B3-005 | PASS | API data status returned candle count, feature count, and feature schema list. |
| QA-B3-005-UI | PASS | Training/Data Pipeline UI showed candle and feature status. |
| QA-B4-001 | PASS | Default strategy registered as `default_rsi_xgboost_long` version `1.0.0`. |
| QA-B4-002 | PASS | Model role `entry_confirmation` exposed as `xgboost` with binary output and approved/active statuses. |
| QA-B4-003 | PASS | Nine B3 required features exposed by strategy API. |
| QA-B4-004 | PASS | Strategy selection rejected on fresh DB without required B3 feature schema. |
| QA-B4-005 | PASS | Strategy selected successfully when compatible B3 features were available. |
| QA-B4-007 | PASS | Invalid strategy parameter `oversold_threshold=60` rejected with HTTP 400. |
| QA-B4-009 | PASS | Frontend Strategy Registry showed strategy requirements and `READY` compatibility. |
| QA-B4-010 | PASS | Selected strategy did not bypass approved-model gate; operation remained `NOT_READY`. |

Not executed in this Playwright run:

- QA-B0-002: DB unavailable/failure injection should be run as a process-startup fault test.
- QA-B2-004: partial empty-state coverage remains from backend API tests; full UI empty-registry state is superseded by B4 startup strategy registration.
- QA-B3-001, QA-B3-002, QA-B3-003: covered by existing backend automated tests and previous smoke; not repeated in Playwright to avoid external public exchange variability.
- QA-B3-004: should be expanded as deterministic service-level fixture before B6.
- QA-B3-006, QA-B3-007: require exchange adapter fault injection and credential-environment assertions.
- QA-B4-006: requires either multiple compatible strategy fixtures or DB-level assertion of deselection history.
- QA-B4-008: requires service-level runtime-context override for non-spot/non-long-only/non-`1m` compatibility.
- B5 UI scenarios were not rerun in Playwright after implementation; current B5 evidence is backend automated tests, migration checks, XGBoost import, and Angular production build.
- B6-B8 scenarios: pending future implementation.

## 15. Review Checklist for Agentic Architect

- Confirm scenario coverage matches MVP scope and does not introduce out-of-scope trading behavior.
- Confirm B6-B8 planned scenarios are acceptable as future gate criteria.
- Confirm whether QA should now implement additional Playwright coverage for B5 model evidence views before B6 begins.

## 16. Audit

- Generated by: @qa.eng
- Action: Updated QA scenario matrix for implemented B0-B5 and planned B6-B8 safety gates.
- Date: 2026-06-14
- Review status: Pending Agentic Architect review.
