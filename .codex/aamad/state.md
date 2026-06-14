# AAMAD Codex State

Created: 2026-06-13 12:15:32 UTC
Repository: `/home/marco/dev/smart-trade`
AAMAD init mode: staging
Repository state: pre-existing
Languages: Python, SQL, TypeScript implied by approved PRD/SAD decisions; repository implementation not started.
Frameworks/libraries: Angular, PrimeNG, TradingView Lightweight Charts, CCXT, XGBoost, TA-Lib, joblib or pickle, MySQL, Alembic, Docker implied by approved PRD/SAD decisions.
Package managers: Python backend uses `uv` with `pyproject.toml` and `uv.lock`; frontend dependency manager remains to be selected during Build setup.
Existing context source: `docs/proposed-solution.md`
Project signal: proposed PRD for a Python-native quantitative trading backend using CCXT, XGBoost, spot long-only execution, and a decoupled Angular + PrimeNG operational frontend.
Backend runtime target: `native-python` unless the Agentic Architect explicitly chooses otherwise.
Frontend stack: Angular + PrimeNG.

## Current Stage

Define phase completed and approved by the Agentic Architect on 2026-06-14. PRD and SAD are final approved for Build handoff. Implementation planning, application bootstrap, and code remain deferred until the Agentic Architect requests the next AAMAD Flow step.

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

## Review Gate

Define phase gate is approved. No next-stage artifact may be generated until the Agentic Architect explicitly requests the next AAMAD Flow step.
