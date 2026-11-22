# Decisions waiting for the user

Setup record (not in the backlog), written for the user as AI Team owner. Each item is a recommendation, not a decision: the canonical entries in `docs/ref/ATLANTECH_Decisions.md` stay `Open` or `Proposed` until approved there. IDs `R-x` are local labels only. Updated 2026-11-21.

| ID | Question | Recommendation | Status |
|---|---|---|---|
| R1 | Accept the seven AI task decisions written this session? | Yes, as written. The one with business weight is AI-055 item (1): `RESOURCE_COST` = tugs assigned ÷ `N_cap` | RECOMMENDED · REQUIRES OWNER CONFIRMATION |
| R2 | DEC-31: where does Part 3 scheduling run? | Option 1, a scheduler inside the Part 3 worker | RECOMMENDED |
| R3 | How does AI-045 (A5 UKC with squat) get built before AI-043 exists? | Build it on labelled synthetic series, as DEC-34 did for A4 | RECOMMENDED · needs a new decision text |
| R4 | Close DEC-07 (and DEC-24) so AI-007 can close? | DEC-07: Option 1, the recommendation the entry already marks "agreed" | RECOMMENDED |
| R5 | DEC-22: financial impact in ranking | Keep it Open; AI-055 ranks by DEC-23 only | No action |
| R6 | AI-032 criterion 3 ("previous ACTIVE file becomes REPLACED in the same transaction") conflicts with CT-12 step 5 and DEC-08, which give that write to the Backend | Follow the contract: the worker never writes `baplie_files.status`; close criterion 3 as the Backend's, or reword it in the backlog | RECOMMENDED |
| R7 | Accept the second-round task decisions (AI-056, AI-074, AI-032)? | Yes, as written | RECOMMENDED · REQUIRES OWNER CONFIRMATION |

## R1 · The AI task decisions of 2026-11-21

- **Entries:** AI-065, AI-055, AI-031, AI-060, AI-025, AI-070 and AI-092 in "AI task decisions", each `Proposed`, each on its own branch.
- **Recommendation:** accept them all. Every item is reversible and stays inside what Closed decisions allow.
- **Watch:** AI-055 item (1). The alternative, berth occupancy time, would be constant for every berth today, because B3's Phase 1 service time depends on the terminal (AI-052).
- **Impact:** AI-056, AI-057, AI-058, AI-066, AI-067 and AI-074 build on these rulings.
- **Risk:** low. A change later is a code change behind one function per item.
- **Owner:** AI Team. After you approve, each entry gets its Status, Decision and approver filled in on `develop`.

## R2 · DEC-31, Part 3 scheduling host (unblocks AI-073)

- **Options:** (1) a scheduler inside the Part 3 worker; (2) the Laravel scheduler enqueues, which needs a new queue.
- **Recommendation:** Option 1, the one the entry already recommends.
- **Why:**
  - There is no `queue:part3`, so Option 1 changes no contract.
  - AI-073 asks for "cadence from `port_setting`" and "overlapping runs prevented". A worker can read the cadence and hold a lock itself.
- **Alternative:** Option 2 would need a CT-08 queue addition and Backend work.
- **Risk:** the Part 3 worker must run on one host only, or take a DB lock. AI-073 would test that.
- **Owner:** AI Team.

## R3 · AI-045 on synthetic data (unblocks closing AI-055)

- **Context:** AI-045 depends on AI-043, which needs real provider and tide data (AI-020, AI-021, AI-042). The user ruled that AI-055 is not `DONE` before AI-045 exists.
- **Recommendation:** build and test A5 (UKC with Barrass squat) on labelled synthetic sea-level and depth series behind the interface the real pipeline will use. Keep DEC-34's gates:
  - real-data re-test before AI-048 is `DONE`;
  - hard limits never loosened;
  - synthetic data always labelled.
- **Alternative:** wait for real data. That keeps AI-055, and every Part 2 demo, open for several sprints.
- **Risk:** squat coefficients are domain values (flag X). They need a source, never a guess. If none exists, AI-045 stays blocked even on synthetic data.
- **How to record it:** a new decision needs an official ID from the team leads. Until then, write it as a `Proposed` AI-045 task decision.
- **Owner:** AI Team, with the domain experts for the coefficients.

## R4 · DEC-07 and DEC-24 (unblock AI-007, then AI-047 and AI-048)

