---
description: AAMAD modular development workflow for context-aware agent coordination.
alwaysApply: true
---

# AAMAD Modular Development Workflow

## Development Module Structure
Execute development in separate modules with fresh context:

1. **Module 1: Project Setup and Configuration** - Python package structure, environment examples, dependency plan, containers, database bootstrap plan.
2. **Module 2: Training and Model Lifecycle** - CCXT historical ingestion, feature engineering, walk-forward validation, out-of-sample backtest, model artifact/metadata/status handling.
3. **Module 3: Inference, Execution, Strategy, and Backend Integration Boundaries** - approved-model loading, minute loop, binary inference signal, RSI/IFR gating, spot long-only position management, CCXT orders, persistence, dashboard read contracts.
4. **Module 4: Angular Frontend and Observability** - Angular + PrimeNG frontend, metrics, charts, live logs, and operational visibility using backend-documented API/read contracts.
5. **Module 5: QA and Readiness** - safety gates, paper-mode evidence, failure paths, acceptance checks, deployment/runbook readiness.

## Context Management Rules
- Start each module with fresh context and read the approved inputs for that module.
- Reference specific project-context artifacts from previous modules.
- Do not attempt end-to-end development in a single step.
- Keep module scope strictly defined; no feature creep.

## Module Success Criteria
Each module must be fully functional and testable independently:

- Module 1: setup.md documents reproducible environment and approved dependency/configuration decisions.
- Module 2: training/validation/backtest flow produces traceable model metadata and status without look-ahead leakage.
- Module 3: inference/execution strategy enforces approved model, spot long-only, one-position, stop/take-profit behavior, and stable backend/dashboard read contracts.
- Module 4: Angular + PrimeNG frontend consumes approved backend API/read contracts without blocking or mutating execution state.
- Module 5: QA evidence maps to RF/RNF acceptance criteria and documented residual risks.

## Development Flow Control
- Complete each module fully before proceeding to the next approved module.
- Validate module functionality before context switch.
- Document module outputs for next module reference.
- Stop for Agentic Architect review whenever an artifact is generated or changed.

> For detailed agent/epic/action mapping, see `.codex/aamad/rules/epics-index.md`.
