# AAMAD Agent Framework

This project uses the AAMAD framework for AI-assisted development.
See the full persona seed definitions in `.codex/aamad/agents/`.

## Project Direction
- Product: quantitative trading platform for crypto spot markets with Python backend/trading services and Angular + PrimeNG frontend.
- MVP mode: M1 timeframe, spot long-only, one configured asset, one open position at a time.
- Core flow: configure asset -> collect history -> train XGBoost model -> walk-forward validation -> out-of-sample backtest -> approve model -> run strategy.
- Execution: direct CCXT integration, approved model only, binary inference signal, explicit strategy and position state.
- Monitoring: decoupled Angular + PrimeNG operational frontend served by Python backend/API contracts.
- Backend runtime target: `native-python` unless the Agentic Architect explicitly chooses otherwise.
- Frontend stack: Angular + PrimeNG.

## Agent Personas
- **@product-mgr** - Product Manager: consolidates the trading PRD, scope boundaries, user outcomes, acceptance criteria, and risk posture.
- **@system.arch** - System Architect: designs the Python backend/trading architecture, Angular + PrimeNG frontend boundary, data/model lifecycle, API contracts, process boundaries, and safety controls.
- **@project.mgr** - Project Manager: prepares Python project structure, configuration, environment files, dependency plan, and container setup.
- **@backend.eng** - Trading Backend Engineer: implements training, validation, model registry, inference/execution loop, strategy state, persistence, and internal integration boundaries.
- **@frontend.eng** - Frontend Engineer: builds the Angular + PrimeNG operational frontend through Python backend/API contracts.
- **@qa.eng** - QA Engineer: validates training/backtest correctness, operational safety gates, execution behavior, dashboard evidence, and end-to-end readiness.

## Workflow
1. **Define** (Phase 1): @product-mgr -> PRD alignment -> @system.arch -> SAD/SFS for trading modules.
2. **Build** (Phase 2): @project.mgr -> @backend.eng / @frontend.eng -> @qa.eng.
3. **Deliver** (Phase 3): deployment, operations, paper/live readiness gates, monitoring, and runbooks.

## Rules
All development follows AAMAD core rules. See project-context/ for artifacts.

## Agent Definitions
See `.codex/aamad/agents/` for AAMAD persona seed definitions adapted for Codex.

<!-- AAMAD-CODEX:START -->
# AAMAD Bootstrap For Codex

This repository has been prepared for AAMAD work in Codex.

## Human Role

The human is the Agentic Architect. The Agentic Architect reviews every generated or updated artifact before any next stage begins.

## AAMAD Flow

Use the global `$aamad-flow` skill and `.codex/aamad/workflow.md` as its handoff guide after bootstrap. When asked to start or continue AAMAD Flow, inspect `.codex/aamad/state.md`, then collaborate with the Agentic Architect on the next approved artifact or role-refinement step.

## Bootstrap Boundary

AAMAD Bootstrap only adapts AAMAD methodology artifacts for Codex. Project discovery, MVP definition, system architecture, implementation planning, application bootstrap, and project-specific agent-role refinement happen later through AAMAD Flow.

## Agent Role Seeds

AAMAD-generated agent descriptions under `.codex/aamad/agents/` are generic seeds. They are not final project-specific technical roles until AAMAD Flow refines them with the Agentic Architect.

## Mandatory Review Gate

After generating or updating any artifact, stop and ask the Agentic Architect for review. Do not move to the next stage until the Architect explicitly approves, requests changes, or redirects the workflow.

## Current Repository Profile

- State: pre-existing
- Languages: Python and SQL implied by PRD; repository implementation not started.
- Frameworks/libraries: Python, Angular, PrimeNG, TypeScript, CCXT, XGBoost, TA-Lib or pandas-ta, joblib or pickle, SQLite or PostgreSQL, Docker implied by PRD/alignment decisions.
- Package managers: not present in repository; Python dependency manager remains to be selected during Build setup.
- Existing context source: `docs/proposed-solution.md`
- Project signal: proposed PRD for a Python-native quantitative trading backend using CCXT, XGBoost, spot long-only execution, and a decoupled Angular + PrimeNG operational frontend.

## AAMAD Codex Files

- `.codex/aamad/state.md`
- `.codex/aamad/workflow.md`
- `.codex/aamad/review-log.md`
- `.codex/aamad/mcp-rules.md`
- `.codex/aamad/templates/`
<!-- AAMAD-CODEX:END -->