- **DEC-07:** close it with Option 1, "a proposal with no windows, linked from the run". The entry already marks that option "(agreed)"; only its Status was never set. Backend coordination: a schema note change only.
- **DEC-24:** Part 1 horizon, time step, minimum window and slot. Its values come from the thresholds register (DEC-30). I have no source for them, so I have no value to recommend.
- **Owner:** AI Team, with the Backend Team for the schema note.

## R6 · AI-032 criterion 3 versus CT-12 (resolution text)

- **Contradictory text:** backlog §5 AI-032, criterion "Previous ACTIVE file becomes REPLACED in the same transaction", and expected output "earlier ACTIVE → REPLACED … ACTIVE/PARSED".
- **Authoritative contract:**
  - CT-12 v1.1 run flow step 5: "Backend · On `PARSED`, in one transaction: new file → `ACTIVE`, previous ACTIVE → `REPLACED`".
  - CT-12: "The worker never writes `baplie_files.status` (DEC-08)".
  - The DEC-08 / CT-15 grants give `w_edi` UPDATE on `parse_status` and `staged_payload` only.
- **Recommendation:** treat criterion 3 as the Backend's deliverable. AI-032 is done when its other two criteria are met; reword the backlog line at its next revision (backlog owner: AI Team).
- **Backend deliverable:** already in CT-12 step 5, so nothing new is needed. One transaction on a `PARSED` C-06: the new file `STAGED` → `ACTIVE`, and the earlier ACTIVE file of the same request → `REPLACED` (respecting `active_request_key`). On any other outcome, nothing changes. Acceptance: a Backend test of that transition (INT-B10).
- **AI worker boundary:**
  - The worker writes `parse_status`, `staged_payload`, issues, containers, manifest entries and `vessels.call_sign` (only when NULL).
  - The worker never writes `baplie_files.status` or creates vessels.
  - Tested: `tests/integration/test_edi_job.py` asserts the file stays `STAGED`.
- **Owner of the decision:** AI Team; CT-12 is unchanged. Status: RECOMMENDED.

## R7 · Round-2 task decisions (all `Proposed`; owner AI Team; none approved)

| Entry | Current text, in short (full text in `ATLANTECH_Decisions.md`) | Why | Components | Contract impact | Tests | Risk | Recommended |
|---|---|---|---|---|---|---|---|
| AI-056 | FIFO only on B5 `TIMEOUT` or `SolverInvariantError`. A finished solve placing nothing → `NO_FEASIBLE_PLAN` / `INFEASIBLE`. FIFO by `requested_eta`, earliest fit, strongest tugs first, NULL score, B2 `check_plan`. Unplaced reasons: `BERTH_OCCUPIED` / `PILOT_UNAVAILABLE` / `TUG_UNAVAILABLE`, or all three ("never together"). `NOT_SOLVED` not built | Architecture §8.9: FIFO never on infeasibility | `part2/outcomes.py` | None (CT-10 v1.1 shapes) | 19 unit | Reasons are diagnostic, not minimal proofs | Accept |
| AI-074 | `part3/trusted.py` is the only Part 3 read of `actual_status_updates`, always `clock_skew_suspect = 0`, no override; a test fails on any other Part 3 reference | I-13, UML rule 8 | `part3/trusted.py`, `pyproject.toml` scopes | None | 8 unit + 1 MySQL | Future Part 3 code must use it (the test enforces it) | Accept |
| AI-032 | Worker never writes file status or creates vessels. Plan / handler split. `message` = `CODE: text`. CT-12 `staged_payload` exactly. `result_detail` fields. Precondition categories | CT-12 steps 3 and 5, DEC-08 | `edi/commit.py`, `edi/job.py` | None (follows CT-12) | 35 unit + 2 MySQL (fault injection) | OD-02 (audit entry) open | Accept, with R6 |
| AI-072 | PSI on reference deciles, empty-bin share 1e-4, 5 decimals. MAE over the caller's window. Drifted = `metric_value > threshold`. Thresholds only from CT-18 keys | Backlog: "threshold from the register" | `part3/drift.py` | None | 15 unit + 1 MySQL | Deciles and 1e-4 are engineering choices | Accept; values per R8 |

## R8 · DEC-30 TR-01 / TR-02 drift thresholds (owner: AI Team)

