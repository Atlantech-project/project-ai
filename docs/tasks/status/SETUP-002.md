# SETUP-002 · Canonical Decisions and Contracts
| Field | Value |
|---|---|
| Status | IN REVIEW |
| Owner | AI Team |
| Branch | feature/SETUP-002-canonical-decisions-contracts |
| Plan | docs/superpowers/plans/2026-10-28-setup-002-canonical-decisions-contracts.md · approval: explicit user approval in this conversation after the plan was presented ("I approve the SETUP-002 plan", 2026-10-28), plus the user's rulings; the file is a transcription written after that approval |
| Updated | 2026-10-28 |

Setup task, not in the official AI backlog. Repository governance only; no production AI code.

## Summary of the change
- **Single source of truth.** `docs/ref/ATLANTECH_Decisions.md` and `docs/ref/ATLANTECH_Contracts.md` are the only records for decisions and contracts.
  - Both preambles now state the rules: edit in place, `Proposed change` rows until approval, approval recorded with who and when, follow-ups without reopening.
  - The decision and contract logs are retired.
- **Migration.**
  - DL-001 and DL-002 became the **AI-001** and **AI-010** entries in the Decisions file's new "AI task decisions" section. Both are Closed on the user's approval. B8's owner is AI Team.
  - No new `DEC-`/`CT-` IDs were assigned.
- **DEC-04 / CT-08.** DEC-04 stays Closed. A new "Open dependency" row records that CT-08 stays Proposed until the Backend Team's sign-off is recorded, and which tasks wait for it. The Decisions file's closing rules don't require that sign-off to close DEC-04.
- **Contracts.** A note maps the local reference copies: `docs/ref/ai-payloads/` mirrors `contracts/ai/`, and `docs/ref/db/` mirrors `contracts/db/`. The contract paths and schema `$id`s are unchanged.
- **Rules.** `CLAUDE.md` and both skills now carry the canonical-document workflow (user rules 1–9).
  - `CLAUDE.md`: sources table moved to the `docs/ref/` paths; new "Decisions and contracts" section; status follows acceptance criteria.
  - Task workflow: ground rules, Phase 2, Phase 4, and Phase 5 rewritten.
  - Review and publish: ground rules, Phases 2–4, Phase 7 rewritten, Phase 9 report, publish blockers.
- **Evals.**
  - Task workflow: evals 5, 6 and 11 updated; new eval 22 `decision-change-canonical`. The fixture builder drops the log handling and strips the "AI task decisions" section.
  - Review and publish: scenario `unapproved-log` became `unapproved-contract-change` (CT-18 Proposed change); `missing-decision-log` became `log-requested`; `docs-only-decision` now uses the canonical AI-001 entry.
  - `check_state.py` now reports the CT-18 and AI-001 statuses, `canonical_changed`, retired logs and DL-/CL- entries. A retired log counts as unsafe.
- **Records.**
  - AI-010 and SETUP-001 reconciled to DONE.
  - New records for AI-001 and AI-004 (DONE) and AI-002 (DONE with an approved scope exception).
  - `WORK_STATUS.md` updated to match.
- **Links.** The root and module READMEs point to the canonical decisions; `common/README.md`'s CT-15 path is fixed.

## Verification (actual, run 2026-10-28 in Git Bash)
Code tests: NOT APPLICABLE. No production code changed; the diff is documentation, skill instructions, eval tooling and records.

- **Branch preparation.**
  - The first `git switch develop` refused because local `develop` was stale. Nothing changed, and all checksums still matched.
  - With the user's approval, `git fetch origin develop:develop` fast-forwarded `develop` from `1cec937` to `9edc32e`. The trees matched (`00bf805`), then `git switch develop` and `git switch -c` ran.
  - `HEAD` = `develop` = `origin/develop` = `9edc32e`. The 13-entry status listing was identical, and every checksum matched.
- **Syntax.**
  - `bash -n` on both task-workflow scripts: exit 0.
  - `py_compile` on `build_fixture.py` and `check_state.py`: exit 0.
  - `json.load` on both `evals.json` files and the 4 `ai-payloads` schemas: all exit 0.
  - Eval IDs unique (22 and 17).
