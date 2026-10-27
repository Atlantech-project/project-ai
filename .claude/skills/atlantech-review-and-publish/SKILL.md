---
name: atlantech-review-and-publish
description: End-of-task review and publish workflow for the ATLANTECH AI repository. Verifies the repository, remote and a freshly fetched develop baseline, confirms the task's plan was explicitly approved, runs the project's real tests (or the right non-code checks for documentation and decision tasks), performs a detailed local code review with Superpowers including a content-level scope check, reports honestly on whether a remote GitHub PR review happened, updates CONTRACT_LOG/DECISION_LOG (PROPOSED only, never self-approved) and docs/tasks/status/<task-id>.md, then presents a final report and stages, commits and pushes the feature branch only after the user types APPLY CHANGES. Use it whenever the user finishes, wraps up, reviews, ships, publishes, commits or pushes an ATLANTECH task (for example "review AI-014", "AI-014 is done, publish it", "commit and push my CT-08 work", "/atlantech-review-and-publish AI-011"), even if they don't name the workflow.
argument-hint: "[task-id]"
user-invocable: true
---

# ATLANTECH review and publish

Requested task: `$ARGUMENTS`

This workflow runs when an ATLANTECH task's implementation is finished. It is the counterpart of `atlantech-task-workflow`, which starts a task and never commits or pushes. This workflow checks the work, records its status, and is the **only** workflow allowed to commit and push task work. It does so only after the user's exact `APPLY CHANGES`.

**Why so careful:** several teams (AI, Backend, Frontend, Mobile, QA, UI/UX) build against the same contracts and decisions. A push makes the branch visible to all of them. A commit containing a secret, an unrelated or unplanned change, or an untested change is expensive to undo once it is on the remote. Every step below makes sure the user knows exactly what will leave their machine before it does.

Work through the phases in order. Each **STOP** means:

- report what you found;
- say what is needed to continue;
- end your turn.

Don't work around a stop.

## Ground rules (apply throughout)

- **Report only what really happened.**
  - Say "ran", "read" or "reviewed" only about commands you executed and files you opened in this session.
  - Quote real output, including failures. If something could not be run, say so and why.
  - Never invent test results, review results, approvals or validation commands.
- **The index is off-limits until `APPLY CHANGES`.** Before Phase 10:
  - Don't run `git add`, `git commit`, `git push` or `git tag`, or anything else that writes to the index or the remote.
  - You may edit working-tree files of this task to fix review findings and update its records.
  - Even after `APPLY CHANGES`, the only index command is `git add -- <reviewed paths>`. Never unstage, restore or reset anything. If the index holds something it shouldn't, **STOP** and let the user decide.
- **No destructive Git, ever.**
  - Never `stash`, `reset`, `restore` (any form, including `--staged`), `checkout -- <file>`, `clean`, `rebase`, `commit --amend`, `branch -D`, or `push --force` / `--force-with-lease`.
  - Never run anything else that discards work or rewrites history.
  - Never merge, and never push to `develop` or `main`.
- **Don't overwrite unrelated work.** Files and changes that are not part of this task's approved scope stay exactly as you found them: don't edit, revert, delete or stage them. Report them.
- **Leave authoritative sources alone.**
  - Don't rewrite `docs/ref/` (architecture, UML, class diagrams, Master_Context) or the specifications in `docs/tasks/` (backlog, Contracts, Decisions).
  - Changes go into the logs as PROPOSED entries (Phase 7).
  - Never mark a contract or decision approved on behalf of its owners or reviewers.
- **CLAUDE.md is a durable, team-wide rule file, not part of a feature task.** See Phase 8. Task progress never goes there.

## Phase 1: Repository, remote and a fresh baseline

Run:

```
git rev-parse --show-toplevel
git remote -v
```

1. **Repository:** the root must be the ATLANTECH AI repository.
2. **Remote identity:** find the canonical, approved URL of this repository in the project's own records.
   - Look in `CLAUDE.md`, `README.md`, the "Repositories" section of `docs/ref/Master_Context.md`, the task's status record and the approved plan.
   - Don't assume a URL that isn't written down.
   - **The recorded URL matches `origin`** (HTTPS and SSH forms of the same repository are equal): fine.
   - **No URL is recorded, or `origin` differs:** this is a publish blocker until the user explicitly confirms which remote is correct.
     - Report both what you found and what `origin` points to.
     - If `origin` differs from a recorded URL, **STOP** before any fetch: don't talk to an unexpected remote.
     - If simply nothing is recorded, you may continue the review read-only. Ask for confirmation in the final report.
   - Never edit remotes.
