# Work status

One row per task that has been started or closed. The official task list stays `docs/tasks/ATLANTECH_AI_TASKS.md`; this index doesn't copy it, and tasks that haven't started don't appear here. Each row links to the task's status record in `docs/tasks/status/<TASK-ID>.md`, which holds the detail (plan and approval, verification, review findings, blockers). Other teams' `CT-`/`DEC-` tasks are tracked by their status in `docs/ref/ATLANTECH_Contracts.md` and `docs/ref/ATLANTECH_Decisions.md`, not here.

Status values follow the backlog (§1.3): `NOT STARTED`, `IN PROGRESS`, `IN REVIEW`, `DONE`, `BLOCKED (<item>)`, `DEFERRED (<decision>)`. A task is `DONE` when every acceptance criterion is met, or an approved scope exception is recorded:
- for work on a branch, after its pull request is reviewed and merged;
- for a decision or contract task, when its accepted outcome is in the canonical document.

| Task | Title | Status | Branch | Record | Updated |
|---|---|---|---|---|---|
| SETUP-001 | Shared AI Workflow Bootstrap (setup task, not in the backlog) | DONE | `feature/SETUP-001-ai-workflow-bootstrap` | [SETUP-001](status/SETUP-001.md) | 2026-10-28 |
| AI-010 | Decide AI code repository and module structure | DONE | `feature/AI-010-ai-repository-module-structure` | [AI-010](status/AI-010.md) | 2026-10-28 |
| AI-001 | Confirm AI scope and component inventory | DONE | — (decision task) | [AI-001](status/AI-001.md) | 2026-10-28 |
| AI-002 | Decide completion signalling, status ownership and READ_ONLY behaviour of AI jobs | DONE | — (decision task) | [AI-002](status/AI-002.md) | 2026-10-28 |
| AI-004 | Decide location of shared validation rule sets | DONE | — (decision task) | [AI-004](status/AI-004.md) | 2026-10-28 |
| SETUP-002 | Canonical Decisions and Contracts (setup task, not in the backlog) | DONE | `feature/SETUP-002-canonical-decisions-contracts` | [SETUP-002](status/SETUP-002.md) | 2026-10-28 |
| AI-016 | Set up CI for AI code | IN REVIEW (PR #5 merged `451daff`; 2 criteria outstanding) | `feature/AI-016-ci-for-ai-code` | [AI-016](status/AI-016.md) | 2026-10-31 |
| AI-014 | Implement unit, datum and time utilities | DONE (PR #7, merge `2f3b89e`) | `feature/AI-014-unit-datum-time-utilities` | [AI-014](status/AI-014.md) | 2026-10-31 |
| SETUP-003 | PortHub contracts and decisions synchronization (setup task, not in the backlog) | IN REVIEW | `feature/SETUP-003-porthub-contracts-decisions-sync` | [SETUP-003](status/SETUP-003.md) | 2026-10-31 |
| AI-009 | Specify AI seed data: constraint types, objective terms, rationale templates v1, model registry rows | IN REVIEW (partial scope, scope exception 2026-11-01; criteria 1, 3, 4 open) | `feature/AI-009-ai-seed-data-specification` | [AI-009](status/AI-009.md) | 2026-11-01 |
| AI-008 | Agree thresholds register and evaluation baseline | IN REVIEW (DEC-30 approval and QA H-44 outstanding) | `feature/AI-008-thresholds-register-evaluation-baseline` | [AI-008](status/AI-008.md) | 2026-10-31 |
| AI-003 | Define and approve AI job and result contract v1 | DONE (PR #14, merge `0ccebd3`; PortHub #34 follow-up open) | `feature/AI-003-ai-job-result-contract-v1` | [AI-003](status/AI-003.md) | 2026-11-03 |
| AI-012 | Implement configuration management | IN REVIEW (criterion 1 partial until AI-011) | `feature/AI-012-configuration-management` | [AI-012](status/AI-012.md) | 2026-11-03 |
| AI-054 | Implement tug-requirement computation | DONE (PR #17, merge `25405fc`, accepted as approval by the Leads Council, no separate review; scope exception on AI-005) | `feature/AI-054-tug-requirement-computation` | [AI-054](status/AI-054.md) | 2026-11-03 |
| AI-011 | Implement shared worker runtime (queue consumer, idempotent claim, retries, logging) | IN REVIEW | `feature/AI-011-shared-worker-runtime` | [AI-011](status/AI-011.md) | 2026-11-03 |
| DEC-20 | Tug requirement formula | IN REVIEW (decision Closed 2026-11-03, interim tables; PortHub PR to follow) | `feature/DEC-20-tug-requirement-formula` | [DEC-20](status/DEC-20.md) | 2026-11-03 |
| AI-013 | Implement data-access layer and request worker DB accounts | DONE (PR #19, merge `109fb54`) | `feature/AI-013-data-access-layer` | [AI-013](status/AI-013.md) | 2026-11-05 |
| AI-015 | Build test harness and synthetic reference-port scenario generator | IN REVIEW | `feature/AI-015-test-harness-scenario-generator` | [AI-015](status/AI-015.md) | 2026-11-05 |
| DEC-21 | Phase 1 delay-risk rule | IN REVIEW (decision Closed 2026-11-05, interim rule; PortHub PR to follow) | `feature/DEC-21-delay-risk-rule` | [DEC-21](status/DEC-21.md) | 2026-11-05 |
| AI-050 | Implement port-state loader for Part 2 | DONE (PR #26, merge `9e0ae86`; confirmed by the Leads Council 2026-11-06) | `feature/AI-050-port-state-loader` | [AI-050](status/AI-050.md) | 2026-11-06 |
| AI-005 | Obtain Part 2 domain rules: tug formula, delay-risk rule, moves definition, financial impact, objective terms | DONE (confirmed by the Leads Council 2026-11-06) | — (decision task) | [AI-005](status/AI-005.md) | 2026-11-06 |
| AI-006 | Define joint-solve scope and resource-availability semantics | DONE (DEC-06 and DEC-32 Closed; confirmed by the Leads Council 2026-11-05) | — (decision task) | [AI-006](status/AI-006.md) | 2026-11-05 |
| AI-053 | Implement B4 delay-risk Phase 1 (rule or NULL) | IN REVIEW (plan approved 2026-11-05; implemented; local review done) | `feature/AI-053-delay-risk-phase-1` | [AI-053](status/AI-053.md) | 2026-11-05 |
| AI-023 | Build BAPLIE D.17A test corpus | IN REVIEW (plan approved 2026-11-06; implemented; local review done; criterion 2 by approved scope exception) | `feature/AI-023-baplie-d17a-test-corpus` | [AI-023](status/AI-023.md) | 2026-11-06 |
