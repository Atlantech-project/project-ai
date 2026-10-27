---
name: atlantech-task-workflow
description: Start-of-task workflow for the ATLANTECH AI repository. Verifies the task ID against the backlog in docs/tasks, checks the Git working tree, creates feature/<task-id>-<slug> from develop, reads the authoritative references, checks contract and decision impact (CT-xx, DEC-xx), then uses Superpowers brainstorming and writing-plans to produce a plan and waits for explicit approval before implementing. Use it whenever the user starts, picks up or resumes an ATLANTECH task (for example "start AI-011", "let's do CT-08", "begin the setup task", "/atlantech-task-workflow AI-014"), even if they don't name the workflow.
argument-hint: "[task-id]"
user-invocable: true
---

# ATLANTECH task workflow

Requested task: `$ARGUMENTS`

This workflow runs at the start of every ATLANTECH task. Its job is to make sure work starts from a clean, correct base, that nobody builds on an unsettled contract or against a closed decision, and that the user approves the plan before any code is written. Several teams (AI, Backend, Frontend, Mobile, QA, UI/UX) share these contracts and decisions, so a quiet assumption here becomes another team's integration bug later.

Work through the phases in order. Each **STOP** means: report what you found, say what is needed to continue, and end your turn. Don't work around a stop.

## Ground rules (apply throughout)

- **Report only what really happened.** Say "read", "inspected" or "ran" only about files you opened and commands you executed in this session. If you only scanned the headings of a large file, say so. If a referenced file is missing (the backlog cites documents that may not be in the workspace, such as `ATLANTECH_AI_IMPLEMENTATION_PLAN.md`), say it is missing. Never invent test results.
- **No commits, pushes or merges.** Only `atlantech-review-and-publish` may commit and push task changes, and only after the user's exact `APPLY CHANGES` following its final report. This overrides the Superpowers skills, which normally commit specs and plans and add `git commit` steps to plans.
- **No destructive Git.** Never `stash`, `reset`, `checkout -- <file>`, `clean`, `branch -D`, `push --force`, or anything else that discards work or rewrites history.
  - Never `git pull` without `--ff-only`, and never add, remove or change remotes.
  - When a Git command fails, quote its actual output and **STOP**. Don't attempt a corrective action.
- **Leave authoritative sources alone without approval.** Don't rewrite the files in `docs/ref/` (architecture, UML, class diagrams, Master_Context, payload schemas, DB references) or the backlog in `docs/tasks/`. The two exceptions are `docs/ref/ATLANTECH_Decisions.md` and `docs/ref/ATLANTECH_Contracts.md`: a needed decision or contract change is written directly into the relevant entry there, marked `Proposed` (see Phase 5). Don't change the ownership of a DB schema, and don't mark anything Approved or Closed without the approval the project requires.
- **No separate decision or contract logs.** There is no `DECISION_LOG.md` or `CONTRACT_LOG.md`, and no `DL-`/`CL-` entries. Don't create them, or any other parallel copy of a decision or contract.
- **State a task's status only from verified evidence.** The Status column in `ATLANTECH_AI_TASKS.md` is the backlog's starting snapshot: every task begins as `NOT STARTED`, and the backlog doesn't track progress. A task's current status comes from:
  - its status record on `develop`;
  - the team tracker, `docs/tasks/WORK_STATUS.md`;
  - Git evidence on `develop`, such as the merge of its branch;
  - for decision and contract tasks, the item's status in `docs/ref/ATLANTECH_Decisions.md` and `docs/ref/ATLANTECH_Contracts.md`, checked against the task's acceptance criteria. A missing log entry or tracker row is not evidence that a decision is unsettled.

  If you haven't read that evidence, call the status **unverified**, not `NOT STARTED`. If those sources disagree, apply Phase 2 step 6.
- **Keep CLAUDE.md for durable rules.** Task progress goes in the status record (Phase 9), never in CLAUDE.md. Approving a task plan never authorises a CLAUDE.md change; see Phase 9.

## Phase 1: Repository and Git state (always first)

Run:

```
git rev-parse --show-toplevel
git remote -v
git status --short --branch
git branch --show-current
```

- **Repository and remote.** The repository root must be the ATLANTECH AI repository, and `origin` must point to `https://github.com/Atlantech-project/project-ai.git`; the SSH form `git@github.com:Atlantech-project/project-ai.git` is the same repository.
  - If there is no `origin`, or it points anywhere else (a fork, another project, a mirror), **STOP**. Report both remote URLs you saw.
  - Don't edit remotes; the user decides. Every later step trusts `origin` as the team's source of truth.
