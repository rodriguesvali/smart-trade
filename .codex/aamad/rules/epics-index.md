---
description: Mapping of AAMAD epics to agent personas, actions, and output artifacts for modular rule-based AI execution.
alwaysApply: true
---

# AAMAD Phase 2 Epics Index Rule

| Epic | Persona | Primary Output Artifact | PRD/SAD Section Reference | Invocation |
| --- | --- | --- | --- | --- |
| Setup | @project.mgr | setup.md | SAD: Environment; PRD: RNF4.1/RNF4.4/RNF4.8 | *setup-project |
| Training and Model Lifecycle | @backend.eng | backend.md | PRD: RF1.1-RF1.10 | *develop-training-pipeline |
| Inference and Execution | @backend.eng | backend.md | PRD: RF2.1-RF2.5 | *implement-inference-engine |
| Strategy and Position Management | @backend.eng | backend.md | PRD: RF2.5.1-RF2.5.20 | *implement-strategy-engine |
| Backend Integration Boundaries | @backend.eng | backend.md | SAD: Data/process flows; PRD: RF/RNF integration constraints | *verify-backend-operational-flow |
| Angular Frontend | @frontend.eng | frontend.md | PRD: RF3.1-RF3.6, RNF4.3/RNF4.10 | *develop-frontend |
| QA | @qa.eng | qa.md | PRD: Acceptance Criteria, RNF4.7/RNF4.12 | *qa |

## Execution Notes
- Each persona works independently referencing the approved PRD and SAD.
- Output artifact for each epic lives in `project-context/2.build/`.
- Mark Future Work visibly in artifacts as needed.
- Update this index as epics progress or new ones are added.
