# Data Ownership Matrix (CT-15)

<div dir="rtl">

**القصة.** قبل ما أي حد يكتب في جدول، لازم يعرف: الجدول ده بتاع مين؟ الـ AI يقدر يقرا منه؟ يكتب فيه؟ والـ Backend مسموحله يعدّل فيه إيه ومش مسموحله إيه؟ الملف ده بيجاوب على السؤال ده لكل جدول من الـ 92.

</div>

The output file of **CT-15 · AI result tables and write ownership** (Approved v1.1). One place both teams check before writing to a table.

| | |
| --- | --- |
| Rights (read, INSERT, UPDATE) | Generated from `project-backend/ATLANTECH/database/grants/workers.sql` at `f94a4cc`: exactly what MySQL enforces (DEC-08) |
| Who creates rows, what the Backend changes | CT-15 v1.1 table |
| Tables | The 92 port tables of CT-17 (`contracts/db/table-names.md`) |
| Do not edit by hand | Change the grants (backend PR, `ai-impact`) or CT-15 (contract change), then regenerate this file |

## Rules

1. **Workers insert new rows; the Backend retires old ones** (REPLACED, ACTIVE, CONFIRMED, REJECTED transitions) (CT-15, DEC-02).
2. A worker completes **only its own run**; every final run update is conditional on `status = 'RUNNING'` (CT-15).
3. **No worker deletes anything and no worker runs DDL** (DEC-08). Only the Backend deletes, and only where CT-15 says so (`yard_placement_items` on regeneration).
4. **The Backend writes every request transition, history row and audit entry**, on C-06 (CT-15, DEC-02). Workers have no access to `audit_logs`.
5. **The Backend never writes an AI column** (the UPDATE columns below) and never edits a result row the AI inserted, except the columns listed under "Backend may change".
6. **Backend-only columns** on shared tables: `result_handled_at` (all four run tables) and `drift_measurements.notified_at` (CT-17 §7, DEC-01). No worker has UPDATE on them.
7. A worker that reads an ENUM value it does not know logs a warning and skips the row (CT-17 §6). A worker insert refused by a CHECK ends the run FAILED without retry (CT-17 §2).
8. Any change to this matrix is a migration or grants PR labelled `ai-impact` with one AI Team approval (CT-17 §6).

## 1. Tables the AI writes results into

The AI creates the rows; the Backend changes only what is listed.

| Table | Created by | AI rights (write) | Backend may change | AI read |
| --- | --- | --- | --- | --- |
| `baplie_parse_issues` | AI | INSERT: w_edi | Nothing | All workers |
| `blocked_periods` | AI | INSERT: w_part1 | Nothing | All workers |
| `container_manifest_entries` | AI | INSERT: w_edi | Nothing | All workers |
| `containers` | AI (new container numbers only, DEC-08) | INSERT: w_edi | Nothing | All workers |
| `demand_forecast_slots` | AI | INSERT: w_part1 | Nothing | All workers |
| `drift_measurements` | AI (`w_part3`) | INSERT: w_part3 | `notified_at` only | All workers |
| `entry_window_proposals` | AI (PROPOSED) | INSERT: w_part1 | CONFIRMED, REJECTED, REPLACED (on C-06) and the confirm / reject columns | All workers |
| `environment_forecast_points` | AI (SCHEDULED, ON_DEMAND) · Backend (MANUAL) | INSERT: w_part1 | Its own MANUAL rows only | All workers |
| `evaluation_metrics` | AI (`w_part3`) | INSERT: w_part3 | Nothing | All workers |
| `feasible_windows` | AI | INSERT: w_part1 | Nothing | All workers |
| `forecast_runs` | AI (SCHEDULED, ON_DEMAND; a failed pull inserts a FAILED run) · Backend (MANUAL) | INSERT: w_part1 | Its own MANUAL runs only | All workers |
| `recommendation_option_tugs` | AI | INSERT: w_part2 | Nothing | All workers |
| `recommendation_options` | AI | INSERT: w_part2 | Nothing (status lives on `recommendations`) | All workers |
| `recommendation_rationale_factors` | AI | INSERT: w_part2 | Nothing | All workers |
| `recommendations` | AI | INSERT: w_part2 | REPLACED, CONFIRMED, MODIFIED_BY_STAFF | All workers |
| `solver_run_model_versions` | AI | INSERT: w_part2 | Nothing | All workers |
| `tide_prediction_points` | AI | INSERT: w_part1 | Nothing | All workers |
| `tide_prediction_runs` | AI | INSERT: w_part1 | Nothing | All workers |
| `yard_placement_items` | AI | INSERT: w_yard | Deletes old items on regeneration (CT-11 lock order) | All workers |