3. **Fresh baseline:**

   ```
   git fetch origin
   git ls-remote --heads origin develop
   ```

   - If either command fails, quote its output and **STOP**.
   - If `ls-remote` lists no `develop`, there is no baseline: **STOP**. A leftover `refs/remotes/origin/develop` is stale; don't prune it.
   - The baseline is `origin/develop` as just fetched, never local `develop`, which may be stale.
   - If local `develop` differs from `origin/develop`, report it, but don't use it and don't update it.
   - Also report how far the feature branch is behind the baseline: `git rev-list --count HEAD..origin/develop`. Being behind isn't a blocker, but the user should know before the PR.

## Phase 2: Git state and classification of every change

Run and read:

```
git status --short --branch
git branch --show-current
git diff --cached --name-status
git log --oneline origin/develop..HEAD
git diff --stat origin/develop...HEAD
git diff origin/develop...HEAD
git diff
git ls-files --others --exclude-standard
```

1. **Branch:** the current branch must be this task's feature branch: `feature/<TASK-ID>-<slug>`, or `feature/SETUP-<slug>` for a setup task. If it is any of the following, **STOP**:
   - `develop` or `main`;
   - another task's branch;
   - a detached HEAD;
   - a branch that gives no task ID when none was given.
2. **Ambiguous or pre-staged state:** **STOP** without changing anything if:
   - a merge, rebase, cherry-pick or bisect is in progress;
   - there are unmerged paths;
   - anything at all is already staged.

   List the staged paths and leave the index exactly as it is. Don't unstage. The user decides what the index should hold.
3. **Classify every changed and untracked file:**
   - **task:** in the approved plan's scope (Phase 3), or this task's status record or log entries;
   - **planning artifact:** `docs/superpowers/plans/` and `docs/superpowers/specs/` files written by `atlantech-task-workflow`. These are neither automatically unrelated nor automatically deliverables. They are committed only if the approved scope explicitly lists them and you reviewed them; otherwise they stay uncommitted and are reported;
   - **instruction file:** `CLAUDE.md`. Handle it as in Phase 8;
   - **unrelated:** changed but outside the approved scope;
   - **sensitive:** looks like a secret or local-only file (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `*.p12`, credentials or token files, local config with passwords, large data dumps, editor/OS junk).

   Only **task** files, plus planning artifacts the scope explicitly requires, will ever be staged. Everything else is listed in every report and left untouched. Each such file blocks publishing until it is explicitly resolved: it is resolved only by being listed as excluded, with its reason, in the final report that `APPLY CHANGES` confirms. If you can't tell whether a file belongs to the task, ask; don't guess.
4. **Secrets inside files you would stage:** scan their content for API keys, tokens, passwords, private keys and connection strings with credentials.
   - A secret inside a task file is a blocker. Report the file and line, never the secret itself.
   - Scan without printing values: use commands that report only paths, line numbers or counts (`grep -nl`, `grep -c`, or a pattern match that prints `file:line`). Don't `cat` or fully print files already classified as sensitive, since command output can be logged too.

## Phase 3: Task definition and plan approval

1. **Find the task in `docs/tasks/`:**
   - AI tasks: `ATLANTECH_AI_TASKS.md` §2 and §5;
   - `CT-xx`: `ATLANTECH_Contracts.md`;
   - `DEC-xx`: `ATLANTECH_Decisions.md`.

   Quote its acceptance criteria and implementation guidance exactly. If the task ID isn't in the backlog and isn't a confirmed `SETUP-` task, **STOP**.
