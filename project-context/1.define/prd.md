# Product Requirements Document - Smart Trade MVP

Status: Approved by Agentic Architect  
Persona: @product-mgr  
Date: 2026-06-13  
Source: `docs/proposed-solution.md` plus AAMAD project alignment in `AGENTS.md` and `.codex/aamad/state.md`

## 1. Executive Summary

Smart Trade is a quantitative trading platform for crypto spot markets. The MVP focuses on a single configured asset on the M1 timeframe, using a native Python backend for data collection, model training, validation, inference, strategy execution, persistence, and backend APIs. The operational frontend is decoupled and built with Angular + PrimeNG.

The product objective is to let an operator configure one crypto spot asset, collect historical data, train an XGBoost model, validate it temporally, run an out-of-sample backtest, approve or reject the model, and only then run a long-only strategy using direct CCXT exchange integration.

The core value proposition is operational control over an ML-assisted spot strategy with explicit model approval gates, traceable inference decisions, durable execution state, and a frontend that exposes training, validation, operation, logs, and risk evidence without coupling the UI to trading execution. Although the MVP ships with one strategy, the product must support a strategy registry so additional strategies can be implemented, registered, validated, selected, and operated without rewriting the execution platform.

The MVP is deliberately narrow: one configured asset, one selected strategy active at a time, one open position at a time, spot long-only, no margin, no futures, no leverage, no short selling, no position scaling, no pyramiding, and no martingale.

## 2. Scope and Operating Boundaries

### In Scope

- Crypto spot market operation through CCXT.
- One configured exchange and symbol for the MVP.
- M1 candle timeframe.
- Long-only strategy execution.
- Strategy registry for implementing and registering multiple strategies.
- One selected operational strategy active at a time for the MVP.
- One open position at a time.
- XGBoost binary confirmation model.
- RSI/IFR as the primary technical entry condition before model confirmation.
- Training pipeline with historical ingestion, feature engineering, walk-forward validation, and final out-of-sample backtest.
- Model lifecycle with approval gate before operational use.
- Direct order execution through exchange private APIs.
- Explicit strategy and position state.
- MySQL persistence with Alembic-managed schema migrations.
- Python backend/API contracts for frontend access.
- Angular + PrimeNG operational frontend.
- Externalized configuration and non-versioned secrets.
- Paper/live readiness workflow, with paper mode expected before live operation.

### Out of Scope

- Futures, margin, leverage, short selling, hedge mode, or derivatives execution.
- Multiple configured assets running concurrently.
- Multiple strategies running concurrently for the same asset in the MVP.
- Multiple open positions.
- Position scaling, averaging down, pyramiding, martingale, or reinforcement entries.
- Portfolio optimization across assets.
- Fully autonomous model approval without operator or configured policy approval.
- Frontend direct access to exchange credentials or trade execution methods.
- Chat-oriented agent runtime, CrewAI product runtime, Next.js frontend, Streamlit dashboard, or Dash dashboard unless explicitly re-approved by the Agentic Architect.

## 3. System Workflow

The MVP workflow must be sequential and auditable:

1. Register available strategies and select the operational strategy for the configured asset.
2. Configure the exchange, spot symbol, M1 timeframe, capital allocation, selected strategy parameters, RSI/IFR thresholds for the MVP strategy, stop loss, take profit, break even, trailing stop, and approval criteria.
3. Validate that the configured asset satisfies exchange limits, precision rules, notional minimums, and M1 liquidity assumptions.
4. Collect historical M1 candles through CCXT public APIs.
5. Generate technical features from price and volume data.
6. Reserve a final holdout window for out-of-sample backtesting.
7. Run walk-forward validation inside the training window.
8. Train an XGBoost model candidate without using holdout data.
9. Backtest the complete selected strategy on the holdout window.
10. Persist model artifact, metadata, metrics, strategy identity, strategy parameters, and status.
11. Approve or reject the model.
12. Start paper or live strategy only if an approved or active model matches the configured asset, timeframe, feature set, selected strategy, and strategy parameters.
13. Run minute-aligned inference and strategy decisions, execute authorized orders through CCXT, and persist all decisions, signals, orders, fills, positions, and logs.