- If the working tree has uncommitted changes (modified, staged **or untracked** files), **STOP**. List the files and the current branch, and ask the user how to handle them. Don't stash, discard, overwrite or move anything. Untracked files count, because switching branches carries them onto the new branch and they would mix into this task.
  - One exception: you are resuming. The current branch is already this task's `feature/<task-id>-*` branch, so the changes probably belong to the task. Report the changes anyway and ask the user to confirm before you continue on that branch.
- Note the current branch. If it is another task's feature branch, the new branch will still come from `develop` (Phase 3), never from that branch.

## Phase 2: Identify and validate the task

1. **Require an ID.** If `$ARGUMENTS` is empty or vague, **STOP** and ask for the task ID or the name of the setup task.
2. **Find the task.** Search with Grep across `docs/tasks/` and the canonical files. AI tasks (`AI-xxx`) are in `docs/tasks/ATLANTECH_AI_TASKS.md`, both in §2 (summary table) and in §5 (details). Contract tasks share their contract's ID (`CT-xx`, `docs/ref/ATLANTECH_Contracts.md`), and decision tasks share their decision's ID (`DEC-xx`, `docs/ref/ATLANTECH_Decisions.md`). Also check any other backlog or team tracker that exists in `docs/tasks/`.
   - **Don't invent a task ID.** If the ID is not in the official backlog, **STOP** and say so. Suggest the nearest real IDs if any look like what the user meant.
   - **Setup work** that is not in the backlog (repo tooling, onboarding, for example) may go ahead as `SETUP-<slug>`. Label it clearly as a setup task that is not in the official backlog, and get the user's confirmation before continuing.
3. **Extract the task details:** title, phase, priority, status, prerequisites, flags (D/A/B/X), inputs, expected outputs, files and interfaces, acceptance criteria, verification evidence, and open questions. Quote the acceptance criteria exactly.
4. **Read status from `develop` without switching branches.** Status records and merged work live on `develop`, not on the branch you happen to be on (often `main`). Run `git fetch origin`, which only updates remote-tracking refs and leaves the working tree alone. Then read through Git:
   - `git ls-tree --name-only origin/develop docs/tasks/status/`
   - `git show origin/develop:docs/tasks/status/<id>.md`
   - `git log --oneline origin/develop`

   If the fetch fails, **STOP** and quote its output.
   - **If `origin/develop` doesn't exist after the fetch:** read from local `develop` if it exists, and note which one you used.
   - **If neither exists:** note it. Phase 3 will stop on it, after checking again.
5. **Check the task's own status.** If the requested task is already `DONE` or `IN REVIEW`, **STOP**. Reopening finished work is the user's call.
6. **Check the prerequisites.** For each prerequisite task, collect every piece of status evidence:
   - the status record on `develop`;
   - the team tracker;
   - the decision and contract entries that close or depend on it;
   - Git evidence of its work merged into `develop` (for example, a merge commit of `feature/<prereq-id>-*` in `git log origin/develop`).

   The backlog's Status column is not current-status evidence (see Ground rules).
   - **Done:** a prerequisite counts as done when the evidence says `DONE` (or shows the work merged) and no other source contradicts it.
   - **Not confirmed as done:** **STOP before creating a branch**. Name each blocking prerequisite and its status. Starting a dependent task early means building on something still moving.
   - **Conflicting evidence:** for example, the status record says `DONE` but the team tracker says `IN REVIEW`, or a status says `DONE` while the decision it closes is still `Open`. **STOP before creating a branch**, and don't pick one source as the answer. Quote each source and what it says, and ask the user or the task owner which is correct. A guessed status either starts work on an unfinished base or wrongly blocks a ready task.
   - **Stopping before this step:** if you stop earlier (for example, to confirm a SETUP task) and a related task matters to your advice, first read its status from `develop` as in step 4; that step is read-only.
     - If you don't read it, call its status unverified rather than quoting the backlog column.
     - Don't draw conclusions that depend on it either. "AI-010 hasn't decided yet" is a status claim too.
7. **Check cross-team dependencies.** Look at the flags and at any linked `CT-xx`, `DEC-xx`, `AIBD-xxx` or `OD-xx` references:
   - **B** means Backend coordination.
   - **X** means domain experts or another team.
   - **D** means the task is blocked by missing data.
   - **A** means it needs an architectural or domain decision.

   For every linked contract or decision, record its status. An **Open** decision or an unapproved contract that the task depends on is a blocker unless the task itself is the one that closes it.
