# SETUP-002 · Canonical Decisions and Contracts: plan

Presented in chat on 2026-10-27 and approved by the user on 2026-10-28 ("I approve the SETUP-002 plan"), together with the rulings below. Branch-preparation correction approved on 2026-10-28. Publishing happens only through `/atlantech-review-and-publish SETUP-002` and the user's `APPLY CHANGES`; this plan has no commit steps.

## Task
- **ID:** SETUP-002 · Canonical Decisions and Contracts (setup task, not in the official backlog).
- **Branch:** `feature/SETUP-002-canonical-decisions-contracts`, from `develop` = `origin/develop` = `9edc32e`. The user's uncommitted edits were carried over and checked against checksums.

## Scope
**In:**
- Make `docs/ref/ATLANTECH_Decisions.md` and `docs/ref/ATLANTECH_Contracts.md` the only records for decisions and contracts.
- Migrate DL-001 and DL-002 into the Decisions file, and retire both logs.
- Map the existing decisions and contracts to their canonical DEC/CT entries.
- Reconcile the status of decision tasks.
- Update `CLAUDE.md`, both project skills, their evals and fixtures, and the stale references in the docs and READMEs.

**Out:**
- Production AI worker logic.
- Rewriting the module READMEs' queue definitions.
- The read-only backlog.
- Historical plan files.
- The old `.claude/worktrees/` worktree.
- Status records for other teams' CT/DEC tasks.

## User rulings (2026-10-28)
1. **DL-003 to DL-008:** the user's edited `docs/ref/` Decisions and Contracts files are canonical and hold the substance of those decisions. Don't recreate DL entries or restore the logs. Report only genuine gaps.
2. **Task ID and branch:** SETUP-002, on the branch above.
3. **B8 owner:** AI Team. The AI-001 inventory is approved; record only the approval evidence that exists.
4. **AI-002:** DONE as a decision task. The missing `ATLANTECH_AI_BACKEND_DEPENDENCIES.md` update becomes an approved scope exception and an external follow-up.
5. **DEC-04 and CT-08:** DEC-04 stays Closed. CT-08 stays Proposed until Backend sign-off is evidenced. Document the dependency.
6. **DL-002:** the repository location and the five modules are approved. The yard and validation worker-to-module mapping is a follow-up; don't rewrite the READMEs' queues.
7. **Statuses:**
   - DONE: AI-010, SETUP-001, AI-001, AI-002 (with the exception above) and AI-004.
   - Still open: AI-003 and the implementation tasks.

## Files
- **Canonical:**
  - `docs/ref/ATLANTECH_Decisions.md`: preamble rules, DEC-04 open-dependency row, new "AI task decisions" section with AI-001 and AI-010.
  - `docs/ref/ATLANTECH_Contracts.md`: preamble rules, and a note on the local reference copies in `ai-payloads/` and `db/`.
- **Rules:**
  - `CLAUDE.md`;
  - `.claude/skills/atlantech-task-workflow/SKILL.md`;
  - `.claude/skills/atlantech-review-and-publish/SKILL.md`.
- **Evals:**
  - task-workflow: `evals.json` (evals 5, 6 and 11 updated; new eval 22 `decision-change-canonical`) and `build_fixtures.sh`;
  - review-and-publish: `evals.json` (evals 5, 13 and 14 reworked, the `verification` text updated), `build_fixture.py` and `check_state.py`.
- **Records:**
  - `docs/tasks/WORK_STATUS.md`;
  - status records AI-010 and SETUP-001 (updated);
  - status records AI-001, AI-002, AI-004 and SETUP-002 (new).
- **Docs links:** `README.md`, plus `common/`, `edi/`, `part1/`, `part2/` and `part3/` `README.md`.
- **Deleted by the user, kept deleted:**
  - `docs/tasks/DECISION_LOG.md` and `docs/tasks/CONTRACT_LOG.md`;
  - `docs/tasks/ATLANTECH_Decisions.md` and `docs/tasks/ATLANTECH_Contracts.md` (moved to `docs/ref/`).
- **Added by the user, preserved:** `docs/ref/ai-payloads/*.json`, `docs/ref/db/table-names.md`.

## Tests and checks
Code tests are NOT APPLICABLE: there is no production code. The checks:
- `bash -n` on both shell scripts;
- `py_compile` on both Python eval scripts;
- `json.load` on both `evals.json` files and every payload schema;
- every review fixture built, then `check_state.py` run on it, plus one negative test;
- the five relevant task-workflow fixtures built, then `check_state.sh compare` run on each;
- eval and builder scenario lists compared;
- a grep sweep for obsolete log and `ai/` references;
- status consistency between `WORK_STATUS.md` and the records;
- link and ID checks;
- `git diff --check`;
- a secret scan;
- checksums of the user's preserved files.

## Risks
- **Fixtures copy the real docs:** they strip the "AI task decisions" section so that scenarios start before AI-001 and AI-010 were decided.
- **Approval evidence is thin:** AI-001 and AI-010 rest on the user's approval. The AI-001 record names roles only, with a blank date. Nothing beyond that is claimed.

## Acceptance (from the user's request)
- Canonical files are the single source of truth.
- No logs remain.
- Rules 1–9 are in `CLAUDE.md` and both skills.
- Task statuses follow the acceptance criteria.
- Paths use `docs/ref/` and `ai-payloads/`.
- Validation was actually run.
- Remaining intentional references are reported.
