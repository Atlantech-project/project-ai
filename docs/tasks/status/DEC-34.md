# DEC-34 · Building A4 rules on synthetic data
| Field | Value |
|---|---|
| Status | DONE (PR #38 merged into `develop`, merge `64cca37`; PortHub `main` synced in `38dd6b5` on 2026-11-21). DEC-34 itself is Closed |
| Owner | AI Team |
| Branch | `feature/DEC-34-a4-synthetic-data` (from `develop` at `0347d01`) |
| Plan | documented exception: decision task, no separate plan file. The user's numbered instructions of 2026-11-20, given in the conversation, are the plan · approval: the user wrote them and directed the work, 2026-11-20 |
| Updated | 2026-11-21 |

Decision task. No code, config or tests changed.

## Approval
Closed on 2026-11-20 with Option 1. As stated by the user in the conversation on 2026-11-20: "The team has agreed on Option 1." The owner is the AI Team. That statement names no individual approver.

## Summary of the change
- **`docs/ref/ATLANTECH_Decisions.md`:** the DEC-34 summary row (Status `Open` → `Closed`; "Close by" stays `Sprint 3`), the entry's Status row (`Open` → `Closed`) and its Decision row (the user's text, on one line). Source, Owner, Closing task, Affects, القصة, Topic, Options and Recommendation are unchanged. Three lines changed; CRLF line endings kept. Committed as `d596433` on 2026-11-20 at the user's direct request, before the review workflow ran.
- **`docs/tasks/status/DEC-34.md`:** this record.
- **`docs/tasks/WORK_STATUS.md`:** this task's row.

## Verification
**Code tests: NOT APPLICABLE.** No code behaviour changed: the diff touches only `docs/ref/ATLANTECH_Decisions.md` and the task records.

**Document checks (2026-11-20):**
- `git diff --check origin/develop...HEAD`: exit 0, no output.
- `git diff --numstat`: 3 insertions, 3 deletions, one file (lines 54, 1309, 1312).
- Table columns: the summary row has 5 cells like its header; the entry's rows have 2 cells. No `|` inside the backtick spans.
- Line endings: 2163 of 2163 lines CRLF; line count unchanged.
- Cited IDs exist in `docs/tasks/ATLANTECH_AI_TASKS.md` §5: AI-009, AI-014, AI-015, AI-020, AI-040, AI-041, AI-042, AI-043, AI-044, AI-048, AI-051, AI-055. `environment_forecast_points` exists (`docs/ref/db/schema.sql` line 551).
- No conflict with a Closed decision or an approved contract: DEC-25 (Closed 2026-11-05, no uncertainty margin in A4) is consistent with "hard limits are never loosened"; no contract mentions DEC-34 or changes.
- PortHub `main` at `983543f`: the DEC-34 entry was identical to `develop` before this change (Status Open, Decision empty).

## Review findings (resolved / unresolved / deferred)
Local manual review in this session (the Superpowers review skills were not available). Scope checked at line level: the three changed lines are exactly the ones the instructions list. No Critical or Important findings.

Minor, left as follow-ups (outside this task's instructions):
1. **PortHub still shows DEC-34 Open.** The Backend reads PortHub; the same change needs a PortHub PR.
2. **Backlog not updated.** `docs/tasks/ATLANTECH_AI_TASKS.md` still lists AI-043 as a prerequisite of AI-044 (§2 summary, §3.2, §5), and the execution waves (§3.3) and critical path (§3.4) still follow AI-040 → AI-041 → AI-043 → AI-044. The decision changes the prerequisites to AI-009 and AI-014.
3. **Affects row.** It lists AI-044 · AI-051; the decision also bears on AI-048 (the gate), AI-015 (fixtures), AI-020 and AI-042 (real-data re-test) and the QA Team. Left unchanged as instructed.
4. **"Affected teams informed."** The Decision row says so; the announcement was drafted on 2026-11-20 and had not been sent when this record was written.

## Remote PR review
Has not occurred: no PR exists for this branch yet, and `gh` is not installed. Only the local review in this session has been done.

## Contract / decision items
- **DEC-34:** Closed, Option 1 (2026-11-20).
- **DEC-25:** referenced only; not changed. No contract changed.

## Blockers and follow-ups
No blockers. Follow-ups: items 1 to 4 above.