8. **Check scope against closed decisions before branching.** If the request adds to or changes the task's backlog scope (for example "also add X to the MVP"), Grep `docs/ref/ATLANTECH_Decisions.md` and `docs/ref/ATLANTECH_Contracts.md` for the topic. If a `Closed` decision or an approved contract contradicts the request, **STOP now**, before any branch exists (Phase 5 has the full rules). An empty branch left behind for a request that can't go ahead is clutter someone must clean up.

## Phase 3: Prepare `develop` and create the branch (new tasks only)

Skip this phase when you are resuming on the task's existing branch (as confirmed in Phase 1). Reach it only after Phase 2 has passed. Never skip the task and dependency checks just to get a branch faster.

This phase is the only place the skill writes to Git. It switches branches, fast-forwards `develop` and creates one new branch. It never commits, pushes or merges. If any command fails, **STOP**, quote its actual output, and don't try to repair anything: no reset, no force, no re-clone, no new remote, no alternative base branch.

**Step 1: fetch, then look for `develop` in both places.** A `develop` branch created on GitHub isn't visible locally until it has been fetched. Never say `develop` is missing before running these:

```
git fetch origin
git ls-remote --heads origin develop
git rev-parse --verify --quiet refs/remotes/origin/develop
git rev-parse --verify --quiet refs/heads/develop
```

- `git fetch origin` is harmless to repeat, even if Phase 2 already fetched.
- `git ls-remote` shows what the remote has right now.
- The two `rev-parse` commands check the remote-tracking ref after the fetch, and the local branch.

`ls-remote` is the authority on whether `origin/develop` exists. If it lists no `develop` but `refs/remotes/origin/develop` is still there, that tracking ref is stale: a plain fetch doesn't prune branches deleted on the remote. Treat `origin/develop` as **missing**, and say the local tracking ref is stale. Don't prune or delete it; that's the user's call.

Report the two facts separately: "local `develop`: exists / missing" and "`origin/develop`: exists / missing". Then act on the combination:

| Local `develop` | `origin/develop` | What to do |
|---|---|---|
| missing | exists | Create a local tracking branch: `git switch --track -c develop origin/develop` |
| exists | exists | Check the fast-forward: `git merge-base --is-ancestor develop origin/develop`. Exit 0 means safe; continue. Any other result means local `develop` has commits that `origin` lacks (ahead or diverged). **STOP**, show `git log --oneline origin/develop..develop`, and don't reset either branch. |
| exists | missing | **STOP.** `develop` exists only locally, and the team base is `origin`'s. Don't push it or create it on the remote. |
| missing | missing | **STOP.** `origin` has no `develop`. Don't create it, and don't branch from `main`, `release` or anything else instead. The base branch is the team's decision. |

Two more **STOP** cases:

- `ls-remote` lists `develop` but `refs/remotes/origin/develop` is still missing after the fetch. The fetch configuration is unusual.
- `ls-remote` itself fails (network or authentication). "Couldn't check" is not the same as "missing".

Still in Step 1, before switching anything, run the existing-branch check from Step 3. It is read-only. If the task branch already exists, **STOP** here, so the user's current branch is left exactly as it was.

**Step 2: update `develop`, fast-forward only.**

```
git switch develop
git pull --ff-only origin develop
```

- Skip `git switch develop` if the `--track` command above already switched you.
- `--ff-only` refuses anything but a fast-forward. If it fails, **STOP** with its output.
- After the pull, re-confirm that the prerequisites are merged into `develop`, if Phase 2 relied on Git history to decide that.

**Step 3: make sure the task branch is still new.** Repeat the Step 1 check after the update, because someone may have pushed the branch in the meantime:

```
git branch --list "feature/<TASK-ID>-*"
git branch -r --list "origin/feature/<TASK-ID>-*"
git ls-remote --heads origin "feature/<TASK-ID>-*"
```

If anything matches, **STOP**. Report each name and where it exists (local, remote-tracking or remote), and ask whether to resume it. Never reuse, overwrite, reset or delete an existing branch, and don't create a second one for the same task.

**Step 4: create the branch.**

```
git switch -c feature/<TASK-ID>-<slug>
```

- `<TASK-ID>` is the ID exactly as the backlog writes it (for example `AI-014`, with the case kept), or `SETUP-<slug>` for a confirmed setup task.
- `<slug>` is a short, lowercase, kebab-case version of the title, for example `feature/AI-014-unit-datum-time-utilities`.

**Step 5: verify.**

```
git branch --show-current
git rev-parse HEAD develop origin/develop
git status --short --branch
```