## 4. Functional Requirements

### Module 1: Training Pipeline

- RF1.1: The system must collect historical M1 OHLCV data through CCXT public connections for the configured exchange and symbol.
- RF1.2: The system must store historical candles, derived features, model metadata, validation metrics, backtest results, strategy decisions, positions, orders, fills, and logs in MySQL-backed structures or durable log files as appropriate.
- RF1.3: The system must generate feature data from price and volume, including RSI/IFR, Bollinger Bands, returns, volatility, volume variation, and other approved derived indicators.
- RF1.4: The training window must be configurable, with an initial default recommendation of 60 days of M1 data before the final holdout window.
- RF1.5: The pipeline must reserve a configurable final holdout window, initially recommended as 3 days, and must not use this data for training.
- RF1.6: The pipeline must run walk-forward validation within the training period to reduce overfitting and look-ahead bias.
- RF1.7: The pipeline must train an XGBoost candidate model that produces a binary confirmation signal.
- RF1.8: The pipeline must run an out-of-sample backtest of the selected strategy. For the MVP default strategy, this includes RSI/IFR entry condition, model confirmation, long spot entry, stop loss, take profit, break even, trailing stop, and inference-conditioned profit handling.
- RF1.9: The pipeline must generate at minimum precision for class `1`, trade count, simulated net PnL, profit factor, maximum drawdown, win rate, and longest losing streak.
- RF1.10: The pipeline must persist each model artifact as `.joblib` or `.pkl` plus metadata including asset, exchange, timeframe, training period, holdout period, feature set, strategy ID, strategy version, strategy parameters, validation metrics, backtest metrics, artifact path, and model status.
- RF1.11: The model lifecycle must support `TRAINED`, `VALIDATED`, `APPROVED`, `ACTIVE`, `REJECTED`, `EXPIRED`, and `RETIRED`.
- RF1.12: The system must prevent operational strategy start unless a matching model is `APPROVED` or `ACTIVE`.

### Module 2: Inference and Execution

- RF2.1: The inference loop must align to the M1 cycle and run after the latest candle is expected to be closed, initially targeting second `01` of each minute.
- RF2.2: The inference service must load only an approved or active model matching the configured exchange, symbol, timeframe, feature set, selected strategy ID, selected strategy version, and strategy parameters.
- RF2.3: If the approved model is absent, corrupted, incompatible, expired, or mismatched, the system must fail safe and not start operational strategy execution.
- RF2.4: The inference output must be binary: `1` means favorable confirmation for long entry or long continuation, and `0` means no confirmation.
- RF2.5: The execution adapter must send authorized spot market buy and sell orders through CCXT private APIs.
- RF2.6: The execution path must persist inference result, model ID, strategy decision, order request, exchange response, fill data, and resulting position state.
- RF2.7: The execution module must handle temporary exchange errors, rate limits, timeouts, invalid responses, and rejected orders without losing strategy state consistency.

### Module 2.5: Strategy and Position Management

