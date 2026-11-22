# Integration requests to other teams

Setup record (not in the backlog), written for the owning teams. Each item says what the AI track needs, from whom, and which AI task waits for it. IDs `INT-xx` are local labels for these requests only; they are not `DEC-` or `CT-` IDs. The AI's interfaces are Redis queues and database tables (no HTTP API), so every request is a contract, schema or data item. Updated 2026-11-21.

## Backend Team

| ID | Priority | Request | Exact need | Blocks | Acceptance |
|---|---|---|---|---|---|
| INT-B1 | High | Approve the CT-10 Proposed change (AI-051) | Add `PILOT_RANK_LIMIT` and `TUG_COUNT` to the STRUCTURAL `binding_constraints` list of `solver_runs.result_detail` / C-06 (minor version: v1.3, or folded into the pending v1.2). No schema change: the payload schemas don't enumerate codes. Text: CT-10 `Proposed change` row in PortHub `contracts/ATLANTECH_Contracts.md` (since `38dd6b5`) | AI-058 merge | CT-10 Status row records the approval (who, when); the row is folded in |
| INT-B2 | High | Approve CT-11 v1.2, including the names the AI Team now proposes to confirm | `no_rehandle_count`; reason codes `NO_SLOT_OF_LENGTH`, `STACK_HEIGHT_REACHED`; `departure_source` values `ONWARD_PLAN` · `ONWARD_REQUEST_ETA` · `ONWARD_BAPLIE_ETA` · `IMPORT_DWELL` · `UNKNOWN` (AI-065 task decision, item 3) | AI-066 | CT-11 Status `Approved v1.2` with approvers |
| INT-B3 | High | DEC-29 data gaps for the yard solver | G-01 onward vessel and ETA per container (nullable `container_manifest_entries` columns, CT-12 optional fields); G-02 `yard_slot_events` and tablet recording; G-04 two-slot representation for 40/45 ft (`yard_slots.container_part`); G-06 slot check at accept/export (`YARD_SLOT_CONFLICT`, 409) | AI-066 production use (AI-065 mapping I6, I11, H6) | Migrations in PortHub `contracts/db/schema.sql`; CT-12/CT-17 updated |
| INT-B4 | Medium | Separate pilot and tug job intervals (DEC-32 follow-up G-14) | Nullable `pilot_start`/`pilot_end` on `recommendation_options` (present) and `planned_start`/`planned_end` on `recommendation_option_tugs`, copied into `plan_components` by P4-L1 | Removes the over-reservation AI-055 has to apply today | AI-050 loader reads them; AI-055/B2 switch from the option window |
| INT-B5 | Medium | Review the AI-060 `message_key` list (CT-13 reviewer) | Keys in the AI-060 task decision item (4) | AI-060 final, Frontend translations | CT-13 records the keys as approved |
| INT-B6 | Low | Retraining grants (DEC-08, CT-17), when retraining is built | `INSERT`/`UPDATE` on `ml_model_versions` and `retraining_runs` for `w_part3` | AI-070 registration, AI-104 | Grant matrix in `table-ownership.md` updated |
| INT-B7 | Low | Optional: a hash column on `ml_model_versions` | e.g. `artifact_sha256 char(64)`; until then AI-070 uses a `.sha256` sidecar | — | Backend decides (schema owner) |
| INT-B8 | Low | Optional: a `code` column on `baplie_parse_issues` | Today the issue code reaches staff only through `staged_payload` (AI-031) | — | Backend decides |

## QA Team

| ID | Priority | Request | Exact need | Blocks | Acceptance |
|---|---|---|---|---|---|
| INT-Q1 | Medium | Stowage upper bounds, or a corrected corpus case 12 | The case expects `LOC+147+9999999` (bay 999, row 99, tier 99) to be out of bounds and its message says "99/99/99"; no document gives the upper bounds of bay, row and tier | AI-031 case 12 (skipped) | Bounds written in CT-24 or CT-12, or the case changed |
| INT-Q2 | Medium | CT-24 Proposed change for new issue codes | AI-031's six codes (`MALFORMED_CONTAINER_NUMBER`, `MALFORMED_TEMPERATURE`, `MALFORMED_OOG`, `MISSING_PORT_OF_DISCHARGE`, `VESSEL_NAME_MISMATCH`, `SIZE_TYPE_CHANGED`) and AI-023's three (`docs/followups/contracts-followup.md` item 3) | Corpus coverage | CT-24 lists the codes |
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
| INT-B10 | Backend Team | CT-12 step 5 test (R6) | Backend test: `PARSED` C-06 → new file `ACTIVE` and the previous ACTIVE file `REPLACED` in one transaction; other outcomes change nothing | Closing AI-032 criterion 3 | Backend test green |
| INT-Q4 | QA Team / domain reviewer | Rationale templates (AI-009 criterion 3) | Domain-reviewed `rationale_templates` rows (code, version, text with placeholders), with the rationale language decided | AI-057 rendering tests per template | Rows in the seed spec; AI-057 renders each one |

**Still open from earlier rounds:**

- INT-B1: CT-10 Proposed change (AI-058 merge gate).
- INT-B2: CT-11 v1.2.
- INT-B3: DEC-29 G-01, G-02, G-04, G-06 (AI-066).
- INT-B4: separate pilot and tug job intervals.
- INT-B5: CT-13 message keys.
- INT-B6: DEC-08 retraining grants (AI-070 registration).
- INT-Q1: stowage upper bounds.
- INT-Q2: CT-24 codes.
- INT-L1, INT-L2: yard dwell and time-limit values.

DEC-30 TR-01 / TR-02 are AI Team values (R8), not an external request.