The current branch must be exactly the name you created, and all three commits must be the same, so the branch starts from the freshly updated `develop`. If not, **STOP** and report.

**Step 6: report.** List:

- the repository (root path and `origin` URL);
- the base (`develop` at `<sha>`, equal to `origin/develop`);
- the task ID;
- the feature branch;
- any unresolved blockers found so far, such as Open decisions, missing references or a Proposed change still pending.

## Phase 4: Read the references

The authoritative set is everything in `docs/ref/` and `docs/tasks/`. Today that is:

- `docs/ref/`: Master_Context.md, ATLANTECH_AI_ARCHITECTURE.md, UML_Context.md (very large), ClassDiagramContext.md, ATLANTECH_Decisions.md (canonical decisions), ATLANTECH_Contracts.md (canonical contracts), `ai-payloads/` (local reference copies of the AI payload JSON Schemas that the contracts publish under `contracts/ai/`) and `db/` (DB references such as `table-names.md`, published under `contracts/db/`).
- `docs/tasks/`: ATLANTECH_AI_TASKS.md, WORK_STATUS.md and `status/`.

Use these current paths. Older records may cite `docs/tasks/ATLANTECH_Contracts.md`, `docs/tasks/ATLANTECH_Decisions.md`, the removed decision and contract logs, or an `ai/` payload folder; read those as the `docs/ref/` files and `docs/ref/ai-payloads/`.

List both directories first, because new files may have been added.

