# part2

AI Part 2, the AI Engine: allocates berth, tugs and pilot in a port-wide joint solve, and recommends yard placement for the Container Terminal.

## Worker and queue

AI Part 2, consuming `queue:part2`. Solve triggers (`solver_run.trigger_type`, Architecture §8.1): `NEW_REQUEST` when the entry window is confirmed, `MANUAL`, `RESOURCE_CHANGE` and `REPLAN`. Yard placement is enqueued when the Backend creates a `terminal_recommendation` with `YARD_REC_REQUESTED` (§8.14).

## Components

| ID | Component | Status |
|---|---|---|
| B2 | Constraint filter | MVP |
| B3 | Service time | MVP: Phase 1 formula. DATA-GATED: M2 LightGBM (Phase 2) |
| B4 | Delay risk | MVP: Phase 1 rule, or NULL until DEC-21 is approved. DATA-GATED: M4 LightGBM |
| B5 | CP-SAT solver with FIFO fallback | MVP |
| B6 | Template rationale | MVP |
| B7 | Re-planning | MVP |
| B8 | Yard placement (new identifier; method set by DEC-29, Open) | MVP |

## Tug requirement (AI-054, DEC-20)

`part2/tugs.py` computes one result per berthing request, before the solver: `compute_tug_requirement(request, tugs, load_rules())` returns `n_min`, `n_cap`, `bp_req`, `eligible_tugs` and `flags`. It is a pure function with no solver import. AI-055 passes the integers to CP-SAT.

- **Numbers:** all in `part2/tug_rules.json`, each section with its `source` and an `interim` note. The rules are PROPOSED and unvalidated, and DEC-20 is still Open, pending the Leads Council. Every result carries `rules_unvalidated` until the file's status is `APPROVED`. This deviates from AI-012: `port_settings.setting_value` is `varchar(255)` and can't hold the table or its sources. Changing a value needs a deploy, not a code change.
- **Inputs:** `arrival_draft`, or `max_draft` with `max_draft_used`. The request's `block_coefficient`, or the type table if it's missing or outside the valid range, with `cb_fallback_used`.
- **Zero tugs:** only when GT is below the threshold and `pilot_requested` is `False`. `None` applies the table with `pilot_request_unknown`. The Backend has no such field yet.
- **Tugs not rated in bollard pull:** excluded with `tug_power_not_bollard_pull`, because no conversion from HP or kW is agreed.
- **Eligibility:** `eligible_tugs` is by rating only. AI-055 must filter by availability (DEC-32).
- **Vessels with power only:** the table is MPA's column for vessels with power. A dead ship needs more tugs, and no field says which applies.
- **Infeasible:** AI-055 reports it. The requirement is never relaxed.

## Delay risk, Phase 1 (AI-053, DEC-21)

`part2/delay_risk.py` gives B4 a level for one option: `assess_delay_risk(...)` returns `code` (0.100 LOW, 0.500 MEDIUM, 0.900 HIGH, or `None` for NULL), `level`, `drivers`, `flags`, `not_assessed`, `coverage` `rule_version` and `inputs` (the W maxima, C ratio and post-storm flag it used, for DEC-21 open item 6). It is a pure function: the caller reads the database and passes plain values, and nothing here imports the solver.

- **Numbers:** all in `part2/delay_risk_rules.json`, each section with its `source` and an `interim` note. The rules file is `PROPOSED` (DEC-21 open item 2): every result carries `rules_unvalidated` until its status is `APPROVED`, as in AI-054. The codes are level codes, not probabilities, and screens show the level only.
- **Result:** the higher of weather W and congestion C. A missing input can only lower it, so a HIGH is reliable and a LOW or MEDIUM with a gap is a lower bound (`is_lower_bound`).
- **NULL:** only for a forecast that is missing, older than `part1_stored_data_max_age_hours` (the caller passes it), or with no point in the option's window. Every other gap gives a flag (`congestion_unavailable`, `storm_history_unknown`, `forecast_partial`, `weather_incomplete`) and the result names what was not assessed.
- **Not applied:** headroom to the safety limits (DEC-30 TR-10 is not filled). The function has no such input.
- **Open:** where "arrivals" come from for C (the AI Team). The task's Proposed entry in `docs/ref/ATLANTECH_Decisions.md` holds the rulings.

## Service time, Phase 1 (AI-052, DEC-28)

