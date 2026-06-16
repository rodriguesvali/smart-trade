# SAD - MVP Pipeline de Treinamento

## 1. Architecture Philosophy and Principles

The MVP architecture prioritizes a safe and traceable training lifecycle before any operational trading capability exists.

Core principles:

- **Training-first scope:** deliver only the strategy catalog, training execution, automatic validation, model evidence, and manual approval/rejection flow.
- **Prepared for multiple strategies:** implement one strategy now, but use a strategy catalog and stable strategy contracts that allow future additions.
- **Model as immutable output:** every training run creates a new trained model record and native XGBoost artifact.
- **No hidden validation:** successful training automatically starts validation, and approval is blocked until the trained model reaches `VALIDATED`.
- **No temporal leakage:** feature generation, scaling, lagging, splitting, early stopping, walk-forward validation, and holdout backtest must preserve chronological boundaries.
- **Backend-mediated frontend access:** Angular + PrimeNG consumes only Python backend/API contracts and never reads MySQL, artifacts, logs, API keys, or external market APIs directly.
- **Versioned persistence:** MySQL stores durable records; Alembic owns schema versioning.
- **Configuration outside code:** exchange/source, symbol, windows, target parameters, XGBoost hyperparameters, artifact directory, and external API settings come from environment/configuration files.

## 2. Stakeholders and Concerns

- **Agentic Architect / operator:** needs clear strategy visibility, training controls, validation evidence, and manual approval decisions.
- **Product Manager:** needs traceability from PRD requirements to implementable architecture.
- **Backend engineer:** needs process boundaries, persistence ownership, lifecycle states, and validation rules.
- **Frontend engineer:** needs read/write API contracts and UI state expectations for `XGBoost Strategies`.
- **QA engineer:** needs acceptance-testable state transitions, data-leakage safeguards, and audit evidence.
- **System architect:** needs the MVP to remain small while preserving future multi-strategy extensibility.
- **External data providers:** CCXT is the primary market-data integration boundary for training data; configured exchanges behind CCXT and explicitly approved sentiment providers are external integration boundaries.

Primary concerns:

- Correct chronological data handling.
- Model reproducibility and portability.
- Traceable approval decisions.
- Safe failure behavior.
- Minimal frontend with no direct privileged access.
- Database migration governance.

## 3. Scope and Constraints

In scope:

- Angular + PrimeNG shell with dashboard frame and `XGBoost Strategies` menu.
- Backend API for strategy listing, strategy detail, training command, training/model status, validation evidence, and approval/rejection.
- One implemented strategy: `RSI Sentiment XGBoost M1`.
- Strategy catalog prepared for multiple strategies.
- Public market/sentiment data ingestion needed for training.
- Feature engineering for RSI/IFR, Open Interest, Long/Short Ratio, and CVD.
- Chronological train, validation-internal, and holdout partitioning.
- XGBoost training with early stopping.
- Automatic walk-forward and holdout validation after successful training.
- Manual approval/rejection of validated models.
- MySQL persistence with Alembic migrations.
- Native XGBoost artifact storage in `.json` or `.ubj`.
- Audit events and logs for critical lifecycle steps.

Out of scope:

- Exchange order execution.
- Paper trading.
- Live trading.
- Position management.
- Private exchange credentials.
- Stop loss, take profit, break even, or trailing stop execution.
- Multiple implemented strategies.
- UI-based strategy code editing.
- Complex authentication.
- Automated hyperparameter search.
- Scheduled retraining.
- Automatic model approval.

Resolved runtime constraints:

- Backend runtime: `native-python`.
- Frontend stack: Angular + PrimeNG.
- Database: MySQL.
- Database versioning: Alembic.
- Runtime target: Linux-native execution, container-friendly.

## 4. Logical View

### Primary Presentation

```text
Angular + PrimeNG Frontend
        |
        | HTTP JSON API
        v
Python Backend/API
        |
        | creates commands / reads state
        v
Training Orchestrator
        |
        +--> Strategy Catalog
        +--> Market/Sentiment Data Ingestion
        +--> Feature Engineering
        +--> XGBoost Trainer
        +--> Validation Pipeline
        +--> Model Registry
        |
        +--> MySQL
        +--> Model Artifact Directory
        +--> Log/Event Sink
```

### Element Catalog

