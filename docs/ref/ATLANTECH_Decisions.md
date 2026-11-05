# ATLANTECH — Decisions, Conflicts and Open Points

This file lists every decision that must be closed before implementation, every conflict between the source documents, and every open point. Each item has a fixed ID from `DEC-01` to `DEC-59`.

- **Closing task:** has the same ID as the item and belongs to the owner team. It sits in the sprint where the first task that needs the decision starts, and is closed at that sprint's FRR or earlier.
- **Status:** `Open` needs a decision by its closing sprint. `Closed` is already settled and kept for reference.
- **Recommendation:** my proposal based on the documents. The final decision is written in the "Decision" row when the Leads Council closes the item.
- **القصة:** under each item, a short story in Arabic that explains where the problem is.

**Single source of truth.** This file is the only record of project decisions; there is no separate decision log. Every change is made directly in the entry it concerns:

- **Edit, don't duplicate.** Update the existing `DEC-` entry for its topic. A decision that belongs to one AI task and has no `DEC-` ID goes in [AI task decisions](#ai-task-decisions), keyed by the task ID. New official `DEC-` IDs are never assigned outside the Leads Council.
- **Proposed until approved.** A proposed change is written as a `Proposed change` row in the entry's table (date · task · change · reason · evidence · awaiting whom); the Status and Decision rows stay as they are until the owner approves it.
- **Approved.** The approval is written into the Status and Decision rows, with who approved it and when, and the `Proposed change` row is removed.
- **Follow-ups.** A sub-detail left unresolved by an approved decision is listed under the entry as a follow-up; it does not reopen the decision.

## Summary

| ID | Item | Owner | Status | Close by |
| --- | --- | --- | --- | --- |
| DEC-01 | AI completion signal | Backend Team | Closed | Sprint 1 |
| DEC-02 | Who writes status transitions, history, audit and run rows | Backend Team | Closed | Sprint 1 |
| DEC-03 | Location of the shared validation rule sets (override, yard adjustment, BAPLIE correction, window re-check) | AI Team | Closed | Sprint 1 |
| DEC-04 | Job envelope, versioning, retries and stale-run timeout | AI Team | Closed | Sprint 1 |
| DEC-05 | SSE source for the dashboard | Backend Team | Closed | Sprint 1 |
| DEC-06 | Joint solve scope: which requests may change per trigger | AI Team | Closed | Sprint 1 |
| DEC-07 | Storing a NO_FEASIBLE_WINDOW result | AI Team | Open | Sprint 5 |
| DEC-08 | Database read source and worker privileges | Backend Team | Closed | Sprint 1 |
| DEC-09 | Where deviation thresholds live | Backend Team | Closed | Sprint 6 |
| DEC-10 | Scope of the AI FastAPI service | AI Team | Closed | Sprint 1 |
| DEC-11 | Redis persistence | Backend Team | Closed | Sprint 3 |
| DEC-12 | AI `port_settings` keys | AI Team | Closed | Sprint 1 |
| DEC-13 | Who keeps the OpenAPI file current | Backend Team | Closed | Sprint 1 |
| DEC-14 | C-01 · Part 1 run | AI Team | Closed | Sprint 1 |
| DEC-15 | C-02 · Part 2 solve | AI Team | Closed | Sprint 1 |
| DEC-16 | C-03 · Yard placement | AI Team | Closed | Sprint 1 |
| DEC-17 | C-04 · BAPLIE parse | AI Team | Closed | Sprint 1 |
| DEC-18 | C-05 · Validation | AI Team | Closed | Sprint 1 |
| DEC-19 | C-06 · Completion message | AI Team | Closed | Sprint 1 |
| DEC-20 | Tug requirement formula | AI Team | Closed | Sprint 2 |
| DEC-21 | Phase 1 delay-risk rule | AI Team | Closed | Sprint 3 |
| DEC-22 | Financial-impact data in ranking | AI Team | Open | Sprint 4 |
| DEC-23 | Objective terms, weights and number of options | AI Team | Closed | Sprint 1 |
| DEC-24 | Part 1 settings: horizon, time step, minimum window, slot | AI Team | Open | Sprint 4 |
| DEC-25 | Uncertainty margin and window confidence | AI Team | Closed | Sprint 3 |
| DEC-26 | Weather and marine providers | AI Team | Open | Sprint 4 |
| DEC-27 | Tidal constants source, datum and reference | AI Team | Open | Sprint 4 |
| DEC-28 | Definition of moves | AI Team | Closed | Sprint 3 |
| DEC-29 | Yard recommendation method, objective and confidence | AI Team | Open | Sprint 3 |
| DEC-30 | Numeric thresholds register | AI Team | Open | Sprint 2 |
| DEC-31 | Part 3 scheduling host | AI Team | Open | Sprint 6 |
| DEC-32 | Availability semantics for pilots and tug masters | AI Team | Closed | Sprint 3 |
| DEC-33 | Manual-planning baseline | AI Team | Open | Sprint 7 |
| DEC-34 | Building A4 rules on synthetic data | AI Team | Open | Sprint 3 |
| DEC-35 | Sign-in identifier | Backend Team | Closed | Sprint 1 |
| DEC-36 | One role per user vs role history | Backend Team | Closed | Sprint 2 |
| DEC-37 | "Reject with reason" on P-44 and P-47 | Backend Team | Open | Sprint 6 |
| DEC-38 | Where to activate the tide constituent set | UI/UX Team | Open | Sprint 3 |
| DEC-39 | CT Supervisor status list | Backend Team | Closed | Sprint 6 |
| DEC-40 | Mobile Acknowledge event type and payload | Backend Team | Closed | Sprint 6 |
| DEC-41 | Automatic sync right after saving an event while online | Mobile Team | Open | Sprint 4 |
| DEC-42 | Staff pages on the tablet and a provisioning screen | Leads Council | Closed | Sprint 2 |
| DEC-43 | Recommendation confidence field on P-38 | AI Team | Open | Sprint 6 |
| DEC-44 | Storing the clock-skew review note | Backend Team | Closed | Sprint 6 |
| DEC-45 | Display time zone | Frontend Team | Open | Sprint 1 |
| DEC-46 | Supported browsers and viewports | Frontend Team | Open | Sprint 1 |
| DEC-47 | Backend environment for development and testing | Backend Team | Closed | Sprint 2 |
| DEC-48 | Field roles on the web | Leads Council | Closed | Sprint 2 |
| DEC-49 | Status and error colours and the icon set | UI/UX Team | Closed | — |
| DEC-50 | BAPLIE correction and withdraw | Leads Council | Closed | — |
| DEC-51 | Shared berths | Leads Council | Closed | — |
| DEC-52 | Boat management (P-61) | Leads Council | Closed | — |
| DEC-53 | Screens baseline | Leads Council | Closed | — |
| DEC-54 | Licence, SaaS and READ_ONLY in the task files | Leads Council | Closed | — |
| DEC-55 | TIMING and NCT recommendation producers | Leads Council | Closed | — |
| DEC-56 | SaaS API location and licence signing key | Leads Council | Closed | — |
| DEC-57 | Port API status codes, error catalogue and version token | Backend Team | Closed | — |
| DEC-58 | Field task details from the CT-07 Mobile review | Backend Team | Closed | — |
| DEC-59 | `port_settings` min and max, and CHAMPION `deployed_at` | Backend Team | Closed | Sprint 2 |

## Backend–AI integration decisions

### DEC-01 · AI completion signal

| | |
| --- | --- |
| Source | D-01 · OD-01 · AIBD-010 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-01 · Sprint 1 |
| Affects | P3-I3 · AI-011 · CT-14 |
| Decision | Closed (2026-10-27), full text in CT-14 v1.0. Option 1: after commit the worker RPUSHes C-06 to `queue:ai-results`; a supervised consumer (`php artisan ai:consume-results`, BLPOP) handles it; a poller every 30 s is the safety net (runs DONE/FAILED with `result_handled_at IS NULL`, and `drift_measurements` with `is_drifted = 1` and `notified_at IS NULL`). De-duplication: `result_handled_at` claim on run tables, Redis key on `job_id` for VALIDATION and PART3_EVALUATION. |

<div dir="rtl">

**القصة.** الموظف داس "موافقة الجمارك"، والـ AI حسب نوافذ الدخول وكتبها في الـ database. بس الـ Laravel مايعرفش إن الـ AI خلص، فالشاشة فاضلة واقفة على "جاري الحساب" لحد ما حد يعمل refresh. محتاجين طريقة الـ AI يقول بيها للـ Backend "أنا خلصت".

</div>

**Topic.** Laravel must learn that a worker finished so it can send SSE and notifications within 5 seconds of the commit. No mechanism is documented.

**Options:**

1. After committing, the worker pushes a JSON message (RPUSH) to a list named `queue:ai-results`; the Backend runs a consumer as a supervised artisan command.
2. A Backend poller reads the run tables at intervals (slower).
3. MySQL change capture (new infrastructure).

**Recommendation.** Option 1 with a poller as a safety net. Both teams agree, and it needs no new infrastructure because Redis is already there.

### DEC-02 · Who writes status transitions, history, audit and run rows

| | |
| --- | --- |
| Source | D-02 · OD-02 · AIBD-011 · AIBD-013 · AIBD-025 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-02 · Sprint 1 |
| Affects | P3-I2 · P4-K1 · AI-058 |
| Decision | Closed (2026-10-27), full text in CT-15 v1.0. Option 1: the Backend creates run rows, writes every request transition, history row and audit entry, and closes old rows (REPLACED, ACTIVE, CONFIRMED, REJECTED); workers insert new rows and complete only their own run (guarded by `status = 'RUNNING'`). `solver_version` is set by the Backend from `port_settings` and overwritten by the worker if different. The yard worker's `lifecycle_status` write is limited to GENERATED / GENERATION_FAILED. |

<div dir="rtl">

**القصة.** لو الـ AI والـ Backend الاتنين بيغيّروا حالة الطلب، ممكن الاتنين يكتبوا في نفس اللحظة والحالة تبوظ، أو الـ history يتسجل مرتين، أو يتسجل من غير audit. لازم يبقى فيه "صاحب" واحد بس لحالة الطلب.

</div>

**Topic.** Request status (SM-4), its history and its audit need a single writer. `solver_runs.solver_version` is mandatory and only the worker knows it.

**Options:**

1. The Backend writes every request transition, history row and audit entry, and creates the run row as QUEUED before enqueueing. The AI writes run progress and result tables only.
2. The AI writes everything in its result transaction.

**Recommendation.** Option 1 (agreed). The Backend writes `solver_version` from `port_settings`; the worker overwrites it if different.

### DEC-03 · Location of the shared validation rule sets (override, yard adjustment, BAPLIE correction, window re-check)

| | |
| --- | --- |
| Source | D-03 · OD-03 · AIBD-008 · AIBD-034 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-03 · Sprint 1 |
| Affects | P4-K4 · P6-P3 · P3-H6 · AI-060 · AI-067 · AI-F03 · CT-13 |
| Decision | Closed (2026-10-27), full text in CT-13 v1.0. Option 1 (async on a worker), since FastAPI is cancelled (DEC-10): override and yard adjustment on `queue:validate` (`w_validate`, SELECT only); BAPLIE correction on `queue:edi` with `source = STAGED_PAYLOAD`; window re-check stays in Laravel. Violations are warnings (override with a reason, audited as SAFETY_EXCEPTION); no result within `validation_timeout_seconds` → change refused (fail closed). |

<div dir="rtl">

**القصة.** الـ AI اقترح الرصيف B12 للسفينة. الموظف عمل override وغيّره لـ B7، بس B7 أقل عمق من الغاطس بتاع السفينة. القاعدة اللي بتمنع ده مكتوبة في كود الـ AI بس. لو الـ Backend كتب نسخة تانية من القاعدة، النسختين ممكن يختلفوا مع الوقت. ولو سأل الـ AI في الخلفية، الموظف هيستنى. لازم نحدد القواعد دي هتعيش فين.

</div>

**Topic.** The same hard rules must apply in two places: when the AI generates a result and when a user edits it. The teams disagree: the AI wants a background job, the Backend wants the check inside Laravel.

**Options:**

1. Async job on the worker (C-05): one Python implementation; the user waits for the result over SSE.
2. A second copy of the rules in Laravel with shared test vectors: instant answer, but two codebases that must stay identical.
3. A synchronous endpoint on the AI FastAPI service: Laravel calls it and waits; the rules are written once in Python.

**Recommendation.** Option 3 for override and yard adjustment: an instant answer (422 with the broken constraint) and a single implementation. BAPLIE correction stays async on `queue:edi` because it is heavy. If FastAPI is unreachable the Backend refuses the change (fail closed). The window re-check stays in Laravel: it confirms the proposal is the latest and the forecast run is still the newest.

### DEC-04 · Job envelope, versioning, retries and stale-run timeout

| | |
| --- | --- |
| Source | D-04 · OD-22 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-04 · Sprint 1 |
| Affects | P3-I1 · AI-011 · CT-08 |
| Decision | Closed (2026-10-27): Option 1. JSON envelope pushed with RPUSH on unprefixed queue names (`queue:part1`, `queue:part2`, `queue:yard`, `queue:edi`, `queue:validate`), `contract_version = "1.0"`; payload schemas per job type referenced from `envelope.schema.json` (CT-08). Retries: Part 1 up to `part1_max_retries` (3), other jobs once, VALIDATION never. A run RUNNING longer than `run_stale_after_seconds` is marked FAILED / TIMEOUT by the Backend sweeper (`part1_run_timeout_seconds` from DEC-14 is dropped). Full envelope, worker and error-category rules in CT-08 v1.0 (approved 2026-10-30 on Backend Team sign-off). |

<div dir="rtl">

**القصة.** الـ Laravel بيحط الـ jobs في Redis بصيغة PHP، والـ worker مكتوب Python ومش هيعرف يقراها. ولو الـ worker وقع وهو شغال، الـ run هيفضل "RUNNING" للأبد. محتاجين نتفق على شكل الرسالة، ونعيد المحاولة كام مرة، وإمتى نعتبر الـ run مات.

</div>

**Topic.** The default Laravel queue format serialises PHP classes that Python cannot read.

**Options:**

1. JSON envelope pushed with RPUSH onto the documented queue name, `contract_version = "1.0"`.
2. Laravel job classes with a decoder in Python.

**Recommendation.** Option 1 (agreed), with unprefixed key names. Retries: Part 1 up to 3 (documented), others once. A run left RUNNING longer than `run_stale_after_seconds` is marked FAILED.

### DEC-05 · SSE source for the dashboard

| | |
| --- | --- |
| Source | D-06 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-05 · Sprint 1 |
| Affects | P3-I4 · FE-033 · CT-05 |
| Decision | Closed (2026-10-30): Option 1. A Laravel streamed endpoint, `GET /api/v1/events`, filtered by role and terminal, with `Last-Event-ID` catch-up from a short-lived Redis store. Reverb for mobile only. Risk for P3-I4: each open browser holds a PHP worker, so limit the connection time and size the worker pool. |

<div dir="rtl">

**القصة.** الـ dashboard لازم يتحدث لحظيًا من غير refresh. محدش اتفق الأحداث دي بتطلع منين وبأي شكل. فالـ Frontend مش هيعرف يبني الـ SSE client، والـ Backend مش هيعرف يبني الـ endpoint.

</div>

**Topic.** The AI documents do not say what feeds the SSE.

**Options:**

1. A Laravel streamed endpoint reading from a short-lived events store (Redis); Reverb for mobile only.
2. Reverb for both web and mobile.

**Recommendation.** Option 1 (Backend position): `GET /api/v1/events` filtered by role and terminal, with `Last-Event-ID` catch-up.

### DEC-06 · Joint solve scope: which requests may change per trigger

| | |
| --- | --- |
| Source | D-07 · OD-08 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-06 · Sprint 1 |
| Affects | AI-050 · AI-055 · P4-K1 · P4-K5 |
| Decision | Closed (2026-10-27): **Option 2** (changed from the earlier Option 1 note). Only the requests listed in the PART2_SOLVE message are variable; every confirmed plan and every other pending recommendation is fixed capacity. Only the previous PENDING_REVIEW version of a solved request becomes REPLACED (by the Backend on C-06). Full rules in CT-10. |

<div dir="rtl">

**القصة.** سفينة جديدة وصلت والـ AI هيحسب لها مكان. هل مسموح يحرّك السفن التانية اللي لسه توصياتها مستنية موافقة؟ ولا يحطها بس في الأماكن الفاضية؟ ولو حرّك سفينة، التوصية القديمة بتاعتها تتلغي؟

</div>

**Topic.** CP-SAT solves for the whole port, so we must define what is fixed and what is variable.

**Options:**

1. Confirmed plans are fixed; pending requests and the trigger request are variable.
2. Only the trigger request is variable.

**Recommendation.** Option 1 (agreed). It defines which pending versions become REPLACED.

### DEC-07 · Storing a NO_FEASIBLE_WINDOW result