- RF2.5.1: The system must provide a strategy registry that lists available strategies by stable ID, name, version, description, supported market type, supported direction, required parameters, required features, model requirements, and operational status.
- RF2.5.2: The system must allow new strategies to be implemented and registered for use by the training, validation, backtest, inference, execution, persistence, and frontend layers through a stable strategy contract.
- RF2.5.3: The MVP must ship with one registered default strategy based on RSI/IFR oversold detection plus XGBoost binary confirmation.
- RF2.5.4: The MVP must support only one selected operational strategy active at a time for the configured asset.
- RF2.5.5: A strategy must not be selectable for operation unless it declares compatibility with spot long-only execution and the configured asset/timeframe requirements.
- RF2.5.6: Before operation, the system must validate exchange minimum quantity, price precision, quantity precision, notional minimum, available balance, and expected liquidity.
- RF2.5.7: For the MVP default strategy, when no position is open, the strategy must first check whether RSI/IFR indicates oversold conditions according to configured thresholds.
- RF2.5.8: For the MVP default strategy, the strategy may open a long position only when RSI/IFR is oversold, the model signal is `1`, balance is sufficient, and exchange limits are satisfied.
- RF2.5.9: While a position is open, new entry signals must not create additional entries or increase position size.
- RF2.5.10: Every opened position must have an initial stop loss calculated from executed average entry price and configured risk parameters.
- RF2.5.11: Every opened position must have an initial take profit target or configured profit handling rule.
- RF2.5.12: The strategy must support moving protection to break even when configured favorable movement is reached, accounting for fees where possible.
- RF2.5.13: The strategy must support trailing stop movement after favorable price movement.
- RF2.5.14: For long positions, stop protection must never move downward after being raised.
- RF2.5.15: When continuation inference remains `1`, the strategy may continue moving the trailing stop upward according to configured rules.
- RF2.5.16: When price has moved favorably and continuation inference changes to `0`, the strategy must realize profit or trigger configured exit behavior.
- RF2.5.17: The strategy must close a position when stop loss, protected stop, trailing stop, take profit, or configured loss of confirmation condition is met.
- RF2.5.18: Position state must be explicit, including no position, open position, break-even protected position, trailing-stop position, take-profit triggered position, closing position, and closed position.
- RF2.5.19: Every strategy decision must be logged with strategy ID, strategy version, strategy parameters, RSI/IFR value where applicable, model signal, model ID, decision, entry price, stop loss, take profit, stop movements, break-even activation, continuation checks, exit action, and exit reason.
- RF2.5.20: Strategy registration must not bypass model approval, exchange validation, position constraints, risk controls, or fail-safe behavior.

### Module 3: Python Backend/API

- RF3.1: The backend must expose API/read contracts used by the Angular + PrimeNG frontend.
- RF3.2: The backend must mediate all frontend access to model status, training metrics, validation results, backtest results, operation state, position state, orders, fills, equity data, and logs.
- RF3.3: The backend must provide a controlled command path for manual retraining requests.
- RF3.4: The backend must not expose exchange credentials to the frontend.
- RF3.5: The backend must not allow frontend UI failures to block or delay trading execution.
- RF3.6: Backend read endpoints must be designed so dashboard polling or streaming does not block database writes from training or execution processes.
- RF3.7: The backend must expose read APIs for registered strategies, selected strategy configuration, strategy compatibility status, and strategy-specific parameters.

### Module 4: Angular + PrimeNG Frontend

- RF4.1: The frontend must provide a training/model view showing model status, training period, holdout period, validation metrics, backtest metrics, approval state, confusion matrix, precision, accuracy, and feature importance.
- RF4.2: The frontend must expose a manual retraining control through the backend API.
- RF4.3: The frontend must provide an operation view with real-time or near-real-time candlestick visualization and visual markers for long entries and exits.
- RF4.4: The frontend must show equity curve, realized PnL, unrealized PnL where available, win rate, profit factor, maximum drawdown, trade count, and current position state.
- RF4.5: The frontend must show current RSI/IFR value, latest inference signal, active model ID, and latest strategy decision.
- RF4.6: The frontend must provide a live log terminal or log view with clear severity display for warnings, exchange errors, rate limits, timeouts, and order rejections.
- RF4.7: The frontend must clearly distinguish paper mode from live mode.
- RF4.8: The frontend must not directly execute trades or access exchange private APIs.
- RF4.9: The frontend must show the selected strategy and allow operators to inspect registered strategy metadata and parameters through backend APIs.

## 5. Non-Functional Requirements