- **Angular + PrimeNG frontend:** presents dashboard shell, strategy table, strategy detail, trained-model table, validation scorecard, and approval/rejection controls.
- **Python Backend/API:** owns all frontend contracts, command validation, read models, status projection, and audit event creation.
- **Training Orchestrator:** coordinates training run lifecycle from `PENDING` to `RUNNING` to `TRAINED` or `FAILED`.
- **Strategy Catalog:** exposes registered strategy metadata and default parameters. MVP contains `RSI Sentiment XGBoost M1`.
- **Market/Sentiment Data Ingestion:** loads configured-timeframe spot price data through CCXT and sentiment proxies for Open Interest, Long/Short Ratio, and CVD from configured public sources.
- **Feature Engineering:** computes RSI/IFR and transforms sentiment features with stationarity and lag rules.
- **XGBoost Trainer:** trains a binary classifier using chronological partitions and early stopping.
- **Validation Pipeline:** automatically runs walk-forward validation and holdout backtest after successful training.
- **Model Registry:** persists trained model metadata, lifecycle status, artifact path, feature schema, validation evidence, and approval decision linkage.
- **MySQL:** durable source of truth for catalog, runs, models, validation results, decisions, and audit events.
- **Model Artifact Directory:** stores native XGBoost `.json` or `.ubj` files.
- **Log/Event Sink:** records operational events and errors for observability and audit.

### Rationale and Analysis

The logical view separates operator experience, API mediation, training workflow, persistence, and artifacts. This supports the PRD’s requirement that the UI can list/open strategies, trigger training, observe status, inspect evidence, and approve/reject models without gaining direct access to database tables or files.

Execution and strategy runtime modules from the broader product vision are intentionally omitted from the MVP logical view. The model approval output is a future input to operational trading, not an active runtime dependency in this phase.

## 5. Process and Runtime View

### Primary Presentation

```text
Process A: Angular frontend dev/build/runtime
Process B: Python Backend/API
Process C: Training worker/orchestrator
Process D: MySQL
Shared: model artifact directory
Shared: log/event storage
```

### Runtime Responsibilities

- **Angular frontend process**
  - Serves the operator UI.
  - Calls backend APIs only.
  - Holds no exchange credentials, database credentials, or artifact paths beyond API-provided display fields.

- **Python Backend/API process**
  - Exposes REST-style API contracts.
  - Validates user commands.
  - Creates training runs and approval/rejection decisions.
  - Serves read models for strategy, model status, metrics, and audit events.
  - Does not execute private exchange orders in this MVP.

- **Training worker/orchestrator process**
  - May run in the same deployable backend container for MVP simplicity or as a separate Python process if build constraints require background isolation.
  - Owns long-running training and validation work.
  - Writes status transitions to MySQL.
  - Writes model artifacts to the configured artifact directory.
  - Emits audit/log events.

- **MySQL process**
  - Stores all durable state.
  - Is accessed only by backend/training processes.

- **Alembic migration execution**
  - Runs from the backend service startup or a dedicated migration command before API readiness.
  - The frontend must not start relying on new fields until migrations are applied.

### Startup Behavior

1. Load environment/configuration.
2. Validate required MySQL connection settings and artifact/log directory paths.
3. Execute Alembic migrations to head or fail startup.
4. Register code-deployed strategies into the strategy catalog.
5. Start backend API.
6. Start frontend separately.

### Failure and Recovery

- If training fails, the training run status becomes `FAILED`, the trained model is not approvable, and the error is persisted.
- If training succeeds but validation fails, the model status becomes `FAILED`, with validation failure evidence.
- If API restarts while training is running, status must be recoverable from MySQL. The MVP may mark interrupted runs as `FAILED` on recovery unless resumable jobs are explicitly implemented.
- If artifact write fails, the model cannot become `TRAINED` or `VALIDATED`.

## 6. Data View

### Primary Entities

- `training_strategies`
  - Strategy catalog metadata.
  - Includes stable strategy ID, name, version, description, model family, feature contract, default parameters, and enabled status. Timeframe belongs to default/training parameters, not strategy identity.

- `training_runs`
  - One row per training execution.
  - Includes run ID, strategy ID/version, status, requested parameters, window configuration, started/finished timestamps, and failure reason.

- `trained_models`
  - One row per model produced by a successful training run.
  - Includes model ID, run ID, strategy ID/version, status, artifact path, artifact format, feature schema hash, target parameters, and timestamps.

