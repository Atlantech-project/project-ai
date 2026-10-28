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
| AI-016 | Set up CI for AI code | IN REVIEW | `feature/AI-016-ci-for-ai-code` | [AI-016](status/AI-016.md) | 2026-10-28 |