- RNF5.1: Backend, training, inference, execution, and support services must run natively on Linux, with Docker-based deployment preferred where useful.
- RNF5.2: The target inference-to-order path should be sub-second under normal operating conditions.
- RNF5.3: Training, execution, backend API, and frontend must be separable processes.
- RNF5.4: API keys, secrets, and credentials must be injected through environment variables or local unversioned configuration.
- RNF5.5: No secrets may be stored in source code, versioned config, committed fixtures, logs, frontend bundles, or API responses.
- RNF5.6: Logs must be durable and support rotation.
- RNF5.7: The execution process must be resilient to temporary network, exchange, and persistence errors.
- RNF5.8: Operational configuration must be externalized, including exchange, symbol, timeframe, selected strategy ID/version, strategy parameters, windows, model path, feature set, approval criteria, RSI/IFR thresholds for the MVP strategy, stop loss, take profit, break even, trailing stop, mode, and credentials.
- RNF5.9: Model artifacts must be replaceable without code changes when metadata and feature compatibility are satisfied.
- RNF5.10: Every inference and operational decision must be traceable to a model ID.
- RNF5.11: The system must fail safe when model, configuration, exchange limits, or persistence prerequisites are invalid.
- RNF5.12: Frontend availability must not be required for strategy execution.
- RNF5.13: The strategy extension mechanism must preserve domain/application boundaries and must not require changes to CCXT execution adapters, database adapters, or frontend internals for every new strategy.

## 6. Data and Model Requirements

- DR6.1: MySQL is the target database for structured application state.
- DR6.2: Alembic must version database schema changes.
- DR6.3: Required entity areas include asset configuration, strategy registry, selected strategy configuration, candles, features, model registry, validation runs, backtest runs, approval events, inference signals, strategy decisions, positions, orders, fills, equity snapshots, operational events, and command requests.
- DR6.4: Model metadata must record artifact location, model type, version, asset, exchange, timeframe, feature list, training window, holdout window, validation method, metrics, strategy ID, strategy version, strategy parameters, approval status, and timestamps.
- DR6.5: Feature generation must be reproducible between training, validation, backtest, and live inference.
- DR6.6: Approval thresholds must be configurable and persisted with the model evaluation result.
- DR6.7: The system must prevent use of a model when the live feature schema differs from the trained feature schema.
- DR6.8: Model status transitions must be auditable.
- DR6.9: Strategy registration and strategy selection changes must be auditable.
- DR6.10: Strategy decisions, validation runs, backtest runs, and operational records must be attributable to strategy ID and strategy version.

## 7. User Experience and Operations

The primary user is an operator responsible for configuring the MVP, approving models, monitoring the strategy, and diagnosing failures. The UI should support operational work rather than marketing presentation.

Expected operator workflows:

1. Review registered strategies and selected strategy metadata.
2. Review configured exchange, symbol, timeframe, capital allocation, selected strategy parameters, risk parameters, and current mode.
3. Trigger or inspect historical data collection and training runs.
4. Review validation and backtest evidence for the selected strategy.
5. Approve or reject a model according to configured criteria and operator judgment.
6. Start paper operation with an approved model and selected compatible strategy.
7. Monitor candle chart, entries, exits, equity curve, model signal, RSI/IFR where applicable, position state, orders, fills, and logs.
8. Escalate to live mode only after readiness criteria are satisfied.
9. Stop or inspect operation when model, strategy, exchange, persistence, or execution errors occur.

Frontend operations must use backend APIs only. Any command that can affect training or operation must be explicit, logged, and reflected back to the UI with status.

## 8. Acceptance Criteria