- **Review-and-publish fixtures.** All 17 scenarios built, and `check_state.py` reports `unsafe: []` for each.
  - `unapproved-contract-change`: CT-18 `Approved v1.0` with the Proposed change present.
  - `docs-only-decision` and `log-requested`: `ai001_status = Proposed`, `canonical_changed` = the Decisions file.
  - Every fixture: no retired logs, 0 DL-/CL- entries, 0 `authoritative_changed`.
  - `--mutate changed-after-report`: exit 0.
  - **Negative test:** a planted `docs/tasks/DECISION_LOG.md` makes `unsafe` contain "a retired decision or contract log exists".
  - The scenario lists in `evals.json` and `SCENARIOS` match.
- **Task-workflow fixtures.** `normal-unblocked`, `onboarding`, `unresolved-contract`, `conflicts-closed-decision` and `decision-change-canonical` built.
  - `check_state.sh compare`: SAFE for each.
  - Each has no log files, no "AI task decisions" section, CT-08 `Proposed v1.0` and CT-18 `Approved v1.0`.
  - The onboarding fixture's `docs/ref` holds 6 Markdown files plus `ai-payloads/` and `db/`.
  - The eval names (22) match the builder's scenario list.
  - The scripts were run from LF copies in the scratchpad, because the working-tree copies are CRLF under `core.autocrlf=true`.
- **Sweep.** No stale `docs/tasks/ATLANTECH_{Contracts,Decisions}` path or `ai/` payload path remains in live files. The remaining log mentions are intentional (see below).
- **Records.** `WORK_STATUS.md` agrees with each record (SETUP-001, AI-010, AI-001, AI-002, AI-004). Every `DEC-`/`CT-` ID cited in the new records and the Decisions file exists.
- **Other checks.**
  - `git diff --check`: exit 0. No trailing whitespace or conflict markers in the untracked files.
  - Secret scan: hits only in the eval fixtures' deliberate fake credentials and in masked contract example payloads. The latter are the same 8 lines as in the committed original.
  - The user's `ai-payloads/*`, `db/table-names.md` and `ATLANTECH_AI_ARCHITECTURE.md` match their pre-branch checksums.
- **Line endings.** `sed -i` had turned 7 edited files to LF in the working tree; they were restored to CRLF. The index stays LF.

**Not run:** the skill evals themselves, which run agents against the fixtures with grading. Only fixture building and state checks were run.

**Reruns after the review fixes (2026-10-28):**
- `bash -n` (both scripts), `py_compile` (both Python files) and `json.load` (both `evals.json`): all exit 0.
- **Review fixtures:** all 17 rebuilt, and `check_state.py` reports `unsafe: []` for each, with the same CT-18 and AI-001 values as before.
- **Negative tests:**
  - A removed `ATLANTECH_Contracts.md` makes `unsafe` contain "a canonical decision or contract file is missing", and `ct18_status` reads `missing`.
  - A planted `DECISION_LOG.md` makes `unsafe` contain "a retired decision or contract log exists".
  - A docs copy with the "AI task decisions" heading renamed makes both builders exit 1 with "still holds an AI-001 decision after stripping".
- **Task-workflow fixtures:** the 5 relevant fixtures rebuilt, and `check_state.sh compare` reports SAFE for each, with no AI task decisions left in them.

## Review findings
Local review: a fresh reviewer subagent ran `superpowers:requesting-code-review` on the uncommitted diff, read-only. Each finding was checked against the files before acting (`superpowers:receiving-code-review`). Verdict: "With fixes". Critical: none.

