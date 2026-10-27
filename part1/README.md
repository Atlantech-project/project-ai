# part1

AI Part 1, predictive and environmental: produces constraints and entry-time windows for a berthing request.

## Worker and queue

AI Part 1, consuming `queue:part1` (enqueued by the Backend at Customs Approval, recompute, manual data submitted or window reopened; see Architecture §7). It also runs its own internal scheduler for periodic environmental pulls: weather every 6 h and tide daily, with no Laravel call.

## Components

| ID | Component | Status |
|---|---|---|
| A1 | Data ingestion | MVP |
| A2 | Astronomical tide (harmonic model, pyTMD, computed in-house) | MVP |
| A3 | Surge residual: `Surge(t) = SeaLevel(t) - Tide(t)` | MVP |
| A4 | Threshold feasibility | MVP |
| A5 | Under-keel clearance with Barrass squat | MVP |
| A6 | Uncertainty margin | FUTURE WORK. MVP: zero margin, `confidence` = NULL (DEC-25, Open) |
| A7 | Demand and peak forecast | MVP: Phase 1 aggregation. DATA-GATED: M3 LightGBM (Phase 2) |

## Writes

- `forecast_run`, `environment_forecast_point` (`SCHEDULED`, `ON_DEMAND`; the Backend writes `MANUAL`)
- `tide_prediction_run`, `tide_prediction_point`
- `demand_forecast_slot`
- `part1_run` (the Backend creates it; Part 1 updates status, outcome, retries and the proposal link)
- `entry_window_proposal`, `feasible_window`, `blocked_period` (Part 1 creates `PROPOSED` and marks `REPLACED`; the Backend writes `CONFIRMED` / `REJECTED`)

## Never

- I-2: Part 1 never allocates resources. It produces constraints and entry-time windows only.
- I-6: hard safety limits are never loosened automatically.
- I-10: tide is computed in-house, not pulled from a provider.
- I-15: manual environmental data passes the same safety constraints.

## Pending

- OQ-1: Python tooling, version, dependency management and environment.
- DEC-25: uncertainty margin and window confidence (Open).

## References

- `docs/ref/ATLANTECH_AI_ARCHITECTURE.md` §2, §4.3, §7, §12.2
- `docs/ref/ATLANTECH_Decisions.md` AI-001 (component status) and AI-010 (module structure) task decisions
