# SETUP-003 · PortHub contracts and decisions synchronization (approved plan, Revision 2)

Transcription of the plan the user approved on 2026-10-31 ("I approve SETUP-003 Revision 2 with the following final decisions"). Branch: `feature/SETUP-003-porthub-contracts-decisions-sync`, from `develop` at `2f3b89e`. Setup task, not in the backlog. Publishing goes through `/atlantech-review-and-publish SETUP-003`; nothing is committed by this plan.

## Rule
PortHub `contracts/` is the source of truth for shared Contracts and Decisions. Shared items follow PortHub; AI-owned and local-only content is preserved; never overwrite newer PortHub text; edit item by item, never copy whole files.

## Scope (in)
1. **Decisions:** range text to DEC-57; DEC-05, 13, 35, 36, 47 to PortHub's Closed text (Summary, Status, Decision); add DEC-57; DEC-04 approved 2026-10-30 and its "Open dependency" row removed; `w_edi` `retry_count` and the 2026-10-28 note.
2. **Contracts:** CT-08 Approved v1.0 (2026-10-30); CT-01 short form and reviewers (DEC-57); CT-02 and CT-03 status lines; CT-03 `username` and `PORT_STAFF`. Links to PortHub-only files become "PortHub `contracts/<file>`".
3. **Schemas and references** in `docs/ref/ai-payloads/`: add c01-part1-run, c02-part2-solve, c03-yard, c04-baplie, `table-ownership.md`, `contract-v1-record.md`, identical to PortHub. Update the "Local reference copies" paragraph.
4. **Not mirrored:** `db/schema.sql` (user decision); the paragraph points to PortHub `contracts/db/schema.sql`.
5. **Dependents:** task-workflow eval 5 (`unresolved-contract`) and its fixture builder; AI-014 record to DONE; evidence lines in the AI-016 record.
6. **Records:** `docs/tasks/status/SETUP-003.md`; `WORK_STATUS.md` (SETUP-003 row; AI-014 DONE with PR #7 and merge `2f3b89e`; AI-016 stays IN REVIEW with PR #5 and merge `451daff`).

## Out of scope
SETUP-004 (`CLAUDE.md`, skills, workflow text); publishing the "AI task decisions" section to PortHub; new `DEC-`/`CT-` IDs; marking implementation tasks done; CT-05's `realtime-sse.md` reference (follow-up); any PortHub PR.

## Final user decisions
- AI-014: DONE (PR #7, merge `2f3b89e`; all acceptance criteria met).
- AI-016: stays IN REVIEW; PR #5 (`451daff`) recorded as evidence; the two outstanding criteria are preserved; no scope exception.
- Preserve every local-only AI decision; task completion status is separate from the status of AI-owned decisions.

## Tests (document and schema checks)
1. Normalized diff against PortHub. 2. Mirrored files identical; envelope `$ref`s resolve; sample payloads validate. 3. DEC-01..57 and CT-01..26 present, Summary rows match entries. 4. No Closed item with a blank Decision. 5. Grep for stale text. 6. Link targets exist. 7. Local-only blocks intact. 8. `ruff`, `mypy`, `pytest` for regressions only.

## Risks
Local-only text lost in a merge (mitigated by item-level edits and check 7); PortHub moves during the task (re-fetch before the final report); Redis version stays provisional; unreviewed Backend-written C-01 to C-04 additions (flagged in the record).

## Acceptance criteria
No shared item contradicts PortHub (checks 1, 3, 4); no local-only decision lost (7); schemas resolve and match (2); no dependent relies on an old status (5); records consistent (3, 6).
