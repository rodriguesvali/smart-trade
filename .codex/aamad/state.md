# AAMAD Codex State

Created: 2026-06-13 12:15:32 UTC
Repository: `/home/marco/dev/smart-trade`
AAMAD init mode: staging
Repository state: pre-existing
Languages: Python, SQL, TypeScript implied by PRD/alignment decisions; repository implementation not started.
Frameworks/libraries: Angular, PrimeNG, CCXT, XGBoost, TA-Lib or pandas-ta, joblib or pickle, MySQL, Alembic, Docker implied by PRD/alignment decisions.
Package managers: not present in repository; Python and frontend dependency managers remain to be selected during Build setup.
Existing context source: `docs/proposed-solution.md`
Project signal: proposed PRD for a Python-native quantitative trading backend using CCXT, XGBoost, spot long-only execution, and a decoupled Angular + PrimeNG operational frontend.
Backend runtime target: `native-python` unless the Agentic Architect explicitly chooses otherwise.
Frontend stack: Angular + PrimeNG.

## Current Stage

Bootstrap alignment completed. The next step is Agentic Architect review of the AAMAD/Codex adaptation and PRD alignment. Architecture, implementation planning, application bootstrap, and code remain deferred until the Agentic Architect approves the next AAMAD Flow step.

AAMAD files generated from the upstream IDE format were adapted into `.codex/aamad/`. AAMAD Flow should use only the Codex-local files in this repository.

## PRD Alignment Summary

- Objective: build a native Linux/Python quantitative trading MVP for crypto spot markets.
- Scope: one configured asset, M1 timeframe, spot long-only, no margin, no futures, no leverage, no short selling, no position scaling.
- Core modules: training pipeline, approved-model inference/execution engine, strategy and position management, Python backend/API for the frontend, and decoupled Angular + PrimeNG operational frontend.
- Safety gates: model must be trained, temporally validated, backtested out of sample, and approved before operational strategy start.
- Operational constraints: sub-second inference-to-order path, externalized configuration, no committed secrets, durable logs, traceable model IDs.
- Data/model storage: MySQL plus model artifact directory and log files accessed by backend/trading services, with frontend access mediated by Python APIs/read models. Database schema changes are versioned with Alembic.

## Review Gate

No AAMAD artifact may advance to the next stage until the human Agentic Architect reviews it and explicitly approves, requests changes, or redirects the workflow.
