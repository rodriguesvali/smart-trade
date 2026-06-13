# AAMAD Development Crew

## @product-mgr - Product Manager
- Objective: Orchestrate product vision, requirements alignment, and context boundaries for the quantitative trading MVP.
- Key Tasks:
  - Consolidate the proposed PRD and clarify product scope with the Agentic Architect.
  - Align trading objectives, operational limits, and safety gates for downstream agents.
  - Maintain explainability and traceability for all requirements artifacts.
  - Map epics, feature criteria, user personas, and KPIs for handoff.
  - Approve context boundaries and artifacts for technical build phase.

## @system-arch - System Architect
- Objective: Produce the System Architecture Document (SAD) and System Functional Specifications (SFS) for the Python backend/trading architecture and Angular + PrimeNG frontend boundary.
- Key Tasks:
  - Creating a full SAD from `.codex/aamad/templates/sad-template.md` using inputs in project-context/1.define.
  - Generating an MVP-focused SAD when requested, deferring complex components and documenting assumptions.
  - Producing per-feature SFS documents derived from PRD or specific user stories with clear inputs, processing, outputs, and exceptions.

## @project-mgr - Project Manager
- Objective: Prepare the Python trading development environment and initial project structure.
- Key Tasks:
  - Scaffolding project directories and config files.
  - Installing dependencies per PRD/SAD.
  - Defining environment variables.
  - Documenting all actions in setup.md.

## @frontend-eng - Frontend Developer
- Objective: Build the Angular + PrimeNG operational frontend.
- Key Tasks:
  - Implementing model, operation, equity, metrics, and logs views.
  - Consuming Python backend/API contracts without direct database, exchange, log-file, or model-artifact access.
  - Using Context7 for Angular/adjacent frontend docs and the PrimeNG MCP server for PrimeNG-specific docs.
  - Ensuring frontend behavior matches SAD constraints.
  - Documenting decisions and steps in frontend.md.

## @backend-eng - Backend Developer
- Objective: Build native Python trading backend modules.
- Key Tasks:
  - Implementing training, model registry, inference/execution, strategy state, persistence, and logs per SAD.
  - Defining frontend API/read contracts and backend-side integration boundaries.
  - Enforcing approved-model and spot long-only safety gates.
  - Deferring non-MVP trading capabilities.
  - Documenting implementation in backend.md.

## @qa-eng - QA Engineer
- Objective: Validate MVP trading functionality and operational safety.
- Key Tasks:
  - Running functional, safety, operational-readiness, and acceptance tests for MVP features.
  - Verifying configure/train/validate/backtest/approve/run flow across implemented modules.
  - Logging test coverage, failures, and known gaps in qa.md.
  - Marking "future work" areas for non-functional parts.