- **Context:** the register lists both as DEFERRED, with the AI Team as owner and AI-072 as the task that needs them.
- **Recommendation:** none. No source in this repository gives values, so I propose none.
- **Effect:** AI-072 code is complete and tested, but it is not production-ready until the values are seeded through CT-18.

## Consolidated review of open recommendations (2026-11-21)

| ID | State | Blocks |
|---|---|---|
| R1 | Open (round-1 task decisions; AI-055 `RESOURCE_COST` = tugs ÷ `N_cap`) | Nothing in code; confirmation only |
| R2 | Open (DEC-31; Option 1 recommended) | AI-073 |
| R3 | Open (AI-045 on synthetic data) | AI-045 → closing AI-055 |
| R4 | Open (DEC-07 Option 1) | AI-007 → AI-047, AI-048 |
| R6 | Open | Closing AI-032 cleanly |
| R7 | Open | Confirmation only |
| R8 | Open | AI-072 production use |

## R9 · AI-071 C1 metric definitions (owner: AI Team; added 2026-11-22)

- **Context:**
  - AI-071 must write `evaluation_metric` rows for `MAE`, `OVERRIDE_RATE`, `WAIT_TIME` and `WINDOW_ACCURACY`. Its acceptance criterion is "hand-computed metric expectations reproduced", which needs a written formula for each metric.
  - The sources name the metrics (Architecture §9.1 C1, UML 3.x "MAE, override rate, waiting time, window accuracy") and the schema scope rule `chk_em_scope` (MAE needs a model version; `OVERRIDE_RATE` and `WAIT_TIME` must have none).
  - No source gives a numerator, denominator, period or row selection.
- **Open items:**
  - **`OVERRIDE_RATE`:** what counts as an override (`MODIFIED_BY_STAFF` options? any staff change?) over which population (recommendations, options, or accepted plans) per period.
  - **`WAIT_TIME`:** which interval (requested ETA to actual berthing start, from trusted `actual_status_updates`?) and which statistic (mean, median).
  - **`WINDOW_ACCURACY`:** DEC-30 TR-11, DEFERRED (OD-16).
  - **`MAE`:** needs a model version to attach to (OD-17); none exists yet.
- **Recommendation:** none. These are business definitions, and I don't invent them. When the AI Team writes them (as the AI-071 task decision, or in DEC-30 for TR-11), AI-071 can be built on AI-074's trusted reads in about the size of AI-072.
- **Blocks:** AI-071.

## R10 · AI-033 status (added 2026-11-22)

- **Finding:** DEC-17 (Closed; "Affects" lists AI-033) removed NFR-PERF-2 from the MVP (Leads Council, 2026-10-27). DEC-30 TR-08 is "out of MVP scope", and CT-12 has no size classes.
- **Action taken:** AI-033 recorded as `DEFERRED (DEC-17)`. This records an existing closed decision; it is not a new one. Nothing was built.
- **If you disagree:** a Leads ruling that brings NFR-PERF-2 back, with size definitions, reopens it.

## Consolidated review of open recommendations (2026-11-22)

| ID | State | Blocks |
|---|---|---|
| R1 | Open (round-1 task decisions; AI-055 `RESOURCE_COST` = tugs ÷ `N_cap`) | Nothing in code; confirmation only |
| R2 | Open (DEC-31; Option 1 recommended) | AI-073 |
| R3 | Open (AI-045 on synthetic data) | AI-045 → closing AI-055 |
| R4 | Open (DEC-07 Option 1) | AI-007 → AI-047, AI-048 |
| R6 | Open | Closing AI-032 (criterion 3) |
| R7 | Open (AI-056, AI-074, AI-032, AI-072, plus the AI-065 mapping) | Closing AI-065; confirmation for the rest |
| R8 | Open | AI-072 production use |
| R9 | Open (new) | AI-071 |
| R10 | Recorded (existing DEC-17) | Nothing |

## R11 · AI-057 partial build (owner: AI Team; added 2026-11-22)

- **What's executable now:**
  - CT-18 §6 makes the Backend render the text. The worker writes only `rationale_template_id` plus `rationale_params`, from the fixed CT-18 placeholder list.
  - `recommendation_rationale_factors` takes `OBJECTIVE_TERM` rows (`WAITING_TIME`, `RESOURCE_COST`, already seeded) and `CONSTRAINT` rows.
  - AI options carry both term values (AI-055), so factor rows and parameters can be built and tested for them.
