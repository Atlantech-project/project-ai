# ATLANTECH AI (`project-ai`) · project instructions

Durable, team-wide rules for this repository. Task progress never goes here; it belongs in `docs/tasks/status/`. Changing this file is its own task (a `SETUP-` task with its own plan, branch, review and PR), never part of a feature task.

## Repository

- Canonical remote (`origin`): `https://github.com/Atlantech-project/project-ai.git`
- Long-lived branches: `main`, `develop`, `release`. Never commit to them directly, never push to them, and never merge locally.
- One task per branch: `feature/<TASK-ID>-<slug>` (or `feature/SETUP-<id>-<slug>` for setup work), branched from the freshly fetched `develop` and merged into `develop` by pull request (`docs/ref/Master_Context.md` §5.4).

## Sources of truth

Read-only. Never rewrite them; propose changes through the logs below.

| File | Holds |
|---|---|
| `docs/ref/Master_Context.md` | Identity, scope, architecture, AI design, data-model map, team, and the rules for AI sessions (§9) |
| `docs/ref/UML_Context.md` | Actors, status vocabularies, global rules, answer codes and per-diagram flows |
| `docs/ref/ClassDiagramContext.md` | Class diagrams in words |
| `docs/ref/ATLANTECH_AI_ARCHITECTURE.md` | AI architecture reference for code agents |
| `docs/tasks/ATLANTECH_AI_TASKS.md` | The official AI task backlog (`AI-001`–`AI-106`) |
| `docs/tasks/ATLANTECH_Contracts.md` | Team contracts `CT-01`–`CT-26` |
| `docs/tasks/ATLANTECH_Decisions.md` | Decisions, conflicts and open points `DEC-01`–`DEC-56` |

Precedence and vocabulary follow `Master_Context.md` §0. Follow its §9 rules in every session; in particular, don't invent business rules or technical decisions.

**Not in this repository** (cited by the documents above; don't reconstruct or guess their content): `ATLANTECH_FRD_v3`, `PortSync.sql`, `SaaS.sql`, `ATLANTECH_AI_IMPLEMENTATION_PLAN.md`, `ATLANTECH_AI_BACKEND_DEPENDENCIES.md`. When a task needs one of them, say it is missing.

## Records

- `docs/tasks/CONTRACT_LOG.md` (`CL-xxx`) and `docs/tasks/DECISION_LOG.md` (`DL-xxx`): proposed changes and new decisions. Entries stay `PROPOSED` until the responsible owners and reviewers explicitly approve them, with who and when recorded. Reference existing `CT-`/`DEC-` IDs; never assign new official ones.
- `docs/tasks/status/<TASK-ID>.md`: one status record per task. `docs/tasks/WORK_STATUS.md`: one row per started task. The backlog remains the official task list.

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
