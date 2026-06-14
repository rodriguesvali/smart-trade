# Operations Runbook - Smart Trade MVP

Status: Draft for Agentic Architect review  
Persona: @qa.eng with @system.arch handoff  
Date: 2026-06-14  
Source artifacts: `project-context/1.define/prd.md`, `project-context/1.define/sad.md`, `project-context/2.build/build-plan.md`, `project-context/2.build/backend.md`, `project-context/2.build/frontend.md`, `project-context/2.build/qa.md`

## 1. Purpose

This runbook defines the controlled path from local deployment to paper operation and live-readiness review for the Smart Trade MVP.

It does not authorize real-capital operation by itself. Live execution remains blocked unless all configured gates pass, live credentials are injected from the environment, manual readiness is enabled, and the Agentic Architect approves the live test window.

## 2. Operating Boundary

Allowed MVP operation:

- Exchange: Bybit spot through CCXT.
- Symbol: `BTC/USDT`.
- Timeframe: `1m`.
- Mode progression: setup -> data -> strategy selection -> training -> approval -> paper -> readiness -> live.
- Direction: long-only.
- Position rule: one open position at a time.
- Strategy rule: one selected strategy active at a time.
- Frontend: read/control only through backend `/api/*`.

Disallowed operation:

- Futures, margin, leverage, short selling, hedge mode, position scaling, averaging down, pyramiding, martingale, concurrent strategies, or direct frontend exchange access.
- Real-capital tests before explicit Agentic Architect approval for a bounded live window.

## 3. Required Configuration

Backend environment values:

```bash
SMART_TRADE_ENVIRONMENT=development
SMART_TRADE_DATABASE_URL=mysql+pymysql://smart_trade:smart_trade@mysql:3306/smart_trade
SMART_TRADE_RUN_MIGRATIONS_ON_STARTUP=true
SMART_TRADE_MODEL_ARTIFACT_DIR=var/model-artifacts
SMART_TRADE_ALLOW_LIVE_TRADING=false
SMART_TRADE_LIVE_TRADING_ACK=
SMART_TRADE_EXCHANGE_API_KEY=
SMART_TRADE_EXCHANGE_API_SECRET=
SMART_TRADE_EXCHANGE_API_PASSWORD=
SMART_TRADE_LIVE_ORDER_QUOTE_AMOUNT_USD=25
SMART_TRADE_LIVE_MAX_ORDER_QUOTE_AMOUNT_USD=100
SMART_TRADE_LIVE_MAX_FEE_RATE=0.005
```

Live credentials must stay outside source control and frontend bundles. `SMART_TRADE_ALLOW_LIVE_TRADING` must remain `false` until the live-readiness gate has been reviewed and approved.

## 4. Local Startup

Container startup:

```bash
docker compose up --build
```

Backend local startup:

```bash
cd backend
uv sync
uv run uvicorn smart_trade_backend.main:app --host 0.0.0.0 --port 8000
```

Frontend local startup:

```bash
cd frontend
npm install
npm start
```

