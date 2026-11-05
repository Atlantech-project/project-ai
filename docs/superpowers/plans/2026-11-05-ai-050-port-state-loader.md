# AI-050 · Implement port-state loader for Part 2 — plan

Written without the Superpowers brainstorming and planning skills (this session ran the workflow by hand). DRAFT: not approved. No step commits; publishing happens through `/atlantech-review-and-publish AI-050`.

Contracts and decisions read from `origin/develop` at `1084024` (DEC-32 Closed 2026-11-05 is in it). Missing from the workspace and not reconstructed: `ATLANTECH_AI_IMPLEMENTATION_PLAN.md` (so "plan F-21" and "plan F-09" are not readable; "F-21 as decided" is taken to mean DEC-32).

## Task

- **ID:** AI-050 · Implement port-state loader for Part 2 (P5, P0, complexity M, flag A)
- **Branch:** `feature/AI-050-port-state-loader` (from `develop` at `1084024`)
- **Prerequisites:** AI-013 DONE (PR #19, `109fb54`) and AI-006 DONE (DEC-06, DEC-32), both confirmed by the Leads Council on 2026-11-05. Their record updates are on `feature/SETUP-status-ai013-ai006-done` (pushed, `139bbea`), not yet merged.

## What "RESERVED rows" means (first acceptance criterion)

- **Table and enum:** `plan_components.reservation_state` `enum('RESERVED','RELEASED','CONSUMED') NOT NULL DEFAULT 'RESERVED'` (`docs/ref/db/schema.sql` line 1042). Table comment, line 1061: "One row per dispatched unit (one per tug). Berth/tug occupancy = RESERVED rows overlapping a window (D-20)."
- **Columns used:** `component_type` (1033: `BERTH`, `PILOT`, `TUG`, `TERMINAL_OPS`), `berth_id` (1034), `tugboat_id` (1035), `assigned_user_id` (1037), `planned_start` / `planned_end` (1040–1041), `operational_plan_id` (1032). `chk_pc_resource` (1059): a `PILOT` row has `berth_id`, `tugboat_id` and `terminal_id` all NULL, so the pilot can only be identified by `assigned_user_id`.
- **Who writes them:** the Backend only (`ATLANTECH_Contracts.md` line 1066: `plan_components` is "Backend only"; the AI workers have SELECT only, `r_part2` grants at schema lines 2169–2216). The Backend creates the rows `RESERVED` in the confirm transaction (Architecture §8.2 line 444; ClassDiagramContext line 288), sets `RELEASED` on plan cancellation (column comment, line 1042), and `CONSUMED` after execution (inferred from the enum; no document states who sets it).
- **Relation to DEC-32's busy rule 3(a)** ("a confirmed operational plan, `operational_plans.status` = `CONFIRMED`", line 923):
  - They agree. A plan is `CONFIRMED` while its rows are `RESERVED`; `CANCELLED` ↔ `RELEASED`; `COMPLETED` ↔ `CONSUMED`. DEC-32 rule 4 already names `plan_components.planned_start` / `planned_end` as the interval for a confirmed plan.
  - The loader reads rows with `reservation_state = 'RESERVED'` joined to `operational_plans.status = 'CONFIRMED'`, and takes a row only when both hold. If a RESERVED row sits under a non-CONFIRMED plan (or the reverse), it is skipped and counted in the snapshot's `inconsistencies` so a test or the log can see it. This is a safety net, not a rule change.
- **No conflict found. One gap, which needs a ruling (decision 1 below):** DEC-32 says the pilot of a confirmed plan is `plan_components.assigned_user_id`. That column is filled when the department officer dispatches the work (`assigned_by`, `assigned_at`; the `chk_pc_assigned` check at line 1058 lets it be NULL). Before dispatch, a `PILOT` row can carry no pilot, and the pilot would look free to the solver, which allows a double-booking.

## Decisions needed from you before implementation

1. **Pilot of a confirmed plan before dispatch.** Proposed: the pilot is `plan_components.assigned_user_id` when it is not NULL, otherwise `recommendation_options.pilot_user_id` of the option the plan references (`operational_plans.recommendation_option_id`, line 922). Interval: the `PILOT` row's `planned_start` / `planned_end`. The Backend should confirm that it creates the `PILOT` row at confirmation. This extends DEC-32 rule 4 (it is the same busy rule, applied to where the pilot is stored) and is written as a `Proposed` row under "AI task decisions" for AI-050, not as a new DEC.
2. **Berth availability rule** (below), written the same way.
3. **Horizon.** The loader takes `horizon_start` and `horizon_end` as arguments and returns every RESERVED component and every option-1 hold overlapping it. Proposed default for the caller (AI-055/056): from the earliest `window_start` to the latest `window_end` of the confirmed windows in scope, because the backlog fixes no horizon. Say if you want a margin added.
4. **Option-1 holds in the snapshot.** DEC-32 rule 3(b) counts options 1 of `PENDING_REVIEW` and `MODIFIED_BY_STAFF` recommendations as busy. They are not "RESERVED rows" but the backlog output list says the snapshot holds "RESERVED components". The loader includes both sources, separately labelled (`confirmed_holds`, `pending_holds`), and excludes recommendations of the requests in the solve (DEC-32 rule 5; DEC-06). This is needed to apply DEC-32 as written.

## Berth availability rule (proposed, DEC-32 pattern)

For an operation interval `[start, end)` at a berth, the berth is **available** when all hold:

1. **In service:** `berths.status` (line 248) is `ACTIVE`, not `MAINTENANCE` or `INACTIVE`. The column comment says it is administrative only: "Reserved/occupied is derived from plan_component and actual status", so `RESERVED` or `BUSY` is never read from it.
2. **Allowed for the terminal:** a `berth_terminals` row links the berth to the request's terminal (`recommendation_options` foreign key `fk_ro_berth` shows the same pair). This is the B2 structural filter (AI-051); the loader only loads the pairs.
3. **Not busy:** the berth appears, over an overlapping interval, in:
   - (a) a `BERTH` row of `plan_components` with `reservation_state = 'RESERVED'` under a `CONFIRMED` plan (`berth_id`, `planned_start`, `planned_end`); or
   - (b) option 1 of a recommendation whose status is `PENDING_REVIEW` or `MODIFIED_BY_STAFF` (`recommendation_options.berth_id`, `planned_start`, `planned_end`; for `MODIFIED_BY_STAFF` the assignment as modified).

   `INVALIDATED`, `REPLACED` and `REJECTED` recommendations, options 2 and 3, and requests solved in the same run hold nothing (DEC-32 rules 3 and 5).
4. **Interval:** half-open, so back-to-back berth stays do not overlap. For a berth the option window is the real berth stay (the table is keyed on the berth, `idx_ro_berth_time`), so unlike the pilot and tug rule there is no over-reservation.

Not done by the loader: a vessel that is still alongside after its `planned_end` (delay) is not detected here; delays reach Part 2 as `REPLAN` triggers (CT-10). Stated as an assumption.

## Scope

**In:**
- `part2/state/` (the backlog's PROPOSED module): `snapshot.py` (`load_port_state`, frozen dataclasses), `availability.py` (pure functions for DEC-32 rules 1–5 and the berth rule above), `__init__.py`.
- `common/db/tables.py`: Core definitions for the tables the loader reads that are missing today (`plan_components`, `operational_plans`, `berths`, `berth_terminals`, `pilot_profiles`, `pilot_rank_limits`, `pilot_schedules`, `port_shifts`, `tug_master_profiles`, `tug_master_schedules`, `users`, `user_role_assignments`, `safety_constraints`, `port_settings`, `container_manifest_entries` if absent). Each is already held to the real schema by the existing test. `RECOMMENDATIONS`, `RECOMMENDATION_OPTIONS`, `RECOMMENDATION_OPTION_TUGS`, `TUGBOATS`, `BERTHING_REQUESTS`, `ENTRY_WINDOW_PROPOSALS`, `FEASIBLE_WINDOWS`, `BLOCKED_PERIODS` exist.
- One repeatable-read transaction on the primary (DEC-08, OD-21), with the load time measured per table and in total.
- Tests (below) and a timing report.
- One `Proposed` row under "AI task decisions" in `docs/ref/ATLANTECH_Decisions.md` (decisions 1 and 2), keyed AI-050; the status record and tracker row.

**Out:**
- B2 filter (AI-051), service time (AI-052), delay risk (AI-053), CP-SAT (AI-055), and wiring into a Part 2 worker handler.
- Writing to any table (the account is SELECT-only here).
- A new horizon or margin setting; changing the schema; the Backend re-check (P5-M1) and the CT-10 wording.
- Editing the backlog, `docs/ref/` files other than the one Decisions row, and CLAUDE.md.
- DEC-32's shared test vectors (a follow-up for the AI Team); this task adds its own tests, written so they can become those vectors.

## Files likely to change

| File | New / existing |
|---|---|
| `part2/state/__init__.py`, `part2/state/snapshot.py`, `part2/state/availability.py` | new |
| `common/db/tables.py` | existing (add tables) |
| `tests/unit/part2/state/test_availability.py` | new (pure rules; no database) |
| `tests/integration/test_port_state_loader.py` | new (real MySQL, real `w_part2` account) |
| `tests/support/scenarios.py` or a small fixture helper | existing / new, only if the AI-015 scenarios lack plan components |
| `docs/ref/ATLANTECH_Decisions.md` | existing: one Proposed row |
| `docs/tasks/status/AI-050.md`, `docs/tasks/WORK_STATUS.md` | new / existing |

## Dependencies

- AI-013 (data-access layer, `connect_worker`, `transaction`, read models): DONE. AI-006: DONE.
- Closed decisions used: DEC-06 (solve scope), DEC-08 (primary reads, `w_part2`), DEC-32, DEC-36 (active role), DEC-20 (tug eligibility is AI-054, not here).
- Cross-team: Backend to confirm decision 1 (when the `PILOT` row and its `assigned_user_id` are written); no blocker for the loader itself.
- AI-015 fixtures (`tests/fixtures`, `tests/support/scenarios.py`) for test data.

## Tests

Commands: `uv run pytest tests/unit -q` and `uv run pytest -m integration -q` (the integration marker needs the MySQL and Redis services, as in CI; run locally if the services are available, otherwise reported as not run).

- **Occupancy (criterion 1):** a RESERVED `TUG`/`BERTH`/`PILOT` row overlapping the horizon is returned; `RELEASED` and `CONSUMED` rows are not; a RESERVED row under a `CANCELLED` plan is skipped and counted as an inconsistency; rows ending exactly at the horizon start or starting exactly at its end are not returned (half-open).
- **Pilot rule (criterion 2, DEC-32):** one test per numbered rule and the cases in DEC-32's follow-up: shift covers the whole interval vs crosses a shift change (overnight `port_shifts` row), inactive user, role ended (`active_to` set), tug `MAINTENANCE` / `INACTIVE` excluded while `BUSY` is not, tug without a master, tug master off shift, back-to-back jobs, option 1 holds vs option 2/3 and `REPLACED` / `REJECTED` / `INVALIDATED`, `MODIFIED_BY_STAFF` held, same-run requests not holding each other, and decision 1 (pilot taken from the option while `assigned_user_id` is NULL).
- **Berth rule:** one test per berth rule above.
- **Consistency:** the snapshot is read in one repeatable-read transaction: a row committed by a second connection during the load is not seen.
- **Timing (criterion 3):** the integration test loads the AI-015 reference-port scenario and records the load time per table and in total; the figure is reported, with no pass/fail threshold, since the backlog sets none.
- Quality gates the repository configures in CI (`.github/workflows/`): lint, type check and format, run before the status record is written.

## Risks

- **Pilot identity before dispatch** (decision 1): wrong choice → silent double-booking or over-blocking.
- **Over-reservation** of pilots and tugs by the interim option/plan interval (DEC-32 rule 4): solves may fail on shortage; DEC-32 open items 2 and 3.
- **`plan_components.status` drift:** Contracts line 1342 lists `plan_components.status` (`UNASSIGNED` … `DONE`), but the schema has `reservation_state` and no `status` column; the loader follows the schema.
- **Time zones:** `port_shifts` times are port local time (`port_profile.timezone`, line 1109) and other datetimes are as stored; shift coverage is computed with `common/time.py`, and daylight-saving edges are tested.
- **Performance:** unknown until measured; the loader reads by horizon and by id sets, not whole tables.
- **Integration tests:** need the CI services; the Backend's seed (CT-18) is not used (same deviation as AI-013).

## Contract / decision changes

- Existing IDs applied unchanged: DEC-06, DEC-08, DEC-32, DEC-36, CT-10, CT-15 (read only).
- One `Proposed` row under "AI task decisions" for AI-050 covering decisions 1 and 2; Owner: AI Team. It stays Proposed until the Owner approves. No new `DEC-` / `CT-` ID.
- Suggested follow-ups for owners (not done here): Backend to confirm when `PILOT` rows get their pilot; CT-10 wording (already DEC-32 open item 5).

## Acceptance criteria

Quoted from the backlog, each with its check:

1. "Occupancy derived exactly from RESERVED rows overlapping a window (tests)" → the occupancy tests above.
2. "Pilot occupancy rule F-21 implemented as decided" → the pilot, tug and berth rule tests; "as decided" is DEC-32 plus decision 1, with F-21's own text unavailable (the implementation plan is not in the workspace).
3. "Snapshot load time measured" → the timing figure from the integration test, in the status record.

## Approval and rulings (2026-11-05)

Plan approved by Mostafa Mohamed Rashwan (Leads Council) on 2026-11-05, with these rulings. They replace the matching "proposed" text above.

1. **Pilot before dispatch.** A `PILOT` component's pilot is `assigned_user_id` when set, otherwise the pilot of the plan's selected option (`operational_plans.recommendation_option_id` → `recommendation_options.pilot_user_id`). `assigned_user_id` wins, because a replacement (P5-M1) may change it. Checked for other components identified only by `assigned_user_id`: none. A `TUG` row carries `tugboat_id`, a `BERTH` row `berth_id`, a `TERMINAL_OPS` row `terminal_id`; the tug master comes from `tug_master_profiles.assigned_tugboat_id` (DEC-32 rule 2(b)). Backend follow-up, in the Proposed row: confirm this, or fill `assigned_user_id` at confirm time.
2. **Berth rule** approved as written. Every hold (RESERVED components and pending option-1 holds, for berths, pilots and tugs) carries its `berthing_request_id`, and a pending hold its `recommendation_id` and option rank, so the solver can drop the holds of the requests in its run and their previous `PENDING_REVIEW` recommendations (DEC-32 rule 5, DEC-06). The loader exposes them and drops none. Unit test: `test_dropping_the_holds_of_the_runs_requests_frees_their_resources` and its neighbours.
3. **Horizon.** No default: `horizon_start` and `horizon_end` are required, keyword-only arguments, set by the caller (wiring is out of scope). Every hold, shift and status row that overlaps `[horizon_start, horizon_end)` is loaded, not only rows inside it. Edge tests: a hold starting before `horizon_start`, one ending after `horizon_end`, one containing the horizon, and back to back at each boundary.
4. **Pending holds** are included, labelled apart from RESERVED rows, with `recommendation_id`, option rank and `berthing_request_id`. This goes beyond the backlog output list ("RESERVED components"), because DEC-32 rule 3(b) requires it.

Two details settled while implementing, both on the safe side:
- The "reverse" inconsistency check (a CONFIRMED plan with a non-RESERVED row) is not made: a component may legitimately be RELEASED or CONSUMED under a CONFIRMED plan (replacement, execution). Only a RESERVED row under a non-CONFIRMED plan is skipped and reported.
- A shift whose `port_shifts` row is not active (`is_active = 0`) does not cover a job. DEC-32 says only "a shift"; a retired shift definition is treated as no shift, the conservative reading.