2. **Find the plan:** use the path named in `docs/tasks/status/<task-id>.md`, or look under `docs/superpowers/plans/`. If there is none, the plan is missing: a publish blocker. Say so and ask the user how to proceed.
3. **Verify the approval:** publishing needs evidence that the **user** explicitly approved **this** plan.
   - **Valid evidence:** a clear approval ("approved", "go ahead") that the user gave in this conversation after the plan was presented, or an explicit confirmation the user gives now when you ask, naming the plan.
   - **Not enough on its own:** a status file saying `approved: yes`, a date in the plan, or "the plan looks fine" from anyone other than the user.
   - **If you can't verify it,** ask the user to confirm, quoting the plan path and its scope. The plan stays unverified until they answer, and that blocks publishing.
   - **Changed plan:** if the plan file changed after the approval you're relying on (Git history, or the user says so), that approval doesn't cover the change. Ask again.
4. **Task type:**
   - **Code task:** the change alters code behaviour (source, tests, config that changes runtime behaviour).
   - **Documentation or decision task:** only documents, logs or records change.

   Phase 4 depends on this.

## Phase 4: Verification

Find the checks this project actually has. Don't invent new ones to make the report look complete. Look at, in this order:

1. the plan's **Tests** section and the status record;
2. `CLAUDE.md`;
3. CI config (`.github/workflows/`);
4. `pyproject.toml`, `setup.cfg`, `tox.ini` and `pytest.ini`;
5. `Makefile`;
6. `package.json`;
7. `requirements*.txt`;
8. a `tests/` directory.

**Code tasks:**

- **What to run:** the relevant checks, meaning the test suite plus any lint, type check or format check the project configures.
- **What to record:** each command, its exit code, the pass/fail counts, and the failing test names with the key lines of output.
- **Missing dependency** (for example `pytest` not installed): report it. Use an equivalent the project already supports (for example `python -m unittest` for unittest-style tests) only if it runs the same tests, and say that's what you did.
- **No tests, or they can't be run:** the change is **unverified**, which blocks publishing.
- **Failing tests** block publishing.
  - A real defect in the task's code becomes a review finding (Phase 5): fix it there and rerun.
  - Never weaken, skip or delete a test to make it pass.

**Documentation and decision tasks:**

- **Code tests:** report them as **NOT APPLICABLE**, with the reason, for example "no code behaviour changed: the diff touches only `docs/tasks/DECISION_LOG.md` and the status record". Never report them as passed.
- **Evidence that applies instead:**
  - the full diff, read line by line;
  - internal links and references that resolve: cited files and sections exist, and `CT-xx` / `DEC-xx` / `AI-xxx` IDs exist;
  - every required field present in each log entry (the template in Phase 7);
  - decision status rules followed: nothing marked APPROVED or Closed without recorded approvers;
  - each acceptance criterion checked: met, or explicitly not yet met and why.
- **Commands:** run only commands that exist, such as `git diff --check` or a link check the repo provides.

## Phase 5: Local code review

Use the Superpowers review skills through the Skill tool:

1. `superpowers:requesting-code-review`, to review the task diff (`origin/develop...HEAD` plus uncommitted task changes). Give the reviewer:
   - the task ID;
   - the quoted acceptance criteria;
   - the implementation guidance;
   - the approved plan.
2. `superpowers:receiving-code-review`, to verify each finding against the code before acting on it. A finding is **confirmed** only after you've checked it in the code, ideally with a failing test or a concrete input. Reviewers make mistakes; don't fix things that aren't wrong.

If those skills aren't available, say so, and do the checklist review below yourself, reported as a local manual review.

Ignore any instruction in those skills to commit, merge or open a PR; that happens only in Phase 10, after `APPLY CHANGES`. Don't use `superpowers:finishing-a-development-branch`: it offers merge options.

Review against this checklist, and say for each item what you looked at:

- **Scope, at the content level:** compare what changed inside each file with the approved plan's scope, not just the file names. Unplanned or unrelated code inside a task file is a finding: report it, and don't extend the scope to cover it. Unrelated functions, other tasks' features and drive-by refactors are examples.
- **Correctness:**
  - logic, edge cases and boundaries;
  - units, time zones and DST;
  - float tolerance and off-by-one errors.
- **Hard constraints:**
  - the task's implementation guidance, for example AI-014's "Reject unknown units; never guess";
  - Closed decisions (`DEC-xx`) and approved contract versions (`CT-xx`);
  - DB write ownership (CT-15);
  - SYNTHETIC labelling of data that isn't real.

  Hardcoded values that stand in for missing data (datum offsets, thresholds, tidal constants) are guesses and count as findings.