`part2/service_time.py` gives B3 a time for one request at one candidate terminal: `compute_service_time(...)` returns `p50_hours`, `p90_hours` (always `None`), `method` (`FORMULA`), `excluded_reason`, `flags` and `inputs`. `hours = moves / productivity_rate + fixed_overhead_minutes / 60`, rounded up to 0.01 h. It is a pure function: the caller reads the database and passes plain values, and nothing here imports the solver.

- **Moves:** `count_moves(...)` applies DEC-28. Discharge is the ACTIVE BAPLE rows whose `port_of_discharge` is `port_profiles.port_code`; loading is the request's optional count, else equal to discharge with the flag `loading_estimated`. No ACTIVE BAPLE gives `None` (the result is `MISSING_MOVES`); an unset `port_code` raises `ConfigurationError`. Moves are never guessed.
- **Profile:** `resolve_profile(...)` takes the row valid on the date (both ends inclusive) for the terminal, the vessel's type before the terminal default. None is `NO_VALID_PROFILE`; two at the same level is `AMBIGUOUS_PROFILE`.
- **Caller supplies:** the profiles, the discharge ports, `port_code`, the loading count, `vessel_type_id` and the port-local date of the start of the request's earliest confirmed window.
- **Exclusions:** `BASIS_UNDEFINED` (not a container vessel), `MISSING_MOVES`, `NO_VALID_PROFILE`, `AMBIGUOUS_PROFILE`, `PROFILE_UNIT_MISMATCH`, `NON_POSITIVE_SERVICE_TIME`.
- **Known limitation:** vessels other than container vessels get no service time in Phase 1 (DEC-28 open item 4 stays open). The task's Proposed entry in `docs/ref/ATLANTECH_Decisions.md` holds the rulings.

## Constraint filter, B2 (AI-051)

`part2/filter/` applies the hard rules before the solve and on every emitted option, AI or FIFO. It is pure: the caller passes the AI-050 `PortState`, the constraint types, a `vessel_type_code` → id map and AI-054's tug requirements (`FilterContext`). The rules are in the AI-051 task decision (Proposed).

- **Before the solve:** `filter_candidates(state, request_id, context)` keeps or removes every berth with all its reasons: `TERMINAL_COMPATIBILITY`, `BERTH_UNAVAILABLE`, `MAX_LOA`, `MAX_DRAFT` (static), Marine Safety Officer codes (A4's `resolve_limit` per berth, over the window), and per request `ENTRY_WINDOW`, `PILOT_UNAVAILABLE`, `PILOT_RANK_LIMIT`, `TUG_COUNT`.
- **NO_FEASIBLE_PLAN:** `binding_constraints(candidates)` gives CT-10 items, one per distinct reason, `detail` at most 255 characters.
- **Options:** `check_option` and `check_plan` add the window (`[start, end)`, UTC) and DEC-32 availability (`BERTH_OCCUPIED`, `PILOT_UNAVAILABLE`, `TUG_UNAVAILABLE`); a plan's other options count as holds, so a FIFO plan that double-books fails.
- **Not enforced yet:** UKC (AI-045; a skipped test waits for it) and equipment-specific limits (no berth–equipment link). The B2 code list is empty until Marine Safety Officer codes are seeded (AI-009).
- **Proposed codes:** `PILOT_RANK_LIMIT` and `TUG_COUNT` are a Proposed CT-10 change; its approval is a merge gate for AI-058.

## Writes

- `solver_run`, `solver_run_model_version`
- `recommendation`, `recommendation_option`, `recommendation_option_tug`, `recommendation_rationale_factor`
- `terminal_recommendation` (generation result only; the Backend creates the row and writes decisions and export fields), `yard_placement_item`

## Never

- I-3: Part 2 is the sole allocation authority; no other worker allocates.
- I-7: Part 1 constraints are hard; the solver never relaxes them. No feasible solution ends as `NO_FEASIBLE_PLAN`.
- I-8: FIFO fallback only on technical solver failure, never on infeasibility.
- I-9: rationale comes from fixed, versioned templates, never an LLM.
- The worker never changes `yard_slot.container_id` and never reserves capacity (§8.14).

## Pending

- OQ-1: Python tooling, version, dependency management and environment.
- DEC-21: Phase 1 delay-risk rule (Open).
- DEC-29: yard recommendation method, objective and confidence (Open).

## References

- `docs/ref/ATLANTECH_AI_ARCHITECTURE.md` §2, §4.3, §8, §12.2
- `docs/ref/ATLANTECH_Decisions.md` AI-001 (component status) and AI-010 (module structure) task decisions