- `training_validation_results`
  - Stores walk-forward and holdout evidence.
  - Includes model ID, validation type, window metadata, ML metrics, operational metrics, and serialized scorecard payloads.

- `training_approval_decisions`
  - Stores manual approval/rejection decisions.
  - Includes model ID, decision, timestamp, operator/agent identifier, and comments.

- `audit_events`
  - Append-oriented event log for training, model creation, validation, approval, rejection, and failures.

### Data Rules

- Every trained model must reference exactly one training run.
- Every approval/rejection decision must reference exactly one trained model.
- A model can move to `APPROVED` only from `VALIDATED`.
- Artifact path and format are required before a model can reach `TRAINED`.
- Validation metrics are required before a model can reach `VALIDATED`.
- Feature transformations must store enough metadata to prove lag and leakage rules were applied.
- It is expressly prohibited to use global aggregate functions in MySQL or vectorized Pandas/NumPy transformations fitted over the complete dataset. Scale parameters such as z-score, min-max, means, and standard deviations must be fitted only with the training partition and then applied forward to internal validation and holdout using retrospective/rolling rules.
- In `training_approval_decisions`, operator comments are optional for `APPROVED` decisions and mandatory for `REJECTED` decisions.

### Alembic Governance

- Alembic is the sole mechanism for schema changes.
- Migration files are owned by backend/system architecture implementation work.
- Each migration must be forward-only for normal delivery.
- Rollback strategy is restore-from-backup or explicit corrective migration; destructive downgrade is not the default operational path.
- Schema changes that affect frontend read models require corresponding API contract updates and QA coverage.
- Startup migration failure blocks backend readiness.

## 7. Model Lifecycle View

### Lifecycle

```text
Training Run:
PENDING -> RUNNING -> TRAINED
PENDING -> RUNNING -> FAILED

Trained Model:
TRAINED -> VALIDATING -> VALIDATED -> APPROVED
TRAINED -> VALIDATING -> VALIDATED -> REJECTED
TRAINED -> VALIDATING -> FAILED
TRAINED -> REJECTED
```

### Training Flow

1. Backend validates command and creates `training_runs` with `PENDING`.
2. Training worker claims the run and sets `RUNNING`.
3. Data loader reads configured-timeframe spot and sentiment data sources.
4. Feature pipeline computes RSI/IFR and sentiment features.
5. Feature pipeline applies stationarity transformations and lag rules.
6. Splitter creates chronological train, internal validation, and holdout windows.
7. XGBoost trainer trains a binary classifier with early stopping.
8. Artifact is saved as `.json` or `.ubj`.
9. `trained_models` is created with status `TRAINED`.
10. Validation starts automatically.

### Validation Flow

1. Model status becomes `VALIDATING`.
2. Walk-forward stability checks run on training-period subwindows.
3. Holdout backtest runs on unseen data.
4. Metrics are persisted.
5. Model status becomes `VALIDATED` or `FAILED`.

### Approval Flow

1. Operator opens a `VALIDATED` model scorecard.
2. Backend receives approve/reject command with optional comments.
3. Backend validates status and artifact/metric completeness.
4. Decision is persisted.
5. Model status becomes `APPROVED` or `REJECTED`.

### Compatibility and Traceability

- Strategy ID/version, feature schema, target parameters, and XGBoost hyperparameters are persisted with each model.
- Future execution runtimes must load only compatible approved models, but runtime loading is outside this MVP.

## 8. Execution and Strategy View

Execution trading is explicitly deferred.

For this MVP:

- No private exchange order APIs are used.
- No position state exists.
- No paper/live loop exists.
- No inference runtime is started.
- No live readiness gate exists.

The only “strategy” behavior in this SAD is the training strategy `RSI Sentiment XGBoost M1`.

Strategy contract:

- Declares required data sources.
- Declares feature definitions and transformations.
- Declares target labeling logic.
- Declares configurable parameters.
- Declares validation routines.
- Produces trained models and evidence.

Future trading execution must treat approved models as inputs and must not reinterpret or mutate training evidence.

## 9. Integration View

### External Integrations

- **CCXT public market data**
  - Primary training-data integration for configured exchange, symbol, and timeframe.
  - Used for spot price/candle data through public CCXT methods.
  - No private trading endpoints in MVP.

