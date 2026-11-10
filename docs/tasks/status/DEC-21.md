# DEC-21 · Phase 1 delay-risk rule
| Field | Value |
|---|---|
| Status | DONE (branch merged into `develop`; closed by Leads rule: merged branch = Closed, 2026-11-10) [was: IN REVIEW (DEC-21 itself is Closed; this task becomes `DONE` when this branch is reviewed and merged)] |
| Owner | AI Team |
| Branch | `feature/DEC-21-delay-risk-rule` (from `develop` at `109fb54`) |
| Plan | documented exception: decision task, no separate plan file. The user's numbered instructions of 2026-11-05, given in the conversation, are the plan · approval: the user wrote them and directed the work, 2026-11-05 |
| Updated | 2026-11-10 |

Decision task. No code, config or tests changed.

## Approval
Closed on 2026-11-05 as an interim rule. As stated by the user in the conversation on 2026-11-05: approved by Mostafa Mohamed Rashwan (Leads Council), 2026-11-05. Decided by the Leads Council; the AI Team (owner) is informed. No AI lead approval is recorded.

## Summary of the change
- **`docs/ref/ATLANTECH_Decisions.md`:** the DEC-21 entry and its summary row. Status Closed; Decision, Agreed with and Implementation rows; a "Decision detail" section with the rule (steps 1 to 7), evidence, limitations, follow-ups and references. Frontend Team added to Affects.
- **Interim storage:** the level goes to the existing `recommendation_options.delay_risk` as a fixed code (LOW 0.100, MEDIUM 0.500, HIGH 0.900). No schema change.
- **`docs/tasks/WORK_STATUS.md`:** this task's row.

## Evidence source
IMF PortWatch (port274) and Open-Meteo history for Damietta, 2019-01-01 to 2026-10-30, fetched by `research/fetch_damietta_history.py`. The data and script are kept outside this repository, and the evidence figures are as supplied by the user; they were not re-derived in this task.

## Contract / decision items
- **DEC-21:** Closed, interim rule.
- **Schema:** `recommendation_options.delay_risk decimal(4,3)`, CHECK `chk_ro_values` 0 to 1 (`docs/ref/db/schema.sql` lines 1149 to 1178), unchanged.
- **DEC-26, DEC-30 (TR-05, TR-10), AI-001:** referenced only; not changed.

## Validation results (actual)
**Code tests: NOT APPLICABLE.** Only documents and records changed.
**Document checks:** see the final report of this task.

## Remote PR review
Has not occurred yet.

## Open questions / follow-ups
- **DEC-21 open items:** listed in the entry (Frontend display of the level, thresholds in a data file for AI-053, recalibration from our own data, licence under DEC-26, recording inputs).
- **PortHub:** the same DEC-21 change goes in a separate PR.