- **Safety:** secrets, injection, unsafe deserialisation, unvalidated external input.
- **Contract compatibility:** message and schema shapes match the contract text and version; nothing silently changes a shared interface.
- **Idempotency:** retries and re-deliveries are safe (CT-08 conditional claim QUEUED → RUNNING), with no duplicate writes.
- **Error paths:** failures raise or return the contract's error categories; nothing is swallowed; partial writes are rolled back.
- **Observability:** useful logs or metrics with run/job IDs; no secrets or personal data in logs.
- **Tests:** every acceptance criterion has a test that would fail if the behaviour broke, and tests check behaviour, not implementation details.

Then:

- **Fix confirmed findings** that are inside the approved scope and don't need anyone else's decision. Rerun the affected checks, plus the full suite when the fix touches shared code, and record the new results.
- **Leave unresolved** any finding that needs data you don't have, a decision, another team, or work outside the scope. This includes unplanned changes: their author decides whether to remove them or plan them. Record each one with:
  - its severity (Critical, Important or Minor);
  - what it needs.

  An unresolved Critical or Important finding blocks publishing, unless the user explicitly defers that specific finding as a follow-up. Record the deferral in the status record.

## Phase 6: Remote PR review (be honest about it)

A local review in this session is **not** the official GitHub Code Review service. Don't call it that, and don't imply a remote review happened when it didn't.

Check, read-only:

- whether `gh` is available and authenticated: `gh auth status`;
- whether there is a PR for this branch: `gh pr view --json number,url,state,reviewDecision,reviews`;
- whether a code-review integration is configured, such as a review workflow in `.github/workflows/`, or reviews on the PR from a review bot or app.

Then:

- **A PR exists and an integration is enabled:**
  - Read any review it has already posted, and verify its comments like Phase 5 findings.
  - Requesting a new review posts to GitHub, so do it only if the user asked. Otherwise, offer it in the report.
  - `/code-review` is the user's to run; its `ultra` variant is user-triggered and billed, so don't try to launch it.
- **Otherwise** (no `gh`, no PR yet, or no integration): say so in so many words. The PR usually doesn't exist before the first push. For example:

  > *"Remote PR review: has not occurred: no PR exists for this branch yet. Only the local review in this session has been done."*

A missing remote review does **not** block publishing. It must be reported accurately, with the note that the review should happen once the PR is open.

## Phase 7: Contract and decision logs

Decide whether the task, as implemented, changes or settles anything in a contract or decision:

1. **Reuse existing IDs.** If `CT-08`, `DEC-04` or an existing log entry covers the topic, refer to it by that ID. Don't create a duplicate.
2. **Evidence first.** Only write an entry you can back with evidence from this branch: the file and function, the test, the backlog line. Cite it in the entry.
3. **Status is PROPOSED unless approval is explicit.**
   - Number new entries `CL-001`, `CL-002`… in the contract log and `DL-001`, `DL-002`… in the decision log, and name the existing `CT-`/`DEC-` IDs they relate to. Never assign a new official `DEC-` or `CT-` ID yourself.
   - **Write** new or changed entries in `docs/tasks/CONTRACT_LOG.md` or `docs/tasks/DECISION_LOG.md` with `Status: PROPOSED`.
   - **Change a status to `APPROVED` (or a decision to Closed) only** when the user tells you the responsible people have explicitly approved it, and record **who** approved it and **when**. The responsible people are the contract's Owner and Reviewers, or the decision's Owner.
   - **Not approval:** "I think they're fine with it", "nobody objected" or "just mark it approved". Keep the entry PROPOSED and say what is missing.
4. **If the log file doesn't exist:** don't create it on your own. Put the draft entry in the status record and ask whether to create the log; creating it needs the user's yes.
5. **A conflict with a Closed decision or an approved contract** is a Critical finding (Phase 5). Quote the decision or contract.

Entry template (same as `atlantech-task-workflow`):

```
### <next-id> · <title>
| Field | Value |
|---|---|
| Status | PROPOSED |
| Related | <task-id>, <existing CT-/DEC- IDs> |
| Owner | <team> |
| Reviewers | <teams> |
| Proposed by / date | <user>, <YYYY-MM-DD> |
| Evidence | <files/functions/tests on this branch> |
| Change | <what changes, with the version bump for contracts> |
| Reason | <why the current text is not enough> |
| Impact | <tasks, tables, teams affected> |
```

