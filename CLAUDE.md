# ATLANTECH AI (`project-ai`) · project instructions

Durable, team-wide rules for this repository. Task progress never goes here; it belongs in `docs/tasks/status/`. Changing this file is its own task (a `SETUP-` task with its own plan, branch, review and PR), never part of a feature task.

## Repository

- Canonical remote (`origin`): `https://github.com/Atlantech-project/project-ai.git`
- Long-lived branches: `main`, `develop`, `release`. Never commit to them directly, never push to them, and never merge locally.
- One task per branch: `feature/<TASK-ID>-<slug>` (or `feature/SETUP-<id>-<slug>` for setup work), branched from the freshly fetched `develop` and merged into `develop` by pull request (`docs/ref/Master_Context.md` §5.4).

## Sources of truth

Read-only, except the two canonical files for decisions and contracts, which are edited only as described under "Decisions and contracts" below.

| File | Holds |
|---|---|
| `docs/ref/Master_Context.md` | Identity, scope, architecture, AI design, data-model map, team, and the rules for AI sessions (§9) |
| `docs/ref/UML_Context.md` | Actors, status vocabularies, global rules, answer codes and per-diagram flows |
| `docs/ref/ClassDiagramContext.md` | Class diagrams in words |
| `docs/ref/ATLANTECH_AI_ARCHITECTURE.md` | AI architecture reference for code agents |
| `docs/ref/ATLANTECH_Decisions.md` | **Canonical** decisions, conflicts and open points `DEC-01`–`DEC-56`, plus AI task decisions keyed by task ID |
| `docs/ref/ATLANTECH_Contracts.md` | **Canonical** team contracts `CT-01`–`CT-26` |
| `docs/ref/ai-payloads/` | Local reference copies of the AI payload JSON Schemas (published as `contracts/ai/`) |
| `docs/ref/db/` | Local DB references, such as `table-names.md` (published as `contracts/db/`) |
| `docs/tasks/ATLANTECH_AI_TASKS.md` | The official AI task backlog (`AI-001`–`AI-106`) |

Use these paths. Older records that cite `docs/tasks/ATLANTECH_Contracts.md`, `docs/tasks/ATLANTECH_Decisions.md`, a decision or contract log, or an `ai/` payload folder mean the files above. Where the backlog says "decision log", read `docs/ref/ATLANTECH_Decisions.md`.

Precedence and vocabulary follow `Master_Context.md` §0. Follow its §9 rules in every session; in particular, don't invent business rules or technical decisions.

**Not in this repository** (cited by the documents above; don't reconstruct or guess their content): `ATLANTECH_FRD_v3`, `PortSync.sql`, `SaaS.sql`, `ATLANTECH_AI_IMPLEMENTATION_PLAN.md`, `ATLANTECH_AI_BACKEND_DEPENDENCIES.md`. When a task needs one of them, say it is missing.

## Decisions and contracts

- **Where they live.** Decisions are read from, and updated directly in, `docs/ref/ATLANTECH_Decisions.md`. Contracts are read from, and updated directly in, `docs/ref/ATLANTECH_Contracts.md`.
- **No logs.** There is no separate decision or contract log. Never create `DECISION_LOG.md`, `CONTRACT_LOG.md`, `DL-`/`CL-` entries, append-only logs or other parallel copies.
- **Inspect first.** Before proposing a change, read the relevant canonical entry, its summary row and the related context (architecture, UML, payload schemas, DB references).
- **Edit, don't duplicate.** Change the existing entry rather than create a duplicate. Reference existing `DEC-`/`CT-` IDs; never assign new official ones. A decision that belongs to one AI task and has no `DEC-` ID goes in the Decisions file's "AI task decisions" section, keyed by the task ID.
- **Proposed until approved.** A proposed change is written as a `Proposed change` row in the entry, or as a `Proposed vX.Y` contract status. It stays clearly proposed until the approval the project requires: the decision's Owner, or the contract's Owner and Reviewers.
- **Approved.** Once approved, update the canonical entry directly (Status, Decision or version), record who approved it and when, and remove the `Proposed change` row. Never fabricate an approval.
- **Follow-ups.** Unresolved sub-details of an approved decision are listed under the entry as follow-ups, without reopening it.

## Records

- `docs/tasks/status/<TASK-ID>.md`: one status record per task. `docs/tasks/WORK_STATUS.md`: one row per started or closed task. The backlog remains the official task list.
- **Status follows acceptance criteria**, not log files. A decision or contract task is `DONE` when its accepted outcome is in the canonical document and its acceptance criteria are met, or when the user approves a documented scope exception. A missing log entry or tracker row doesn't keep it open. A documented contract never makes the implementation, integration or testing tasks that depend on it done.

## Task workflow

Two project skills split the work:

1. **`/atlantech-task-workflow <TASK-ID>`** starts a task: verifies the task, its dependencies, contracts and decisions; creates the feature branch from the fetched `develop`; plans with Superpowers; and **stops for explicit plan approval**. After approval it implements and tests. It never stages, commits, pushes or merges.
2. **`/atlantech-review-and-publish <TASK-ID>`** finishes a task: verifies the remote and baseline, the plan approval, real tests (or document checks), a local review, and the records; presents a final report; and only after the user's exact `APPLY CHANGES` stages the reviewed paths, commits and pushes the feature branch. It never merges.

A status file's `approved: yes` is not, on its own, proof of plan approval. Any change after the final report requires a new report and a new `APPLY CHANGES`.

## Git safety

- Never `stash`, `reset`, `restore`, `checkout -- <file>`, `clean`, `rebase`, `commit --amend`, `branch -D`, or force-push.
- Stage only explicit, reviewed paths (`git add -- <paths>`); never `git add .`, `-A`, `-u` or `commit -a`.
- Never commit secrets, local settings, worktrees, scratch or test output.
- When a Git command fails, quote its output and stop; don't improvise a repair.
