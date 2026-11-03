# DEC-20 · Tug requirement formula
| Field | Value |
|---|---|
| Status | IN REVIEW (DEC-20 itself is Closed; this task becomes `DONE` when this branch is reviewed and merged) |
| Owner | AI Team |
| Branch | `feature/DEC-20-tug-requirement-formula` (from `develop` at `25405fc`) |
| Plan | documented exception: decision task, no separate plan file. The user's own numbered instructions of 2026-11-03, given in the conversation, are the plan · approval: the user wrote them and directed the work, 2026-11-03 |
| Updated | 2026-11-03 |

Decision task. No code, config or tests changed.

## Approval
Closed on 2026-11-03, with interim tables. As stated by the user in the conversation on 2026-11-03: "I am the Leads Council and I approve DEC-20 now. Agreed with: Mostafa Mohamed Rashwan, Leads Council. Date: 2026-11-03". AI lead approval from Menna Gamal (AI lead, @MennaGamal-87), 2026-11-03, is carried over from the PortHub draft.

This replaces the earlier position, recorded in AI-054, that DEC-20 stays Open pending the Leads Council.

## Summary of the change
- **`docs/ref/ATLANTECH_Decisions.md`:** the DEC-20 entry, its summary row and register row TR-23.
- **Base:** the PortHub draft on `feature/AI-054-dec-20-tug-formula` (`e638134`), which matches the merged code. The draft's `Proposed change` row isn't carried over.
- **Added to the draft:** the `Agreed with` and `Implementation` rows, and the fitting SWL and `tug_rules.json` open items.
- **Changed from the draft:** the title, in the heading and summary row; "Updated recommendation" becomes "Decision detail", and the table is labelled interim; the open items are reordered, and the draught item is reworded; the worked example states GT 40,000, the value in its test.
- **Corrected to match `part2/tugs.py`:** a `pilot_override` also applies below `T_COMPULSORY`; `N_cap` follows an overridden `N_min`; eligibility uses the band from step 4; displacement and Cb apply only to tankers and bulk carriers; `pilot_request_unknown` is raised only below `T_COMPULSORY`.
- **`rules_unvalidated`:** stays until the rules are validated and the file is `APPROVED`. Closing DEC-20 doesn't validate them.
- **`docs/tasks/status/AI-054.md` and `docs/tasks/WORK_STATUS.md`:** DEC-20's new status, and this task's row.

## Prerequisites and dependencies
- **AI-005:** stays open, because DEC-21, DEC-22 and DEC-28 are Open. The backlog isn't edited.
- **AI-054:** `DONE`. PR #17 merged by the Leads Council (Mostafa Mohamed Rashwan) on 2026-11-03; merge accepted as approval, no separate review.
- **AI-009:** unchanged. Its tug content still cites DEC-20 as Open, in `docs/drafts/ai-payloads/seed-spec.md`, and it stays open on other items.

## Contract / decision items
- **DEC-20:** Closed, interim tables.
- **CT-13:** its `TUG_COUNT` code cites DEC-20 by ID. No change.
- **DEC-28, DEC-32:** Open, not changed.

## References inspected
- **Read in full:** the DEC-19 and DEC-20 entries on `develop`; DEC-20 on PortHub `main` and on `feature/AI-054-dec-20-tug-formula`; `part2/tug_rules.json`; `docs/tasks/status/AI-054.md`; `docs/tasks/WORK_STATUS.md`; backlog §5 AI-005.
- **Read sections:** `part2/tugs.py` (from line 150); the AI-054 plan (lines 10 to 45); the `tugboats` table in PortHub's `contracts/db/schema.sql`.
- **Missing:** `ATLANTECH_FRD_v3`, `ATLANTECH_AI_IMPLEMENTATION_PLAN.md`.

## Validation results (actual)
**Code tests: NOT APPLICABLE.** The diff touches only documents and records, and no code behaviour changes. `pytest` couldn't be run here either: `uv` isn't installed in this shell, and an Application Control policy blocks `.venv\Scripts\python.exe`. The worked example's test, `test_the_worked_example`, last passed in AI-054's recorded run.

**Document checks, run on 2026-11-03:**
- **Worked example:** recomputed independently with `awk`: Δ = 76,752.00 t, BP_mass = 86.0512 t, so `BP_req` = 87. The 50 t floor doesn't apply.
- **Values:** the entry's table and constants read against `part2/tug_rules.json` and `part2/tugs.py`.
- **`git diff --check`:** exit 0 on the tracked files. It doesn't cover this untracked file, which a separate search found free of trailing whitespace.
- **Secret scan:** no match in the added lines.

## Review findings
Independent read-only reviewer on this diff: 0 Critical, 2 Important, 7 Minor. All are resolved except one Minor, left as found: `docs/tasks/status/AI-054.md` still says AI-011's PR isn't merged, in a line outside this change.
- **Resolved, Important:** the Plan row claimed a future approval; the `tug_rules.json` follow-up had no validation precondition.
- **Resolved, Minor:** the accuracy corrections listed above, the worked example's GT, this record's change list and wording, and the `seed-spec.md` follow-up.

## Remote PR review
Has not occurred: no PR exists for this branch yet. Only the local review in this session has been done.

## Open questions / follow-ups
- **DEC-20 open items:** listed in the entry, including the fitting SWL check and changing `part2/tug_rules.json` from `PROPOSED`.
- **`part2/README.md`:** still says DEC-20 is Open. Left for the `tug_rules.json` code task, as this task changes no code.
- **`docs/drafts/ai-payloads/seed-spec.md`:** its tug content row still says DEC-20 is Open and blocked. AI-009's owner updates it; it isn't changed here.
- **PortHub:** the same DEC-20 change goes in a separate PR, after this branch is pushed.
- **Backend review:** the PortHub draft asked the Leads Council, including the Backend Team, to review it. No separate Backend review is recorded.
