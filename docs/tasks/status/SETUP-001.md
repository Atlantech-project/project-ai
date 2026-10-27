# SETUP-001 · Shared AI Workflow Bootstrap
| Field | Value |
|---|---|
| Status | IN REVIEW |
| Owner | AI Team |
| Branch | feature/SETUP-001-ai-workflow-bootstrap |
| Plan | docs/superpowers/plans/2026-10-27-setup-001-ai-workflow-bootstrap.md · approval: explicit user approval in the planning conversation, 2026-10-27 |
| Updated | 2026-10-27 |

Setup task, not in the official AI backlog. No production AI code.

## Summary of the change
Bootstraps the shared AI workflow: root `CLAUDE.md`, the two project skills (`atlantech-task-workflow`, `atlantech-review-and-publish`) with their evals, the contract and decision logs, this status structure, `.gitignore`, the shared `.claude/settings.json`, and the existing reference documents (added unchanged).

## One-time Git exception
The branch was created while this task's own files were untracked (the normal task workflow stops on untracked files). Before branching, the untracked set was checked to be exactly the planned files plus the ignored worktree, and `develop` was checked to equal the freshly fetched `origin/develop` (`eb74c85`). This exception applies to SETUP-001 only.

## Verification
Code tests: NOT APPLICABLE (no production code; the change is documentation, skill instructions and eval tooling). Smoke checks run on 2026-10-27:
- Eval assets parse: both `evals.json` (JSON), `build_fixture.py` and `check_state.py` (`py_compile`), `build_fixtures.sh` (`bash -n`).
- Task-workflow fixture `claude-md-proposal` builds; its CLAUDE.md carries the corrected commit rule; `check_state.sh compare` reports SAFE, no changes.
- Review fixtures `docs-only-decision` (DL-001 PROPOSED in the log) and `missing-decision-log` (no log present) build; `check_state.py` reports `unsafe: []`.
- `.gitignore` ignores the worktree, local settings and `-workspace/` paths, not the skills or evals.
- Every `docs/...` path cited by CLAUDE.md, the logs, WORK_STATUS and this record exists; ID ranges match the specs (`CT-26`, `DEC-56`, `AI-106`).
- Secret scan: matches only the eval fixtures' deliberate fake credentials; no machine-specific paths.

## Review findings
Local manual review (Superpowers review skills not available in this session). Fixed: fixture builders copied the real logs, WORK_STATUS and status records into fixtures (broke `missing-decision-log` and onboarding-style scenarios); contract range was stated as `CT-23` instead of `CT-26`. Unresolved: none.

## Remote PR review
Has not occurred: no PR exists for this branch yet, `gh` is not installed, and no review workflow is configured. Only the local review in this session has been done.

## Known gaps
- Not in the repository and not reconstructed: `ATLANTECH_FRD_v3`, `PortSync.sql`, `SaaS.sql`, `ATLANTECH_AI_IMPLEMENTATION_PLAN.md`, `ATLANTECH_AI_BACKEND_DEPENDENCIES.md`. The project context is therefore incomplete.

## Contract / decision items
- None. Both logs start empty.

## Blockers and follow-ups
- After this is merged into `develop`: AI-010 (module structure in project-ai) is the first product task, run as its own task.
- The local branch `worktree-atlantech-review-and-publish-skill` (unpushed commit `358e119`, an older skill version) and its worktree are not merged; removing them is the user's decision.