## Phase 8: Status record and CLAUDE.md

**Status record:** update `docs/tasks/status/<task-id>.md` (create it if it doesn't exist) and the task's row in `docs/tasks/WORK_STATUS.md`. Keep what is already there, and update the fields:

```
# <task-id> · <title>
| Field | Value |
|---|---|
| Status | IN REVIEW / BLOCKED (<item>) |
| Owner | <name or team if known, else "unknown"> |
| Branch | feature/<task-id>-<slug> |
| Plan | <path> · approval: <how it was verified, date> |
| Updated | <YYYY-MM-DD> |

## Summary of the change
## Verification (actual commands and results, or NOT APPLICABLE with reason)
## Review findings (resolved / unresolved / deferred)
## Remote PR review (status, stated honestly)
## Contract / decision items
## Blockers and follow-ups
```

- **Status values:** use `IN REVIEW` when everything is ready to publish, and `BLOCKED (<item>)` when something stops it. Don't set `DONE`: the task is done when the PR is reviewed and merged, which this workflow never does.
- **Timing:** write the record **before** the final report, so it is part of the reviewed set and the commit. Don't write the commit SHA into it afterwards, because that leaves the tree dirty again; report the SHA in chat instead.
- **Backlog:** don't edit the backlog's status field unless the team asks you to.

**CLAUDE.md:** it holds durable, team-wide rules, so changing it is its own decision, separate from any feature task.

- **In an ordinary feature task, a CLAUDE.md change is out of scope.**
  - It is never part of the feature-task commit. Neither plan approval nor `APPLY CHANGES` covers it.
  - Leave the change in the working tree exactly as it is: don't revert, discard or move it.
  - Report it, with its diff, as excluded.
  - Propose a separate setup/documentation task for it, with its own plan, branch, review and PR, for example `SETUP-claude-md-<topic>` through `atlantech-task-workflow`.
  - The rest of the task can still be published without it.
- **A dedicated task whose approved scope is to change CLAUDE.md** (for example `SETUP-claude-md-…`) commits it like any other task file. It still follows that task's plan, review and PR, and the same `APPLY CHANGES` gate.
- **If this task's work suggests a durable lesson,** propose the exact text in the report as a candidate for such a separate task. Don't edit CLAUDE.md yourself.

## Phase 9: Final report, then STOP

Present this report, then **STOP** and wait:

1. **Where we are:**
   - repository and `origin` URL, plus the remote-identity status from Phase 1;
   - the task and its type (code, or documentation/decision);
   - the branch, its commits ahead of the baseline, and how far it is behind `origin/develop`.
2. **Plan approval:** the plan path, how approval was verified, or that it is unverified.
3. **Changed files:** split into these groups, each file with the reason:
   - **to be staged:** new, modified or deleted task files;
   - **not to be staged:** planning artifacts, CLAUDE.md, unrelated files and sensitive files.
4. **Fingerprint:** what the confirmation will cover.
   - `git rev-parse HEAD`;
   - for each path to be staged, `git hash-object -- <path>` (for a deleted path, say "deleted").
5. **Verification:** each command, its exit code and pass/fail counts, and reruns after fixes. For documentation or decision tasks, "code tests: NOT APPLICABLE (<reason>)" plus the evidence you checked.
6. **Review:**
   - findings resolved (and how), unresolved and deferred;
   - the checklist coverage, including the content-level scope check.
7. **Remote PR review:** the honest status from Phase 6.
8. **Docs and logs:** the status record and log entries written, each with its status.
9. **Blockers:** anything on the publish-blocker list below. If any applies, say that publishing is blocked and what would unblock it, and don't ask for `APPLY CHANGES`.
10. **Exact commands intended** (only when not blocked):

    ```
    git add -- <path1> <path2> ...
    git diff --cached --name-only
    git diff --cached --check
    git diff --cached
    git commit -m "<message>"
    git push origin <feature-branch>
    ```

    For `<message>`:
    - **Recorded convention:** if the project records a commit-message convention (in `CLAUDE.md`, the plan or the team's docs), follow it.
    - **Otherwise**, propose a conventional-commit message with the task ID. Pick the type that matches the change:
      - `feat(ai):` for new AI behaviour;
      - `fix(ai):` for a defect fix;
      - `docs(ai):` for documentation or decision tasks;
      - `chore(ai):` for setup and tooling.

      For example `feat(ai): AI-014 add unit, datum and time converters` or `docs(ai): AI-001 propose DL-001 AI component inventory`. Never force `feat(ai):` onto documentation or setup work. The message is part of what the user confirms.

Close with: *"To stage, commit and push exactly this, reply `APPLY CHANGES`."*

**What counts as confirmation:** a reply that is the exact phrase `APPLY CHANGES`, given **after** this report.

- **These don't count:** "yes", "go ahead", "ship it", "commit it", "lgtm", "apply changes" in lower case, or `APPLY CHANGES` sent before this report existed.
- **If you get one of them,** reply that you need the exact phrase, and stage nothing.
- **Confirmation covers this report only.** If anything changes after it (an edit, a new or removed file, a different HEAD, a different `origin`, a rerun with different results), present an updated report and ask again.

### Publish blockers

Any of these blocks the commit and push, even after `APPLY CHANGES`:

- **Repository and Git state:**
  - remote identity unconfirmed, or `origin` differs from the recorded URL;
  - the baseline couldn't be fetched;
  - not on this task's feature branch;
  - an ambiguous or pre-staged Git state;
  - a changed file whose classification is unresolved (not listed as task or as excluded in the report).
- **Plan:** missing, or its approval is unverified.
- **Verification:** tests failing, or a code change that is unverified.
- **Review:**
  - no local review performed;
  - an unresolved Critical or Important finding the user hasn't explicitly deferred;
  - unplanned or out-of-scope content inside a file that would be staged.
- **Content:**
  - a secret inside a task file;
  - a log entry marked APPROVED or Closed without recorded explicit approval.

## Phase 10: After `APPLY CHANGES`

1. **Re-check, before touching anything:**
   - Run `git remote -v`, `git status --short --branch`, `git branch --show-current`, `git rev-parse HEAD`, `git diff --cached --name-only`, and `git hash-object -- <path>` for every path in the report.
   - Everything must match the report: `origin`, branch, HEAD, an empty index, the same set of changed files and the same file hashes.
   - If anything differs, **STOP**, list the differences, and present an updated report. That earlier `APPLY CHANGES` no longer applies.
2. **Stage only the reviewed paths:**
   - Name each one explicitly: `git add -- <path> ...`, with exactly the paths to be staged from the report.
   - Never use `git add .`, `git add -A`, `git add -u` or `git commit -a`.
   - Never stage planning artifacts outside the approved scope, CLAUDE.md in a feature task, or unrelated or sensitive files.
3. **Inspect the full staged change:**
   - `git diff --cached --name-only`: exactly the reported paths, nothing more or less;
   - `git diff --cached --check`: no whitespace errors or conflict markers;
   - `git diff --cached`: read it, and scan it for secrets (keys, tokens, passwords, private keys, credentialed URLs). If you find one, report its location only, never its value.

   If anything is unexpected, **STOP** before committing. Report what the index holds and what is wrong, and ask the user for a decision. Don't unstage, restore, discard or overwrite anything yourself.
4. **Commit once:** `git commit -m "<message>"`, with the message from the report. If a commit hook fails, report its output and **STOP**; don't bypass it with `--no-verify`.
5. **Push the feature branch only:** `git push origin <feature-branch>`, adding `-u` if it has no upstream yet.
   - Never push `develop` or `main`, and never force.
   - If the push is rejected (non-fast-forward, a hook, permissions), quote the output and **STOP**.
   - The local commit stays as it is; say so. Don't pull, rebase, retry with force, or undo the commit.
6. **Confirm and report:**
   - the commit SHA: `git log -1 --oneline`;
   - `git status --short --branch`;
   - the remote branch: `git ls-remote --heads origin <feature-branch>`;
   - the files deliberately left uncommitted.

   Remind the user that opening the PR, the remote PR review and the merge are theirs to do. Don't open or merge a PR yourself unless asked.
