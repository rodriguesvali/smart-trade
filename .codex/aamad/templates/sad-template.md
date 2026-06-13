# AAMAD SAD Template - Quantitative Trading MVP

## Context & Instructions
Generate a System Architecture Document for the trading MVP described by the approved PRD/alignment decisions. The architecture must prioritize safety, traceability, frontend/backend separation, process isolation, and operational correctness.

Do not introduce chat interfaces, Next.js, assistant-ui, CrewAI, margin trading, futures, leverage, short selling, or position scaling unless explicitly approved by the Agentic Architect.

## Input Requirements

**PRD Document**: [PASTE OR LINK APPROVED PRD]
**MVP Scope**: [CONFIRMED MVP SCOPE]
**Selected Backend Runtime**: [native-python | other approved runtime]
**Frontend Stack**: Angular + PrimeNG
**Database**: MySQL
**Database Versioning**: Alembic

## System Architecture Specification

### 1. Architecture Philosophy and Principles
- Safety-first operational design.
- Approved-model gating.
- Process isolation.
- Observable by default.
- Configuration outside code.
- Backend-mediated frontend access.
- Versioned database schema changes with Alembic.
- Minimal MVP before expansion.

### 2. Stakeholders and Concerns
- Agentic Architect/operator.
- Trading execution process.
- Training/model lifecycle.
- Angular + PrimeNG frontend/operator console.
- Python backend/API for frontend.
- Exchange/API boundary.
- MySQL data storage, model artifact storage, and log storage.

### 3. Scope and Constraints
- Spot long-only.
- One configured asset.
- M1 timeframe.
- One position at a time.
- No margin, futures, leverage, short selling, position scaling, pyramiding, or martingale.
- Linux-native Python execution.
- Angular + PrimeNG frontend.
- Frontend must not directly access database, model artifacts, log files, exchange APIs, or secrets.

### 4. Logical View
- Training pipeline.
- Feature engineering.
- Model registry.
- Inference engine.
- Strategy engine.
- Execution adapter.
- Persistence layer.
- Python backend/API and frontend read models.
- Angular + PrimeNG frontend.
- Alembic migration layer.
- Logging/observability.

### 5. Process and Runtime View
- Independent training process.
- Independent inference/execution process.
- Python backend/API process for frontend read contracts and approved commands.
- Angular frontend build/runtime boundary.
- Shared MySQL database, model artifact directory, and log directory accessed by backend/trading processes, not directly by frontend.
- Startup and shutdown behavior.
- Restart and recovery behavior.

### 6. Data View
- MySQL schema ownership and schema versioning with Alembic.
- Alembic migration history and migration execution policy.
- Candle data.
- Feature data.
- Model metadata and artifacts.
- Validation/backtest metrics.
- Inference records.
- Strategy decisions.
- Orders and exchange responses.
- Positions and state transitions.
- Operational logs.

### 7. Model Lifecycle View
- Training data window.
- Holdout separation.
- Walk-forward validation.
- Backtest outside sample.
- Status transitions: TRAINED, VALIDATED, APPROVED, ACTIVE, REJECTED, EXPIRED, RETIRED.
- Model compatibility checks.
- Traceability from inference to model ID.

### 8. Execution and Strategy View
- Minute-aligned loop.
- Candle consolidation assumptions.
- RSI/IFR entry condition.
- Binary XGBoost confirmation.
- Market order behavior.
- Stop loss, take profit, break even, trailing stop.
- Exit reasons.
- Fail-safe behavior.

### 9. Integration View
- CCXT public and private boundaries.
- Database access.
- Model artifact storage.
- MySQL access boundaries.
- Alembic migration boundaries.
- Python backend/API contracts for Angular frontend.
- Frontend read models for model validation, operation, positions, metrics, and logs.
- Backend-mediated log read paths.
- Environment/configuration loading.

### 10. Deployment View
- Local Linux layout.
- Docker/container plan.
- Angular build and serving strategy.
- Python backend/API deployment strategy.
- Shared volumes.
- Environment variables.
- MySQL initialization.
- Alembic migration execution.
- Operational modes: training, paper, live.

### 11. Quality Attributes
- Latency.
- Reliability.
- Resilience.
- Observability.
- Security and secret handling.
- Data integrity.
- Migration safety.
- Reproducibility.
- Maintainability.

### 12. Key Architectural Decisions
- Decision.
- Context.
- Options considered.
- Chosen approach.
- Consequences.
- PRD traceability.

Required decisions include:
- MySQL connection and pooling strategy.
- Alembic migration ownership and execution point.
- Migration rollback/forward-fix policy.
- Schema compatibility expectations for training, execution, and frontend read models.

### 13. Risks and Mitigations
- Market/exchange risk.
- Model risk.
- Data leakage risk.
- Execution risk.
- Operational risk.
- Security risk.

### 14. Future Work and Explicit Deferrals
- Multi-asset operation.
- Short/futures/margin/leverage.
- Position scaling.
- Cloud deployment.
- Advanced monitoring/alerts.
- Additional model families.
- Alternative frontend stacks only if explicitly approved.

### 15. Sources
- Approved source artifacts.

### 16. Assumptions
- Explicit architecture assumptions.

### 17. Open Questions
- Decisions requiring Agentic Architect review.

### 18. Audit
- Persona, action, date, backend runtime, frontend stack, source inputs, and review status.
