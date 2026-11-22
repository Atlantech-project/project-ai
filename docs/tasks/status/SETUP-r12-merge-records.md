# SETUP-r12-merge-records · R12 merge verification and the last stale records (setup task, not in the backlog)

| Field | Value |
|---|---|
| Status | DONE (PR #63, merge `6c29250`, 2026-11-22 13:09:51Z; CI green on `6c29250`) [was: IN REVIEW (documents only; DONE when its PR merges)] |
| Owner | AI Team |
| Branch | `feature/SETUP-r12-merge-records` (from `develop` at `bba5945`) |
| Plan | the user's instruction of 2026-11-22: verify PRs #61 and #62, sync `develop` and PortHub, correct remaining stale status records, record the trimming decision and the Unicode result; no new batch |
| Updated | 2026-11-22 |

## Summary of the change
- AI-031: R12 merged (PR #61, `c116038`); INT-Q2 pending and not an AI blocker; no trimming by decision; the lone-surrogate case not reproducible (MySQL rejects it, error 3140). Decision entry, record and tracker row.
- SETUP-five-task-records-pr60 → DONE (PR #62, `bba5945`).
- R12 and INT-Q2 in the trackers; Checkpoint 9; report section 18.

## Verification
Code tests: NOT APPLICABLE (documents only). Evidence: GitHub pulls API (PRs #61, #62), check runs on `c116038` and `bba5945`, the MySQL probe (scratch table, dropped), PortHub `origin/main` `ls-tree`, duplicate checks, `git diff --check`.
