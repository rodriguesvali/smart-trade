# AAMAD Codex State

Created: 2026-06-13 12:15:32 UTC
Repository: `/home/marco/dev/smart-trade`
AAMAD init mode: staging
Repository state: pre-existing with B0 bootstrap approved.
Languages: Python, SQL, TypeScript.
Frameworks/libraries: Angular, PrimeNG, TradingView Lightweight Charts, CCXT, XGBoost, TA-Lib, joblib or pickle, MySQL, Alembic, Docker implied by approved PRD/SAD decisions.
Package managers: Python backend uses `uv` with `pyproject.toml` and `uv.lock`; frontend uses npm with `package-lock.json`.
Existing context source: `docs/proposed-solution.md`
Project signal: proposed PRD for a Python-native quantitative trading backend using CCXT, XGBoost, spot long-only execution, and a decoupled Angular + PrimeNG operational frontend.
Backend runtime target: `native-python` unless the Agentic Architect explicitly chooses otherwise.
Frontend stack: Angular + PrimeNG.

## Current Stage

Define phase completed and approved by the Agentic Architect on 2026-06-14. Build phase B0 setup was completed and approved by the Agentic Architect on 2026-06-14. Build phase B1 was completed and approved by the Agentic Architect on 2026-06-14. Build phase B2 was completed and approved by the Agentic Architect on 2026-06-14. Build phase B3 was completed and approved by the Agentic Architect on 2026-06-14. Build phase B4 was completed and approved by the Agentic Architect on 2026-06-14. Build phase B5 was completed and approved by the Agentic Architect on 2026-06-14. Build phase B6 was completed and approved by the Agentic Architect on 2026-06-14. Build phase B7 was completed and approved by the Agentic Architect on 2026-06-14. Build phase B8 live spot execution was completed and approved by the Agentic Architect on 2026-06-14. Deliver phase operations runbook has been drafted and is pending Agentic Architect review. QA scenario planning for B0-B8 has been updated with B8 evidence and remains pending Agentic Architect review.

AAMAD files generated from the upstream IDE format were adapted into `.codex/aamad/`. AAMAD Flow should use only the Codex-local files in this repository.

## Define Summary

- Objective: build a native Linux/Python quantitative trading MVP for crypto spot markets.
- Scope: Bybit spot `BTC/USDT`, M1 timeframe, 1,000 USD initial capital, spot long-only, one selected strategy active at a time, one open position at a time, no margin, no futures, no leverage, no short selling, no position scaling.
- Core modules: training pipeline, approved-model inference/execution engine, plugin-based strategy registry with strategy-declared model roles, strategy and position management, Python backend/API for the frontend, and decoupled Angular + PrimeNG operational frontend.
- Safety gates: model roles required by the selected strategy must be trained, temporally validated, backtested out of sample, manually approved, and `APPROVED` or `ACTIVE` before operational strategy start.
- Operational constraints: sub-second inference-to-order path, externalized configuration, no committed secrets, durable logs, traceable model IDs/model roles, manual live enablement after paper readiness.
- Data/model storage: MySQL plus model artifact directory and log files accessed by backend/trading services, with frontend access mediated by Python APIs/read models. Database schema changes are versioned with Alembic.
- Frontend: Angular + PrimeNG, TradingView Lightweight Charts, no authentication for MVP.
- Build/runtime decisions: Python 3.14, `uv`, TA-Lib, XGBoost, CCXT, MySQL, Alembic migrations executed on backend startup.

## Approved Artifacts

- `project-context/1.define/prd.md`
- `project-context/1.define/sad.md`
- `project-context/2.build/build-plan.md`
- `project-context/2.build/setup.md`
- `project-context/2.build/backend.md`
- `project-context/2.build/frontend.md`

## Pending Artifacts

- `project-context/2.build/qa.md`
- `project-context/3.deliver/operations-runbook.md`

## Review Gate

Deliver phase operations runbook is pending Agentic Architect review. QA scenario planning remains pending review. Do not advance to another Deliver artifact until the Architect explicitly approves, requests changes, or redirects.