## 2. Shared tables: the Backend creates the row, the AI fills its own columns

| Table | Created by | AI rights (write) | Backend may change | AI read |
| --- | --- | --- | --- | --- |
| `baplie_files` | Backend (STAGED, PENDING) | UPDATE w_edi: parse_status, staged_payload | ACTIVE / REPLACED / WITHDRAWN, correction columns, `staged_payload` on correction | All workers |
| `baplie_parse_runs` | Backend (QUEUED; old run → REPLACED) | UPDATE w_edi: status, outcome, error_category, retry_count, container_count, result_detail, worker_version, started_at, finished_at | Old run → REPLACED; `result_handled_at`; stale RUNNING → FAILED / TIMEOUT (sweeper, DEC-04) | All workers |
| `part1_runs` | Backend (QUEUED) | UPDATE w_part1: status, outcome, retry_count, entry_window_proposal_id, started_at, finished_at | Old run → REPLACED when it sends a new one; `result_handled_at`; stale RUNNING → FAILED / TIMEOUT (sweeper, DEC-04) | All workers |
| `solver_runs` | Backend (QUEUED, `solver_version` from `port_settings`) | UPDATE w_part2: status, objective_value, solve_time_ms, solver_version, result_detail, started_at, finished_at | `result_handled_at`; stale RUNNING → FAILED / TIMEOUT (sweeper, DEC-04) | All workers |
| `terminal_recommendations` | Backend (YARD_PLACEMENT: YARD_REC_REQUESTED; reset on regeneration) | UPDATE w_yard: lifecycle_status, confidence, rationale_template_id, rationale_params, failure_reason | Decision, accept or reject, export; never the AI columns | All workers |
| `vessels` | Backend | UPDATE w_edi: call_sign, flag_state | Everything except what the AI fills: `call_sign`, `flag_state` only when NULL | All workers |
| `yard_runs` | Backend (QUEUED; old run → REPLACED) | UPDATE w_yard: status, outcome, error_category, retry_count, result_detail, worker_version, started_at, finished_at | Old run → REPLACED; `result_handled_at`; stale RUNNING → FAILED / TIMEOUT (sweeper, DEC-04) | All workers |

## 3. Backend-only tables the AI reads

The Backend writes these; workers have SELECT only.

| Table | AI read |
| --- | --- |
| `actual_status_updates` | All workers |
| `berth_terminals` | All workers |
| `berthing_request_cargos` | All workers |
| `berthing_request_status_histories` | All workers |
| `berthing_requests` | All workers |
| `berths` | All workers |
| `capability_types` | All workers |
| `cargo_types` | All workers |
| `channel_waypoints` | All workers |
| `constraint_types` | All workers |
| `container_size_types` | All workers |
| `deviation_logs` | All workers |
| `dg_zone_allowed_classes` | All workers |
| `equipment` | All workers |
| `equipment_capabilities` | All workers |
| `equipment_cargo_compatibilities` | All workers |
| `equipment_categories` | All workers |
| `external_systems` | All workers |
| `imdg_classes` | All workers |
| `license_states` | All workers, columns: mode, read_only_reason |
| `ml_model_versions` | All workers |
| `ml_models` | All workers |
| `navigation_channels` | All workers |
| `objective_terms` | All workers |
| `oog_zone_details` | All workers |
| `operational_plans` | All workers |
| `organization_units` | All workers |
| `pilot_profiles` | All workers |
| `pilot_rank_limits` | All workers |
| `pilot_schedules` | All workers |
| `plan_components` | All workers |
| `port_profiles` | All workers |
| `port_settings` | All workers |
| `port_shifts` | All workers |
| `rationale_templates` | All workers |
| `recommendation_overrides` | All workers |
| `reefer_zone_details` | All workers |
| `retraining_runs` | All workers |
| `safety_constraints` | All workers |
| `status_types` | All workers |
| `storage_allocation_items` | All workers (nobody writes it yet: DEC-55, future work) |
| `storage_facilities` | All workers |
| `storage_facility_cargo_compatibilities` | All workers |
| `storage_movements` | All workers |
| `storage_types` | All workers |
| `tank_details` | All workers |
| `terminal_cargo_types` | All workers |
| `terminal_productivity_profiles` | All workers |
| `terminals` | All workers |
| `tide_constituent_sets` | All workers |
| `tide_constituents` | All workers |
| `tug_master_profiles` | All workers |
| `tug_master_schedules` | All workers |
| `tugboats` | All workers |
| `user_role_assignments` | All workers |
| `users` | All workers, columns: id, name, is_active |
| `vessel_types` | All workers |
| `warehouse_details` | All workers |
| `yard_blocks` | All workers |
| `yard_slots` | All workers |
| `yard_zone_types` | All workers |
| `yard_zones` | All workers |