- **What isn't defined:**
  - (a) FIFO-fallback options have no terms and no binding constraints, so "every option has ≥ 1 factor" has no rule for them.
  - (b) Which template code goes with which option: no templates exist (INT-Q4).
  - (c) "Rendering tests per template" need the template texts.
- **Recommendation:**
  - Approve building the slice that is already determined: objective-term factors and CT-18 parameters for AI options, plus the isolation test.
  - Decide (a), for example: no factor row for FIFO options, recorded as a scope exception; or the two terms computed after the fact.
  - Leave (b) and (c) to INT-Q4.
- **Effect:** AI-057 stays open until INT-Q4 arrives. AI-058 still needs AI-057.

## Handoff: every open decision and external request (2026-11-22)

| ID | Question for you | Recommended | Unblocks | Owner |
|---|---|---|---|---|
| R1 | Confirm the round-1 AI task decisions (incl. AI-055 `RESOURCE_COST` = tugs ÷ `N_cap`) | Accept | Confirmation only | AI Team |
| R2 | DEC-31 Part 3 scheduling host | Option 1 (scheduler in the Part 3 worker) | AI-073 | AI Team |
| R3 | Build AI-045 (A5 UKC) on labelled synthetic data, like DEC-34 | Yes, once a squat coefficient source exists | AI-045 → closing AI-055 | AI Team |
| R4 | DEC-07 (and DEC-24) | Option 1 | AI-007 → AI-046 to AI-048 | AI Team, Backend |
| R6 | AI-032 criterion 3 is the Backend's (CT-12 step 5) | Accept | Closing AI-032 | AI Team |
| R7 | Accept the AI-056, AI-074, AI-032, AI-072 and AI-065 entries | Accept | Closing AI-065 | AI Team |
| R8 | DEC-30 TR-01 / TR-02 drift thresholds | No value proposed (no source) | AI-072 in production | AI Team |
| R9 | C1 metric definitions (`OVERRIDE_RATE`, `WAIT_TIME`; TR-11 `WINDOW_ACCURACY`) | No value proposed (business definitions) | AI-071 | AI Team |
| R10 | AI-033 recorded as `DEFERRED (DEC-17)` | Recorded; reopen only by a Leads ruling | Nothing | Leads Council |
| R11 | AI-057 partial slice and the FIFO factor rule | Approve the slice; decide the FIFO rule | AI-057 start | AI Team |

| Request | Team | Deliverable | Unblocks |
|---|---|---|---|
| INT-Q4 | QA / domain reviewer | Reviewed `rationale_templates` rows and the rationale language | AI-057 → AI-058 → AI-059, AI-066 |
| INT-B1 | Backend | Approve the CT-10 Proposed change | AI-058 merge |
| INT-B10 | Backend | Test of CT-12 step 5 | Closing AI-032 |
| INT-B6 | Backend | DEC-08 grants for `ml_model_versions` | Closing AI-070 |
| INT-B3 | Backend | DEC-29 G-01, G-02, G-04, G-06 | AI-066 |
| INT-B9 | Backend | `pilot_requested` and the tug override columns | Accuracy of B2 tug counts |
| INT-Q1 / INT-Q2 | QA | Stowage bounds; CT-24 codes | AI-031 case 12 |
| INT-L1 / INT-L2 | Leads, Terminal operations | Yard dwell and time-limit values | AI-066 |
| Data (flag D) | Leads Council, domain experts | Providers, tidal constants, master data, history | AI-020 to AI-024, AI-042 → Part 1 chain |
| INT-B4 | Backend | Delivered in the schema (PortHub `d55a263`); P4-L1 copying into `plan_components` remains | Already done on the AI side (R5.3) |

## Five-task batch review (2026-11-22)

No new decision owned by the user, the Backend, QA or the Leads Council came up. The one new rule is AI-owned and recorded as item (9) of the AI-031 task decision (still Proposed, owner AI Team): a value above the `int` columns' maximum is an ERROR, so the file is quarantined. It is the column's storage limit, not an operational bound.