Health checks:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/health/db
curl -sS http://127.0.0.1:8000/api/health
curl -sS http://127.0.0.1:4200/
```

Expected result:

- Backend health is `ok`.
- Database health is available.
- Alembic startup migration reaches head.
- Frontend loads and uses backend `/api/*` only.

## 5. Pre-Operation Verification

Run before any paper/live progression:

```bash
cd backend
uv run pytest
uv run ruff check .

npm --prefix ../frontend run build
```

Expected result:

- Backend tests pass.
- Backend lint passes.
- Angular production build passes.
- No real exchange private endpoint is called by tests.

## 6. Data, Strategy, and Model Sequence

Register strategies:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/strategies/register
```

Collect public candles:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/data/ingestion-runs \
  -H "Content-Type: application/json" \
  -d '{"limit":1000}'
```

Check data status:

```bash
curl -sS http://127.0.0.1:8000/api/data/status
```

Select the default strategy after compatible features exist:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/strategies/select \
  -H "Content-Type: application/json" \
  -d '{"strategy_registry_id":"default_rsi_xgboost_long","parameters":{}}'
```

Train selected strategy models:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/models/train
```

Review model evidence:

```bash
curl -sS http://127.0.0.1:8000/api/models
curl -sS http://127.0.0.1:8000/api/models/training-runs
curl -sS http://127.0.0.1:8000/api/models/<model_id>/evidence
```

Approve only after metrics satisfy the configured criteria:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/models/<model_id>/approve
```

No-go conditions:

- Missing or incompatible selected strategy.
- Missing B3 feature schema.
- Holdout/training evidence is absent.
- Walk-forward/backtest evidence is absent.
- Model artifact is missing or corrupt.
- Approval thresholds are not met.

## 7. Paper Operation Gate

Start paper replay:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/paper/runs \
  -H "Content-Type: application/json" \
  -d '{"limit":500}'
```

Inspect paper and operation status:

```bash
curl -sS http://127.0.0.1:8000/api/paper/status
curl -sS http://127.0.0.1:8000/api/operation/status
curl -sS http://127.0.0.1:8000/api/events
```

Minimum paper evidence before live readiness:

- At least 7 consecutive paper days.
- At least 30 simulated trades, or a full 7-day run if fewer signals occur.
- No unresolved critical failures.
- Consistent position/order state.
- Complete model and strategy traceability.
- Exchange limit evidence available.
- Paper results inside approved risk thresholds.

## 8. Live Readiness Gate

Check readiness:

```bash
curl -sS http://127.0.0.1:8000/api/live-readiness/status
```

Enable readiness only after every check passes:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/live-readiness/enable \
  -H "Content-Type: application/json" \
  -d '{"requested_by":"agentic-architect"}'
```

No-go conditions:

- Any readiness blocker remains.
- Any pending/unreconciled order exists.
- Any unresolved critical event exists.
- Model/strategy traceability is incomplete.
- Paper window or trade-count evidence is insufficient.
- The operator cannot explain the latest strategy, model, position, and risk state from backend evidence.

## 9. Live Execution Controls

Live status:

```bash
curl -sS http://127.0.0.1:8000/api/live/status
```

Live execution requires all of the following:

- `SMART_TRADE_ALLOW_LIVE_TRADING=true`.
- `SMART_TRADE_LIVE_TRADING_ACK=I_UNDERSTAND_LIVE_RISK`.
- Private exchange credentials are present in environment only.
- Latest live-readiness review is `READY`.
- A selected compatible strategy exists.
- A compatible approved or active model exists.
- No unreconciled live order exists.
- Exchange limits, precision, balance, and fee checks pass.

Bounded live order command after approval:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/live/orders \
  -H "Content-Type: application/json" \
  -d '{"side":"BUY","requested_by":"agentic-architect","idempotency_key":"approved-live-window-001","quote_amount_usd":25}'
```

The frontend must remain evidence-only for live operation. It may display live status and recent orders from backend read models, but it must not store credentials or call exchange APIs.

## 10. Incident Response

Stop live progression immediately when:

- Backend reports an exchange timeout, rate limit, invalid response, or rejected order that leaves order state uncertain.
- Any live order is pending/unreconciled.
- Database writes fail or schema compatibility fails.
- Model artifact loading fails.
- Feature schema differs from the approved model schema.
- Frontend displays inconsistent state compared with backend API evidence.

Operator response:

1. Keep `SMART_TRADE_ALLOW_LIVE_TRADING=false` until state is reconciled.
2. Inspect `/api/live/status`, `/api/operation/status`, `/api/events`, and database-backed order/position evidence.
3. Do not submit another live order while pending live orders exist.
4. Preserve logs and command responses for review.
5. Resume only after the Agentic Architect approves the reconciled state.

## 11. Release Checklist

- B0-B8 review gates approved.
- `project-context/2.build/qa.md` reviewed or explicitly deferred.
- Backend tests and ruff pass.
- Frontend production build passes.
- Alembic migration reaches head on a fresh database.
- `.env` files are local-only and contain no committed secrets.
- Model artifact directory is writable and not served to frontend.
- Frontend calls backend `/api/*` only.
- Paper evidence satisfies B7 criteria.
- Live credentials and live flags are disabled by default.
- Agentic Architect has approved the exact live test window, amount, and stop conditions.

## 12. Residual Risks

- B8 uses fake-exchange automated tests only; no real Bybit private endpoint or sandbox order has been executed.
- Long-running scheduler hardening remains future work before unattended live operation.
- Real exchange metadata, account fee tier, jurisdiction availability, and liquidity must be validated in the approved live window.
- Frontend B5-B8 evidence views have build/code-review evidence, but full Playwright rerun across all model/paper/readiness/live views remains a QA follow-up.

## 13. Audit

- Generated by: @qa.eng with @system.arch handoff.
- Action: Created Deliver phase operations runbook and live-readiness control checklist after B8 approval.
- Date: 2026-06-14.
- Review status: Pending Agentic Architect review.