| | |
| --- | --- |
| Source | D-08 · OD-10 · PS-01 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-07 · Sprint 5 |
| Affects | P4-J1 · AI-048 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الطقس وحش طول الأيام الجاية، والـ AI مالقاش أي نافذة دخول. لازم يسجل "مفيش نافذة" ومعاها الفترات الممنوعة وسببها. بس الـ schema مايسمحش بفترة ممنوعة من غير proposal.

</div>

**Topic.** `blocked_periods.proposal_id` is mandatory, so a proposal must exist even when no window exists.

**Options:**

1. A proposal with no windows, linked from the run (schema note change only).
2. An unlinked proposal found by request and time.

**Recommendation.** Option 1 (agreed).

### DEC-08 · Database read source and worker privileges

| | |
| --- | --- |
| Source | D-09 · OD-21 · AIBD-028 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-08 · Sprint 1 |
| Affects | P3-I5 · AI-013 |
| Decision | Closed (2026-10-27): Option 1. Workers read from the primary; six accounts (`w_part1`, `w_part2`, `w_yard`, `w_edi`, `w_validate`, `w_part3`); no DELETE, no DDL, column-level UPDATE on tables a worker does not own; no `audit_logs` access (the Backend writes all audit entries on C-06). Rule: **workers insert new rows; the Backend retires old ones** (REPLACED / ACTIVE transitions). Full matrix under "Final grants" below. The Backend writes the grants script. |

<div dir="rtl">

**القصة.** لو كل الـ workers داخلين على الـ database بنفس الحساب بكل الصلاحيات، أي bug في الـ parser ممكن يمسح جدول الخطط. ولو قرأوا من نسخة متأخرة، ممكن يحسبوا على رصيف اتحجز من ثواني.

</div>

**Topic.** Each worker must read port state and write only its own results.

**Options:**

1. Read from the primary, one account per worker with limited rights, `audit_logs` INSERT/SELECT only.
2. Read from the replica and tolerate lag.

**Recommendation.** Option 1 (agreed); the Backend writes the grants script.

**Final grants (agreed with the AI Team, 2026-10-27):**

| Account | Queue / trigger | INSERT | UPDATE (columns) |
| --- | --- | --- | --- |
| `w_part1` | `queue:part1` + Part 1 scheduler (weather pull, daily tide, demand forecast) | `entry_window_proposals` · `feasible_windows` · `blocked_periods` · `forecast_runs` (SCHEDULED / ON_DEMAND) · `environment_forecast_points` · `tide_prediction_runs` · `tide_prediction_points` · `demand_forecast_slots` | `part1_runs` (`status`, `outcome`, `retry_count`, `entry_window_proposal_id`, `started_at`, `finished_at`) on its own run only |
| `w_part2` | `queue:part2` | `solver_run_model_versions` · `recommendations` · `recommendation_options` · `recommendation_option_tugs` · `recommendation_rationale_factors` | `solver_runs` (`status`, `objective_value`, `solve_time_ms`, `solver_version`, `result_detail`, `started_at`, `finished_at`) |
| `w_yard` | `queue:yard` | `yard_placement_items` | `yard_runs` (`status`, `outcome`, `error_category`, `result_detail`, `worker_version`, `started_at`, `finished_at`) · `terminal_recommendations` (`lifecycle_status`, `confidence`, `rationale_template_id`, `rationale_params`, `failure_reason`) |
| `w_edi` | `queue:edi` (parse and BAPLIE correction) | `baplie_parse_issues` · `containers` (new numbers only) · `container_manifest_entries` | `baplie_parse_runs` (`status`, `outcome`, `error_category`, `retry_count`, `container_count`, `result_detail`, `worker_version`, `started_at`, `finished_at`) · `baplie_files` (`parse_status`, `staged_payload`) · `vessels` (`call_sign`, `flag_state`, only when NULL) |
| `w_validate` | `queue:validate` (override and yard-adjustment validation) | — | — |
| `w_part3` | Part 3 scheduler (host per DEC-31) | `evaluation_metrics` · `drift_measurements` | — |

**Update 2026-10-28:** `retry_count` added to `w_edi` on `baplie_parse_runs` so the grants match CT-15 v1.1, which lists it among the AI columns (backend `feature/CT-15-edi-retry-count`). The full matrix, generated from the grants script, is `contracts/ai/table-ownership.md` (CT-15 output).

**Read grants (all accounts):** SELECT on every port table, except: `users` column-level (`id`, `name`, `is_active`); `license_states` column-level (`mode`, `read_only_reason`); no access to `audit_logs`, `notification_logs`, `user_devices`, `recommendation_reviews` or the SaaS database.

**Done by the Backend, not by workers:**

- `baplie_files.status` (new file → ACTIVE, previous ACTIVE → REPLACED) on C-06 with PARSED.
- The previous `part1_runs` → REPLACED when a new run is enqueued (same as `yard_runs` in CT-11).
- The previous `entry_window_proposals` → REPLACED on C-06 when a new proposal was produced (same as recommendations in CT-10).
- Every `audit_logs` entry, on C-06.
- Marking stale RUNNING runs as FAILED (sweeper, P3-I2).

**Not in the grants now:** `terminal_recommendations` TIMING / STORAGE_ALLOCATION and `storage_allocation_items` (out of MVP, DEC-55); Part 3 retraining tables (`ml_model_versions`, `retraining_runs`) until retraining is built. Both are added through CT-17.

**Worker health:** each worker writes a Redis key `worker:{name}:heartbeat` (timestamp, version, queue depth; TTL 60 s). No DB grant is needed.

**Rules confirmed by the AI Team (acknowledgement, 2026-10-27):**

- **Final run update is guarded:** `UPDATE <run> SET status = 'DONE' … WHERE id = :run_id AND status = 'RUNNING'`. 0 rows → the Backend replaced the run; the worker rolls back the whole transaction (including inserted proposals or recommendations) and sends no C-06. Applies to `part1_runs`, `solver_runs`, `yard_runs` and `baplie_parse_runs`.
- **Failed weather pull:** `w_part1` inserts a new `forecast_runs` row with `status = FAILED`, `data_stale = 1` and no points; it never updates an older row. "Is the stored data stale?" is computed at read time from the age of the latest SUCCESS run against `part1_stored_data_max_age_hours` (48).
- **Backend reads the current proposal** through `part1_runs.entry_window_proposal_id` of the latest DONE run, never by `status = 'PROPOSED'` (there is a short window with two PROPOSED rows before C-06 is handled). Applies to `GET …/part1-result` and the window re-check on confirm.
- **C-06 for `PART1_RUN`** carries `entry_window_proposal_id` (required when a proposal was inserted, otherwise `null`). Input to DEC-19.

### DEC-09 · Where deviation thresholds live

| | |
| --- | --- |
| Source | D-10 · OD-16 (part) · AIBD-020 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-09 · Sprint 6 |
| Affects | P5-O6 · P5-O7 |
| Decision | Closed (2026-10-31): Option 1. `port_settings` keys per component type. The numbers come from DEC-30, and the keys are added to `reference-seed.json` then. |

<div dir="rtl">

**القصة.** القاطرة اتأخرت 10 دقايق. هل ده تأخير مهم يستاهل إعادة تخطيط، ولا عادي؟ الحد ده لازم الـ Port Admin يغيّره، بس مفيش مكان في الـ database نحفظه فيه.

</div>

**Topic.** The thresholds that make a delay "significant" per operation type have no place in the schema.

**Options:**

1. `port_settings` keys per component type.
2. A new table.

**Recommendation.** Option 1 (agreed). Edited from P-62.

### DEC-10 · Scope of the AI FastAPI service

| | |
| --- | --- |
| Source | New decision |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-10 · Sprint 1 |
| Affects | AI-F01 · AI-F02 · AI-F03 · CT-16 |
| Decision | Closed (2026-10-27): FastAPI is cancelled. Laravel and Python talk only through Redis and MySQL. Validation moves to `queue:validate` (CT-13); health moves to Redis heartbeat keys `worker:{name}:heartbeat` (CT-16). |

<div dir="rtl">

**القصة.** اتقرر إن الـ AI هيبقى ليه APIs بـ FastAPI، بس كل المستندات مبنية على إن الكلام بين الـ Backend والـ AI عن طريق Redis بس. لو ماحددناش الـ FastAPI مسؤول عن إيه، كل تيم هيفترض حاجة. ممكن نلاقي نفس الشغل متعمل مرتين، أو حل CP-SAT واخد ثواني مستني جوه HTTP request.

</div>

**Topic.** The AI will expose APIs with FastAPI. The documents say Laravel and Python talk only through Redis, so the role of FastAPI must be set.

**Options:**

1. FastAPI is an internal API layer on top of the workers: health and readiness of each worker, synchronous validation (DEC-03), and run status for diagnosis. Heavy work (Part 1, Part 2, parsing, yard) stays on the queues.
2. FastAPI replaces the queues and all work becomes HTTP.

**Recommendation.** Option 1. FastAPI is internal to the port server and is not exposed to the web or mobile app. Laravel is its only client, authenticated with a service token header (`X-Service-Token`). FastAPI publishes its own OpenAPI file (CT-16).

### DEC-11 · Redis persistence

| | |
| --- | --- |
| Source | AIBD-029 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-11 · Sprint 3 |
| Affects | P3-I2 · P6-R6 |
| Decision | Closed (2026-10-31): Option 1. AOF enabled with `appendfsync everysec`, and the P3-I2 sweeper as the safety net. The SSE catch-up store (CT-05) stays short-lived: a client whose events are lost gets `RESYNC`. |

<div dir="rtl">

**القصة.** السيرفر عمل restart، والـ Redis كان فيه 5 jobs لسه ماتنفذتش. من غير persistence الـ jobs دي هتضيع، والطلبات هتفضل "مستنية" على الشاشة ومحدش هيحسبها.

</div>

**Topic.** If Redis goes down, queued jobs may be lost. Persistence is not documented.

**Options:**

1. AOF enabled (`appendfsync everysec`).
2. RDB snapshots only.
3. No persistence; rely on the sweeper that re-queues QUEUED runs.

**Recommendation.** Option 1, with the sweeper (P3-I2) as a safety net.

### DEC-12 · AI `port_settings` keys

| | |
| --- | --- |
| Source | AIBD-021 · PS-02 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-12 · Sprint 1 |
| Affects | AI-012 · P2-F9 |
| Decision | Closed (2026-10-27): Option 1. AI settings live in `port_settings`, edited only by `PORT_GM` with audit and min / max plus cross-field validation on save; workers read them per job without cache. Key list and defaults in CT-18 v1.0. |

<div dir="rtl">

**القصة.** لو وقت الـ solver أو عدد مرات إعادة المحاولة مكتوبين جوه الكود، أي تغيير محتاج developer وdeploy جديد. محتاجين قايمة متفق عليها بالإعدادات اللي الـ Backend يحطها في الـ database والـ AI يقراها.

</div>

**Topic.** AI settings must change without code changes.

**Options:**

1. Proposed list: `weather_pull_hours`, `tide_horizon_days`, `part1_stored_data_max_age_hours` (48), `part1_assessment_horizon_hours`, `part1_time_step_minutes`, `part1_min_window_minutes`, `demand_slot_minutes`, `solver_time_limit_seconds` (10), `solver_options_per_request`, `part1_max_retries` (3), `run_stale_after_seconds`, `part3_evaluation_cron`, `drift_psi_threshold`, `drift_mae_threshold`.
2. Environment variables (cannot change at runtime).

**Recommendation.** Option 1. Undocumented values are set in DEC-24 and DEC-30.

### DEC-13 · Who keeps the OpenAPI file current

| | |
| --- | --- |
| Source | Backend open inputs |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-13 · Sprint 1 |
| Affects | P1-A4 · CT-02 |
| Decision | Closed (2026-10-29): Option 1. The Backend Team is the single owner of the OpenAPI file (CT-02). Its source is project-backend `ATLANTECH/openapi/port-api.yaml`, published unchanged to PortHub `contracts/openapi/port-api.yaml` with `composer contracts:openapi`. Every backend PR that adds or changes an endpoint updates the file in the same PR, opens the paired PortHub PR, and the backend drift test and the Spectral CI check fail otherwise. The API readiness pack (CT-23) links the OpenAPI diff. Decided by Marwan (Backend lead) in P1-A4. |

<div dir="rtl">

**القصة.** الـ Backend غيّر اسم حقل في الـ API ونسي يحدّث الـ OpenAPI. الـ Frontend بنى الشاشة على الاسم القديم، والشاشة وقعت في الـ demo. لازم يبقى فيه صاحب واحد للملف ده وقاعدة إنه يتحدث مع كل تغيير.

</div>

**Topic.** Frontend and Mobile build against the OpenAPI file, so it must stay up to date.

**Options:**

1. The Backend Team is the single owner; any PR that changes an endpoint updates the file in the same PR.
2. Each team updates its own part.

**Recommendation.** Option 1, with an OpenAPI diff in the API readiness pack (CT-23).


## AI contract v1 (C-01 to C-06)

### DEC-14 · C-01 · Part 1 run

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-001 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-14 · Sprint 1 |
| Affects | P3-I7 · P4-J3 · AI-048 · CT-09 |
| Decision | Approved (2026-10-26). Payload schema as proposed by the AI Team: `berthing_request_id` (integer ≥ 1), `reason` (CUSTOMS_APPROVAL / RECOMPUTE / MANUAL_DATA / REOPEN), `manual_forecast_run_id` required only when MANUAL_DATA and forbidden otherwise; `additionalProperties: false`. Backend validates every message against the schema before RPUSH and sends `triggered_by_user_id = null` for CUSTOMS_APPROVAL, the acting user otherwise. Open question to the AI Team: confirm the schema covers `payload` only and is referenced from `envelope.schema.json` (CT-08) when `job_type = PART1_RUN`. |

<div dir="rtl">

**القصة.** بعد موافقة الجمارك، الـ Backend بيبعت للـ AI رسالة "احسب نوافذ الدخول للطلب ده". لو الحقول وأسباب الإعادة مش متفق عليها، الـ AI ممكن يرفض الرسالة أو يحسب غلط. ومفيش حد محدد للـ run ياخد قد إيه قبل ما نعتبره فشل.

</div>

**Topic.** The message that starts the entry-window computation for one request on `queue:part1`.

**Options:**

1. Payload: `berthing_request_id`, `reason` (CUSTOMS_APPROVAL / RECOMPUTE / MANUAL_DATA / REOPEN), `manual_forecast_run_id` when MANUAL_DATA.

**Recommendation.** Approve the proposed payload. The timeout is not documented: proposed `part1_run_timeout_seconds = 120` in `port_settings`.

### DEC-15 · C-02 · Part 2 solve

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-002 to 005 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-15 · Sprint 1 |
| Affects | P4-J3 · P4-K3 · P4-K5 · P5-O7 · AI-058 · CT-10 |
| Decision | Approved (2026-10-26), full text in CT-10 v1.0. Payload-only schema referenced from the envelope. Only one `PART2_SOLVE` QUEUED or RUNNING at a time; triggers arriving meanwhile are merged, so the payload carries a `triggers` list (each entry: `trigger_type`, `berthing_request_ids` min 1, plus `changed_resources` / `operational_plan_id` / `requested_by_user_id` per type, optional `context_note` ≤ 500 for logs only). `payload.trigger_type` = highest precedence (REPLAN > RESOURCE_CHANGE > MANUAL > NEW_REQUEST). `purpose` removed from the payload and derived per request by the AI. `result_detail` is per request, with run outcomes SOLVED / PARTIALLY_SOLVED / NO_FEASIBLE_PLAN / FIFO_FALLBACK / GENERATION_FAILED, a closed STRUCTURAL constraint list, and `failure_reason` only when status = ERROR. |

<div dir="rtl">

**القصة.** نفس الـ worker بيتطلب منه 4 حاجات مختلفة: توصية جديدة، إعادة توليد، رصيف اتعطل، أو سفينة اتأخرت. كل حالة ليها بيانات مختلفة، ولو الرسالة مش واضحة الـ AI مش هيعرف هو بيحل مشكلة إيه بالظبط.

</div>

**Topic.** The message for solve, regenerate, resource change and delay re-plan on `queue:part2`.

**Options:**

1. Payload: `trigger_type` (NEW_REQUEST / MANUAL / RESOURCE_CHANGE / REPLAN), `berthing_request_ids`, `purpose` (INITIAL / DELAY_REPLAN), `changed_resource`, `operational_plan_id`, `context_note`; plus the `result_detail` shape with the outcome and binding constraints.

**Recommendation.** Approve as proposed. `context_note` is stored in logs only.

### DEC-16 · C-03 · Yard placement

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-006 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-16 · Sprint 1 |
| Affects | P6-P1 · AI-066 · CT-11 |
| Decision | Approved (2026-10-27), full text in CT-11 v1.0. Payload-only schema with `terminal_recommendation_id` and `operational_plan_id` (both required). Runs on a new `queue:yard` with its own worker. Run tracking in a new `yard_runs` table (Backend adds it through CT-17; `run_id = yard_runs.id`). Regeneration reuses the same `terminal_recommendations` row and marks older active runs REPLACED. Partial placement → `YARD_REC_GENERATED` with unplaced containers and reason codes in `yard_runs.result_detail`; none placed → `GENERATION_FAILED` / `INFEASIBLE`. `yard_slot_id` always NULL in v1; nothing is a reservation. `confidence` = preferred-zone share (DEC-29 Option A). |

