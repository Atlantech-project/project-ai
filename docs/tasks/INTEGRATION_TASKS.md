# Integration requests to other teams

Setup record (not in the backlog), written for the owning teams. Each item says what the AI track needs, from whom, and which AI task waits for it. IDs `INT-xx` are local labels for these requests only; they are not `DEC-` or `CT-` IDs. The AI's interfaces are Redis queues and database tables (no HTTP API), so every request is a contract, schema or data item. Updated 2026-11-21.

## Backend Team

| ID | Priority | Request | Exact need | Blocks | Acceptance |
|---|---|---|---|---|---|
| INT-B1 | High | Approve the CT-10 Proposed change (AI-051) | Add `PILOT_RANK_LIMIT` and `TUG_COUNT` to the STRUCTURAL `binding_constraints` list of `solver_runs.result_detail` / C-06 (minor version: v1.3, or folded into the pending v1.2). No schema change: the payload schemas don't enumerate codes. Text: CT-10 `Proposed change` row in PortHub `contracts/ATLANTECH_Contracts.md` (since `38dd6b5`) | AI-058 merge | CT-10 Status row records the approval (who, when); the row is folded in |
| INT-B2 | High | Approve CT-11 v1.2, including the names the AI Team now proposes to confirm | `no_rehandle_count`; reason codes `NO_SLOT_OF_LENGTH`, `STACK_HEIGHT_REACHED`; `departure_source` values `ONWARD_PLAN` · `ONWARD_REQUEST_ETA` · `ONWARD_BAPLIE_ETA` · `IMPORT_DWELL` · `UNKNOWN` (AI-065 task decision, item 3) | AI-066 | CT-11 Status `Approved v1.2` with approvers |
| INT-B3 | High | DEC-29 data gaps for the yard solver | G-01 onward vessel and ETA per container (nullable `container_manifest_entries` columns, CT-12 optional fields); G-02 `yard_slot_events` and tablet recording; G-04 two-slot representation for 40/45 ft (`yard_slots.container_part`); G-06 slot check at accept/export (`YARD_SLOT_CONFLICT`, 409) | AI-066 production use (AI-065 mapping I6, I11, H6) | Migrations in PortHub `contracts/db/schema.sql`; CT-12/CT-17 updated |
| INT-B4 | Delivered (schema, PortHub `d55a263`) | Separate pilot and tug job intervals (DEC-32 follow-up G-14) | Nullable `pilot_start`/`pilot_end` on `recommendation_options` (present) and `planned_start`/`planned_end` on `recommendation_option_tugs`, copied into `plan_components` by P4-L1 | Removes the over-reservation AI-055 has to apply today | AI-050 loader reads them (PR #56): done for existing holds. New assignments keep the option window until a source gives job durations (none exists; not guessed) |
| INT-B5 | Medium | Review the AI-060 `message_key` list (CT-13 reviewer) | Keys in the AI-060 task decision item (4) | AI-060 final, Frontend translations | CT-13 records the keys as approved |
| INT-B6 | Low | Retraining grants (DEC-08, CT-17), when retraining is built | `INSERT`/`UPDATE` on `ml_model_versions` and `retraining_runs` for `w_part3` | AI-070 registration, AI-104 | Grant matrix in `table-ownership.md` updated |
| INT-B7 | Low | Optional: a hash column on `ml_model_versions` | e.g. `artifact_sha256 char(64)`; until then AI-070 uses a `.sha256` sidecar | — | Backend decides (schema owner) |
| INT-B8 | Low | Optional: a `code` column on `baplie_parse_issues` | Today the issue code reaches staff only through `staged_payload` (AI-031) | — | Backend decides |

## QA Team

| ID | Priority | Request | Exact need | Blocks | Acceptance |
|---|---|---|---|---|---|
| INT-Q1 | Medium | Stowage upper bounds, or a corrected corpus case 12 | The case expects `LOC+147+9999999` (bay 999, row 99, tier 99) to be out of bounds and its message says "99/99/99"; no document gives the upper bounds of bay, row and tier | AI-031 case 12 (skipped; re-checked 2026-11-22: PortHub `main` schema, Contracts and Decisions still give no maxima) | Bounds written in CT-24 or CT-12, or the case changed |
| INT-Q2 | Medium | CT-24 Proposed change for new issue codes | AI-031's seven codes (`MALFORMED_CONTAINER_NUMBER`, `MALFORMED_TEMPERATURE`, `MALFORMED_OOG`, `MISSING_PORT_OF_DISCHARGE`, `VESSEL_NAME_MISMATCH`, `SIZE_TYPE_CHANGED`; `MALFORMED_CALL_SIGN` added 2026-11-22, R12) and AI-023's three (`docs/followups/contracts-followup.md` item 3) | Corpus coverage | CT-24 lists the codes Not an AI implementation blocker: `MALFORMED_CALL_SIGN` is merged (PR #61) and AI-031 is `DONE` |
| INT-Q3 | Medium | Real recorded provider payloads and the real tide (DEC-34 gate) | Recorded forecasts for AI-020 and the tide from AI-042, to re-run the AI-044 table tests | AI-048 `DONE` | Tests pass on real data |

## Frontend Team

| ID | Priority | Request | Exact need | Blocks |
|---|---|---|---|---|
| INT-F1 | Low | Translations for the validation `message_key` values | After INT-B5; keys in the AI-060 task decision | Officer sees localized override warnings |

## Leads Council, Terminal operations and domain experts

| ID | Priority | Request | Exact need | Blocks |
|---|---|---|---|---|
| INT-L1 | High | Default import dwell time value (DEC-29 G-05) | A value for the proposed `port_settings` key `yard_import_dwell_hours` (AI-065 P7); no value is invented | AI-066 rule 2 (b); without it every container is "departure unknown" |
| INT-L2 | Medium | Yard solver time limit value (DEC-29 open item 8, DEC-30) | A value for the proposed key `yard_solver_time_limit_seconds` | AI-066 |
| INT-L3 | Medium | A real BAPLIE with onward-vessel data (DEC-29 G-01) | The Leads Council provides it | INT-B3 G-01 |
| INT-L4 | Low | Damietta Port Authority reference for compulsory pilotage | Source for the AI-051 confirmed rule | AI-051 follow-up |
| INT-L5 | Medium | Damietta yard bay numbering (DEC-29 G-04) | How bays b and b+1 pair for 40/45 ft | AI-066 H6 |

## Additions 2026-11-21 (round 3)

| ID | Owner | Request | Exact deliverable | Blocks | Acceptance / tests |
|---|---|---|---|---|---|
| INT-B9 | Backend Team | DEC-20 missing tug inputs | Nullable `berthing_requests.pilot_requested` (bool) and a tug-count pilot override, if the form collects them (DEC-20 data requirements). Today the shared B2 loader passes `pilot_requested = None` (table applies) | Accuracy of AI-054 / B2 tug counts | Columns in PortHub `schema.sql`; the AI loader then reads them (one-line change plus a unit test) |
| INT-B10 | Backend Team | CT-12 step 5 test (R6) | Backend test: `PARSED` C-06 → new file `ACTIVE` and the previous ACTIVE file `REPLACED` in one transaction; other outcomes change nothing | Closing AI-032 criterion 3 | Backend test green. Re-checked 2026-11-22: Backend `develop` `554b09c` has no step-5 handler or test (P3-H1 to P3-H8 unchecked) |
| INT-Q4 | QA Team / domain reviewer | Rationale templates (AI-009 criterion 3) | Domain-reviewed `rationale_templates` rows (code, version, text with placeholders), with the rationale language decided | AI-057 rendering tests per template | Rows in the seed spec; AI-057 renders each one |

**Still open from earlier rounds:**

- INT-B1: CT-10 Proposed change (AI-058 merge gate).
- INT-B2: CT-11 v1.2.
- INT-B3: DEC-29 G-01, G-02, G-04, G-06 (AI-066).
- INT-B4: delivered in PortHub `schema.sql` `d55a263`; the AI loader reads the columns (branch `feature/AI-050-dec28-dec32-schema-followups`). P4-L1 copying the intervals into `plan_components` is still the Backend's.
- INT-B5: CT-13 message keys.
- INT-B6: DEC-08 retraining grants (AI-070 registration).
- INT-Q1: stowage upper bounds.
- INT-Q2: CT-24 codes.
- INT-L1, INT-L2: yard dwell and time-limit values.

DEC-30 TR-01 / TR-02 are AI Team values (R8), not an external request.

## Additions 2026-11-22 (batch 2: AI-057, AI-058, AI-059, AI-070, AI-071, AI-092)

| ID | Owner | Request | Exact deliverable | Blocks | Acceptance / tests |
|---|---|---|---|---|---|
| INT-B11 | Backend Team (DEC-02 and CT-10 owner; schema owner), Leads Council if DEC-02 is reopened | Regenerating a pending request cannot be written: `uq_rec_active` versus "REPLACED on C-06" | Choose one: **(a)** let `w_part2` set the previous current INITIAL version of each solved request (`PENDING_REVIEW` or `MODIFIED_BY_STAFF`) to `REPLACED` in the same transaction that inserts the new version: column grant UPDATE `recommendations.status`, limited by CT-15 to that transition, guarded by `WHERE id = ? AND status IN (…)`; DEC-02, CT-10 "Solve scope" and CT-15 updated. **(b)** the Backend marks it `REPLACED` before it enqueues the solve (then a failed or infeasible re-solve leaves the request with no current version). **(c)** a schema change so the new row is not counted by `active_key` until the Backend handles C-06 (for example a new status), with CT-17 and CT-15 updates. AI recommendation: (a), see R13 | AI-058 (every MANUAL and RESOURCE_CHANGE re-solve of a pending request); AI-059 (RESOURCE_CHANGE path) | The chosen option written in DEC-02 / CT-10 / CT-15 (and the schema for (c)); a MySQL test that regenerating a request with a `PENDING_REVIEW` and with a `MODIFIED_BY_STAFF` version succeeds, and that a failed run leaves the previous version current |
| INT-Q4 (extended) | QA Team / domain reviewer; AI Team for the selection rule | Rationale templates (AI-009 criterion 3) | Besides the rows (code, version, text) and the language: which template goes with which option (AI rank 1, AI alternatives, FIFO), and whether any template needs `{terminal}`, `{delta_minutes}` or `{constraint}` `{value}` `{limit}` `{unit}` for options, with their definitions (AI-057 fills only `vessel`, `berth`, `etb`, `waiting_minutes`, `tug_count`, `window_start`, `window_end`) | AI-057 criteria 1 (FIFO, with R11 (a)) and 2 | Rows in `seed-spec.json`; `test_every_seeded_template_parses_and_renders` runs for each row |

**Evidence for INT-B11 (2026-11-22):**
- `schema.sql` (pin `d55a263` = PortHub `main`, same SHA-256): `active_key` = `berthing_request_id` while `status IN (PENDING_REVIEW, MODIFIED_BY_STAFF, CONFIRMED)` and `purpose = INITIAL`; `uq_rec_active` UNIQUE.
- DEC-02 (Closed, owner Backend Team, "Affects … AI-058"): the Backend closes old rows (REPLACED); workers insert new rows. CT-10 "Solve scope": "When the Backend receives C-06, it marks REPLACED only the previous PENDING_REVIEW version". CT-15: `recommendations` INSERT only for `w_part2`.
- Reproduced on MySQL 8.4 with the schema's exact generated column: the second INITIAL insert for a request fails with `ERROR 1062 (23000): Duplicate entry '1550' for key 'uq_rec_active'`, and the same over a `MODIFIED_BY_STAFF` version; a `DELAY_REPLAN` insert succeeds (`active_key` NULL).
- The Backend's own `tests/Feature/Database/DatabaseRulesTest.php` (`develop` `554b09c`) asserts "one live INITIAL recommendation per request: uq_rec_active". The Backend has no PART2_SOLVE result handler yet.
- Also affected: CT-10 replaces only `PENDING_REVIEW`, but a `MODIFIED_BY_STAFF` version blocks the insert too.

**Re-checked 2026-11-22 (batch 2):**
- INT-B1: still open. PortHub `main` CT-10 is `Proposed v1.2` with the AI-051 `Proposed change` row; no approval recorded.
- INT-B6: still open. PortHub `table-ownership.md`: "No worker writes them until retraining is built (DEC-08)".
- INT-Q4: no `rationale_templates` rows (`seed-spec.json`: `[]`).

## Update 2026-11-22 (batch 2 resumed: AI-058, AI-059)

| ID | State now | What changed |
|---|---|---|
| INT-B11 | Open; now the only blocker of AI-058 | AI-058 refuses a regenerate before any write (`PRECONDITION_FAILED`, the message names INT-B11), so the previous version stays current; MySQL-tested for `PENDING_REVIEW` and `MODIFIED_BY_STAFF`. When the Backend Team and the Leads Council choose an option, only that check changes (option (a): plus one guarded `REPLACED` update and its grant) |
| INT-B1 | Open, but no longer a merge gate for AI-058 | AI-058 writes `result_detail` with the approved CT-10 v1.1 codes: `PILOT_RANK_LIMIT` → `PILOT_UNAVAILABLE`, `TUG_COUNT` → `TUG_UNAVAILABLE`, B2's text kept in `detail`. Approving the Proposed change lets staff see the finer code; the two mappings are then removed |
| Field status codes (for AI-071 R9 and MAE) | Open (Backend Team) | Unchanged |

**For the Backend Team, from AI-059 (no request, information):** a DELAY_REPLAN proposal's options keep every component that has a `STARTED` or `DONE` event at its resource and interval, so the confirmation step "keep STARTED components" (UML 2.14) finds them unchanged in the proposal. A started resource that is no longer usable gives `NO_FEASIBLE_PLAN` with a reason instead of a proposal.

## Update 2026-11-22 (AI-059 trigger handler)

| ID | State now | What changed |
|---|---|---|
| INT-B11 | Open; the only blocker of AI-058 and AI-059 | The PART2_SOLVE handler (`feature/AI-059-part2-solve-trigger-handler`) runs every trigger end to end; a MANUAL or RESOURCE_CHANGE re-solve of a request with a current version fails with `PRECONDITION_FAILED` naming INT-B11 and leaves the previous version current (MySQL + Redis scenarios) |
| INT-B12 (new, information) | Backend Team | The AI side now sends real PART2_SOLVE C-06 messages (`SOLVED`, `PARTIALLY_SOLVED`, `NO_FEASIBLE_PLAN`, `FIFO_FALLBACK`, `GENERATION_FAILED`). Backend `develop` (`554b09c`, last read) has no C-06 handler for PART2_SOLVE: the request transition, REPLACED (after INT-B11), audit and SSE steps of CT-14 are the Backend's. Acceptance: a Backend test that consumes the C-06 of a SOLVED and of a FIFO_FALLBACK run |
| Forecast feed | AI Team (AI-020, AI-021; data, flag D) | B4 gets no forecast: no feed writes `forecast_runs` yet, and no rule says which run a solve uses. When the feed exists, the AI Team decides the run-selection rule (for example the latest SUCCESS run covering the option) |