- AC8.1: Given a configured exchange and symbol, the training pipeline can collect M1 history and persist it.
- AC8.2: Given collected history, the pipeline can generate reproducible features.
- AC8.3: Given configured training and holdout windows, the pipeline excludes holdout data from training.
- AC8.4: Given a candidate model and selected strategy, the pipeline runs walk-forward validation and final out-of-sample strategy backtest.
- AC8.5: Given validation and backtest results, the system persists model artifact, metadata, metrics, and status.
- AC8.6: Given no approved or active matching model for the configured asset, timeframe, selected strategy, and strategy parameters, the strategy cannot start.
- AC8.7: Given an approved matching model, the inference loop can produce minute-aligned binary signals and persist model-linked inference records.
- AC8.8: Given the MVP default strategy, oversold RSI/IFR, binary signal `1`, sufficient balance, and valid exchange limits, the strategy can open one long spot position.
- AC8.9: Given an open position, the strategy ignores additional entry signals for position increase.
- AC8.10: Given an open position, the strategy manages stop loss, take profit, break even, trailing stop, and inference-conditioned exits.
- AC8.11: Given an authorized strategy exit, the execution adapter submits the spot sell order through CCXT and records the exchange response.
- AC8.12: Given exchange/network failures, the execution module records the error and preserves consistent position and order state.
- AC8.13: Given backend state, the Angular + PrimeNG frontend shows model status, validation/backtest evidence, operation state, chart markers, equity curve, metrics, position state, inference signal, RSI/IFR, and logs.
- AC8.14: Given frontend unavailability, backend trading services continue operating.
- AC8.15: Given invalid or missing credentials, the system does not expose secrets and fails safe without live execution.
- AC8.16: Given multiple registered strategies, the system can list them, expose their metadata, select one compatible strategy for the MVP operation, and attribute validation, backtest, model, and operational records to that strategy.
- AC8.17: Given a registered strategy that is incompatible with spot long-only MVP constraints, the system prevents selecting it for operation.

## 9. Open Questions

- OQ9.1: What Python version and dependency manager should be standardized for backend services?
- OQ9.2: Which initial exchange, symbol, capital allocation, and fee/slippage assumptions should be used for MVP defaults?
- OQ9.3: Which indicator library should be selected: TA-Lib, pandas-ta, or another approved package?
- OQ9.4: Which Angular charting library should be used for candlesticks, markers, and equity curve?
- OQ9.5: What exact approval thresholds should determine `APPROVED` versus `REJECTED`?
- OQ9.6: Should model approval be manual-only for MVP, policy-driven, or policy-driven with manual confirmation?
- OQ9.7: What is the mandatory paper-mode duration or evidence threshold before live operation?
- OQ9.8: What are the retention periods for candles, features, logs, model artifacts, validation reports, and execution records?
- OQ9.9: Who owns Alembic migration execution in deployment: startup command, operator command, or CI/CD step?
- OQ9.10: What are the MVP authentication requirements for the operational frontend?
- OQ9.11: What exact strategy registration contract should be used for future strategies, including required methods, metadata, validation hooks, and parameter schema?
- OQ9.12: Should new strategy registration happen through code deployment only for the MVP, or should runtime/plugin loading be supported later?

## 10. Sources

- `docs/proposed-solution.md`
- `AGENTS.md`
- `.codex/aamad/state.md`
- `.codex/aamad/workflow.md`
- `.codex/aamad/templates/prd-template.md`
- `.codex/aamad/agents/product-mgr.md`

## 11. Assumptions

- The Agentic Architect has redirected AAMAD Flow to begin PRD consolidation from `docs/proposed-solution.md`.
- The backend runtime target is `native-python`.
- The frontend stack is Angular + PrimeNG.
- MySQL and Alembic are the current database and migration alignment.
- The MVP should use paper mode before live trading unless the Agentic Architect explicitly removes that gate.
- The MVP ships with one default registered strategy, but the product architecture must support adding more registered strategies later.
- Only one strategy is selected for operation at a time in the MVP.
- Derivatives-only data such as open interest and funding rate are optional and not required for spot-only MVP acceptance.
- Runtime implementation, architecture decisions, project scaffolding, and code generation remain out of scope until this PRD is reviewed and approved.

## 12. Audit

- Generated by: @product-mgr
- Action: Consolidated draft PRD from proposed solution into AAMAD project-context format; revised to require an extensible strategy registry while keeping one active MVP strategy.
- Date: 2026-06-13
- Review status: Approved by Agentic Architect.
- Handoff gate: PRD approved. Next AAMAD Define step may proceed when requested by the Agentic Architect.