| ID | State after the batch | Recommendation | Unblocks |
|---|---|---|---|
| R1 | Open. AI-055 item (1) `RESOURCE_COST` = tugs assigned ÷ `N_cap` re-read: it uses only DEC-20's own `N_cap` and needs no new data | Accept as written; not self-approved | Confirmation only |
| R3 | Open. Nothing new: no squat-coefficient source, AI-043 not started | Unchanged | AI-045 → closing AI-055 |
| R6 | Open. Re-verified: CT-12 v1.1 step 5 and the Backend's own `table-ownership.md` give the status change to the Backend | Accept: close criterion 3 as the Backend's once INT-B10 passes | Closing AI-032 |

## R12 · Corrected `call_sign` longer than the column (owner: AI Team; added 2026-11-22)

**Status: APPROVED 2026-11-22 by the user ("I approve R12: introduce ERROR `MALFORMED_CALL_SIGN` ..."), recorded as the approved item (10) of the AI-031 task decision. Implemented and merged: PR #61, merge `c116038`, 2026-11-22.** Still pending: the QA Team's CT-24 code listing (INT-Q2), which does not block the AI implementation. Surrounding spaces are not trimmed, by decision. A lone UTF-16 surrogate cannot reach the fill (MySQL rejects it in the JSON column, error 3140; reproduced 2026-11-22). The independent review of `d7cd794` added the not-text case (a JSON number, boolean, list or object is also `MALFORMED_CALL_SIGN`, not dropped).

- **Found by:** the independent review of the AI-031 storable-range fix. The issue is older than that fix.
- **Problem:** `vessels.call_sign` is `varchar(10)`. `edi/rules/staged.py` accepts a corrected `call_sign` of any length, and `edi/commit.py` writes it as a fill-empty value. A longer value would fail the UPDATE (MySQL 1406), so the correction job fails instead of quarantining. Only the correction path is exposed: the file parser gives `call_sign = None`.
- **Options:** (a) a new ERROR code (for example `MALFORMED_CALL_SIGN`), which also needs a CT-24 Proposed change by the QA Team; (b) no fill, plus a WARNING under a new code; (c) no fill and no issue.
- **Recommended:** (a). It matches how every other value the schema cannot hold is handled, and staff see what to fix.
- **Effect:** a small AI-031 follow-up (one rule and its tests) once chosen. Nothing changes until then.
- **Investigated and implemented, 2026-11-22** (AI-owned technical decision under the AI-031 task decision, item (10); owner AI Team; approved by the user 2026-11-22), on `feature/AI-031-call-sign-length`:
  - Reproduced against MySQL 8.4: a corrected 11-character call sign fails the fill with `DataError (1406, "Data too long for column 'call_sign'")`; 10 characters commit.
  - The file path cannot carry a call sign (the parser reads IMO and name from TDT only); tested.
  - No existing code fits; the new ERROR `MALFORMED_CALL_SIGN` follows the `MALFORMED_<FIELD>` pattern. It joins the INT-Q2 request to the QA Team (CT-24 code list). No contract text changes: CT-12's vessel object and fill rule are unchanged.
  - `flag_state` (`char(2)`) is also fillable under CT-12, but nothing produces it today (not in the parser or the CT-12 `staged_payload` vessel object), so it carries no risk now.

## Batch 2 recommendations (2026-11-22)

Everything below is a recommendation. Nothing here is approved or implemented as a decision; the canonical entries stay as they are until their owners approve.

| ID | Question | Recommended | Owner | Blocks |
|---|---|---|---|---|
| R11 (a) | Which factors explain a FIFO option? | No factor rows; scope exception on AI-057 criterion 1 for FIFO options | AI Team | AI-057 criterion 1 |
| R9 (proposals) | Definitions of `OVERRIDE_RATE`, `WAIT_TIME`, `WINDOW_ACCURACY`, and the MAE pairs | The definitions below, for review | AI Team (TR-11 in DEC-30) | AI-071 |
| R13 | How does a re-solve of a pending request get written, given `uq_rec_active`? | INT-B11 option (a): `w_part2` sets the previous current version to `REPLACED` in its own transaction | Backend Team (DEC-02, CT-10, CT-15), Leads Council | AI-058, AI-059 |

### R11 (a) · FIFO factors (updates R11)

