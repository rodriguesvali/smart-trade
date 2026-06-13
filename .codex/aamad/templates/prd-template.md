# AAMAD PRD Template - Native Python Quantitative Trading MVP

## Context & Instructions
Generate or revise a Product Requirements Document for a native Python quantitative trading system. Base decisions on approved inputs, especially `docs/proposed-solution.md` or the approved project-context PRD.

The product is not a chat application and does not require CrewAI, Next.js, or an agent runtime unless the Agentic Architect explicitly changes scope.

## Input Requirements

**Source PRD/Notes**: [PASTE OR LINK APPROVED INPUTS]
**System Concept**: [INSERT SYSTEM DESCRIPTION]
**Selected Backend Runtime**: [native-python | other approved runtime]
**Frontend Stack**: Angular + PrimeNG

## PRD Structure

### 1. Executive Summary
- Product objective.
- Target operator/user.
- Core value proposition.
- MVP scope.
- Out-of-scope items.

### 2. Scope and Operating Boundaries
- Market and instrument scope.
- Timeframe.
- Trading direction.
- Position constraints.
- Live/paper operation assumptions.
- Explicit exclusions such as margin, futures, leverage, short selling, position scaling, pyramiding, or martingale.

### 3. System Workflow
- Configure asset and operational parameters.
- Collect historical data.
- Train model.
- Validate model.
- Run out-of-sample backtest.
- Approve or reject model.
- Start paper/live strategy only with approved model.

### 4. Functional Requirements

#### Module 1: Training Pipeline
- Historical ingestion.
- Feature engineering.
- Training window and holdout separation.
- Walk-forward validation.
- Out-of-sample backtest.
- Metrics and model approval.
- Model artifact and metadata persistence.

#### Module 2: Inference and Execution
- Minute-aligned inference loop.
- Approved model loading.
- Binary signal generation.
- Direct CCXT order execution.
- Execution state persistence.

#### Module 2.5: Strategy and Position Management
- RSI/IFR oversold condition.
- Binary inference confirmation.
- Long-only entry rules.
- One-position rule.
- Stop loss, take profit, break even, trailing stop.
- Exit conditions.
- Strategy decision logging.

#### Module 3: Angular + PrimeNG Frontend
- Training/model view.
- Operation view.
- Candlestick chart with entries/exits.
- Equity curve.
- Trade metrics.
- Live log terminal.
- Python backend/API contracts used by the frontend.

### 5. Non-Functional Requirements
- Linux-native operation.
- Latency expectations.
- Frontend/backend decoupling.
- Secret handling.
- Process isolation.
- Logging and retention.
- Resilience.
- Externalized configuration.
- Model traceability.
- Fail-safe behavior.

### 6. Data and Model Requirements
- MySQL database requirements and required entities.
- Alembic schema versioning and migration requirements.
- Model artifact format.
- Model status lifecycle.
- Feature set traceability.
- Metrics and approval thresholds.

### 7. User Experience and Operations
- Angular + PrimeNG screens/tabs and operator workflows.
- Frontend API behavior and allowed commands.
- Manual retraining trigger expectations.
- Paper/live readiness workflow.
- Error visibility and recovery guidance.

### 8. Acceptance Criteria
- Training pipeline acceptance.
- Model approval gate acceptance.
- Inference/execution acceptance.
- Strategy management acceptance.
- Angular + PrimeNG frontend acceptance.
- Operational safety acceptance.

### 9. Open Questions
- MySQL connection/runtime assumptions.
- Alembic migration ownership and execution policy.
- Angular charting/data visualization library selection.
- Indicator library selection.
- Package manager and Python version.
- Initial exchange/symbol/capital defaults.
- Paper-mode requirement before live mode.

### 10. Sources
- Approved source artifacts and research.

### 11. Assumptions
- Explicit assumptions used by the PRD.

### 12. Audit
- Persona, action, date, source inputs, and review status.
