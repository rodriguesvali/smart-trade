---
description: Runtime adapter guidance for building the Smart Trade MVP as a native Python trading system.
globs:
alwaysApply: true
---

# Native Python Trading Adapter Rules

## Purpose
- Define runtime-specific guidance when `AAMAD_TARGET_RUNTIME=native-python`.
- This adapter governs implementation patterns for the generated Python trading MVP.

## Setup
- Use Python as the primary runtime on Linux.
- Approved backend PRD/alignment-implied libraries include CCXT, XGBoost, TA-Lib or pandas-ta, joblib or pickle, MySQL client/ORM dependencies, Alembic, structured logging, web/API framework dependencies selected in SAD/setup, and Docker tooling.
- The concrete package manager, Python version, Python API framework, MySQL client/ORM, frontend build/serving strategy, and container layout must be confirmed in SAD/setup before implementation.
- Configure all secrets through environment variables or non-versioned local files.
- Provide `.env.example` with variable names only.

## Mapping
- Training pipeline: historical ingestion, feature engineering, walk-forward validation, out-of-sample backtest, model artifact persistence, and metrics.
- Model registry: model artifact, metadata, features, parameters, validation/backtest metrics, status, and traceability IDs.
- Inference/execution engine: minute-aligned loop, approved model loading, binary signal generation, CCXT order submission, and state recording.
- Strategy engine: RSI/IFR entry gating, spot long-only position lifecycle, stop loss, take profit, break even, trailing stop, and exit reasons.
- Frontend API/read models: backend-mediated contracts for the Angular + PrimeNG frontend covering model validation, operation, equity, metrics, position state, and logs.
- Persistence: MySQL-backed repositories and read models with Alembic-managed schema migrations.

## Execution
- Enforce the operational sequence: configure asset -> collect history -> train -> validate -> backtest -> approve -> run.
- Never start operational strategy without an `APPROVED` or `ACTIVE` model matching asset, timeframe, features, and parameters.
- Align inference timing to the second `01` of each minute unless SAD changes this requirement.
- Prefer paper mode before live operation and require Agentic Architect approval for live execution.
- Design idempotent database writes and explicit state transitions for positions, orders, model status, and strategy decisions.
- Treat Alembic migrations as reviewed build artifacts; do not apply destructive schema changes without explicit Agentic Architect approval.

## Tools
- Bind exchange access through CCXT with least-privilege API keys.
- Keep private exchange methods isolated behind a narrow execution boundary.
- Use database access patterns that do not block the minute execution path.
- Provide frontend API/read contracts that cannot mutate trade execution state unless explicitly approved.

## Logging
- Persist operational logs with rotation.
- Log model ID, asset, timeframe, signal, RSI/IFR value, decision, order response, position state, and exit reason where applicable.
- Redact credentials and sensitive account data from logs, diagnostics, Prompt Trace, and artifacts.

## Quality Gates
- Validate no look-ahead leakage in training/validation/backtest.
- Validate exchange minimums, precision, notional limits, and liquidity assumptions before execution.
- Validate all model status transitions.
- Validate fail-safe behavior for missing/corrupt/incompatible/unapproved models.
- Validate failure paths for network timeout, API rate limit, order rejection, database write failure, and process restart.

## Failure Policy
- Halt operational start when model, asset, timeframe, feature set, strategy parameters, credentials, or database state are invalid.
- Halt and write Diagnostic when a requested change expands beyond MVP scope or weakens safety gates.