- **Question:** AI-057 criterion "Every option has ≥ 1 factor". A FIFO option (AI-056: plan by arrival order after a solver timeout or defect) has no objective terms and no binding constraint.
- **Recommended:** **Option 1: no factor row for FIFO options, recorded as a scope exception to criterion 1** ("every option" read as every AI option). FIFO options are still explained, by their template (INT-Q4: a FIFO template naming the fallback) and `recommendations.source = FIFO`.
- **Why:**
  - The table means "Constraints/objective terms that actually drove the solve (FR-1.4.10)" (`schema.sql` comment). Nothing drove a FIFO plan except arrival order.
  - Computing `WAITING_TIME` and `RESOURCE_COST` after the fact (Option 2) would put values in that table that no solve used, and staff would read them as reasons.
  - The code already keeps FIFO apart (`fifo_factors`), so Option 1 changes nothing and Option 2 is one function.
- **Alternatives:** (2) the two term values computed after the fact; (3) a new factor type for arrival order, which needs a schema change (Backend Team, CT-17).
- **Risks:** a staff user sees a FIFO option with no factor list; the FIFO template must say why.
- **Affected:** AI-057 criterion 1; CT-18 §6 unchanged; no contract change.
- **Impact if approved:** record the scope exception in the AI-057 task decision; no code change.

### R9 · proposed C1 definitions (updates R9; not decided)

These are technical proposals, so the AI Team has something concrete to approve, change or reject. None is used in code: `part3/evaluation.py` computes only MAE.

**`OVERRIDE_RATE`** (system-level, no model version, `dataset_type = PRODUCTION`)
- **Proposed formula:** for a period [start, end): among `operational_plans` confirmed in the period (`confirmed_at`) whose recommendation has `source = AI`, the share whose berthing request had at least one `recommendation_overrides` row on any option of any of its recommendation versions with `overridden_at ≤ confirmed_at`. Value in [0, 1], 5 decimals. No confirmed AI plan in the period → no row.
- **Source fields:** `operational_plans.confirmed_at`, `recommendation_id`, `berthing_request_id`; `recommendations.source`; `recommendation_overrides.recommendation_option_id`, `overridden_at`; `recommendation_options.recommendation_id`.
- **Business meaning:** how often staff had to change what the engine proposed before acting on it.
- **Why per request:** an override creates a `MODIFIED_BY_STAFF` version (ClassDiagramContext), so the override row and the confirmed option may sit on different versions; counting per request avoids that question.
- **Limitations:** rejections and "Regenerate" are not counted as overrides; FIFO plans are left out because they don't measure the engine (a business choice to confirm); one number for all component types (the schema has no component column).
- **Alternatives:** per option instead of per plan; count regenerations; include FIFO.

