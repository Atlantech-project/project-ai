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