- **Sentiment data providers**
  - CCXT is preferred when the configured exchange exposes the required public derivative/sentiment metrics through supported methods.
  - Any non-CCXT sentiment provider must be explicitly approved as a separate adapter before implementation.
  - Used for Open Interest, Long/Short Ratio, and CVD or CVD-like deltas.
  - Source freshness and lag behavior must be recorded or conservatively shifted.

### Internal Integrations

- **Frontend -> Backend/API**
  - JSON HTTP contracts.
  - Commands: start training, approve model, reject model.
  - Queries: list strategies, get strategy detail, list trained models, get model scorecard, get audit events/log summaries.

- **Backend/API -> MySQL**
  - Read/write source of truth.
  - Backend mediates all frontend access.

- **Training worker -> MySQL**
  - Reads strategy/run configuration.
  - Writes lifecycle states, metrics, and audit events.

- **Training worker -> Artifact directory**
  - Writes native XGBoost artifacts.
  - Stores path in MySQL.

- **Alembic -> MySQL**
  - Owns schema migration history.
  - Must run before backend readiness.

### API Contract Sketch

- `GET /api/strategies`
  - Returns strategy table rows.

- `GET /api/strategies/{strategy_id}`
  - Returns strategy detail, parameters, feature contract, and trained-model summary.

- `POST /api/strategies/{strategy_id}/training-runs`
  - Starts a training run using configured/default parameters.

- `GET /api/training-runs/{run_id}`
  - Returns training run status and errors.

- `GET /api/strategies/{strategy_id}/models`
  - Returns trained models for the strategy.

- `GET /api/models/{model_id}`
  - Returns model metadata, validation status, and scorecard.

- `POST /api/models/{model_id}/approve`
  - Approves a `VALIDATED` model with comments.

- `POST /api/models/{model_id}/reject`
  - Rejects a post-training model with comments.

- `GET /api/audit-events`
  - Returns chronological audit events for system lifecycle actions, including training starts, completions, failures, validation transitions, and approval/rejection decisions with timestamps.

Final endpoint names may be refined during implementation, but the backend-mediated boundary is fixed.

## 10. Deployment View

### Local Linux Layout

```text
smart-trade/
  backend/
  frontend/
  models/
  logs/
  alembic/
  compose.yaml
  .env
```

### Runtime Components

- MySQL container or local MySQL service.
- Python backend/API service.
- Training worker, either same service or separate worker process.
- Angular + PrimeNG frontend service.
- Shared model artifact volume mounted only into backend/training services.
- Log volume mounted only into backend/training services.

### Environment Variables and Configuration

Required configuration categories:

- MySQL connection.
- Artifact directory.
- Log directory.
- Default exchange/source settings.
- Default symbol `BTC/USDT`.
- Default timeframe `M1`, configurable per training request.
- Training/validation/holdout windows.
- Target parameters `N`, `X`, and `Y`.
- XGBoost hyperparameters.
- `GLOBAL_RANDOM_SEED`, a stable numeric value used to fix XGBoost `random_state`/`seed` and any deterministic split or sampling behavior.
- Sentiment provider credentials or public API configuration when needed.

Secrets must not be committed, logged, or exposed to the frontend.

## 11. Quality Attributes

- **Correctness:** chronological splits, no global statistics leakage, and explicit model status gates.
- **Reproducibility:** fixed XGBoost seed and persisted configuration/feature metadata.
- **Portability:** native XGBoost `.json` or `.ubj` artifact format.
- **Observability:** audit events, lifecycle statuses, logs, scorecards, and failure reasons.
- **Security:** no direct frontend access to MySQL, artifact files, logs, secrets, or external API keys.
- **Reliability:** failed training/validation leaves explicit `FAILED` state and blocks approval.
- **Maintainability:** strategy catalog allows additional strategies without replacing the training lifecycle model.
- **Migration safety:** Alembic gates backend readiness and schema changes require review.
- **Usability:** frontend shows a clear linear flow: choose strategy, train, validate automatically, inspect scorecard, approve/reject.

Latency is not a primary MVP quality attribute because no live inference or execution loop exists in this phase.

## 12. Key Architectural Decisions

### AD1 - Native Python Backend/API