- **Initial onboarding** (no `docs/tasks/status/` records exist yet, or the user says it's the first task): inspect every reference document. For very large files, read the table of contents and headings fully, then read in depth the sections that relate to AI, contracts and the current phase.
- **Later tasks**: list the whole reference set, then read in depth:
  - every source the task cites (for example "Master_Context §6", "UML 2.16", "plan §8.2");
  - the sections on the components, tables and interfaces the task touches;
  - any document that could conflict with them: the contract and decision entries the task links to (including any `Proposed` changes recorded in them), and the status records of prerequisite tasks.

Finish with an **"Inspected" list** that separates "read in full", "read sections …" and "headings only". If a cited source is missing from the workspace, say so.

## Phase 5: Contract and decision impact

Compare what the user asked for, and what the task needs, against the existing contracts and decisions:

1. **Reuse existing IDs.** If `DEC-04` or `CT-08` already covers the topic, refer to it by that ID instead of creating a new item.
2. **Closed or approved items are settled.** If the request contradicts a `Closed` decision (for example, DEC-55 makes TIMING and NCT recommendations future work) or an approved contract, **STOP**. Quote the decision and explain the conflict. Do not plan around it quietly.
3. **Propose changes in the canonical document, never in a log.** Decisions live only in `docs/ref/ATLANTECH_Decisions.md` and contracts only in `docs/ref/ATLANTECH_Contracts.md`. If the task needs a new decision or a contract change:
   - **Inspect first.** Read the relevant entry in full, its summary-table row, the linked `DEC-`/`CT-` entries and the related context (architecture, UML, payload schemas in `docs/ref/ai-payloads/`, DB references in `docs/ref/db/`).
   - **Edit the existing entry; don't duplicate it.** When an entry covers the topic, add a `Proposed change` row to that entry's table. A whole new contract version may instead be written as `Proposed vX.Y` in the contract's Status row. When no entry covers a decision that belongs to one AI task, add it to the Decisions file's "AI task decisions" section, keyed by the task ID, with Status `Proposed`. Any other new topic needs a new official ID, so ask the user. Never assign a new official `DEC-` or `CT-` ID yourself.
   - **Keep it visibly proposed.** Apart from a `Proposed vX.Y` status, the entry's Status, Decision and version rows stay as they are until the approval the project requires: the decision's Owner, or the contract's Owner and Reviewers. Name the owner and the reviewers, and explain why the change is needed.
   - **Write it only on the task branch.** Without a task branch yet, put the exact draft in your message instead.
   - **After approval, update the canonical entry directly.** Fold the change into the Status, Decision or version rows (bumping a contract's version), record who approved it and when, and remove the `Proposed change` row. Do this only when the user tells you the responsible people explicitly approved it. "Nobody objected" is not approval.

   ```
   | Proposed change | <YYYY-MM-DD> · <task-id> · <what changes, with the version bump for contracts> · Reason: <why the current text is not enough> · Evidence: <documents, files or tests> · Impact: <tasks, tables, teams> · Awaiting: <owner / reviewers> |
   ```

4. **Stop if something blocks safe work.** If an Open or Proposed item blocks safe implementation (the task would have to guess a message format, a schema, or who owns a write), **STOP**. Explain what must be decided, and by whom. Planning may still go ahead if the user wants it, but the plan must mark that part as blocked.

## Phase 6: Plan with Superpowers

Use the installed Superpowers skills through the Skill tool:

1. `superpowers:brainstorming`, to explore the requirements, questions and approach with the user.
2. `superpowers:writing-plans`, to turn the result into an implementation plan.

These ATLANTECH rules override the Superpowers defaults:

- Save the spec and plan files, but **don't commit them**, and leave out any `git commit` steps in the plan. Note instead that publishing happens through `/atlantech-review-and-publish <task-id>`.
- Don't offer to start execution at the end. Go to the approval gate below.
- Keep CLAUDE.md changes out of the plan. Don't add them as plan steps or files to change, even when the user asked for one in the same message. Present them separately, as Phase 9 describes.

The plan must contain these sections:

- **Task:** ID, title, branch.
- **Scope:** what is in, and explicitly what is out.
- **Files likely to change:** say which are new and which are existing.
- **Dependencies:** prerequisites with their status, plus cross-team items.
- **Tests:** what is tested, how, and the commands to run (TDD where it fits).
- **Risks:** including data, performance and coordination risks.
- **Contract/decision changes:** existing IDs touched, plus any `Proposed change` rows to write in the canonical documents.
- **Acceptance criteria:** quoted from the backlog, each mapped to a verification step.

## Phase 7: Approval gate

Present the plan and **STOP**. Ask the user explicitly to approve it or request changes. Questions, comments and silence are not approval. Implementation needs a clear yes, such as "approved" or "go ahead". Don't edit any source files before then.

## Phase 8: Implement (only after approval)

- Implement only the approved task and scope. If you find more work, note it as a follow-up; don't do it now.
- Follow the project instructions (CLAUDE.md, if present) and the specification sections read in Phase 4.
- Use `superpowers:test-driven-development` where it fits, and `superpowers:verification-before-completion` before you claim the work is done.
- Run the tests and checks and report the **actual** output: commands, pass/fail counts, failures. If something could not be run, say so and explain why.
- Don't commit, push or merge. When implementation, tests, the status record and your local review are complete, end with a summary of the changed files and direct the user to run `/atlantech-review-and-publish <task-id>`.

## Phase 9: Status record

Keep the task's status in `docs/tasks/status/<task-id>.md`, and keep its row in `docs/tasks/WORK_STATUS.md` in step with it. Create the record only once you are on the task's own branch, then update it at each phase change.

If you stop before that branch exists (dirty tree, missing `develop`, blocked prerequisite, decision conflict), **don't write the file**. Put the record's content in your stop message instead. A file written on `main` or `develop` is untracked work that mixes into whatever is done there next, and it makes the next run of this workflow stop on a dirty tree.

```
# <task-id> · <title>
| Field | Value |
|---|---|
| Status | NOT STARTED / IN PROGRESS / IN REVIEW / BLOCKED (<item>) / DONE |
| Branch | feature/<task-id>-<slug> |
| Plan | <path to plan> · approved: <yes/no, date> |
| Updated | <YYYY-MM-DD> |

## Prerequisites and dependencies
## Contract / decision items (existing IDs, Proposed changes in the canonical documents)
## References inspected
## Validation results (actual)
## Open questions / follow-ups
```

`approved: yes` is a record, not by itself proof that the user approved the current plan; `atlantech-review-and-publish` verifies explicit approval in the conversation or asks the user to confirm.

Use the backlog's status values: `NOT STARTED`, `IN PROGRESS`, `IN REVIEW`, `DONE`, `BLOCKED`, `DEFERRED`. Status changes go in this record. Don't edit the backlog's status field unless the team asks you to.

**CLAUDE.md:** it holds durable, team-wide instructions, so changing it is a decision of its own, separate from any task. Transient progress never goes there.

When the work produces a durable rule or lesson, or the user asks for one:

- Present the exact proposed text in its own clearly labelled section, outside the plan.
- Say that approving the task plan does **not** approve this change.
- Don't edit CLAUDE.md in this task, even after the plan is approved.
- The change follows the repository's own approval and pull-request process for instruction changes. If none is documented, ask the user how they want it handled, for example as its own SETUP task and PR. Never fold it into the task branch.

## Reporting at each stop

Each stop or phase-end message should have these parts:

1. **Where we are:** phase, task, branch.
2. **What was run and inspected:** the actual commands and files.
3. **What was found:** blockers, conflicts, Proposed changes, missing references.
4. **What is needed from the user:** the exact next decision or approval.