**Resolved:**
- **Important:** the AI-010 record set DONE while the branch-protection criterion was unverified, without labelling it as a scope exception. The record now states the exception, citing the user's explicit ruling "AI-010 is DONE… Do not reopen AI-010", and keeps OQ-6 as a follow-up.
- **Minor:**
  1. AI-010 dates are now consistent: merged 2026-10-27, approved as a decision 2026-10-28.
  2. OQ-4 added to AI-010's open follow-ups; "DEC-02 vs §12.4" closed by the Closed DEC-02, DEC-08 and CT-15.
  3. "Unchanged in substance" now notes that DL-002's queue assignments were left to the worker-to-module follow-up.
  4. Both skills now cover `Proposed vX.Y`, and limit the "AI task decisions" section to one-task decisions; any other new topic means asking the user.
  5. Both fixture builders fail loudly if an AI-001 decision survives the strip. The task-workflow builder's comment is corrected.
  6. `check_state.py` decodes Git output as UTF-8 with replacement, and reports a missing canonical file as unsafe instead of crashing.
  7. The CT-18 injection is bounded to the CT-18 section.
  8. The stale "PROPOSED entries" heading in the task-workflow fixture is updated.
  9. Eval 22 states CT-18's real Owner and Reviewers.
  10. AI-002 uses plain `DONE` in the tracker and the record, and the ad-hoc "FU-AI002-1" label is dropped.
  11. AI-002 carries a caveat on how thin DEC-54's text is for OD-18.

**Not changed (judged acceptable):**
- In most task-workflow fixtures, the preamble link `[AI task decisions](#ai-task-decisions)` dangles because the section is stripped. It is harmless in a fixture.
- In some fixtures the status records say AI-001 and AI-010 are DONE while their canonical entries are stripped. The new rule says a missing record isn't evidence of an unsettled decision, so the risk is low.

**Unresolved or deferred:** none.

## Remote PR review
Has not occurred:
- `gh` is not installed;
- `.github/workflows/` doesn't exist;
- the branch hasn't been pushed, so no PR exists.

Only the local review in this session has been done. A remote review should happen once the PR is open.

## Intentional remaining references to the retired logs
- **Rule text that forbids logs or explains their retirement:** `CLAUDE.md`, both SKILL.md files, and both Decisions/Contracts preambles.
- **Eval negative checks** (`check_state.py`, both `evals.json` files) and the `log-requested` prompt.
- **History:** the "AI task decisions" section intro (DL-001 and DL-002 provenance); the AI-001 status record (provenance and the backlog criterion quoted verbatim); the AI-010 and SETUP-001 records; both historical plans in `docs/superpowers/plans/`.
- **Backlog:** `docs/tasks/ATLANTECH_AI_TASKS.md` mentions a "decision log" 15 times. The backlog is read-only; `CLAUDE.md` maps that term to `docs/ref/ATLANTECH_Decisions.md`.
- **Not touched:** `.claude/worktrees/atlantech-review-and-publish-skill/`, an old worktree outside the task.

## Contract / decision items
- **Changed directly in the canonical files** (no `Proposed change` rows written):
  - AI-001 and AI-010 task decisions (Closed, on the user's approval);
  - DEC-04 "Open dependency" row;
  - preambles of both files.
- **Unchanged:** CT-08 stays Proposed v1.0.
- **DL-003 to DL-008:** per the user's ruling, their substance is the user's edited canonical entries.
  - Closed DEC-01, -02, -03, -04, -06, -08, -10, -12, -14 to -19 and -23, each pointing to its CT text.
  - Contracts CT-09 to CT-18: approved, except CT-08.
  - No exact gap was found to report. The original DL-003 to DL-008 texts aren't in the repository, so a line-by-line comparison wasn't possible.

## Follow-ups
- **CT-08:** Backend Team sign-off. Until then, AI-003 and the tasks that depend on it stay open.
- **AI-010 module docs:** the yard and validation worker-to-module mapping, the matching README refresh, and the stale "Pending" list in `common/README.md` (DEC-02 and DEC-10 are now Closed).
- **AI-002:** the external `ATLANTECH_AI_BACKEND_DEPENDENCIES.md` update (open; see the AI-002 record).
- **AI-001:** decision date; DEC-21, DEC-25, DEC-29 and DEC-31 still Open; `Master_Context.md` §6.4 wording on C3/C4.
- **`Master_Context.md` §5.4:** its owner should add `project-ai`.
- **OQ-6:** branch protection and PR flow are unverified.
- **Local schema copies:** the envelope's `$ref`s to `c01`–`c04` aren't present in `docs/ref/ai-payloads/` (they live in `contracts/ai/`).
- **Old worktree:** `worktree-atlantech-review-and-publish-skill` and its worktree; removing them is the user's call.