<div dir="rtl">

**القصة.** الخطة اتأكدت لسفينة حاويات، والـ Backend لازم يطلب من الـ AI توصية أماكن الحاويات في الساحة. محتاجين نتفق على شكل الطلب، ونتفق كمان إن الـ AI بيقترح بس ومش بيحجز أماكن بنفسه.

</div>

**Topic.** The yard recommendation message on `queue:part2`.

**Options:**

1. Payload: `terminal_recommendation_id` (in YARD_REC_REQUESTED) and `operational_plan_id`. The worker never reserves a slot.

**Recommendation.** Approve as proposed.

### DEC-17 · C-04 · BAPLIE parse

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-007 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-17 · Sprint 1 |
| Affects | P3-H3 · AI-030 · AI-033 · CT-12 |
| Decision | Approved (2026-10-27), full text in CT-12 v1.0: the Backend proposal accepted by the AI Team. Payload `baplie_file_id` + `source` (FILE / STAGED_PAYLOAD); new `baplie_parse_runs` table (CT-17); outcomes PARSED / QUARANTINED / REJECTED plus FAILED runs for technical errors; the worker writes `parse_status` and `staged_payload` only, the Backend sets ACTIVE / REPLACED on C-06; corrections are re-validated and committed by the worker. Supported versions: SMDG BAPLIE 2.2.1 (D.95B) and 3.1.1 (D.13B); anything else is REJECTED. NFR-PERF-2 (BAPLIE parse time by file size) is **removed from the MVP**, requested by the AI Team and approved by the Leads Council on 2026-10-27; QA runs no BAPLIE performance tests (CT-24). |

<div dir="rtl">

**القصة.** المطلوب إن تحليل الملف ياخد 3 أو 10 أو 25 ثانية حسب "حجمه"، بس محدش عرّف يعني إيه ملف صغير أو كبير. فمش هنعرف نختبر الأداء ولا نقول إنه ناجح.

</div>

**Topic.** The BAPLIE parsing message on `queue:edi`.

**Options:**

1. Payload: `baplie_file_id` only; the worker reads the rest from the row. The NFR-PERF-2 size classes (3 / 10 / 25 seconds) need size definitions.

**Recommendation.** Approve. Size classes (proposed): small up to 500 containers, medium up to 5,000, large up to 20,000.

### DEC-18 · C-05 · Validation

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-008 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-18 · Sprint 1 |
| Affects | AI-F03 · P4-K4 · P6-P3 · CT-13 |
| Decision | Closed (2026-10-27), full text in CT-13 v1.0. Async variant: `VALIDATION` job with `validation_type` (OVERRIDE / YARD_ADJUSTMENT), `subject_id`, `proposed_change`; `run_id = null`, correlation by `job_id`; result `validation_result` returned in C-06. |

<div dir="rtl">

**القصة.** لما الموظف يعدّل الرصيف، الـ Backend هيسأل الـ AI "التعديل ده سليم؟". لو شكل السؤال والإجابة مش متفق عليهم، رسالة الخطأ اللي هتوصل للموظف مش هتقول هو كسر أنهي قيد.

</div>

**Topic.** The shape of the validation request and its result. Depends on DEC-03 and DEC-10.

**Options:**

1. If DEC-03 = FastAPI: `POST /internal/v1/validate` with `validation_type` (OVERRIDE / YARD_ADJUSTMENT), `subject_id`, `proposed_change`; the answer `{valid, violations[]}` comes back immediately.
2. If async: the same fields plus `request_token`, with the result returned through C-06.

**Recommendation.** Option 1 for override and yard adjustment; BAPLIE correction async on `queue:edi` with the same fields.

### DEC-19 · C-06 · Completion message

| | |
| --- | --- |
| Source | AI contract v1 · AIBD-010 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-19 · Sprint 1 |
| Affects | P3-I3 · AI-011 · CT-14 |
| Decision | Closed (2026-10-27), full text in CT-14 v1.0. Fields: `contract_version`, `job_type`, `job_id`, `run_id`, `status` (DONE / FAILED), `outcome`, `error_category`, `finished_at`, `worker_version`, plus one extra field per job type (`entry_window_proposal_id`, `terminal_recommendation_id`, `baplie_file_id`, `validation_result`, `drift_measurement_ids`). List name `queue:ai-results`. |

<div dir="rtl">

**القصة.** لما الـ AI يخلص، رسالة "خلصت" لازم تقول خلص إيه، ونجح ولا فشل، وليه. من غير كده الـ Backend مش هيعرف يغيّر حالة الطلب صح ولا يبعت الإشعار المناسب.

</div>

**Topic.** The shape of the completion message the worker sends to the Backend.

**Options:**

1. `{contract_version, job_type, run_id, status, outcome, error_category, finished_at}`; Part 3 uses it for DRIFT_ALERT.

**Recommendation.** Approve; the list name is `queue:ai-results`.


## AI decisions (inputs and logic)

### DEC-20 · Tug requirement formula (N_min, N_cap, BP_req per berthing request)

| | |
| --- | --- |
| Source | OD-04 · RSK-01 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-20 · Sprint 2 |
| Affects | AI-054 · AI-055 |
| Decision | Closed (2026-11-03), **interim tables**: the hybrid in "Decision detail" below. Tug requirements are computed before the solver, outside CP-SAT, and passed to it per berthing request as `N_min`, `N_cap`, `BP_req` (tonnes), `eligible_tugs` and flags. The values are interim until the open items below are settled. |
| Agreed with | Mostafa Mohamed Rashwan, Leads Council, 2026-11-03. AI lead approval: Menna Gamal (AI lead, @MennaGamal-87), 2026-11-03. |
| Implementation | `project-ai` `part2/tugs.py`, `part2/tug_rules.json`, `tests/unit/part2/test_tugs.py` (AI-054). CP-SAT constraints: AI-055. |

<div dir="rtl">

**القصة.** سفينة طولها 300 متر داخلة الميناء. محتاجة كام قاطرة؟ 2 ولا 3 ولا 4؟ القاعدة دي بيقررها خبراء القطر مش المبرمجين، ولحد دلوقتي محدش ادّاها لنا. من غيرها الـ solver مش هيعرف يحجز قاطرات.

</div>

**Topic.** The number of tugs per vessel (from GT, DWT and tug power) is not defined, and this blocks CP-SAT.

**Options:**

1. Input from the Tug Manager / Marine Safety Officer.
2. A provisional table by vessel length until the input arrives.

**Recommendation.** Request the formula formally in Sprint 1. If it does not arrive, the provisional table is marked "unvalidated" in the rationale and can be replaced without code changes (pluggable rule).

**Decision detail.** Option 2, extended to a hybrid: a table by LOA, with a mass-based bollard pull for tankers and bulk carriers. No formula has arrived from the Tug Manager or Marine Safety Officer, and Sprint 2 needs a rule. The rules are from literature and not yet validated by them, and they can be replaced without code changes.

**Options considered:**

| Option | Result |
| --- | --- |
| Fixed table by length only | Rejected: ignores vessel mass for heavy, slow ships |
| Hybrid: table by LOA, plus mass-based bollard pull for tankers and bulk carriers | **Chosen** |
| Physics only | Rejected: needs windage and environmental data not available in v1 |
| Free solver choice | Rejected: the solver could choose too few tugs |

**Calculation (per berthing request):**

1. **Compulsory towage.** If `gross_tonnage` is below `T_COMPULSORY`, `pilot_requested` is `False` and there is no `pilot_override`: `N_min` = `N_cap` = `BP_req` = 0. `T_COMPULSORY` = 1000, interim and conservative. If `pilot_requested` is unknown below `T_COMPULSORY`, the table applies, with flag `pilot_request_unknown`.
2. **Displacement, only for step 3's types.** Δ = LOA × beam × draught × Cb × 1.025 (tonnes).
   - **Draught:** `berthing_requests.arrival_draft`; if missing, `vessels.max_draft` with flag `max_draft_used`.
   - **Cb:** `berthing_requests.block_coefficient`; if missing or outside [0.50, 0.90], bulk carrier 0.80, tanker 0.80, container 0.65, other 0.85, with flag `cb_fallback_used`.
   - **LOA instead of LBP** slightly overestimates Δ, accepted as conservative. GT and NT are never used as a weight: they measure volume.
3. **Mass-based bollard pull, `TANKER` and `BULK_CARRIER` only.** BP_mass = 60 × Δ / 100,000 + 40 (tonnes).
4. **Table: MPA's column for vessels with power (interim).** Upper LOA limits are inclusive, so a decimal LOA between bands takes the higher band. `BP_floor` is N_base × the minimum, derived here; MPA doesn't state it.

   | LOA (m) | N_base | Min BP per tug (t) | BP_floor (t) |
   | --- | --- | --- | --- |
   | ≤ 60 | 1 | 10 | 10 |
   | ≤ 122 | 2 | 10 | 20 |
   | ≤ 200 | 2 | 17 | 34 |
   | ≤ 280 | 2 | 25 | 50 |
   | > 280 or GT ≥ 75,000, draught < 17 m | 4 | 25 | 100 |
   | > 280 or GT ≥ 75,000, draught ≥ 17 m | 4 | 45 | 180 |

5. **Final values.** `BP_req` = ceil(max(BP_mass if it applies, BP_floor)). `N_min` = N_base. `N_cap` = `N_min` + 1. `eligible_tugs`: tugs whose `tug_power` is in bollard pull and at least the minimum per tug. This is by rating only: availability is AI-055's job (DEC-32). A tug rated in `HP` or `KW` is excluded with flag `tug_power_not_bollard_pull`; no conversion is agreed.
6. **Pilot override.** An optional `pilot_override` replaces `N_min`, `BP_req` or both, with flag `pilot_override`. `N_cap` follows the overridden `N_min`, and eligibility stays by the band from step 4.

Every result carries flag `rules_unvalidated` until the rules are validated and `part2/tug_rules.json` has status `APPROVED`. Closing this decision doesn't validate them: the file stays `PROPOSED` (see the open items).

**Worked example:** bulk carrier, LOA 225 m, beam 32 m, draught 13 m, Cb 0.80, GT 40,000: Δ = 76,752 t, BP_mass = 86.05 t, `BP_req` = 87, `N_min` = 2, `N_cap` = 3.

**Thrusters:** credit for bow or stern thrusters is out of scope for v1. The berthing request has no thruster data, so results are conservative.

**CP-SAT interface (AI-055).** For each request r and tug t, with x[r,t] ∈ {0,1}:
- Σ x[r,t] over eligible tugs ≥ `N_min`
- Σ x[r,t] over eligible tugs ≤ `N_cap`
- Σ BP(t) · x[r,t] over eligible tugs ≥ `BP_req`
- x[r,t] = 0 for a tug that isn't eligible

If infeasible, the request is reported as infeasible; the requirement is never silently relaxed.

**Data requirements:** `vessels.loa`, `vessels.beam`, `vessels.max_draft`, `vessel_types.code`, `berthing_requests.arrival_draft`, `gross_tonnage`, `block_coefficient`, `tugboats.tug_power`, `tugboats.tug_power_unit`. Missing from the schema: `pilot_requested` and a tug-count `pilot_override`. A missing or non-positive LOA, beam, GT or draught raises an error.

**Deviation from AI-012:** the values are in `part2/tug_rules.json`, not `port_settings`, whose `setting_value` is `varchar(255)` and can't hold the table or its sources. A change needs a deploy, not a code change.