## 4. Tables the AI cannot see

| Table | Why |
| --- | --- |
| `audit_logs` | The Backend writes every audit entry on C-06 (DEC-08) |
| `notification_logs` | Notifications are a Backend concern (DEC-08) |
| `recommendation_reviews` | Who viewed which recommendation (DEC-08) |
| `user_devices` | Device tokens and push tokens (DEC-08) |

## 5. Per worker

| Worker (role) | Trigger | INSERT | UPDATE (columns) |
| --- | --- | --- | --- |
| `w_part1` (`r_part1`) | `queue:part1` + Part 1 scheduler | `entry_window_proposals`, `feasible_windows`, `blocked_periods`, `forecast_runs`, `environment_forecast_points`, `tide_prediction_runs`, `tide_prediction_points`, `demand_forecast_slots` | `part1_runs` (status, outcome, retry_count, entry_window_proposal_id, started_at, finished_at) |
| `w_part2` (`r_part2`) | `queue:part2` | `solver_run_model_versions`, `recommendations`, `recommendation_options`, `recommendation_option_tugs`, `recommendation_rationale_factors` | `solver_runs` (status, objective_value, solve_time_ms, solver_version, result_detail, started_at, finished_at) |
| `w_yard` (`r_yard`) | `queue:yard` | `yard_placement_items` | `yard_runs` (status, outcome, error_category, retry_count, result_detail, worker_version, started_at, finished_at)<br>`terminal_recommendations` (lifecycle_status, confidence, rationale_template_id, rationale_params, failure_reason) |
| `w_edi` (`r_edi`) | `queue:edi` | `baplie_parse_issues`, `containers`, `container_manifest_entries` | `baplie_parse_runs` (status, outcome, error_category, retry_count, container_count, result_detail, worker_version, started_at, finished_at)<br>`baplie_files` (parse_status, staged_payload)<br>`vessels` (call_sign, flag_state) |
| `w_validate` (`r_validate`) | `queue:validate` | — | — |
| `w_part3` (`r_part3`) | Part 3 scheduler (DEC-31) | `evaluation_metrics`, `drift_measurements` | — |

All six read every table in sections 1 to 3; none reads section 4.

## 6. Not granted yet

| Item | State |
| --- | --- |
| `terminal_recommendations` TIMING / STORAGE_ALLOCATION, `storage_allocation_items` | Out of the MVP (DEC-55); added through CT-17 when built |
| Part 3 retraining (`ml_model_versions`, `retraining_runs`) | No worker writes them until retraining is built (DEC-08) |

## Change log

| Date | Change |
| --- | --- |
| 2026-10-28 | First published version, generated from `workers.sql` and CT-15 v1.1. `w_edi` gets UPDATE on `baplie_parse_runs.retry_count` so the grants match CT-15 (DEC-08 grants were missing it) |
| 2026-10-28 | P1-B3: `w_yard` gets UPDATE on `yard_runs.retry_count` (CT-11 column; CT-08 "where granted"; DEC-04 one yard retry). Goes beyond CT-15 v1.1 `:1080` and the DEC-08 matrix `:289`: **needs AI Team approval** with a CT-15 / DEC-08 update before merge |
