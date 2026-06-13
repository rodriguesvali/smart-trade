# AAMAD Bootstrap Artifact Review

Date: 2026-06-13
Reviewer persona: AAMAD Flow / Codex
Source PRD: `docs/proposed-solution.md`
Review status: Pending Agentic Architect approval

## PRD Understanding

The proposed product is a quantitative trading MVP for crypto spot markets with Python backend/trading services and a decoupled Angular + PrimeNG operational frontend. It uses CCXT for exchange access, XGBoost for binary short-term confirmation, RSI/IFR as the primary technical gate, local persistence, explicit model validation and approval, and backend-mediated frontend APIs/read models.

The MVP constraints are:

- M1 timeframe.
- One configured asset.
- Spot long-only.
- One open position at a time.
- No margin, futures, leverage, short selling, position scaling, pyramiding, or martingale.
- Operational strategy starts only after model training, temporal validation, out-of-sample backtest, and approval.

## Artifact-by-Artifact Review

| Artifact | Review Finding | Alignment Action |
| --- | --- | --- |
| `AGENTS.md` | Bootstrap text still reflected generic AAMAD and chat/CrewAI assumptions. | Added project direction, native Python runtime target, PRD-implied technologies, trading-specific personas, and trading workflow. |
| `.codex/aamad/state.md` | State had only generic repository profile. | Added PRD alignment summary, technologies, scope constraints, safety gates, and `native-python` runtime target. |
| `.codex/aamad/workflow.md` | Handoff did not distinguish AAMAD methodology from the product runtime. | Added project alignment guidance, prohibited unapproved scope expansion, and next valid Define step. |
| `.codex/aamad/mcp-rules.md` | Frameworks were initially listed as not detected, then backend-only Context7 was approved. | Added Angular + PrimeNG stack, required Context7 for Angular/adjacent frontend docs, and required the dedicated PrimeNG MCP server for PrimeNG docs. |
| `.codex/aamad/agents/product-mgr.md` | Product persona was oriented to enterprise multi-agent applications. | Refined toward trading PRD consolidation, scope boundaries, risk posture, and acceptance criteria. |
| `.codex/aamad/agents/system-arch.md` | Architect persona assumed CrewAI/default agent runtime concerns, then Python-only frontend monitoring. | Refined toward Python backend/trading architecture, Angular + PrimeNG frontend boundary, backend-mediated API/read contracts, process boundaries, model lifecycle, safety gates, and operational resilience. |
| `.codex/aamad/agents/project-mgr.md` | Setup persona was generic and could be read as agent-app setup. | Refined toward Python project structure, env examples, dependency plan, containers, and no business logic. |
| `.codex/aamad/agents/backend-eng.md` | Backend persona assumed chat endpoints and runtime agents. | Replaced with Trading Backend Engineer responsibilities for training, model registry, inference/execution, strategy, persistence, and logging. |
| `.codex/aamad/agents/frontend-eng.md` | Frontend persona assumed Next.js chat UI, then a Python dashboard. | Replaced with Angular + PrimeNG Frontend Engineer responsibilities and MCP documentation rules. |
| `.codex/aamad/agents/integration-eng.md` | Integration responsibilities overlapped with Backend, Dashboard, and QA for the MVP, creating an extra artifact/gate without enough value. | Removed as an active MVP persona. Backend now owns integration boundaries and dashboard read contracts; QA owns operational-readiness validation. |
| `.codex/aamad/agents/qa-eng.md` | QA persona assumed chat flow validation. | Replaced with trading QA for validation integrity, strategy safety, failure paths, paper/live readiness, and dashboard checks. |
| `.codex/aamad/agents/dev-crew.md` | Crew summary still described chat UI and generic multi-agent app work. | Updated role summaries to match trading modules and process boundaries. |
| `.codex/aamad/rules/adapter-registry.md` | Default runtime was `crewai`. | Changed default to `native-python` and kept other adapters optional only. |
| `.codex/aamad/rules/adapter-native-python.md` | Missing. | Added native Python trading adapter with setup, module mapping, execution, logging, quality gates, and failure policy. |
| `.codex/aamad/rules/development-workflow.md` | Module flow assumed CrewAI, API endpoints, and frontend integration. | Replaced with setup, training/model lifecycle, inference/execution/strategy, dashboard, and QA/readiness modules. |
| `.codex/aamad/rules/epics-index.md` | Epics assumed frontend/backend chat app work. | Replaced with trading epics mapped to PRD RF/RNF sections. |
| `.codex/aamad/rules/aamad-core.md` | Core adapter wording assumed generated multi-agent application. | Generalized wording to generated application while keeping AAMAD methodology intact. |
| `.codex/aamad/templates/mr-template.md` | Research template assumed CrewAI multi-agent product. | Replaced with quantitative trading/domain research template. |
| `.codex/aamad/templates/prd-template.md` | PRD template assumed CrewAI multi-agent system. | Replaced with native Python quantitative trading PRD template. |
| `.codex/aamad/templates/sad-template.md` | SAD template assumed Next.js, assistant-ui, and CrewAI. | Replaced with native Python trading SAD template. |
| `.codex/aamad/prompts/prompt-phase-1.md` | Prompt assumed generic multiagent app generation. | Updated for trading Define-phase PRD/research workflow. |
| `project-context/` | Directories exist only as placeholders. | Left unchanged; no Define artifacts generated without approval. |

## Remaining Decisions

- Approve this bootstrap alignment or request changes.
- Decide whether to copy `docs/proposed-solution.md` into `project-context/1.define/product-requirements-document.md` as the approved PRD, or revise it first.
- Later, during SAD/setup, decide Python version, Python dependency manager, frontend dependency manager, Python API framework, MySQL client/ORM, Angular charting/data visualization approach, indicator library, paper/live gating policy, and container layout.

## Sources

- `docs/proposed-solution.md`
- `AGENTS.md`
- `.codex/aamad/*`

## Assumptions

- The proposed PRD is the current product intent but has not yet been copied into `project-context/1.define/` as an approved AAMAD artifact.
- `native-python` is the correct default backend runtime because the PRD explicitly calls for Python-native CCXT execution.
- Angular + PrimeNG is the approved frontend stack.
- Optional AAMAD runtime adapters remain available but are not part of the default product architecture.
- The Integration Engineer role is intentionally removed from MVP active flow to reduce context switching and artifact overhead.

## Open Questions

- Should `docs/proposed-solution.md` be accepted as-is as the approved PRD?
- Which Angular charting/data visualization library should be used with PrimeNG?
- Which MySQL client/ORM stack should be used with Alembic?
- Should TA-Lib or pandas-ta be preferred for the first implementation?
- Should paper mode be mandatory before any live operation?

## Audit

- Persona: AAMAD Flow / Codex
- Action: bootstrap artifact review, PRD alignment, MVP role consolidation, and Angular + PrimeNG frontend alignment
- Date: 2026-06-13
- Review status: Pending Agentic Architect approval