- **Context:** PRD requires Python-native training with XGBoost and data tooling.
- **Options considered:** native Python service, external ML service, notebook/manual scripts.
- **Chosen approach:** native Python backend/API plus training worker.
- **Consequences:** simple dependency model, direct access to XGBoost and pandas stack, clean backend mediation for frontend.
- **PRD traceability:** PRD sections 7 RF4-RF11, 8 RNF1.

### AD2 - Angular + PrimeNG Frontend

- **Context:** Operator needs a visual strategy/model workflow.
- **Options considered:** CLI-only, Streamlit, Angular + PrimeNG.
- **Chosen approach:** Angular + PrimeNG operational UI.
- **Consequences:** decoupled frontend with API contracts; no direct persistence or file access.
- **PRD traceability:** PRD sections 5, 7 RF1-RF3, 10.

### AD3 - MySQL with Alembic

- **Context:** Training and model lifecycle require durable, auditable persistence.
- **Options considered:** SQLite, file metadata, MySQL.
- **Chosen approach:** MySQL as target database, Alembic as migration mechanism.
- **Consequences:** explicit schema governance; migrations block startup on failure.
- **PRD traceability:** PRD sections 9, 11 CA8-CA9.

### AD4 - Native XGBoost Artifact Format

- **Context:** PRD and XGBoost review require model portability.
- **Options considered:** `.pkl`, `.joblib`, `.json`, `.ubj`.
- **Chosen approach:** `.json` or `.ubj`.
- **Consequences:** less Python-version coupling; future runtime portability improves.
- **PRD traceability:** PRD sections 4, 7 RF4/RF10, 8 RNF8.

### AD5 - Automatic Validation After Training

- **Context:** A model should not wait in an ambiguous trained-but-unvalidated state for normal flow.
- **Options considered:** manual validation command, automatic validation.
- **Chosen approach:** automatic validation after successful training.
- **Consequences:** simpler operator flow; approval remains manual and gated.
- **PRD traceability:** PRD sections 5, 7 RF6, 11 CA5.

### AD6 - No Automatic Metric Threshold Approval

- **Context:** PRD says validation generates evidence, but quality judgment is manual in MVP.
- **Options considered:** hard metric thresholds, advisory scorecard only.
- **Chosen approach:** advisory scorecard with manual decision.
- **Consequences:** avoids false confidence in early MVP; operator remains accountable.
- **PRD traceability:** PRD section 12 decision 3.

### AD7 - Backend-Mediated Access Only

- **Context:** Frontend must not access privileged storage or secrets.
- **Options considered:** direct database reads, direct artifact reads, backend API.
- **Chosen approach:** backend API only.
- **Consequences:** simpler security model and clearer audit trail.
- **PRD traceability:** PRD sections 7 RF1-RF11, 8 RNF7.

### AD8 - Sentiment Lag Safety

- **Context:** sentiment APIs can lag relative to the configured candle timeframe and create unintended look-ahead bias.
- **Options considered:** use raw aligned timestamps, apply conservative lag when needed.
- **Chosen approach:** source-specific lag rule, conservatively shifted when latency risk exists.
- **Consequences:** reduces leakage risk, may sacrifice some signal recency.
- **PRD traceability:** PRD sections 6, 8 RNF9, 11 CA3/CA9.

### AD9 - In-Process Background Training for First MVP Slice

- **Context:** The MVP needs manual training execution with observable `RUNNING` state, but not a distributed job platform.
- **Options considered:** separate worker container, in-process background thread/task.
- **Chosen approach:** in-process background execution inside the Python backend is acceptable for the first build slice if it writes `RUNNING` and terminal states synchronously to MySQL.
- **Consequences:** simpler deployment; future extraction to a separate worker remains possible if training duration or concurrency requires it.
- **PRD traceability:** PRD sections 5, 7 RF4-RF6, 10.

### AD10 - Training Data Source Boundary

- **Context:** training data must be obtained through a stable exchange abstraction instead of coupling the architecture directly to a single exchange API.
- **Options considered:** direct Bybit public API, direct Binance public API, Coinglass API, CCXT public market-data adapter.
- **Chosen approach:** CCXT is the primary integration boundary for configured exchange, symbol, timeframe, OHLCV candles, and any exchange-supported public derivative/sentiment metrics. CVD-like data may use provider-supported deltas or remain source-dependent within the approved feature contract.
- **Consequences:** keeps the MVP aligned with the Native CCXT product direction and avoids hard-coding Bybit as the architectural data origin. If a required sentiment metric is unavailable through CCXT for the configured exchange, dataset construction must fail explicitly or wait for an approved provider adapter.
- **PRD traceability:** PRD sections 6, 12 decision 4.