**`WAIT_TIME`** (system-level, `PRODUCTION`)
- **Proposed formula:** the mean, in minutes and to 5 decimals, of max(0, actual berthing start − `requested_eta`) over the vessels whose BERTH component's first trusted "berthing started" event falls in the period. Trusted means read through `part3/trusted.py` (`clock_skew_suspect = 0`). No such vessel → no row.
- **Missing input (owner Backend Team):** which `actual_status_updates.status` code of a BERTH component means "berthing started" (the `status_types` seed is the Backend's).
- **Business meaning:** the delay between when a vessel asked to arrive and when it got its berth; Master_Context's "avoidable idle time".
- **Limitations:** `requested_eta` is the planned arrival, not an observed one (the schema records no actual arrival for every vessel); early berthing counts as 0.
- **Alternatives:** from the confirmed window's start instead of `requested_eta`; median instead of mean; from a PILOT "boarded" event if it is recorded for every vessel.

**`WINDOW_ACCURACY`** (DEC-30 TR-11, DEFERRED, OD-16)
- **Proposed formula, for TR-11:** among confirmed entry windows whose vessel's first trusted entry event falls in the period, the share where that event lies inside [window start, window end). No model version while Part 1 is rules and physics.
- **Missing input:** the status code that marks entry (Backend Team), and the TR-11 decision itself (AI Team, DEC-30).
- **Limitations:** a vessel that never enters is not counted.

**MAE pairs** (formula defined; inputs not)
- **Proposed:** for M2, actual service time = last trusted "departed" − first trusted "berthing started" of the BERTH component, in hours, against the confirmed option's `service_time_p50_hours`; the model version from `solver_run_model_versions` of the run that produced the option. Only options with `service_time_method = ML` count.
- **Missing input:** the two status codes (Backend Team) and a model version (OD-17, INT-B6).

### R13 · Writing a re-solve of a pending request (INT-B11)

- **Question:** the worker must insert a new `PENDING_REVIEW` INITIAL recommendation for every solved request (CT-10). When the request already has a current INITIAL version (`PENDING_REVIEW` or `MODIFIED_BY_STAFF`), `uq_rec_active` refuses the insert (reproduced: MySQL 8.4, error 1062), because DEC-02 and CT-10 let only the Backend set `REPLACED`, after C-06.
- **Recommended:** INT-B11 **option (a)**: in the worker's result transaction, for each solved request, set its current version to `REPLACED` (guarded: that row id, and status `PENDING_REVIEW` or `MODIFIED_BY_STAFF`), then do the inserts. The Backend keeps every other C-06 step (request transition, audit, SSE); its "marks REPLACED" step becomes a no-op it can keep for safety.
- **Why:**
  - It is the backlog's own criterion for AI-058: "Previous version REPLACED only on success".
  - One transaction: a failed, timed-out or infeasible run changes nothing, so the previous version stays current and staff can regenerate later (UML 2.13).
  - It is the smallest change: one column grant and one transition. The CT-08 run guard already rolls back a run that is no longer RUNNING.
- **Alternatives:** (b) the Backend replaces before enqueueing: simple, but a failed re-solve leaves the request with no current version, against the backlog criterion and UML 2.13. (c) a schema change so the new row doesn't count in `active_key` until C-06: keeps DEC-02 intact but adds a status and changes CT-17, CT-15 and the Backend's reads.
- **Risks:** reopens a Closed Backend decision (DEC-02) for one transition; the worker must find the right current version (one per request, guaranteed by `uq_rec_active` itself).
- **Affected contracts:** CT-10 (Solve scope), CT-15 (grants), DEC-02; CT-17 only for (c).
- **Affected criteria:** AI-058 "Previous version REPLACED only on success" and "Run fully traceable"; AI-059 "Failure keeps previous version current".
- **Implementation impact:** AI-058 writes the update first in its transaction; tests with a `PENDING_REVIEW` and a `MODIFIED_BY_STAFF` previous version, and a failure case.
- **Owner:** Backend Team, with the Leads Council since DEC-02 is Closed. The AI Team (you) proposes it; nothing changes in DEC-02 or CT-10 until they approve.

### Open recommendations after batch 2

| ID | State |
|---|---|
| R1, R2, R3, R4, R6, R7, R8 | Unchanged (see the handoff table above) |
| R9 | Open; proposals written above |
| R10 | Recorded (DEC-17) |
| R11 | Slice built (AI-057, `feature/AI-057-rationale-factors`); (a) recommended above; (b) and (c) wait for INT-Q4 |
| R12 | Approved and merged (PR #61) |
| R13 | New, open: needs the Backend Team and the Leads Council |

## Batch 2 resumed (2026-11-22): AI-058 and AI-059

Recommendations only; nothing here is approved.

| ID | Question | Recommended | Owner | Blocks |
|---|---|---|---|---|
| R13 | Regenerate write (INT-B11) | Unchanged: option (a). AI-058 is built so that only its precondition check changes once this is decided | Backend Team, Leads Council | AI-058 regenerate, AI-059 MANUAL and RESOURCE_CHANGE |
| R14 | Confirm the AI-058 and AI-059 task decisions | Accept as written | AI Team | Confirmation only |

### R14 · AI-058 and AI-059 task decisions (both `Proposed`)

| Entry | In short | Why | Risk | Recommended |
|---|---|---|---|---|
| AI-058 | Schema CHECKs mirrored before the write; regenerate refused before any write (INT-B11); `result_detail` kept to CT-10 v1.1, the two Proposed codes written as their approved parents; job intervals NULL (DEC-32 rule 4) | Stays inside DEC-02, CT-10 v1.1 and CT-15 without waiting for INT-B1 | Staff see `PILOT_UNAVAILABLE` where the finer reason is a rank limit (the `detail` text still says so) | Accept |
| AI-059 | Begun = a `STARTED` or `DONE` event; "fixed" = same resource and same interval, so the option's start and end are the started interval and B3 is not used; a started resource no longer usable gives `NO_FEASIBLE_PLAN`; disagreeing intervals fail the run | Architecture §8.13 "STARTED components fixed" with the one-interval option of DEC-32 rule 4; no duration invented | A delay after berthing can't lengthen a started berth stay; that needs a rule the sources don't have (follow-up) | Accept |
