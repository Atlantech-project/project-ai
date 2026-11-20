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

## A4 threshold feasibility (AI-044)

`part1.feasibility.assess(steps, constraint_types, constraints, scope, units)` checks each time step against every applicable limit and returns, per step, the failing constraint types; `blocked_periods(results, step_length)` merges adjacent blocked steps. It is pure: no database, no clock, no queue. The rules are in the [AI-044 task decision](../docs/ref/ATLANTECH_Decisions.md) (Proposed).

- **Input (DEC-34):** steps with the fields of `environment_forecast_points` and the unit columns of `forecast_runs`, plus optional tide and surge in metres. Datetimes are timezone-aware UTC.
- **Code lists** (`series.py`): codes A4 owns (`MAX_WIND_KN` → `wind_speed`, `MAX_WAVE_HEIGHT_M` → `wave_height`), codes owned elsewhere (`MIN_UKC_M` → AI-045), and `CONFIGURATION_ERROR` for an applying code in neither. A new seed code needs a line there.
- **Scope:** a row applies when each scope column is NULL or matches, on `[active_from, active_to)`. With no berth, every berth-scoped row of the terminal applies; `resolve_limit` takes an optional berth so AI-051 can use it per candidate berth. Equipment-scoped rows never apply here. An IMDG class row (`2`) covers its divisions (`2.1`); a division row covers only that division.
- **Strictest wins:** lowest value for `MAX_ALLOWED`, highest for `MIN_REQUIRED`. Equal to the limit passes; no tolerance, no margin (DEC-25).
- **Reasons:** `LIMIT_EXCEEDED`, or `MISSING_VALUE` when a series with a limit has no reading. Periods are one per reason and type, and may overlap.
- **Not here:** reading the rows, gap tolerance (DEC-24), windows and persistence (AI-048); UKC (AI-045).
- **Tests** run on SYNTHETIC data only (`tests/unit/part1/feasibility/`, `tests/fixtures/a4/`). AI-048 is not Done until they also pass on real provider payloads (AI-020) and the real tide (AI-042) (DEC-34).

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