### AD11 - Frontend Feature Evidence Boundary

- **Context:** The operator needs model evidence, but raw transformed feature samples can increase payload size and expose unnecessary internals.
- **Options considered:** expose raw transformed feature samples, expose metadata and scorecards only.
- **Chosen approach:** frontend exposes feature schema metadata, status history, and consolidated scorecards only.
- **Consequences:** better MVP performance and simpler security posture; deeper feature audit can remain backend/internal or future work.
- **PRD traceability:** PRD sections 7 RF3/RF7, 10, 11 CA7.

## 13. Risks and Mitigations

- **Data leakage risk**
  - Mitigation: chronological splits, no global statistics, train-fitted transformations applied forward, lag safety for sentiment.

- **Sentiment data availability risk**
  - Mitigation: provider abstraction, source metadata, explicit failure state if required features cannot be built.

- **Model overfitting risk**
  - Mitigation: internal validation for early stopping, walk-forward stability checks, holdout backtest.

- **Artifact portability risk**
  - Mitigation: native XGBoost `.json`/`.ubj`.

- **Operational confusion between strategy and model**
  - Mitigation: separate `training_strategies`, `training_runs`, and `trained_models` entities.

- **Approval without evidence**
  - Mitigation: backend/API gate requires `VALIDATED` status and complete artifact/metric references.

- **Schema drift risk**
  - Mitigation: Alembic-only migrations, startup migration check, schema review rules.

- **Credential leakage risk**
  - Mitigation: environment/config files outside version control, backend-only access, no frontend exposure.

## 14. Future Work and Explicit Deferrals

Deferred from this MVP:

- Multiple implemented strategies.
- Paper trading.
- Live trading.
- Private exchange integration.
- Inference loop.
- Order execution.
- Position and risk management.
- Approved-model runtime loading.
- Live readiness gates.
- Advanced monitoring widgets.
- Automated hyperparameter search.
- Scheduled retraining.
- Adaptive targets based on ATR or rolling volatility.
- Authentication and role-based access control.
- Cloud deployment.

## 15. Sources

- `project-context/1.define/prd.md`
- `project-context/1.define/revisao.md`
- `project-context/1.define/review.md`
- `.codex/aamad/agents/system-arch.md`
- `.codex/aamad/templates/sad-template.md`
- `docs/proposed-solution.md`

## 16. Assumptions

- The reset MVP scope supersedes broader prior build-phase notes for this artifact.
- The first implementation can run training in a background thread/task inside the backend service process if `RUNNING` and terminal states are written synchronously to MySQL.
- MySQL and Alembic are required architecture choices for this project even though the current MVP is training-only.
- Training data source selection should prefer CCXT for the configured exchange, symbol, timeframe, candles, and any supported public sentiment metrics, while the architecture keeps provider metadata, lag rules, and failure behavior explicit.
- No private exchange credentials are needed for this MVP.
- The frontend has no authentication for MVP unless the Agentic Architect later changes scope.
- Approval comments are optional; rejection comments are mandatory.
- Default values for `N`, `X`, `Y`, and data windows are deployment configuration defaults, documented in `.env.example`, and may be changed per volatility regime.
- The frontend exposes feature schema metadata and scorecards, not raw transformed feature samples.

## 17. Open Questions

No open architecture questions remain for this SAD draft.

Implementation defaults still to be set during build planning:

- Exact `.env.example` values for training window, internal validation window, holdout window, `N`, `X`, and `Y`.
- Exact endpoint/provider mapping for CVD-like data after the first public API spike.

## 18. Audit

- Persona: `@system.arch`
- Action: `create-sad --mvp`
- Artifact: `project-context/1.define/sad.md`
- Date: 2026-06-15
- Backend runtime: `native-python`
- Frontend stack: Angular + PrimeNG
- Database: MySQL
- Database versioning: Alembic
- Source inputs: `project-context/1.define/prd.md`, `project-context/1.define/revisao.md`, `project-context/1.define/review.md`, `.codex/aamad/templates/sad-template.md`, `.codex/aamad/agents/system-arch.md`
- Review status: approved by the Agentic Architect on 2026-06-15
