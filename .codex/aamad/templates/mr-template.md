# AAMAD Market/Domain Research Template - Quantitative Trading System

## Context & Instructions
Generate focused research for a quantitative trading MVP using a Python backend/trading runtime, CCXT, XGBoost, technical indicators, local persistence, and a decoupled Angular + PrimeNG operational frontend.

Use this template only when the Agentic Architect asks for research. The existing proposed PRD in `docs/proposed-solution.md` is the current primary source until approved or revised.

## Research Query Structure

**Primary Focus**: [INSERT THE TRADING SYSTEM CONCEPT HERE]

Example: "Crypto spot long-only quantitative trading system using a Python backend, CCXT, XGBoost, RSI/IFR, walk-forward validation, and Angular + PrimeNG operational monitoring."

## Research Dimensions

### 1. Product and User Context
- Target operator profile and workflow.
- Primary operational pain points.
- Safety, auditability, and observability needs.
- Adoption barriers for running automated trading locally.
- Value proposition for a training -> validation -> approval -> execution workflow.

### 2. Trading Domain and Risk Context
- Spot crypto market constraints relevant to M1 trading.
- Exchange limits, precision, fees, slippage, liquidity, and rate limits.
- Long-only scope rationale and excluded strategies.
- Paper/live readiness expectations.
- Operational risk controls and failure modes.

### 3. Technical Feasibility
- CCXT capabilities and limitations for historical candles and private order methods.
- XGBoost suitability for binary short-term confirmation signals.
- TA-Lib vs pandas-ta tradeoffs.
- SQLite vs PostgreSQL tradeoffs for local MVP operation.
- Angular + PrimeNG frontend architecture and charting/data-grid tradeoffs.
- Docker and Linux deployment considerations.

### 4. Data, Model, and Validation Quality
- Historical data quality risks and candle completeness.
- Feature engineering risks, leakage risks, and walk-forward validation needs.
- Out-of-sample backtest design and approval metrics.
- Model lifecycle and metadata requirements.
- Traceability between inference decisions and model versions.

### 5. Operations, Security, and Compliance
- Secrets handling for exchange API keys.
- Logging and redaction requirements.
- Resilience for timeouts, rate limits, rejected orders, and process restarts.
- Monitoring, alerting, and runbook needs.
- Legal, financial, and user-risk disclaimers relevant to automated trading software.

## Output Format Requirements

### Executive Summary
- Product opportunity and operator value.
- Technical feasibility summary.
- Highest-risk assumptions.
- Recommended next decisions for the Agentic Architect.

### Findings by Dimension
For each research dimension:
- Key insights.
- Evidence and sources.
- Design implications.
- Risks and mitigations.

### Decision Points
- Database choice.
- Angular charting/data visualization approach.
- Indicator library.
- Package/dependency manager.
- Paper-mode and live-mode gating.
- Deployment/container strategy.

### Risk Assessment Matrix
- High risk.
- Medium risk.
- Low risk.

### Actionable Recommendations
- Immediate Define-phase actions.
- Build-phase priorities.
- Delivery and readiness gates.

## Research Quality Requirements
- Cite authoritative sources when research is requested.
- Prefer recent, primary technical documentation for library behavior.
- Clearly separate facts, assumptions, and recommendations.
- Do not provide financial advice or profitability guarantees.