**Open items (follow-ups; they don't reopen the decision):**

1. Confirm `T_COMPULSORY` (1000 or 2000) with the Alexandria Port Authority.
2. Replace the interim MPA table with the Alexandria Port Authority's own table.
3. Confirm whether the form's draught is the arrival draught or the maximum draught. The schema holds `arrival_draft`, with `vessels.max_draft` as the fallback.
4. v2: wind-based bollard pull for high-windage ships: BP_wind = 1.25 × 0.5·ρ·C·A_L·V²/9810. Needs windage area and gust forecasts.
5. Fitting SWL limit on `eligible_tugs`: not applied. Check whether the schema has the field; `contracts/db/schema.sql` on PortHub `main` at `b4d2deb` has no match for `swl`, `safe_working` or `fitting`.
6. After the validation in item 9, change `part2/tug_rules.json` from `PROPOSED` to `APPROVED`, which removes the `rules_unvalidated` flag, in a separate code task. That task also updates `tests/unit/part2/test_tugs.py`, which asserts `PROPOSED`, and `part2/README.md`, which still says DEC-20 is Open.
7. Vessels without power: MPA has a separate, higher column, which isn't used. No field says which applies.
8. Tug Manager: decide whether `LNG_CARRIER` should use the mass-based formula. It's "other" for now.
9. Tug Manager and Marine Safety Officer: validate the rules (AI-005). `DWT` isn't used.
10. Backend: add `pilot_requested` to the request, and a place for a tug-count override.
11. Tug Manager: enter fleet power in bollard pull, or agree a conversion.

**References:**
- MPA Singapore Tug Assignment Guidelines, rev. 11 Feb 2025: https://www.mpa.gov.sg/api/media/c3d47522-816b-4197-b4f2-8bbaa3f87097/tug_assignment_guidelines.pdf. Checked on 2026-11-03: the column for vessels with power matches the table.
- Formula: https://www.seanews.com.tr/authors/cahit-istikbal/what-is-bollard-pull-and-how-to-calculate-it/162591/. Checked on 2026-11-03: confirms the formula and the example of 10,000 t giving 46 t, as a rough minimum. It names neither Hensen nor ship types.
- Hensen, *Tug Use in Port* (IMO MSC.1/Circ.1101): cited by the AI lead for the attribution and the limit to tankers and bulk carriers; not checked.
- Compulsory towage, cited by the AI lead, not checked: Alexandria Port Authority, https://apa.gov.eg/en/alex-port-navigation-data/ (above 2000); Ministry of Transport, https://www.mts.gov.eg/en/port/%D9%85%D9%8A%D9%86%D8%A7%D8%A1-%D8%A7%D9%84%D8%AF%D8%AE%D9%8A%D9%84%D8%A9/ (1000 and above).

### DEC-21 · Phase 1 delay-risk rule

| | |
| --- | --- |
| Source | OD-05 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-21 · Sprint 3 |
| Affects | AI-053 · P-38 (Frontend Team) |
| Decision | Closed (2026-11-05), **interim rule**: Option 2 as a level, not a probability. B4 writes LOW / MEDIUM / HIGH with its driving factors, from a weather factor and a congestion factor, or NULL when the forecast is missing or stale. Thresholds are calibrated on IMF PortWatch and Open-Meteo history for Damietta (2019-01-01 to 2026-10-30) and are interim until our own data allows M4 (data-gated, AI-001). Interim storage: the level is written to the existing column `recommendation_options.delay_risk` as a fixed code (LOW = 0.100, MEDIUM = 0.500, HIGH = 0.900), with no schema change. Full rule in "Decision detail" below. |
| Agreed with | Mostafa Mohamed Rashwan, Leads Council, 2026-11-05. Decided by the Leads Council; the AI Team (owner) is informed. |
| Implementation | `project-ai` AI-053 (not yet implemented). |

<div dir="rtl">

**القصة.** الشاشة المفروض تقول للموظف "الخطة دي احتمال تتأخر 30%". بس إحنا لسه مافيش عندنا تاريخ تأخيرات نتعلم منه. لازم نتفق على قاعدة بسيطة مؤقتة، أو نعرض "مش متقيّم".

</div>

**Topic.** B4 needs a rule to estimate delay probability before any history exists.

**Options:**

1. NULL until a rule is approved.
2. A simple rule from weather margin and port congestion.

**Recommendation.** A simple rule approved in Sprint 1 so B4 is fully delivered. If not approved, it writes NULL and P-38 shows "Not assessed".

**Decision detail.** Option 2, as a level and not a probability. There is no delay history to learn from, so the rule is calibrated on public data for Damietta and is interim until our own operational data allows M4 (data-gated, AI-001).

**Rule (per recommendation, at planning time, over the vessel's window):**

1. **Weather factor W**, from the Open-Meteo forecast for the port:
   - HIGH: max gust > 35 kn, or max wind > 20 kn, or max wave height > 2.0 m
   - MEDIUM: max gust 30–35 kn, or max wave height 1.5–2.0 m
   - LOW: otherwise

   These are forecast-model screening levels, NOT safety limits. When the `safety_constraints` defaults exist (DEC-30 TR-10), headroom to those limits is added as an extra HIGH/MEDIUM condition.
2. **Congestion factor C** = expected arrivals in the 24 h around the ETA ÷ the median daily arrivals of the last 28 days:
   - MEDIUM: ratio ≥ 1.3
   - HIGH: ratio ≥ 1.6

   A ratio is used so the rule is scale-free (PortWatch undercounts versus the port authority, and the live system uses its own counts).
3. **Post-storm backlog.** If the window starts 1–3 days after a day where W was HIGH, C goes up one level (capped at HIGH).
4. **Result** = max(W, C). The rationale names the factor(s) that set the level.
5. **NULL** when the forecast is missing or older than `part1_stored_data_max_age_hours` (48).
6. Every result carries flag `rules_unvalidated` until the rule is validated.
7. **Storage (interim).** The level is written to the existing column `recommendation_options.delay_risk` as a fixed code: LOW = 0.100, MEDIUM = 0.500, HIGH = 0.900. These are level codes, NOT probabilities. Conditions:
   - (a) P-38 and every other screen show the level only, never the number (< 0.34 LOW, < 0.67 MEDIUM, otherwise HIGH);
   - (b) each recommendation records the rule version in `solver_run_model_versions`, so Phase 1 codes can be told apart from M4's calibrated probabilities later;
   - (c) Part 3 evaluates Phase 1 values as levels only, with no probability metrics (for example Brier score) on them;
   - (d) when M4 is promoted, the same column carries its probability and the codes stop.

Weekday and month are not inputs: the weekday effect is small (Sunday ≈ 7 % lower) and seasonality is already captured by the forecast.

**Evidence (Damietta, PortWatch port274 / EG DAM, 2,860 days, no gaps):**

- Daily calls rose from ≈5 (2019–2022) to ≈7 (2023–2026). 2023+ percentiles: median 7, P75 9, P90 11, P95 12 → ratio cut-offs 9/7 ≈ 1.3 and 11/7 ≈ 1.6.
- Busiest months May–June (≈8/day), quietest December (5.7).
- Calls relative to the surrounding 29-day median, by weather:

  | Weather | Calls vs normal | Days with 0–1 calls |
  | --- | --- | --- |
  | gust ≤ 30 kn and wave ≤ 1.5 m | normal | 2–3 % |
  | gust 30–35 kn or wave 1.5–2 m | −15 % | 7–10 % |
  | gust 35–40 kn | −37 % | 18 % |
  | gust > 40 kn, wind > 20 kn or wave > 2 m | −41 % to −49 % | 25–40 % |

- Rough days (W = HIGH) are 3.9 % of days, ≈3 a month Jan–Mar, ≈0 Jun–Oct; 80 episodes, 57 of them one day long.
- Day 2 and day 3 after an episode: +11 % and +17 % above normal (backlog).
- Same rough days at neighbouring ports: Alexandria 0.56, El Dekheila 0.47, Port Said 0.80 of normal → regional weather effect.

**Limitations:**

- PortWatch is an AIS estimate and reads lower than the port authority bulletin (4 checked days: bulletin 9–15 arrivals, PortWatch 3–12); only relative patterns are used.
- ERA5 reanalysis smooths peaks (max wind never above 25 kn in 8 years); thresholds are in model units and must be applied to Open-Meteo forecast values, not anemometer readings.
- Fewer calls is a proxy for slow-down or closure, not a measured delay.

**Open items (follow-ups; they don't reopen the decision):**

1. Frontend: P-38 shows the level, never the `delay_risk` number (condition a). Column: `recommendation_options.delay_risk` `decimal(4,3)`, CHECK `chk_ro_values` 0–1 (`schema.sql` lines 1149–1178), unchanged.
2. AI-053 implements the rule with the thresholds in a data file (like `part2/tug_rules.json`, status `PROPOSED`), not in code.
3. Recalibrate the cut-offs from our own operational data once available; M4 replaces the rule only after beating it (AI-001, DEC-30 TR-05).
4. P-38 shows "Not assessed" when the level is NULL (Frontend).
5. Open-Meteo free tier is non-commercial only; the commercial licence is DEC-26.
6. Record every input (W values, C ratio, post-storm flag) with each recommendation so M4 has features from day one.

**References:**

- IMF PortWatch Daily_Ports_Data (ArcGIS FeatureServer), port274.
- Open-Meteo Historical (ERA5) and Marine archive APIs, Damietta (31.46, 31.76), offshore wave point (31.53, 31.76). Weather data by Open-Meteo.com (CC BY 4.0).
- Data script: `research/fetch_damietta_history.py` (copy with the retry fix).

### DEC-22 · Financial-impact data in ranking

| | |
| --- | --- |
| Source | OD-06 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-22 · Sprint 4 |
| Affects | AI-055 · AI-057 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الترتيب المطلوب للاختيارات بالوقت الأول وبعدين بالتكلفة المالية. بس مفيش أي داتا عن تكلفة انتظار السفينة أو تشغيل الرصيف، فمش هنعرف نرتب بالفلوس.

</div>

**Topic.** The documented order is time first, then financial impact, but there is no cost data.

**Options:**

1. Time-only ranking until a cost model is approved.
2. An estimated cost per waiting hour.

**Recommendation.** Option 1.

### DEC-23 · Objective terms, weights and number of options

| | |
| --- | --- |
| Source | OD-07 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-23 · Sprint 1 |
| Affects | AI-009 · AI-055 · AI-057 |
| Decision | Closed (2026-10-27): objective terms `WAITING_TIME` and `RESOURCE_COST`, equal weights (1.0 / 1.0) stored as `port_settings` keys `objective_weight_waiting_time` and `objective_weight_resource`; each term normalised to [0, 1] per request before weighting (scaled ×1000 for CP-SAT). 1 to 3 options per request: options 2 and 3 only within `solver_option_equivalence_pct` (10) of option 1. Full text in CT-10 and CT-18. |

<div dir="rtl">

**القصة.** الـ solver محتاج يعرف "أحسن خطة" يعني إيه: أقل انتظار للسفن؟ ولا أعلى استغلال للأرصفة؟ ولا الاتنين؟ وبأي نسبة؟ وكمان يطلع للموظف كام اختيار؟

</div>

**Topic.** CP-SAT needs a clear objective.

**Options:**

1. Codes for waiting time and resource utilisation, and 3 options per request.
2. Lexicographic: time, then utilisation.

**Recommendation.** Option 1 with initial weights in the seed data (AI-009), adjustable later.

### DEC-24 · Part 1 settings: horizon, time step, minimum window, slot

| | |
| --- | --- |
| Source | OD-09 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-24 · Sprint 4 |
| Affects | AI-047 · AI-048 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ AI بيدوّر على نوافذ دخول آمنة. بيدوّر لقدّام قد إيه؟ بيفحص كل كام دقيقة؟ وأقل نافذة مقبولة طولها قد إيه؟ من غير الأرقام دي الحساب مش هيبدأ.

</div>

**Topic.** The window computation needs fixed values set by the Marine Safety Officer and staff.

**Options:**

1. Horizon 72 hours, step 30 minutes, minimum window 60 minutes, demand slot 60 minutes (proposed).

**Recommendation.** Approve the proposed values as `port_settings` keys, changeable later without code.

### DEC-25 · Uncertainty margin and window confidence

| | |
| --- | --- |
| Source | OD-11 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-25 · Sprint 3 |
| Affects | AI-044 · AI-048 |
| Decision | Closed (2026-11-05): Option 1. The MVP applies no uncertainty margin: A4 checks forecast values against the `safety_constraints` thresholds as they are, and every window's confidence (`feasible_windows.confidence`) is written as NULL. A6 stays out of scope (AI-001). Full text in "Decision detail" below. |
| Agreed with | Mostafa Mohamed Rashwan, Leads Council, 2026-11-05. Decided by the Leads Council; the AI Team (owner) is informed. |
| Implementation | `project-ai` AI-044 (no margin term in the threshold check) and AI-048 (window confidence written as NULL) (not yet implemented). |

<div dir="rtl">

**القصة.** التوقعات الجوية مش مضمونة 100%. المفروض نسيب هامش أمان، ونعرض للموظف "واثقين من النافذة دي بنسبة كذا". بس حساب الهامش ده اتأجل لـ future work، فلازم نقرر نعرض إيه دلوقتي.

</div>

**Topic.** A6 (margin) is future work, so MVP behaviour must be defined.

**Options:**

1. Zero margin and confidence = NULL.

**Recommendation.** This option. P-37 shows no confidence value.

**Decision detail.** Option 1, recorded as already settled by AI-001 (Closed), which lists A6 as out of scope and states that the MVP uses zero margin and `confidence` = NULL.

1. **No margin.** A6 is future work, so there is no model to compute a margin. A4 compares forecast values directly with the `safety_constraints` thresholds.
2. **Safety rests on the thresholds.** With zero margin, the `safety_constraints` defaults must be conservative. A separate fixed margin in `port_settings` is not added: it would duplicate tightening the thresholds, which the Marine Safety Officer owns (DEC-30 TR-10), and give two sources for the same safety limit.
3. **Confidence NULL means "not assessed".** It is never stored or shown as 0 % or 100 %.
4. **Not the DEC-21 headroom.** DEC-21 uses headroom to the safety limits for the delay-risk level only. That is not an A6 margin and does not change any window.

**Open items (follow-ups; they don't reopen the decision):**

1. Frontend: P-37 shows no confidence value; when it is NULL the field is hidden, never shown as "0%".
2. When the Marine Safety Officer provides the TR-10 values (DEC-30, CT-25), he is told that no margin is added on top of them, so the values must already be conservative.
3. Building A6 later needs a new decision; it does not reopen this one.

**References:**

- AI-001 · AI scope and component inventory (this file): A6 out of scope, zero margin, `confidence` NULL.
- DEC-30 TR-10 (`safety_constraints` defaults) and TR-22 (this decision).
- DEC-21 (delay-risk headroom, separate from A6).
- Schema: `contracts/db/schema.sql` in PortHub and `docs/ref/db/schema.sql` in project-ai (same lines), lines 686–697 (`feasible_windows.confidence`, line 691, `decimal(4,3) DEFAULT NULL`, nullable; `chk_fw_values` on line 696 allows NULL).

### DEC-26 · Weather and marine providers

| | |
| --- | --- |
| Source | OD-12 · RSK-04 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-26 · Sprint 4 |
| Affects | AI-020 · AI-040 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Part 1 محتاج توقعات رياح وأمواج ورؤية لميناء دمياط. لسه ماختارناش هنجيبها منين، ولا اتأكدنا إن الرخصة تسمح نستخدمها، ولا لو المصدر الأساسي وقع هنعمل إيه.

</div>

**Topic.** A primary and a fallback are needed covering every A4 variable (wind, visibility, waves, current, sea level).

**Options:**

1. Open-Meteo (Forecast + Marine) as primary, and a second provider as fallback after comparing licence and coverage.

**Recommendation.** Compare 2 or 3 providers on variables, licence and coverage for Damietta, and pick two in Sprint 1.

### DEC-27 · Tidal constants source, datum and reference

| | |
| --- | --- |
| Source | OD-13 · RSK-05 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-27 · Sprint 4 |
| Affects | AI-021 · AI-042 · P2-F5 |
| Decision | ______ |

<div dir="rtl">

**القصة.** عشان نحسب المد لازم ثوابت فلكية خاصة بالميناء. ولازم عمق الأرصفة والمد يتقاسوا من نفس المستوى المرجعي. لو المستويين مختلفين بمتر، ممكن نقول إن السفينة تعدّي وهي فعلًا هتلمس القاع.

</div>

**Topic.** A2 needs published constants for the reference port and a single datum shared with the depths.

**Options:**

1. Published constants for Damietta on LAT.

**Recommendation.** This option, with a published tide table as the validation reference and an error tolerance set in DEC-30.

### DEC-28 · Definition of moves

| | |
| --- | --- |
| Source | OD-14 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-28 · Sprint 3 |
| Affects | AI-052 |
| Decision | Closed (2026-11-05): Option 1, made precise. Moves = discharge + loading, one move per container. Discharge = containers in the request's ACTIVE BAPLIE whose port of discharge is this port's UN/LOCODE. Loading = an optional request field; when empty it is set equal to discharge, with flag `loading_estimated`. A container vessel is solved only once its BAPLIE is ACTIVE; if a request still reaches the solver without one, it is left out with reason `MISSING_MOVES` as a safety net, and moves are never guessed. Full rule in "Decision detail" below. |
| Agreed with | Mostafa Mohamed Rashwan, Leads Council, 2026-11-05. Decided by the Leads Council; the AI Team (owner) is informed. |
| Implementation | `project-ai` AI-052 (not yet implemented). |

<div dir="rtl">

**القصة.** زمن خدمة السفينة بيتحسب من عدد حركات الونش. ملف الـ BAPLIE فيه كل الحاويات اللي على المركب، وكل حاوية مكتوب عليها هتنزل في أنهي ميناء، فنقدر نعدّ اللي نازل عندنا. بس الحاويات اللي هتطلع على المركب مش في الملف خالص. لازم نتفق هنعرف العدد الكلي إزاي.

</div>

**Topic.** Service time (B3) needs the number of moves.

**Options:**

1. Discharge from the BAPLIE + loading count entered or estimated.

**Recommendation.** This option. Loading count is an optional request field; if empty it is estimated equal to discharge.

**Decision detail.** Option 1, made precise. The BAPLIE lists every container on board, each with its port of discharge, so discharge is counted from it; loading is not in the BAPLIE.

**Rule (per berthing request of a container vessel, `vessel_types.code` = `CONTAINER`):**

1. **Discharge** = the number of `container_manifest_entries` rows of the request's ACTIVE BAPLIE (`baplie_files.status` = `ACTIVE`) whose `port_of_discharge` equals the port's UN/LOCODE (`port_profiles.port_code`). The code is read from the port's data, never hard-coded. Transshipment containers discharged here count; containers staying on board do not. If the port's UN/LOCODE (`port_profiles.port_code`) is not set, the job fails with `CONFIGURATION_ERROR` (CT-08 §7); discharge is never counted as zero.
2. **Loading** = the request's optional loading count when set. When empty, loading = discharge, with flag `loading_estimated`.
3. **Moves** = discharge + loading. One container is one move. Twin and tandem lifts are not credited, so service time errs long (conservative, as in DEC-20).
4. **Out of the MVP:** restows, hatch-cover moves, and twin or tandem lift credit.
5. **Precondition and safety net.** A container vessel's request is solved only once its BAPLIE is ACTIVE; the Backend does not enqueue the solve before that (planning flow agreed by the Leads Council; CT-10 does not yet state it, see open item 2). If a request still reaches the solver without an ACTIVE BAPLIE (for example, the BAPLIE was withdrawn or quarantined after the solve was enqueued), moves are NULL and the request is left out with reason `MISSING_MOVES`. Moves are never guessed.
6. **Vessels other than container vessels** have no BAPLIE. Rule 5 does not apply to them; their B3 basis is not set by this decision (open item 4).
7. Each result records discharge, loading and `loading_estimated`, so M2 (B3 Phase 2) has these features from day one.

**Open items (follow-ups; they don't reopen the decision):**

1. Backend (CT-17): add the optional loading-count field to the berthing request (`berthing_requests` has none today).
2. Backend (CT-10): today `NEW_REQUEST` is enqueued when Part 1 finishes with `WINDOWS_FOUND`, without checking the BAPLIE. For a container vessel it must wait for the later of `WINDOWS_FOUND` and the BAPLIE becoming ACTIVE. Until this is done, such requests reach the solver early, are left out with `MISSING_MOVES`, and nothing re-triggers them.
3. CT-10: add `MISSING_MOVES` as a new value. CT-10 has no per-request reason list for a request that is left out (per-request `outcome` is `SOLVED`, `FIFO_FALLBACK` or `NO_FEASIBLE_PLAN`), so Backend and AI Team choose where it goes.
4. AI Team: the B3 basis for vessels other than container vessels.
5. Terminal operations: confirm that loading ≈ discharge is a fair default for Damietta.
6. Backend / seed (CT-18): set `port_profiles.port_code` for Damietta (`EGDAM`); it is nullable and empty in the reference seed.
7. AI-030: confirm the port-of-discharge qualifier against the SMDG BAPLIE message implementation guides (2.2.1 and 3.1.1), not the samples. The corpus file `01-valid-221.edi` and the CT-12 example put the discharge port on `LOC+12` and `CNSHA` on `LOC+11`, which may not match the guide; if they are wrong, correct them (CT-12).

**References:**

- DEC-17 and CT-12 (BAPLIE parse, ACTIVE / QUARANTINED / REJECTED) · DEC-50 (correction and withdraw) · CT-10 (PortHub `contracts/ATLANTECH_Contracts.md` lines 489–497 solve rules, 499–537 `result_detail` and per-request `outcome`) · DEC-20 (conservative rounding).
- Schema (PortHub `contracts/db/schema.sql`): `baplie_files` (lines 65–96: `berthing_request_id` line 68, `status` line 74); `container_manifest_entries` (lines 367–398: `port_of_discharge` line 384); `port_profiles` (lines 1066–1083: `port_code` line 1069, nullable, filled from SaaS); `berthing_requests` (lines 195–235, no loading-count field); `vessel_types` (lines 1828–1834; seed `contracts/db/reference-seed.json` line 180, code `CONTAINER`). Parser: no BAPLIE parser code exists yet (`edi/` holds only a README; AI-030 is not implemented); the CT-12 example (`contracts/ATLANTECH_Contracts.md` lines 807–808) and the corpus file `contracts/ai/baplie-corpus/01-valid-221.edi` (lines 10–11) show the load port as `LOC+11` and the discharge port as `LOC+12`, to be confirmed in AI-030. Planning gate: not documented; CT-10 sends `NEW_REQUEST` when Part 1 finishes with `WINDOWS_FOUND` and does not mention the BAPLIE, while the BAPLIE gate in CT-11 (lines 572 and 630) applies to the yard job only.

### DEC-29 · Yard recommendation method, objective and confidence

| | |
| --- | --- |
| Source | OD-15 · RSK-09 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-29 · Sprint 3 |
| Affects | AI-065 · AI-066 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ AI المفروض يقترح الحاويات تتحط فين في الساحة، بس محدش حدد يعمل ده إزاي. هل بقواعد بسيطة زي "المبرّد جنب الكهربا"؟ ولا بموديل optimization؟ وإيه اللي يخلّينا "واثقين" في الاقتراح؟

</div>

**Topic.** The B8 method is not defined.

**Options:**

1. Option A: rule-based heuristic (group by movement, type and weight, then compatible blocks).
2. Option B: CP-SAT assignment (needs an objective that is not documented).

**Recommendation.** Option A; confidence = share of containers placed in a zone of their preferred type.

### DEC-30 · Numeric thresholds register

| | |
| --- | --- |
| Source | OD-16 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-30 · Sprint 2 |
| Affects | AI-008 · AI-072 |
| Decision | ______ |
| Proposed change | 2026-10-31 · AI-008 · Adopt the thresholds register below as the DEC-30 decision: 6 `FILLED`, 13 `DEFERRED` (each with an owner and the task that needs it), 1 `OUT OF MVP SCOPE` and 7 `REFERENCE` rows. A value becomes `AGREED` only when this change is approved · Reason: there is no single register yet. CT-18 waits on DEC-30 for `drift_psi_threshold`, `drift_mae_threshold` and the `safety_constraints` defaults, and AI-016 waits on it for the coverage gate · Evidence: the register below; `docs/tasks/status/AI-008.md`. Every `FILLED` value is traced to a non-NFR source; NFR figures and IDs are not used as sources (user ruling, 2026-10-31) · Impact: AI-016 · AI-021 · AI-024 · AI-044 · AI-061 · AI-071 · AI-072 · AI-090 · AI-101 to AI-103 · AI-104; CT-18 seed (Backend Team); CT-25 (QA Team) · Awaiting: AI Team owner, with approval by the whole team (option 1) |

<div dir="rtl">

**القصة.** أرقام كتير الشغل محتاجها ومحدش حددها. إمتى نقول إن الموديل بدأ يبوظ (drift)؟ وكام سم خطأ مسموح في حساب المد؟ من غيرها مش هنعرف نقول إن أي حاجة نجحت أو فشلت.

</div>

**Topic.** Drift, deviation significance, data sufficiency, tide tolerance, BAPLIE size classes, coverage.

**Options:**

1. One register owned by the AI Team and approved by the whole team.

**Recommendation.** This option: inputs prepared (QA-AI1), approved in Sprint 1, final write-up in AI-008.

**Proposed thresholds register (AI-008, 2026-10-31; not approved).** This register is part of the Proposed change above.
- **Labels:** `TR-xx` labels are local to this register. They are not official IDs.
- **Sources:** NFR figures and IDs are not used as sources.
- **Statuses:**
  - `FILLED`: a non-NFR document states the value.
  - `DEFERRED`: no agreed value yet; the owner and the task that needs it are named.
  - `OUT OF MVP SCOPE`: excluded by a decision.
  - `REFERENCE`: defined by another decision or contract, not by this register.
- **Approval:** values become `AGREED` only when DEC-30 is approved.

| TR | Threshold | Status | Value | Source | Owner | Needed by |
| --- | --- | --- | --- | --- | --- | --- |
| TR-01 | Drift PSI threshold (`drift_psi_threshold`) | DEFERRED | — | CT-18 §4 (⟨AI⟩ value) | AI Team | AI-072 · CT-18 seed |
| TR-02 | Drift rolling-MAE threshold (`drift_mae_threshold`) | DEFERRED | — | CT-18 §4 (⟨AI⟩ value); one key covers M2, M3 and M4, which have different units | AI Team | AI-072 · CT-18 seed |
| TR-03 | Rolling-MAE window length | DEFERRED | — | Arch §9.1 (C2) | AI Team | AI-072 |
| TR-04 | Data sufficiency per model (M2, M3, M4, C4) | DEFERRED | — | Arch §9.5 gives an estimate (about 9,500 calls a year, "several months"), not a threshold | AI Team | AI-024 (records the criteria here) |
| TR-05 | Phase 2 promotion margin over the Phase 1 baseline (M2, M3, M4) | DEFERRED | — | Arch §10; the meaning of "MAE" for the M4 classifier is open (OD-16) | AI Team | AI-101 · AI-102 · AI-103 |
| TR-06 | C3 Champion/Challenger guard | FILLED | Challenger promoted only if not worse on both MAE and override rate, on held-out time-based data; no numeric margin | Arch §9.3 · UML AD-16 P6/D3 | AI Team | AI-104 |
| TR-07 | Tide prediction tolerance and test period | DEFERRED | — | DEC-27 (tolerance set in DEC-30) | AI Team, with the DEC-27 source | AI-021 |
| TR-08 | BAPLIE size classes and parse-time targets | OUT OF MVP SCOPE | — | Out of MVP scope – per DEC-17 Decision row and CT-12 v1.0 | — | — |
| TR-09 | Test coverage gate | DEFERRED | — | AI-016 acceptance criterion "Coverage gate enforced at the agreed value" · AI-016 task decision item (8) | AI Team | AI-016 (`fail_under`) |
| TR-10 | Port-wide `safety_constraints` defaults (wind, gust, visibility, wave, minimum UKC and others) | DEFERRED | — | CT-18 §1 and §7 | AI Team (seed); input from the Marine Safety Officer through CT-25 (QA Team) | AI-044 · CT-18 seed |
| TR-11 | Window-accuracy definition (C1) | DEFERRED | — | AI-071 (OD-16) | AI Team | AI-071 |
| TR-12 | Stored environmental data freshness | FILLED | 48 h, and the data must cover the assessment horizon | CT-18 v1.0 `part1_stored_data_max_age_hours` · DEC-12 (Closed) · Arch §7.2 · UML 2.10 | AI Team | AI-025 · AI-041 |
| TR-13a | CP-SAT solver time limit | FILLED | 10 s (configurable default; min 1, max 120) | CT-18 v1.0 `solver_time_limit_seconds` · CT-10 | AI Team | AI-055 |
| TR-13b | Total Part 2 pipeline time | DEFERRED | — | No non-NFR source | AI Team | AI-061 |
| TR-14a | Recommendation latency percentiles under concurrency | DEFERRED | — | No non-NFR source | AI Team | AI-061 |
| TR-14b | Parallel solves | DEFERRED | — | No non-NFR source | AI Team | AI-061 |
| TR-15 | Option equivalence | FILLED | 10 % of option 1 | DEC-23 (Closed) · CT-18 `solver_option_equivalence_pct` · CT-10 | AI Team | AI-055 |
| TR-16 | Validation timeout and result TTL | FILLED | 15 s / 600 s | CT-13 · CT-18 `validation_timeout_seconds`, `validation_result_ttl_seconds` | AI Team | AI-060 · AI-067 |
| TR-17 | Part 1 retries | FILLED | 3 | DEC-04 (Closed) · CT-08 v1.0 · CT-18 `part1_max_retries` | AI Team | AI-048 |
| TR-18 | Worker restart time and availability | DEFERRED | — | No non-NFR source; CT-16 raises an alert when a worker is DOWN for more than 2 minutes | AI Team; consulted: Backend Team | AI-090 |
| TR-19 | Evaluation key question (not a threshold) | REFERENCE | — | Master_Context §4 (Port Authority daily bulletin): whether the port can handle more than about 26 vessels a day, assessed experimentally, not a pass/fail limit | AI Team | AI-084 |
| TR-20 | Deviation significance per operation type (UML AD-16 D1) | REFERENCE | — | DEC-09 (Open, Sprint 6); a Port Admin setting | Backend Team | — |
| TR-21 | Part 1 horizon, time step, minimum window, demand slot, gap tolerance | REFERENCE | — | DEC-24 (Open) | AI Team | — |
| TR-22 | Uncertainty margin and window confidence | REFERENCE | — | DEC-25 (Closed 2026-11-05; the MVP uses zero margin and `confidence` NULL) | AI Team | — |
| TR-23 | Tug count per vessel | REFERENCE | — | DEC-20 (Closed, interim tables) | AI Team | — |
| TR-24 | `run_stale_after_seconds` | REFERENCE | — | CT-18 §4 and §7 (the AI Team supplies it with its calculation) | AI Team | — |
| TR-25 | Clock-skew suspect rule | REFERENCE | — | `ClassDiagramContext.md` OI-06 | Backend Team | — |

### DEC-31 · Part 3 scheduling host

| | |
| --- | --- |
| Source | OD-17 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-31 · Sprint 6 |
| Affects | AI-073 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Part 3 بيقيّم أداء الـ AI بشكل دوري، بس مفيش حد مسؤول يشغّله، ومفيش queue خاصة بيه. لازم نحدد مين اللي بيقول له "يلا اشتغل".

</div>

**Topic.** There is no `queue:part3`.

**Options:**

1. A scheduler inside the Part 3 worker.
2. The Laravel scheduler enqueues (needs a new queue).

**Recommendation.** Option 1.

### DEC-32 · Availability semantics for pilots and tug masters

| | |
| --- | --- |
| Source | OD-19 |
| Owner | AI Team |
| Status | Closed |
| Closing task | DEC-32 · Sprint 3 |
| Affects | AI-050 · P5-M1 |
| Decision | Closed (2026-11-05): Option 1, made precise. One definition of "available" for pilots and tugs, applied by both the AI (AI-050) and the Backend (P5-M1). A pilot or tug is busy when it is assigned in a confirmed plan, or proposed in option 1 of a `PENDING_REVIEW` or `MODIFIED_BY_STAFF` recommendation, over an overlapping operation interval. Only option 1 holds resources; confirming option 2 or 3 triggers a Backend re-check that refuses the confirmation on a conflict. Until the schema stores an operation interval per pilot and tug assignment, the option or plan window is used (it over-reserves). Full rule in "Decision detail" below. |
| Agreed with | Mostafa Mohamed Rashwan, Leads Council, 2026-11-05. Decided by the Leads Council; the AI Team (owner) is informed. |
| Implementation | `project-ai` AI-050 (not yet implemented). Backend P5-M1 (the re-check and pilot or tug replacement). |

<div dir="rtl">

**القصة.** المرشد ده "متاح"؟ هو في ورديته، بس اتقترح لسفينة تانية في نفس الوقت ولسه محدش أكد. لو الـ AI والـ Backend عرّفوا "متاح" بشكلين مختلفين، هنحجز نفس المرشد لسفينتين.

</div>

**Topic.** B2 and B5 need a definition of "available".

**Options:**

1. A pilot is on shift and not proposed or assigned in an overlapping window. A tug is available when its status is available and its master is on shift.

**Recommendation.** This option.

**Decision detail.** Option 1, made precise so the AI and the Backend apply the same test.

**Rule (for an operation interval [start, end) of a pilotage or towage job):**

1. **Pilot available** when all hold:
   - (a) the user is active (`users.is_active`) and the active role is Pilot (`user_role_assignments.role` = `MARINE_PILOT`, `active_to` NULL; DEC-36);
   - (b) a shift (`pilot_schedules`, with the times of its `port_shifts` row) covers the whole interval; a job that crosses a shift change is not available;
   - (c) the pilot is not busy (rule 3).
2. **Tug available** when all hold:
   - (a) its status (`tugboats.status`) is not `MAINTENANCE` or `INACTIVE`;
   - (b) its tug master (`tug_master_profiles.assigned_tugboat_id`) is available by rule 1 for the same interval, using `tug_master_schedules` for the shift and the active role `TUG_MASTER`;
   - (c) the tug is not busy (rule 3).

   `BUSY` is a current-state flag set by the Tug Master; it is not used here. Busyness comes only from overlap (rule 3).
3. **Busy.** The pilot or tug appears, with an overlapping operation interval, in:
   - (a) a confirmed operational plan (`operational_plans.status` = `CONFIRMED`); or
   - (b) option 1 of a recommendation whose status is `PENDING_REVIEW` or `MODIFIED_BY_STAFF` (for `MODIFIED_BY_STAFF`, the assignment as modified).

   `INVALIDATED`, `REPLACED` and `REJECTED` recommendations, and options 2 and 3, hold nothing.
4. **Overlap** is measured on the operation interval of the assignment, not on the vessel's berth stay. Intervals are half-open, so back-to-back jobs do not overlap. **Interim source:** the schema does not yet store a separate operation interval per assignment, so the interval used is:
   - for the pilot and tugs of an option, `recommendation_options.planned_start` and `planned_end`;
   - for a confirmed plan, `plan_components.planned_start` and `planned_end` of its `PILOT` or `TUG` row (pilot: `assigned_user_id`; tug: `tugboat_id`).

   This interim interval is longer than the real job, so it over-reserves: it never double-books, but fewer pilots and tugs look free.
5. **Same run.** Requests solved in the same run do not hold resources against each other: they are variables of the same solve (DEC-06). The previous `PENDING_REVIEW` or `MODIFIED_BY_STAFF` recommendation of a request in the run holds nothing either, since it becomes `REPLACED`.
6. **Confirming option 2 or 3.** The Backend re-checks the option's pilot and tugs with this rule, excluding the same recommendation's option 1, in the same step as the window re-check (DEC-03). On a conflict the confirmation is refused and names the busy resource; the user picks another option or requests regeneration (MANUAL). There is no override: a double-booked pilot or tug cannot be executed.
7. **Replacing a pilot or tug** (P5-M1) uses the same rule.
8. **One definition.** AI-050 and P5-M1 implement this text and run the same test vectors.

**Open items (follow-ups; they don't reopen the decision):**

1. Backend: the re-check on confirming option 2 or 3, and a stable error code for the refusal in `contracts/error-codes.md` (DEC-57).
2. Backend (CT-17): store an operation interval per pilot and tug assignment, on recommendation options and on plans. Rule 4 then uses it, without reopening this decision.
3. AI Team: until item 2 is done, watch for solves that fail on pilot or tug shortage caused by the over-reservation in rule 4.
4. AI Team: write the shared test vectors (overlap edges, shift change, same-run requests, option 2/3 conflict); the Backend runs them in P5-M1.
5. CT-10: add that a pending recommendation holds capacity through its option 1 only (rule 3). Today it says only that "every other pending recommendation is fixed and treated as occupied capacity".

**References:**

- DEC-06 (fixed and variable requests per solve) · DEC-03 (re-check in Laravel) · DEC-36 (one active role) · CT-10 (PortHub `contracts/ATLANTECH_Contracts.md`: line 481, tug master shift change sent as `TUG` (DEC-32); line 497, solve scope and REPLACED).
- Schema: `contracts/db/schema.sql` in PortHub and `docs/ref/db/schema.sql` in project-ai (same lines). `users.is_active` 1816 · `user_role_assignments.role` 1791, `active_to` 1795 · `pilot_schedules` 1011–1025 · `tug_master_schedules` 1733–1747 · `port_shifts.start_time` and `end_time` 1109–1110 · `tug_master_profiles.assigned_tugboat_id` 1722 · `tugboats.status` 1758 · `recommendations.status` 1265 · `recommendation_options.pilot_user_id` 1157, `planned_start` and `planned_end` 1155–1156 · `recommendation_option_tugs` 1137–1144 (no interval) · `operational_plans.status` 923 · `plan_components.planned_start` and `planned_end` 1040–1041.

### DEC-33 · Manual-planning baseline

| | |
| --- | --- |
| Source | OD-20 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-33 · Sprint 7 |
| Affects | AI-084 |
| Decision | ______ |
| Proposed change | 2026-10-31 · AI-008 · Draft manual-planning baseline procedure (option 1): (1) **Scenarios:** agreed replay scenarios built from the reference-port data (CT-25, AI-022), each value labelled published or synthetic. (2) **Manual plan:** each scenario is planned with documented manual planning rules agreed with a domain expert. **These rules are still pending** (QA-AI1). (3) **AI and FIFO:** the same scenarios run through the AI recommendation and the FIFO fallback. (4) **Indicators:** the three plans are compared on the six Master_Context §4 indicators: conflicts detected and resolved; resource utilisation (berths, tugs, pilots, equipment); avoidable idle time; estimated operational cost; feasibility and quality of recommendations; downstream effect on re-handling where demonstrated. (5) **Roles:** the QA Team prepares the procedure and scenarios, a domain expert agrees the manual rules, and the AI Team runs the comparison in AI-084 · Reason: AI-008 acceptance criterion "Manual baseline procedure documented"; AI-084 needs a defined baseline · Evidence: Master_Context §4 · Proposal §12 (Table 8) · DEC-33 option 1 · AI-084 · Impact: AI-062 · AI-084; QA Team (QA-AI1, CT-25) · Awaiting: AI Team owner; QA Team and a domain expert for the manual rules |

<div dir="rtl">

**القصة.** عشان نقول إن الـ AI أحسن من التخطيط اليدوي، لازم نعرف التخطيط اليدوي بيتعمل إزاي بالظبط ونقيسه على نفس السيناريوهات. من غير كده المقارنة مالهاش معنى.

</div>

**Topic.** Evaluating the AI needs a comparison with manual planning.

**Options:**

1. Replay scenarios with documented manual rules agreed with an expert.

**Recommendation.** This option; the QA Team prepares the procedure (QA-AI1).

### DEC-34 · Building A4 rules on synthetic data

| | |
| --- | --- |
| Source | Plan decision |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-34 · Sprint 3 |
| Affects | AI-044 · AI-051 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Part 2 (أهم جزء) محتاج قواعد الأمان بتاعة الـ Part 1 عشان يبدأ. لو استنينا الـ Part 1 يخلص كله بالداتا الحقيقية، الـ Part 2 هيتأخر كذا sprint. الحل إننا نبني القواعد على داتا تجريبية الأول.

</div>

**Topic.** The documented critical path is AI-040 → 041 → 043 → 044, but Part 2 needs AI-044 early.

**Options:**

1. A4 is built and tested on synthetic series; the real surge feed joins later.
2. Wait for the full Part 1 chain.

**Recommendation.** Option 1, so Part 2 starts CP-SAT in Sprint 4.


## Product and screen decisions

### DEC-35 · Sign-in identifier

| | |
| --- | --- |
| Source | Screens P-16/P-52 · FR-AC-01 · FR-AC-09 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-35 · Sprint 1 |
| Affects | P1-C1 · P1-C3 · FE-025 · MB-P52 |
| Decision | Closed (2026-10-28): Option 1. Users sign in with `username` on the web (P-16) and the tablet (P-52); the `users` table has no email column. `username` is unique and stored lowercase; `phone` is contact only and never used for sign-in. P-16 shows a Username field instead of Email. CT-03 and CT-04 use `{ "username", "password" }`. |

<div dir="rtl">

**القصة.** شاشة الدخول على الويب بتطلب email، بس الـ requirements بتقول إن المستخدم بيتعمل بـ username وتليفون ومن غير email خالص. يعني المستخدم مش هيلاقي حاجة يدخل بيها.

</div>

**Topic.** Screens: email on the web, username on the tablet. The FRD creates users with name, username and phone, with no email.

**Options:**

1. Username on web and tablet.
2. Add an email to users and use it on the web.

**Recommendation.** Option 1 because it matches the requirements. P-16 uses username instead of email.

### DEC-36 · One role per user vs role history

| | |
| --- | --- |
| Source | Screens P-24 · P2-E2 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-36 · Sprint 2 |
| Affects | P2-E2 · FE-045 |
| Decision | Closed (2026-10-28): Option 1. A user has one active role at a time. Assigning a new role ends the current one (`active_to` set) and inserts the new row in the same transaction; rows are never deleted, so `user_role_assignments` keeps the full history. Schema: `uq_ura_active` becomes unique on (`user_id`, `active_assignment_key`) so the database refuses a second active role. P-24 shows the active role and the history list. |

<div dir="rtl">

**القصة.** الشاشة بتقول إن كل مستخدم ليه دور واحد، والـ Backend معمول إنه يدّي أدوار وينهيها بتاريخ. لو موظف اتنقل من Tug Officer لـ Pilotage Officer، هل بيبقى معاه الاتنين؟ ولا القديم بينتهي؟

</div>

**Topic.** The screens say one role; the Backend assigns and ends roles with dates.

**Options:**

1. One active role at a time; history kept with `active_to`.

**Recommendation.** This option.

### DEC-37 · "Reject with reason" on P-44 and P-47

| | |
| --- | --- |
| Source | Screens P-44/P-47 · P5-M2 |
| Owner | Backend Team |
| Status | Open |
| Closing task | DEC-37 · Sprint 6 |
| Affects | P5-M2 · FE-067 · FE-070 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الشاشة فيها زرار "رفض بسبب" للمرشد المقترح، بس الـ Backend مفيهوش endpoint للرفض، وفيه تأكيد أو استبدال بس. لو الـ Frontend عمل الزرار، مش هيلاقي حاجة يكلمها.

</div>

**Topic.** The Backend tasks only have confirm or replace.

**Options:**

1. Add reject with a reason (new endpoint and component status).
2. Confirm or replace only.

**Recommendation.** Option 2: replace covers the case and no new status is needed.

### DEC-38 · Where to activate the tide constituent set

| | |
| --- | --- |
| Source | Screens P-59 · P2-F5 |
| Owner | UI/UX Team |
| Status | Open |
| Closing task | DEC-38 · Sprint 3 |
| Affects | P2-F5 · FE-076 |
| Decision | ______ |

<div dir="rtl">

**القصة.** تفعيل ثوابت المد مع فحص المستوى المرجعي محتاج زرار في شاشة. ممكن يبقى عند الـ Marine Safety Officer أو عند الـ Port Admin، ومحدش قرر مين.

</div>

**Topic.** Activation with the datum check can live on P-59 or P-26.

**Options:**

1. P-59 (Marine Safety Officer).
2. P-26 (Port Admin, next to the chart datum).

**Recommendation.** Option 1, since it is the same Backend task (P2-F5) and the same decision owner.

### DEC-39 · CT Supervisor status list

| | |
| --- | --- |
| Source | Screens P-55 · Flutter tasks |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-39 · Sprint 6 |
| Affects | P5-O8 · MB-P55 |
| Decision | Closed (2026-10-31): Option 1. `new_status` is `STARTED` or `DONE` for terminal components too; P-55 labels them In progress and Executed. Full text in CT-07 v1.0. |

<div dir="rtl">

**القصة.** مشرف التيرمنال بيسجل حالة الشغل من التابلت، بس محدش حدد الحالات اللي هيختار منها. هل هي نفس حالات المرشد (بدأ وخلص)؟ ولا حالات خاصة بالتيرمنال؟

</div>

**Topic.** P-55 says the terminal status list needs confirmation.

**Options:**

1. The same task statuses: In progress and Executed.
2. Terminal-specific statuses from `status_types`.

**Recommendation.** Option 1 for the MVP: In progress and Executed on the terminal component.

### DEC-40 · Mobile Acknowledge event type and payload

| | |
| --- | --- |
| Source | Flutter R1 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-40 · Sprint 6 |
| Affects | P5-O3 · MB-P55 · MB-P19 · CT-07 |
| Decision | Closed (2026-10-31): Option 1. `type = "ACKNOWLEDGE"` and `payload = { notification_id }`. A repeat is recognised from the notification state and returns `DUPLICATE`; no new column. Full text in CT-07 v1.0. |

<div dir="rtl">

**القصة.** المرشد بيدوس "استلمت" على الإشعار وهو مش متصل بالنت، فالحدث بيتحفظ على الجهاز ويتبعت بعدين. لو شكل الحدث مش متفق عليه، الـ Backend هيرفضه، والنظام هيفضل يصعّد كأن المرشد ماستلمش.

</div>

**Topic.** Acknowledge goes through the Outbox and needs an agreed event type.

**Options:**

1. `event_type = "ACKNOWLEDGE"` and `payload = {notification_id}`.

**Recommendation.** This option, documented in CT-07.

### DEC-41 · Automatic sync right after saving an event while online

| | |
| --- | --- |
| Source | Flutter F4 (suggested) |
| Owner | Mobile Team |
| Status | Open |
| Closing task | DEC-41 · Sprint 4 |
| Affects | MB-F4A |
| Decision | ______ |

<div dir="rtl">

**القصة.** المرشد داس "بدأت" والنت شغال. هل التحديث يتبعت على طول؟ ولا يستنى لحد ما يدوس زرار sync؟ لو استنى، المكتب هيشوف الحالة متأخرة.

</div>

**Topic.** Should the app sync immediately after saving an event when it is online?

**Options:**

1. Yes, immediate sync.
2. Only on triggers (connection restored, sync button).

**Recommendation.** Option 1 so updates reach the office quickly.

### DEC-42 · Staff pages on the tablet and a provisioning screen

| | |
| --- | --- |
| Source | Screens OQ-9 · A-2 |
| Owner | Leads Council |
| Status | Closed |
| Closing task | DEC-42 · Sprint 2 |
| Affects | — |
| Decision | Closed (2026-11-01): Option 1. Staff pages on the tablet and a provisioning screen are not in the MVP, and no task builds them. Brought by Marwan (Backend lead) for the Leads Council. |

<div dir="rtl">

**القصة.** ملف الشاشات القديم كان فيه سؤال: هل موظفي المكتب يستخدموا التابلت؟ وهل فيه شاشة لتجهيز الأجهزة؟ الحاجتين دول مش موجودين في الـ requirements، ولازم نقفل السؤال عشان محدش يشتغل عليهم.

</div>

**Topic.** They are not in the requirements.

**Options:**

1. Not in the MVP.
2. Add them.

**Recommendation.** Option 1.

### DEC-43 · Recommendation confidence field on P-38

| | |
| --- | --- |
| Source | FE-OQ-11 |
| Owner | AI Team |
| Status | Open |
| Closing task | DEC-43 · Sprint 6 |
| Affects | FE-059 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ Frontend عايز يعرض "درجة الثقة" في التوصية، بس مفيش حقل زي ده في الـ database، والـ AI مش بيحسبه. يا نشيله من الشاشة، يا نضيفه في كل الطبقات.

</div>

**Topic.** There is no stored confidence field for a recommendation.

**Options:**

1. Not shown.
2. Add a field.

**Recommendation.** Option 1: P-38 shows the objective score and rationale only.

### DEC-44 · Storing the clock-skew review note

| | |
| --- | --- |
| Source | FE-OQ-31 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-44 · Sprint 6 |
| Affects | P5-O5 · FE-065 |
| Decision | Closed (2026-10-31): Option 1. The flag is shown with no review note for the MVP. |

<div dir="rtl">

**القصة.** ساعة التابلت كانت غلط، فالحدث وصل بوقت مش منطقي واتعلّم "مشكوك فيه". الموظف عايز يكتب ملاحظة إنه راجعه، بس مفيش مكان يتحفظ فيه الكلام ده.

</div>

**Topic.** P-41 shows a Clock-skew suspect flag; where a review note is stored is unclear.

**Options:**

1. Show the flag only, no note.
2. A note field on `actual_status_updates`.

**Recommendation.** Option 1 for the MVP.

### DEC-45 · Display time zone

| | |
| --- | --- |
| Source | FE-OQ-14 |
| Owner | Frontend Team |
| Status | Open |
| Closing task | DEC-45 · Sprint 1 |
| Affects | FE-006 · MB-F1 |
| Decision | ______ |

<div dir="rtl">

**القصة.** الـ database بتسجل كل حاجة بتوقيت UTC. لو الشاشة عرضت الوقت زي ما هو، الموظف هيشوف السفينة جاية الساعة 7 وهي فعلًا جاية الساعة 10 بتوقيت مصر.

</div>

**Topic.** The database is UTC and shifts are local time.

**Options:**

1. Display in port time from `port_profiles.timezone`.
2. User device time.

**Recommendation.** Option 1 on web and mobile.

### DEC-46 · Supported browsers and viewports

| | |
| --- | --- |
| Source | FE-OQ-23 |
| Owner | Frontend Team |
| Status | Open |
| Closing task | DEC-46 · Sprint 1 |
| Affects | FE-006 · FE-108 |
| Decision | ______ |

<div dir="rtl">

**القصة.** من غير ما نحدد المتصفحات والمقاسات اللي هندعمها، الـ QA مش هيعرف يختبر على إيه، وأي مشكلة على متصفح قديم هتبقى bug ملهاش نهاية.

</div>

**Topic.** The test scope must be defined.

**Options:**

1. Latest two versions of Chrome, Edge and Firefox; desktop from 1280 px and tablet from 768 px.

**Recommendation.** This option.

### DEC-47 · Backend environment for development and testing

| | |
| --- | --- |
| Source | FE-OQ-29 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-47 · Sprint 2 |
| Affects | FE-101 · MB-F4B · QA-01 |
| Decision | Closed (2026-10-29): Option 1 as the target. A shared dev server is updated on every merge to `develop`, and a separate demo on every release; the host and the deployment come with P6-R6 (or earlier if a host becomes available). Until then Frontend, Mobile and QA run the backend from `develop` on their own machine with `docker compose --profile server up -d --build` (app, nginx, MySQL 8.4, Redis 7.4; no local PHP needed; http://localhost:8000). Seed data arrives with P1-B6. Decided by Marwan (Backend lead). |

<div dir="rtl">

**القصة.** الـ Frontend والـ Mobile عايزين يجربوا على API حقيقي، بس الـ Backend شغال على جهازه بس. من غير سيرفر مشترك بيتحدث أول بأول، كل تيم هيختبر على حاجة مختلفة.

</div>

**Topic.** Frontend, Mobile and QA need a server with the latest develop and seed data.

**Options:**

1. A dev server updated on every merge to develop, and a separate demo updated on every release.

**Recommendation.** This option.

### DEC-48 · Field roles on the web

| | |
| --- | --- |
| Source | FE-OQ-12 |
| Owner | Leads Council |
| Status | Closed |
| Closing task | DEC-48 · Sprint 2 |
| Affects | FE-021 |
| Decision | Closed (2026-11-01): Option 1. A pilot, tug master or CT Supervisor who signs in on the web lands on P-20 with a "use the mobile app" message; there is no web version of My Tasks. Brought by Marwan (Backend lead) for the Leads Council. |

<div dir="rtl">

**القصة.** المرشد فتح الموقع من الكمبيوتر وعمل login. مفيش ليه أي شاشة على الويب، فهيشوف إيه؟

</div>

**Topic.** What happens when a pilot, tug master or CT Supervisor signs in on the web.

**Options:**

1. P-20 with a "use the mobile app" message.
2. A web version of My Tasks.

**Recommendation.** Option 1.


## Closed items (for reference)

### DEC-49 · Status and error colours and the icon set

| | |
| --- | --- |
| Source | FE-OQ-21 · FE-OQ-22 |
| Owner | UI/UX Team |
| Status | Closed |
| Closing task | — |
| Affects | FE-015 · FE-018 |
| Decision | Closed. |

<div dir="rtl">

**القصة.** الـ Frontend كان مستني يعرف ألوان الأخطاء والتحذيرات وشكل الأيقونات. الحاجات دي اتعتمدت مع الهوية.

</div>

**Topic.** Colours and button styles are approved.

### DEC-50 · BAPLIE correction and withdraw

| | |
| --- | --- |
| Source | Old screens file vs FRD |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | P3-H5 · P3-H6 · FE-052 |
| Decision | Closed: implemented (P3-H5, P3-H6) and shown on P-31. |

<div dir="rtl">

**القصة.** ملف الشاشات القديم كان بيقول "مفيش تعديل ولا سحب لملف الـ BAPLIE"، والـ requirements بتقول فيه. اتقفلت على حسب الـ requirements.

</div>

**Topic.** The requirements include correction and withdraw.

### DEC-51 · Shared berths

| | |
| --- | --- |
| Source | Old screens file vs P2-F2 |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | P2-F2 · FE-049 |
| Decision | Closed: allowed; P-28 takes one or more terminals. |

<div dir="rtl">

**القصة.** ملف الشاشات القديم كان بيقول "كل رصيف لتيرمنال واحد"، والـ database بتسمح برصيف مشترك. اتقفلت إن الرصيف المشترك مسموح.

</div>

**Topic.** The requirements and the schema allow a shared berth.

### DEC-52 · Boat management (P-61)

| | |
| --- | --- |
| Source | Old screens file |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | — |
| Decision | Closed: future work. |

<div dir="rtl">

**القصة.** كانت فيه شاشة لإدارة الـ boats، بس مفيش جدول ولا requirement ليها. اتنقلت لـ future work.

</div>

**Topic.** There is no boat entity in the requirements or the schema.

### DEC-53 · Screens baseline

| | |
| --- | --- |
| Source | Old Figma |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | UX-W1 to UX-W6 |
| Decision | Closed. |

<div dir="rtl">

**القصة.** تصميمات الـ Figma القديمة كانت مبنية على ملف شاشات قديم. ملف الشاشات الجديد اتعتمد وبقى هو المرجع.

</div>

**Topic.** The new screens file is approved.

### DEC-54 · Licence, SaaS and READ_ONLY in the task files

| | |
| --- | --- |
| Source | D-11 · OD-18 · AIBD-023 |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | — |
| Decision | Closed: future work. |

<div dir="rtl">

**القصة.** ملفات التاسكات كان فيها شغل للرخص والـ READ_ONLY، وده كله اتأجل لـ future work.

</div>

**Topic.** Licence and SaaS are approved as future work, and READ_ONLY behaviour is defined by the team.

### DEC-55 · TIMING and NCT recommendation producers

| | |
| --- | --- |
| Source | OD-23 |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | — |
| Decision | Closed: future work. |

<div dir="rtl">

**القصة.** كان فيه سؤال مين هيعمل توصيات التوقيت والتيرمنال غير الحاويات. الاتنين برا الـ MVP.

</div>

**Topic.** Outside the current scope.

### DEC-56 · SaaS API location and licence signing key

| | |
| --- | --- |
| Source | Backend open inputs |
| Owner | Leads Council |
| Status | Closed |
| Closing task | — |
| Affects | — |
| Decision | Closed: future work. |

<div dir="rtl">

**القصة.** الـ Backend كان سايب سؤالين: الـ SaaS API هيتحط فين، ومفتاح توقيع الرخصة. الاتنين تبع الـ SaaS اللي اتأجل.

</div>

**Topic.** Both belong to SaaS and licensing.

### DEC-57 · Port API status codes, error catalogue and version token

| | |
| --- | --- |
| Source | CT-01 draft and FR-GL-08 vs the code; NFR-CONC-1 vs FR-GL-05 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | CT-01 |
| Affects | FR-GL-08 · NFR-CONC-1 · CT-01 · P1-A2 · P1-C1 · P2-D4 · FE-030 |
| Decision | Closed: (1) the API status set adds 400, 404, 405, 419, 429 and 500 to FR-GL-08's list, with 423 reserved (DEC-54). (2) Stable codes live in `contracts/error-codes.md`. (3) The version token is `updated_at DATETIME(6)`, returned as `version`, not an integer. (4) v1.0 of CT-01 is adopted by the Backend lead without team review. (5) The Backend code is the source of truth for CT-01 and CT-02: Frontend and Mobile review critical changes only, and QA tests without reviewing. |

<div dir="rtl">

**القصة.** الـ FR-GL-08 كان بيعد 7 أكواد بس، والـ API بيرجع أكواد تانية زي 404 و 405 و 419. فاتسجلت القايمة الكاملة، والأكواد الثابتة اتنقلت لملف لوحدها. وكمان الـ NFR-CONC-1 كان بيقول version رقم، والـ FR-GL-05 بيقول `updated_at`، فاتثبت `updated_at` بدقة الـ microseconds.

</div>

**Topic.** The full API status set, one error catalogue file, and one version token.

### DEC-58 · Field task details from the CT-07 Mobile review

| | |
| --- | --- |
| Source | CT-07 review on PortHub PR #27 |
| Owner | Backend Team |
| Status | Closed |
| Closing task | — |
| Affects | P1-C5 · P5-N3 · P5-O1 · P5-O3 · MB-P19 · MB-P54 · MB-P55 · CT-04 · CT-07 |
| Decision | Closed (2026-10-31): (1) Acknowledging any notification of a re-sent task marks all its `SENT` rows `ACKNOWLEDGED`. (2) `notification_logs.status` stays `SENT` · `FAILED` · `ACKNOWLEDGED`; the `ESCALATED` value in the CT-21 example is corrected there. (3) Tasks carry a server-set `system_label` for the P-55 labels (CT-07). (4) `GET /api/v1/system/info` is the connectivity check, with no `GET /system/ping` (CT-04 v1.1). |

<div dir="rtl">

**القصة.** الـ Mobile راجع CT-07 ولقى حاجات مش متحددة: الإشعار بيتبعت أكتر من مرة، فالتأكيد يسري على مين؟ والشاشة بتعرض labels ملهاش مصدر، والـ UML بيعتمد على ping مش موجود في أي عقد.

</div>

**Topic.** The review found gaps between CT-07, CT-21, the P-55 screen and the UML.

**Options:**

1. For the labels: the app works them out from its cache, with a `reason` on `removed`.
2. For the labels: the server sends `system_label`.

**Recommendation.** The Backend recommended Option 1 to save time. The lead chose Option 2, so every client gets the same answer.

### DEC-59 · `port_settings` min and max, and CHAMPION `deployed_at`

| | |
| --- | --- |
| Source | CT-18 · `reference-seed.json` |
| Owner | Backend Team |
| Status | Closed |
| Closing task | DEC-59 · Sprint 2 |
| Affects | P1-B6 · P2-F9 · P2 settings page (P-62) · AI-009 · CT-17 · CT-18 |
| Decision | Closed (2026-11-04): Option 1. `port_settings` has `min_value` and `max_value` (added by P1-B6, backend PR #48), and a `CHAMPION` row in the seed carries `deployed_at`. The AI Team approved CT-18 v1.1 (reported by Marwan). |

<div dir="rtl">

**القصة.** CT-18 بيطلب إن الـ min والـ max يتطبقوا لما الـ setting يتحفظ، بس جدول `port_settings` مفيهوش أعمدة ليهم. وكمان مثال الـ CHAMPION كان ناقصه `deployed_at`، فالصف ماكانش هيدخل الجدول أصلًا.

</div>

**Topic.** CT-18 needs min and max stored and enforced, and the schema has no columns for them. The CT-18 example also breaks the `chk_mlv_champion_deployed` check.

**Options:**

1. Add two columns to `port_settings`.
2. Read min and max from the seed files at runtime.

**Recommendation.** Option 1, chosen by the Backend lead on 2026-10-31, so the app does not depend on contract files in production. It closes when the AI Team approves CT-18 v1.1. A `CHAMPION` row in `seed-spec.json` also carries `deployed_at`.

## AI task decisions

Decisions that belong to one AI backlog task and have no `DEC-` ID. Each is keyed by its task ID; no `DEC-` ID is assigned here. Their text was first drafted on 2026-10-27 as entries DL-001 and DL-002 of the retired decision log and moved here by SETUP-002 unchanged in substance. The one exception: DL-002's per-module queue assignments are left to the AI-010 follow-up on the worker-to-module mapping.

| Task | Item | Owner | Status |
| --- | --- | --- | --- |
| AI-001 | AI scope and component inventory | AI Team | Closed |
| AI-010 | AI code repository location and module structure | AI Team | Closed |
| AI-016 | CI provider, Python tooling and quality gates | AI Team | Proposed |
| AI-014 | Unit, datum and time utilities | AI Team | Proposed |
| AI-003 | AIBD-032 and AIBD-036 outcome for contract v1 | AI Team | Closed |
| AI-012 | Configuration management | AI Team | Proposed |
| AI-011 | Shared worker runtime | AI Team | Proposed |
| AI-013 | Data-access layer | AI Team | Proposed |
| AI-015 | Test harness and scenario generator | AI Team | Proposed |
| AI-050 | Port-state loader: pilot identification, berth availability and holds | AI Team | Proposed |

### AI-001 · AI scope and component inventory

| | |
| --- | --- |
| Source | AI-001 · Master_Context §6 · `ATLANTECH_AI_ARCHITECTURE.md` §4.3, §8.14, §9.5, §14, §15 · plan OD-17, OD-23 (plan not in this repository) |
| Owner | AI Team |
| Status | Closed |
| Affects | AI-009 · AI-010 · AI-065 · AI-073 · DEC-21 · DEC-25 · DEC-29 · DEC-31 · DEC-55 |
| Decision | **MVP:** B1 BAPLIE parser (EDI Parser worker) · A1 data ingestion · A2 astronomical tide · A3 surge residual · A4 threshold feasibility · A5 UKC with Barrass squat · A7 demand aggregation (Phase 1) · B2 constraint filter · B3 service time (Phase 1 formula) · B4 delay risk (Phase 1 rule, or NULL until DEC-21 is closed) · B5 CP-SAT solver with FIFO fallback · B6 template rationale · B7 re-planning · B8 yard placement · C1 outcome evaluation · C2 drift monitor. **DATA-GATED:** M2 service time LightGBM (B3 Phase 2) · M3 demand LightGBM (A7 Phase 2) · M4 delay-risk LightGBM (B4) · C3 guarded retraining · C4 forecast bias correction. A data-gated model replaces its Phase 1 path only after passing its baseline comparison. **OUT-OF-SCOPE (future work):** A6 uncertainty margin (the MVP uses zero margin and `confidence` = NULL, DEC-25) · TIMING terminal recommendations and NCT storage allocation (DEC-55) · Vision module · any cross-port or SaaS model sharing. **B8:** working label for Part 2 yard placement (UML assigns it to Part 2; AI Architecture v3 does not list it, while this repository's `ATLANTECH_AI_ARCHITECTURE.md` §8.14 and §14 do). **Owner of B8: AI Team.** Its method is set by DEC-29; the Part 3 scheduling host by DEC-31. |
| Approval | The AI-001 decision record supplied on 2026-10-27 states `Closed`, approved by AI Lead · Team Lead (roles as named in that record), with the decision date left blank. The repository user (Git user `mostafa`) explicitly approved this inventory, and set the B8 owner to AI Team, on 2026-10-28 (SETUP-002). No other approver names or dates are recorded. |

**Follow-ups (they don't reopen the decision):**

- The supplied record's decision date is blank; add it if the AI Lead or Team Lead provides it.
- DEC-21 (B4 rule) and DEC-25 (A6 and confidence) are Closed (2026-11-05). Still open: DEC-29 (B8 method), DEC-31 (Part 3 host).
- `Master_Context.md` §6.4 calls C3/C4 "future work", while this decision and Architecture §9.5 call them data-gated. The owner of `Master_Context.md` should align its wording.

### AI-010 · AI code repository location and module structure

| | |
| --- | --- |
| Source | AI-010 · `Master_Context.md` §5.4 · `ATLANTECH_AI_ARCHITECTURE.md` I-5, §4.3 · D18 · plan F-18 (plan not in this repository) |
| Owner | AI Team |
| Status | Closed |
| Affects | AI-011 – AI-016 · CT-26 |
| Decision | (1) AI code lives in `Atlantech-project/project-ai`, with one `feature/<task>` branch per task from `develop`, merged by pull request. (2) Top-level modules: `common/` (shared by all workers), `edi/` (EDI Parser, B1), `part1/` (A1–A7), `part2/` (B2–B8) and `part3/` (C1–C4, periodic). Each part is one deployable worker (D18). Implemented as a documentation-only skeleton by AI-010 (PR #3, merged into `develop` as `9edc32e`). |
| Approval | AI-010 was merged into `develop` on 2026-10-27 (PR #3). The repository user (Git user `mostafa`) approved the location and the five modules as a decision on 2026-10-28 (SETUP-002). No other approver names are recorded. |

**Follow-ups (they don't reopen the decision):**

- **Worker-to-module mapping for yard and validation.** The module READMEs from AI-010 still place B8 on `queue:part2` and have no validation worker. The newer closed decisions use a separate yard worker on `queue:yard` (`w_yard`, DEC-16, CT-11) and a validation worker on `queue:validate` (`w_validate`, DEC-03, DEC-18, CT-13), with accounts set by DEC-08. Where these two workers live in the module tree, and the matching README text, still need to be decided. That README update should also refresh the "Pending" list in `common/README.md`, which still names DEC-02 and DEC-10, both now Closed.
- **Left open by AI-010:** Python tooling, version, dependency management and environment (OQ-1); the in-repo location of schemas (OQ-2); tests, tools and model-artefact locations (OQ-7). The "FastAPI module" question is moot, because DEC-10 cancelled FastAPI.
- `Master_Context.md` §5.4 lists `project-backend`, `project-frontend` and `project-mobile` but not `project-ai`. Its owner should add it.

### AI-016 · CI provider, Python tooling and quality gates

| | |
| --- | --- |
| Source | AI-016 (backlog: "CI provider not documented") · AI-010 follow-ups OQ-1 (Python tooling, version, dependency management, environment) and OQ-7 (test location) · CT-17 §2 (MySQL 8.4, UTC sessions) · CT-08 (unprefixed keys, RPUSH/BLPOP) · AI-012 AC "No secret in the repository (scan in CI)" |
| Owner | AI Team |
| Status | Proposed |
| Affects | AI-011 – AI-015 (all code is written under these gates) · AI-012 (CI secret scan) · AI-008 / DEC-30 (coverage figure) |
| Decision | ______ |
| Proposed change | 2026-10-28 · AI-016 · (1) **CI:** GitHub Actions, `.github/workflows/ci.yml`, on every push and every pull request, no path filters. (2) **Python 3.14** (`requires-python = ">=3.14,<3.15"`, `.python-version`). (3) **uv** with a committed `uv.lock`; the project is not packaged (`tool.uv.package = false`). (4) **Tools:** Ruff (lint and format), mypy strict with an explicit `files` scope, pytest and pytest-cov. PyMySQL and redis-py are test-only (`test` dependency group); production DB and Redis clients are chosen by AI-011 / AI-013. (5) **Tests:** `tests/unit/`, `tests/integration/`, `tests/support/` at the root; the production package layout (OQ-8) stays with AI-011. (6) **Services in CI:** `mysql:8.4` (CT-17) and `redis:7.4`, the latter **provisional** until the Backend Team confirms its Redis version. (7) **Secret scan:** Gitleaks CLI 8.30.1, pinned and checksum-verified (not the separately licensed Gitleaks Action), over the full fetched history; one narrow allowlist for false positives, each entry justified in the AI-016 status record; GitHub secret scanning and push protection to be enabled by a repository admin. (8) **Coverage:** measured and reported, **no threshold** until AI-008 / DEC-30 agrees the figure. (9) **Required check:** the aggregate job `ci-ok`, to be required by branch protection on `develop`, `main` and `release` (PR required, branch up to date, no bypass), applied by a repository admin · Reason: AI-016 needs a CI provider and tooling, and AI-010 left OQ-1 open · Evidence: `docs/tasks/status/AI-016.md` (Python 3.14 compatibility check, local and Linux-container runs) · Impact: every AI task's local setup and CI; Backend (Redis version) · Awaiting: AI Team owner |
| Approval | None yet as the team decision. The repository user (Git user `mostafa`) approved these choices for the AI-016 implementation on 2026-10-28. |

**Follow-ups (open):**

- The Backend Team confirms the Redis version; until then `redis:7.4` is provisional.
- A repository admin enables branch protection with `ci-ok` required and GitHub secret scanning with push protection; both are verified afterwards and recorded in the AI-016 status record.
- AI-008 / DEC-30 supplies the coverage figure, which becomes `fail_under` in `pyproject.toml`.

### AI-014 · Unit, datum and time utilities

| | |
| --- | --- |
| Source | AI-014 (backlog: "Reject unknown units; never guess") · `ATLANTECH_AI_ARCHITECTURE.md` §7.2, §7.3, §13.1 · `ClassDiagramContext.md` (`SpeedUnit`, `VisibilityUnit`, `ConstraintUnit`, `PortShift`, `PortProfile.timezone`) · AI-010 follow-up OQ-8 (package layout) · DEC-27 (datum, Open) |
| Owner | AI Team |
| Status | Proposed |
| Affects | AI-020 · AI-021 · AI-025 · AI-044 and every later worker using `common` · AI-011 (OQ-8) |
| Decision | ______ |
| Proposed change | 2026-10-29 · AI-014 · (1) **Layout:** `common/__init__.py`, `common/units.py`, `common/time.py`, `common/datum.py`, imported as `common.units` / `common.time` / `common.datum`; tests in `tests/unit/common/`; the final package layout is left to AI-011 (OQ-8). `common/time.py` shares the stdlib `time` name: safe with absolute imports, and no script is ever run from inside `common/`. (2) **Time-zone data:** `tzdata` is an unconditional runtime dependency (`tzdata>=2026.6`, locked in `uv.lock`), so every platform uses the same IANA database version; zones come only from `zoneinfo.ZoneInfo`, with no OS fallback. (3) **Datum:** consistency check only; `MissingDatumError` for a missing or empty value, `DatumMismatchError` unless the tide set's `datum_reference`, the channel's `depth_datum` and the berth's `depth_datum` are exactly equal (no normalisation); no conversion between datums, which depends on DEC-27. (4) **DST:** a local time in a spring-forward gap raises `NonExistentLocalTimeError`, one in a fall-back overlap `AmbiguousLocalTimeError` (both `LocalTimeError`); no fold or earlier/later option, and any such option needs its own decision · Reason: AI-014 must convert units and times in one place and never guess (backlog guidance) · Evidence: `docs/tasks/status/AI-014.md`, tests in `tests/unit/common/` · Impact: AI-020, AI-021, AI-025, AI-044 and every later worker using `common`; AI-011 (OQ-8) · Awaiting: AI Team owner |
| Approval | None yet as the team decision. The repository user approved these choices for the AI-014 implementation on 2026-10-29. |

### AI-003 · AIBD-032 and AIBD-036 outcome for contract v1

| | |
| --- | --- |
| Source | AI-003 (backlog: "Every AIBD contract marked PROPOSED is either approved or explicitly rejected") · AIBD §2.1 AIBD-032 and AIBD-036, as supplied by the AI lead on 2026-11-03 (`ATLANTECH_AI_BACKEND_DEPENDENCIES.md` is not in the repository) · CT-16 · CT-18 · AI-090 · AI-009 |
| Owner | AI Team |
| Status | Closed |
| Affects | AI-003 · AI-009 · AI-090 |
| Decision | (1) **AIBD-032** is rejected as a contract v1 item. Health visibility is covered by CT-16 (Approved). The supervision tool is a deployment choice, left to AI-090. (2) **AIBD-036:** CT-18 v1.0, approved on 2026-10-27, defines the seed shape and scope, and that counts as approval for contract v1. The seed content is AI-009's deliverable and stays tracked there. |
| Approval | Decided by MennaGamal-87 (AI lead), 2026-11-03. Item (2) rests on the existing CT-18 approval by the Backend Team. |

**Follow-ups (they don't reopen the decision):**

- AI-090 chooses the supervisor tool. The AI lead cites implementation plan §7, "supervisor tool chosen in AI-090"; that plan is not in this repository.
- AI-009 delivers the seed content and the ⟨AI⟩ values in CT-18. This decision doesn't make AI-009 done.
### AI-012 · Configuration management

| | |
| --- | --- |
| Source | AI-012 (backlog) · DEC-12 · DEC-08 · CT-18 §4 and §7 · CT-08 §7 · `ATLANTECH_AI_ARCHITECTURE.md` (secrets live in environment configuration) · AIBD §6.1 as quoted by the user on 2026-11-03 (`ATLANTECH_AI_BACKEND_DEPENDENCIES.md` is not in the repository, so the names were not checked against it) |
| Owner | AI Team |
| Status | Proposed |
| Affects | AI-011 · AI-013 · AI-020 and every worker · Backend Team (deployment environment, BOOL text) |
| Decision | ______ |
| Proposed change | 2026-11-03 · AI-012 · (1) **Layout:** `common/config.py`, imported as `common.config`; final package layout left to AI-011 (OQ-8). (2) **Environment names:** `AI_DB_HOST`, `AI_DB_USER_<PART>`, `AI_REDIS_URL`, `AI_PROVIDER_PRIMARY_KEY`, `AI_PROVIDER_SECONDARY_KEY`, `AI_ARTIFACT_DIR`, `AI_BAPLIE_VOLUME` (AIBD §6.1), plus `AI_DB_PASSWORD_<PART>`, `AI_DB_PORT` and `AI_DB_NAME`. `<PART>` is `PART1`, `PART2`, `YARD`, `EDI`, `VALIDATE` or `PART3`, one per DEC-08 account. CI maps its existing `MYSQL_*` and `REDIS_URL` values to these names without renaming them. (3) **Missing configuration:** a missing database or Redis variable stops the worker at startup. The startup check covers only keys the worker uses that have an approved value in CT-18 today; ⟨AI⟩ keys are read when a job needs them, and a problem during a job fails that job with `CONFIGURATION_ERROR` (CT-08 §7, CT-18 §4). (4) **Refresh rule:** per job, no cache (DEC-12), on an autocommit connection, or committing or rolling back after every read. (5) **BOOL text:** exactly `1`, `0`, `true`, `false`; anything else is an error. (6) **DECIMAL:** parsed with `Decimal`, never `float`. · Reason: no contract names the environment variables or the BOOL text, and backlog criterion 1 ("stops the worker") needs reconciling with CT-08 §7 and CT-18 §4 · Evidence: `common/config.py`, `tests/unit/common/test_config.py`, `tests/integration/test_port_settings.py` · Impact: AI-011, AI-013, AI-020 and every worker; Backend for (2) and (5) · Awaiting: AI Team owner; Backend Team to confirm the environment names and what Laravel writes for BOOL values |
| Approval | None yet as the team decision. The repository user approved these choices for the AI-012 implementation on 2026-11-03. `AI_DB_PORT` and `AI_DB_NAME` were added by the implementer, not taken from AIBD §6.1, because a connection needs them and code holds no defaults; the user approved them the same day. All the names stay Proposed, awaiting Backend confirmation. |

### AI-011 · Shared worker runtime

| | |
| --- | --- |
| Source | AI-011 (backlog) · CT-08 §2, §6 and §7 · CT-10 · CT-11 · CT-12 · CT-14 · CT-15 · CT-17 · DEC-04 · DEC-08 · AI-010 follow-ups OQ-2 and OQ-8 |
| Owner | AI Team |
| Status | Proposed |
| Affects | AI-013 and every worker · AI-090 (schema files) · Backend Team (`AI_SCHEMA_DIR`, CT-08, CT-15, DEC-08, `chk_p1r_retry`) |
| Decision | ______ |
| Proposed change | 2026-11-03 · AI-011 · (1) **Layout (OQ-8):** `common/runtime/`, imported as `common.runtime.<module>`; no packaging; workers run as `python -m <module>` from the repository root. (2) **Connections:** the runtime takes a DB-API connection factory, in manual commit; AI-013 owns the driver and pool. (3) **Wrong queue:** a `job_type` that doesn't match the queue is logged at ERROR with `job_type`, `run_id` and queue, dropped and never claimed. This deviates from CT-08 §6 step 3; a `Proposed change` to CT-08 is on PortHub. A missing `job_type` isn't treated as a wrong queue. (4) **Retries:** immediate, no delay. (5) **Schemas (OQ-2):** loaded from `AI_SCHEMA_DIR`, Proposed like the AI-012 names. It defaults to `docs/ref/ai-payloads/` only inside a Git checkout (development and CI), with a warning. A missing schema stops the worker at startup. (6) **`part1_max_retries` above 3:** `CONFIGURATION_ERROR`, never clamped, until the Backend resolves it against `chk_p1r_retry`. (7) **`yard_runs.retry_count`:** used; a `Proposed change` to CT-15 and DEC-08 is on PortHub. (8) **Before settings are read:** a failed read gets one retry, since Part 1's limit isn't known yet. (9) **Logs:** an exception is logged as its type and traceback location, never its text. · Reason: no contract covers (1), (2), (4), (5), (8) and (9), and (3) and (6) handle gaps in the approved text · Evidence: `common/runtime/`, `tests/unit/common/runtime/`, `tests/integration/test_worker_runtime.py` · Impact: AI-013, AI-090 and every worker; Backend for (3), (5), (6) and (7) · Awaiting: AI Team owner; Backend Team for (3), (5), (6) and (7) |
| Approval | None yet as the team decision. The repository user approved these choices for the AI-011 implementation on 2026-11-03, including `yard_runs.retry_count` for the AI Team. |

**Follow-ups (they don't reopen the decision):**

- Retry delay is undefined. If a provider needs one, it should come from `port_settings`.
- AI-090 ships the schema files and sets `AI_SCHEMA_DIR`.
- Where the yard and validation workers live in the module tree (AI-010 follow-up).

### AI-013 · Data-access layer

| | |
| --- | --- |
| Source | AI-013 (backlog) · CT-15 · CT-17 §2 and §6 · DEC-08 · AI-010 follow-up OQ-8 |
| Owner | AI Team |
| Status | Proposed |
| Affects | Every worker · AI-015 · AI-090 (TLS, environment) · Backend Team (CT-17 test setup, environment names) |
| Decision | ______ |
| Proposed change | 2026-11-03 · AI-013 · (1) **Layout (OQ-8):** `common/db/`, imported as `common.db.<module>`. (2) **Driver:** SQLAlchemy Core, PyMySQL and `cryptography`, pinned in `uv.lock`. (3) **Connections:** `connect_worker` gives one transaction shared by the runtime's raw cursors and the repositories, with a pool of one and one overflow, and a pre-ping. (4) **Test setup, a deviation from CT-17 §6:** tests run on our own CI services, not the Backend's docker compose, from the full `schema.sql` with the six accounts created as `atlantech:worker-accounts` does, and without the CT-18 seed. (5) **Schema copy:** `docs/ref/db/schema.sql`, byte-exact, with its source commit and SHA-256 in `schema.sql.source.json`, checked offline. (6) The backlog's "PortSync.md DDL" is read as `contracts/db/schema.sql`. (7) **Initial status of `recommendations`:** workers insert only `PENDING_REVIEW`. CT-15 names no status; evidence: DEC-06 and CT-10 ("Only the previous PENDING_REVIEW version of a solved request becomes REPLACED"), the CT-20 example and the schema default. (8) **Datetimes:** a value with an offset is converted to UTC; one without is taken as UTC; workers create only aware values, with `datetime.now(UTC)`. Reason: the task needs these, and CT-17 §6's setup isn't usable from this repository's CI. Evidence: `common/db/`, `tests/integration/test_worker_accounts.py`, `tests/integration/test_db_layer.py`, `tests/integration/test_runtime_real_accounts.py`. Impact: AI-015 and every worker; Backend for points 4 and 7. Awaiting: AI Team; Backend Team for points 4 and 7 |
| Approval | None yet as the team decision. The repository user approved these choices for the AI-013 implementation on 2026-11-03 and 2026-11-04. MennaGamal-87 (AI lead) approved on 2026-11-04 counting the privilege matrix as Backend-approved, because it is generated from Backend's `workers.sql` and CT-15 is approved by Backend; `yard_runs.retry_count` stays pending its PortHub Proposed change. |

**Follow-ups (they don't reopen the decision):**

- CT-15 writes the worker's `lifecycle_status` value as `GENERATED`; the ENUM and CT-11 use `YARD_REC_GENERATED`. The code follows the ENUM. CT-15's wording should be corrected.
- **Deployment risk for AI-090:** workers and MySQL share the port server, so TLS may be off there. PyMySQL 1.2.3 uses TLS by default, without checking the certificate. Without TLS, its first `caching_sha2_password` login crashes, even with `cryptography` installed. Backend question: does production/prototype MySQL offer TLS to the worker accounts? If not, it must be fixed before deployment.
- `database/grants/workers.sql` on backend `develop` has a stray `-- DEMO (do not merge)` comment that isn't in `schema.sql`.

### AI-015 · Test harness and synthetic scenario generator

| | |
| --- | --- |
| Source | AI-015 (backlog: "Never present results on synthetic data as operational performance"; "Distribution choices are assumptions; document them") · `Master_Context.md` §4 · NFR-CAP-1 (`UML_Context.md`) · AI-010 follow-up OQ-7 (locations for tests and tools) · AI-013 follow-up (real seed data with parent rows) |
| Owner | AI Team |
| Status | Proposed |
| Affects | AI-022 · AI-061 · AI-062 and every later test that needs master data |
| Decision | ______ |
| Proposed change | 2026-11-05 · AI-015 · (1) **Locations (OQ-7):** `tools/scenario_generator/` (generator, command line `python -m tools.scenario_generator`), `tests/fixtures/` (sample scenarios and the seed register `scenario_seeds.json`), `tests/support/scenarios.py` (fixture loader). (2) **Format:** one JSON file per scenario, `SYNTHETIC_<size>_seed<N>.json`, with a `metadata` block (`synthetic: true`, `label`, `size`, `seed`, `days`, `generator_version`, `start_date`, `counts`, `assumptions`) and rows per table in insert order. (3) **Label rule:** every file name starts with `SYNTHETIC_`, every name inside the data starts with "SYNTHETIC" (the generator does this and a test checks it), and the loader refuses a file or scenario whose file name or metadata isn't labelled. The port has no UN/LOCODE, sits at latitude 0, longitude 0, and IMO numbers carry a deliberately wrong check digit, so no real port or ship can be meant. (4) **Reproducibility:** one `random.Random(seed)`, a fixed start date (2026-01-05 UTC) and no wall clock; the samples are compared byte for byte with a fresh run. (5) **Loading:** with foreign key checks on, in one transaction, into the schema copy `docs/ref/db/schema.sql`. (6) **Assumptions:** the distribution choices are listed in `tools/scenario_generator/README.md` and in each file's metadata. They are assumptions, not Damietta data. (7) **Scope:** master data for the port, terminals, berths, channel, tugboats, vessels and berthing requests only; users, tides, weather, pilots, containers and BAPLIE data are not generated · Reason: the backlog asks for repeatable scenarios before real data exists, and no document fixes the file format or locations · Evidence: `tools/scenario_generator/`, `tests/unit/tools/`, `tests/integration/test_scenario_load.py`, `docs/tasks/status/AI-015.md` · Impact: AI-022, AI-061, AI-062 · Awaiting: AI Team owner |
| Approval | None yet as the team decision. Mostafa Rashwan (Lead Council) approved the AI-015 task and its PROPOSED justification on 2026-11-05, and the implementation plan the same day. |

**Follow-ups (they don't reopen the decision):**

- The schema copy is at PortHub `b4d2deb`. A Backend migration adds `port_settings.min_value` and `port_settings.max_value`; the generator writes no `port_settings` rows, so it is not affected, but the copy needs refreshing when PortHub regenerates `schema.sql`.
- AI-022 supplies real reference-port master data; this generator doesn't replace it.

### AI-050 · Port-state loader: pilot identification, berth availability and holds

| | |
| --- | --- |
| Source | AI-050 (backlog: "Pilot occupancy rule F-21 implemented as decided") · AI-006 follow-up "Berth availability rule not written as a separate statement" · DEC-32 · DEC-06 · `schema.sql` `plan_components` (lines 1030–1061), `operational_plans` (918–936), `recommendation_options` (1149–1179), `berths` (240–259) |
| Owner | AI Team |
| Status | Proposed |
| Affects | AI-051 · AI-055 · AI-060 · P5-M1 · DEC-32 (applies it; does not change it) |
| Decision | ______ |
| Proposed change | 2026-11-05 · AI-050 · (1) **Pilot of a confirmed plan.** The pilot of a `PILOT` row of `plan_components` is `assigned_user_id` when it is set; otherwise it is `recommendation_options.pilot_user_id` of the option the plan references (`operational_plans.recommendation_option_id`). `assigned_user_id` wins, because a replacement (P5-M1) may change it. The interval is the `PILOT` row's `planned_start` and `planned_end` (DEC-32 rule 4). A `PILOT` row can identify its pilot only this way, because `chk_pc_resource` leaves its `berth_id`, `tugboat_id` and `terminal_id` NULL. No other component needs the fallback: a `TUG` row is identified by `tugboat_id` (never NULL for a `TUG` row; its master comes from `tug_master_profiles.assigned_tugboat_id`, DEC-32 rule 2(b)), a `BERTH` row by `berth_id`, and a `TERMINAL_OPS` row by `terminal_id`. (2) **Berth available** for `[start, end)` when: (a) `berths.status` is `ACTIVE`, not `MAINTENANCE` or `INACTIVE`; (b) a `berth_terminals` row allows the berth for the request's terminal; (c) it is not busy, meaning it appears, over an overlapping interval, in a `BERTH` row of `plan_components` with `reservation_state = RESERVED` under an `operational_plans` row with `status = CONFIRMED`, or in option 1 of a recommendation whose status is `PENDING_REVIEW` or `MODIFIED_BY_STAFF` (`recommendation_options.berth_id`, `planned_start`, `planned_end`; for `MODIFIED_BY_STAFF` the assignment as modified). `INVALIDATED`, `REPLACED` and `REJECTED` recommendations and options 2 and 3 hold nothing. Intervals are half-open. The option window is the real berth stay, so a berth hold does not over-reserve. A delayed vessel still alongside after its `planned_end` is not detected by the loader; delays arrive as `REPLAN` triggers (CT-10). (3) **Holds carry their request.** Every hold the loader returns (confirmed `plan_components` rows and pending option-1 holds, for berths, pilots and tugs) carries its `berthing_request_id`, and a pending hold also its `recommendation_id` and option rank, so the solver can drop the holds of the requests in the current run and their previous `PENDING_REVIEW` recommendations (DEC-32 rule 5, DEC-06). The loader exposes them and does not drop them itself. Pending holds are not `RESERVED` rows and go beyond the backlog output list; DEC-32 rule 3(b) requires them. (4) **Overlap, not containment:** the loader returns every hold, shift and status row that overlaps `[horizon_start, horizon_end)`; both are required arguments. · Reason: DEC-32 names `assigned_user_id` for the pilot of a confirmed plan, but that column is filled at dispatch (`chk_pc_assigned` allows NULL), so a confirmed plan could show no pilot and the pilot would look free; AI-006 left the berth rule unwritten · Evidence: `schema.sql` lines 922, 1033–1041, 1058–1059, 1155–1157, 248; DEC-32 rules 3 to 5; `part2/state/` and its tests on branch `feature/AI-050-port-state-loader` · Impact: AI-051, AI-055 (the solver drops the holds of its own run), AI-060, P5-M1 (pilot replacement, same rule); Backend · Awaiting: AI Team (owner) |
| Approval | None yet as the team decision. Mostafa Rashwan (Lead Council) approved the AI-050 plan with these rulings on 2026-11-05. |

**Follow-ups (they don't reopen the decision):**

- Backend: confirm rule (1), or fill `plan_components.assigned_user_id` for the `PILOT` row at confirm time, which makes the fallback unnecessary.
- If `MODIFIED_BY_STAFF` versions keep the staff-modified assignment somewhere other than option 1 of that recommendation, the loader must read it from there (Backend to confirm).
