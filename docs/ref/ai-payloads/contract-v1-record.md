# AI contract v1 · Decision record (P1-A5)

| | |
| --- | --- |
| Date | 2026-10-30 |
| Written by | Backend Team, without a joint session |
| Reviewed | Approved by MennaGamal-87 (AI Team) on PortHub #23, 2026-10-31 |

P1-A5 asks for a joint session that settles the integration decisions and approves contract v1. The Backend Team reviewed where each one stands and closed what remained, and the AI Team reviews the result on GitHub.

## Integration decisions

| ID | Question | Where it stands |
| --- | --- | --- |
| D-01 | How Laravel learns a job finished | Closed: DEC-01 |
| D-02 | Who writes transitions, history, audit and run rows | Closed: DEC-02 |
| D-03 | Where override, yard adjustment, BAPLIE correction and window re-check run | Closed: DEC-03 |
| D-04 | Job envelope, versioning, retries | Closed: DEC-04 |
| D-05 | Contract v1: payloads C-01 to C-06 and JSON Schemas | Closed by this record |
| D-06 | What feeds the SSE endpoint | Closed by this PR: DEC-05 |
| D-07 | Which requests a solve may change | Closed: DEC-06 |
| D-08 | How `NO_FEASIBLE_WINDOW` is stored | Open: DEC-07, due Sprint 5 |
| D-09 | Read source and database privileges | Closed: DEC-08 |
| D-10 | Where deviation thresholds live | Open: DEC-09, due Sprint 6 |
| D-11 | Do weather pulls and Part 3 run in `READ_ONLY` | Deferred: DEC-54, future work |

D-08 and D-10 are not needed before their sprints, so they stay open.

## Contract v1 files

| Contract | File | Origin |
| --- | --- | --- |
| CT-08 envelope | `envelope.schema.json` | Copied unchanged from `project-ai` `docs/ref/ai-payloads/` |
| CT-09 C-01 | `c01-part1-run.schema.json` | **New, written by the Backend Team** from the approved CT-09 text |
| CT-10 C-02 | `c02-part2-solve.schema.json` | **New, written by the Backend Team** from the approved CT-10 text |
| CT-11 C-03 | `c03-yard.schema.json` | **New, written by the Backend Team** from the approved CT-11 text |
| CT-12 C-04 | `c04-baplie.schema.json` | **New, written by the Backend Team** from the approved CT-12 text |
| CT-13 C-05 | `c05-validation.schema.json` | Existing |
| CT-14 C-06 | `c06-completion.schema.json` | Existing |

CT-08 moves from Proposed to Approved on the Backend Team's sign-off, as its status line provides.

## For the AI Team to check

1. C-01 to C-04 are yours under CT-08. Please confirm they match what your workers expect, and copy them to `project-ai` `docs/ref/ai-payloads/`, where `envelope.schema.json` already refers to them.
2. In C-01, `manual_forecast_run_id` is required with `MANUAL_DATA` and forbidden with other reasons. CT-09 states the first part; the second is our reading.
3. In C-02, `berthing_request_ids` has unique items. This is our addition, in line with CT-10's "one entry per request".
