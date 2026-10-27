# SETUP-001 plan · Shared AI Workflow Bootstrap

- **Task:** SETUP-001 (setup task, not in the AI backlog) · branch `feature/SETUP-001-ai-workflow-bootstrap` · documentation/tooling task, no production code.
- **Approved:** by the user in the planning conversation on 2026-10-27, with decisions 1–4 below.

## Scope

In:
1. Root `CLAUDE.md`: repository identity, sources of truth, records, task workflow gates, Git safety, and the split of responsibility between the two project skills.
2. `.claude/skills/atlantech-task-workflow/`: the existing skill and evals, kept, with edits for the tracker (`WORK_STATUS.md`), log-entry numbering, and the fixture line that said the user commits and pushes.
3. `.claude/skills/atlantech-review-and-publish/`: consolidated from the current working tree of the `atlantech-review-and-publish-skill` worktree (copies verified by hash), with the same tracker and numbering edits; eval fixtures renamed from `DEC-57` to `DL-001`.
4. `docs/tasks/CONTRACT_LOG.md` and `docs/tasks/DECISION_LOG.md`: header, rules and template, no entries.
5. `docs/tasks/WORK_STATUS.md` and `docs/tasks/status/SETUP-001.md`.
6. `.gitignore` and the shared `.claude/settings.json`.
7. The existing reference documents in `docs/ref/` and `docs/tasks/`, added unchanged.

Out: AI-010 and any production AI code; replacement content for missing documents; broad evaluation runs; merging.

## Decisions

1. Logs live in `docs/tasks/`; `docs/ref/` stays read-only.
2. Log IDs are `CL-nnn` and `DL-nnn`; existing `CT-`/`DEC-` IDs are referenced; no new official `DEC-` IDs are assigned.
3. `.gitignore` ignores `.claude/worktrees/`, `.claude/settings.local.json` and `.claude/skills/*-workspace/`.
4. `.claude/settings.json` is committed if it contains no secrets or machine-specific values.

## One-time Git exception

`atlantech-task-workflow` stops when the tree has untracked files. For this bootstrap only, the untracked files are this task's own scope, so the branch is created with them present, after checking that the untracked set is exactly the expected one and that `develop` equals the freshly fetched `origin/develop`. Any other untracked file stops the procedure. The exception does not carry over to later tasks.

## Tests

No production code. Verification: smoke checks of both skills (eval assets parse; fixtures build; targeted Git-state checks), document checks (links, IDs, required fields), `git diff --check`, and a secret scan of everything to be staged.

## Publishing

Through `/atlantech-review-and-publish SETUP-001`; staging, commit and push only after the exact `APPLY CHANGES`. The pull request into `develop` and the merge are the user's. AI-010 follows as a separate task after the merge.
