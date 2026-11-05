# AI-053 · Implement B4 delay-risk Phase 1 (rule or NULL) — plan

DRAFT v2, not yet approved. Written without the Superpowers brainstorming and planning skills (this session ran the workflow by hand). No step commits; publishing happens through `/atlantech-review-and-publish AI-053`.

Read from `origin/develop` at `9e0ae86` (AI-050 merged, PR #26). Missing from the workspace and not reconstructed: `ATLANTECH_AI_IMPLEMENTATION_PLAN.md` (so "plan OD-05" is read through DEC-21, which carries source OD-05).

## Task

- **ID:** AI-053 · Implement B4 delay-risk Phase 1 (rule or NULL) (P5, P2, complexity S, flag A)
- **Branch:** `feature/AI-053-delay-risk-phase-1` (from `develop` at `9e0ae86`)
- **Backlog guidance:** "Write NULL until a rule is approved; never invent a score."
- **The rule:** DEC-21 (Closed 2026-11-05, Leads Council, **interim**): a level, not a probability. LOW / MEDIUM / HIGH from a weather factor W and a congestion factor C, or NULL. Stored in the existing `recommendation_options.delay_risk` as fixed codes LOW = 0.100, MEDIUM = 0.500, HIGH = 0.900 (no schema change).

## Rulings of the Leads Council (Mostafa Rashwan, 2026-11-05)

General principle: result = max(W, C), so a missing input can only make the level too low, never too high. A HIGH is always reliable; a LOW or MEDIUM computed with a gap is a **lower bound**. DEC-21 rule 5 has one NULL case (forecast missing or older than 48 h). That stays the only NULL case (plus the degenerate "no point in the window", ruling 5). In every other case the level is computed, and each gap is recorded as a flag next to `rules_unvalidated`, with the rationale naming what was not assessed. The five rulings are interpretations of DEC-21, so they are recorded as a **Proposed** AI-053 entry under "AI task decisions" (see "Contract / decision changes"), not as settled.

1. **Congestion inputs.** W alone, with the flag `congestion_unavailable`. A median of 0, fewer than 28 days of history, or either input missing means "unavailable", never a division by zero. (NULL would change a closed decision, and for the first 28 days after go-live every recommendation would read "Not assessed".) Open question for the AI Team: the source of "expected arrivals in the 24 h around the ETA" (berthing requests by ETA, and which statuses?) and of the "daily arrivals" for the median. DEC-21 doesn't say. The caller supplies the numbers.
2. **Boundaries.** 30 kn and 1.5 m are MEDIUM. The upper edge is already set by the text: HIGH is strictly above 35 kn (gust) and 2.0 m (wave), so 35 kn and 2.0 m are MEDIUM. Wind has no MEDIUM band: above 20 kn is HIGH, anything else is LOW for wind. Boundary tests at gust 29.9 / 30.0 / 35.0 / 35.1 kn and wave 1.49 / 1.5 / 2.0 / 2.01 m.
3. **Safety-limit headroom.** Not applied. The pinning test asserts the result is unchanged even when `safety_constraints` rows exist (the CT-18 seed may add them before anyone agrees the headroom cut-offs). Follow-up: a Proposed change on DEC-21 with the headroom cut-offs, raised when TR-10 is filled.
4. **Storm history.** Compute, with the flag `storm_history_unknown`. "Unknown" (a missing value) is kept apart from "no HIGH days" (an empty set). Missing history can only lower C by one level (the same lower-bound case as ruling 1). "1–3 days after" is counted in the port's days (Africa/Cairo, `port_profiles.timezone`), not UTC days.
5. **Partial forecast coverage.** Compute and flag `forecast_partial`; NULL only when no point falls in the window. Record the coverage (points used vs expected). Caveat: the proposed DEC-30 TR-12 says stored data must also cover the assessment horizon; if TR-12 is approved as written and read as part of "stale", partial coverage becomes NULL. Revisit when DEC-30 closes.

## Prerequisites

- **AI-005:** DONE, confirmed by Mostafa Rashwan (Leads Council) on 2026-11-05, no scope exception. Its record and tracker row are in the separate records change (branch `feature/SETUP-status-ai005-ai050-done`, awaiting `APPLY CHANGES`).
- **AI-050:** merged (PR #26, `9e0ae86`). AI-053 does not use the loader.
- **Decisions used (all Closed):** DEC-21 (the rule), DEC-12 and CT-18 `part1_stored_data_max_age_hours` = 48 (freshness), AI-001 (M4 data-gated). **Not closed:** DEC-30 / TR-10 (safety-limit defaults, DEFERRED) and TR-12 (stored data freshness, proposed): neither is applied.

## Scope

**In:**
- `part2/delay_risk.py`: a pure function, same style as `part2/tugs.py` (AI-054). Input, for one option: the forecast points in its window with the forecast step and wind unit, the maximum forecast age and the age found, the congestion inputs, the storm-history input, the port time zone and the window. Output: `DelayRiskResult(code, level, drivers, flags, not_assessed, coverage, rule_version, inputs)` or a NULL result carrying the reason. `inputs` returns what the level was computed from (W maxima in kn and m, W level, C ratio and level before the post-storm raise, whether the window is in the post-storm period, whether it raised C), so M4 has its features from day one (DEC-21 open item 6). Storing them is AI-058's. No database, no clock, no solver import. `is_lower_bound` is true when any gap flag is set.
- `part2/delay_risk_rules.json`: every number of DEC-21 with its source and an `interim` note (thresholds, level codes, ratio cut-offs, 28-day history, 24 h window, 1 to 3 day backlog, rule version). The module holds no thresholds. Rule status `PROPOSED`, as DEC-21 open item 2 says (the rule is Closed but not validated). `rules_unvalidated` is derived from that status, as in AI-054: every result carries it until the file's status is `APPROVED`.
- Wind speed is converted to knots with `common/units.py` from the unit the forecast run reports (`KNOTS`, `METRES_PER_SECOND`, `KM_PER_HOUR`). An unknown unit raises; nothing is guessed (AI-014).
- Unit tests, a status record and a tracker row.

**Out (each a different task, or the caller's):**
- Reading `environment_forecast_points`, arrivals or history from the database; the solver call (AI-055/056).
- Writing `recommendation_options.delay_risk`, and recording the rule version in `solver_run_model_versions` (needs an `ml_model_versions` row for the Phase 1 rule, which the Backend seeds; none is documented, see Risks).
- The rationale text (B6, AI-057) and P-38. The function returns what was driven and what was not assessed; it writes no text.
- Part 3 evaluation of Phase 1 values as levels (DEC-21 condition (c)).
- The headroom condition (DEC-30 / TR-10).
- Editing `docs/ref/` (other than the one Proposed entry) and CLAUDE.md.

## Rule as implemented (DEC-21 "Decision detail", numbered as there)

Per option, over the option's window `[planned_start, planned_end)`:

1. **W (weather)**, on the maxima of the forecast points whose `valid_at` falls in the window, in knots and metres:
   - HIGH: max gust > 35, or max wind > 20, or max wave > 2.0;
   - MEDIUM: max gust 30 to 35, or max wave 1.5 to 2.0, both ends inclusive (ruling 2);
   - LOW: otherwise.
   A metric with no value in the window is not assessed: the level uses the others, and `weather_incomplete` is flagged and named in `not_assessed`.
2. **C (congestion)** = expected arrivals in the 24 h around the ETA ÷ median daily arrivals of the last 28 days: MEDIUM at ratio ≥ 1.3, HIGH at ratio ≥ 1.6, otherwise LOW. Unavailable (ruling 1): flag `congestion_unavailable`, result from W alone.
3. **Post-storm backlog:** if the window starts 1 to 3 port days after a port day on which W was HIGH, C goes up one level, capped at HIGH. History unknown (ruling 4): rule not applied, flag `storm_history_unknown`. An empty set means none.
4. **Result** = max(W, C) over the factors that were assessed. `drivers` lists the factor(s) that set the level (W, C, or both; "backlog" when rule 3 raised C).
5. **NULL** when the forecast is missing or older than `part1_stored_data_max_age_hours` (48, passed in by the caller from `port_settings`), or no forecast point falls in the window. Nothing else is NULL.
6. Every non-NULL result carries `rules_unvalidated` while the rules file status is not `APPROVED` (today `PROPOSED`). Gap flags (`congestion_unavailable`, `storm_history_unknown`, `forecast_partial`, `weather_incomplete`) sit next to it; `forecast_partial` also records points used vs expected (expected from the forecast step the caller passes).
7. **Codes:** LOW 0.100, MEDIUM 0.500, HIGH 0.900, as `Decimal`. The result carries the rule version so the worker can record it.

## Files likely to change

| File | New / existing |
|---|---|
| `part2/delay_risk.py` | new |
| `part2/delay_risk_rules.json` | new |
| `tests/unit/part2/test_delay_risk.py` | new |
| `docs/ref/ATLANTECH_Decisions.md` | existing: one Proposed entry under "AI task decisions" (AI-053) and its summary-table row |
| `part2/README.md` | existing: one line on B4 Phase 1, only if AI-054's README lines set the precedent |
| `docs/tasks/status/AI-053.md`, `docs/tasks/WORK_STATUS.md` | new / existing |

## Dependencies

- AI-005, AI-050: DONE. `common/units.py`, `common/time.py` and `common/config.py` exist.
- Cross-team: none for the function. The caller (AI-055/056) supplies the inputs. The AI Team still has to say where arrivals come from; the Backend must seed an `ml_model_versions` row for the Phase 1 rule before the rule version can be recorded.

## Tests

Unit only, no services: `uv run pytest tests/unit/part2/test_delay_risk.py -q`, plus `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy`.

- **Weather boundaries:** gust 29.9 / 30.0 / 35.0 / 35.1 kn and wave 1.49 / 1.5 / 2.0 / 2.01 m; wind 20.0 (LOW) / 20.1 (HIGH), with no MEDIUM band for wind; conversion from `METRES_PER_SECOND` and `KM_PER_HOUR`; an unknown unit raises.
- **Maxima over the window:** only points inside `[planned_start, planned_end)` count (a point exactly at the end is excluded); the maximum decides.
- **Congestion:** ratio 1.29 / 1.3 / 1.59 / 1.6; median 0, median missing, fewer than 28 days of history, expected arrivals missing: each gives W alone with `congestion_unavailable` and `is_lower_bound`.
- **Backlog:** a HIGH port day 1, 2 and 3 days before the window raises C one level (LOW to MEDIUM to HIGH, capped); 0 and 4 days do not. A day boundary test around Cairo midnight, where UTC and port days differ. An empty set means none; `None` means unknown, with the flag.
- **max(W, C)** and `drivers` for each combination; a HIGH with gaps stays HIGH and is not flagged as a lower bound only by the gap (a HIGH is reliable).
- **NULL path (the "or NULL path tested" criterion):** forecast missing, stale (48 h and 48 h + 1 s), no point in the window; the result carries no code and a reason. Congestion or history gaps never give NULL.
- **Partial coverage:** points used vs expected is recorded with `forecast_partial`.
- **Codes and flags:** exact `Decimal` codes; `rules_unvalidated` on every non-NULL result; the rule version is returned.
- **Never a number off the three codes:** a property check over a grid of inputs.
- **Headroom pinned:** the result is unchanged whatever `safety_constraints` rows exist (the function takes no such input; the test passes extra data through the public entry point to show it is ignored).
- **Rules file:** every value has a `source`; the module holds no thresholds; an unknown rule status raises (as `tug_rules.json` is tested); the status is `PROPOSED`, and `rules_unvalidated` disappears only when it is `APPROVED`.
- **Returned inputs:** W maxima, C ratio, post-storm flag (True / False / None for unknown) and coverage are returned; unavailable inputs come back as `None`, never zero; a NULL result has no inputs.

## Risks

- **Rule is interim and unvalidated** (DEC-21): calibrated on PortWatch and ERA5 history and applied to Open-Meteo forecasts; screens show the level only (condition (a), the Frontend's).
- **Lower bounds:** with the gaps allowed, many early results will be flagged lower bounds (for the first 28 days C is unavailable). The flags and `not_assessed` make this visible; a LOW is never presented as complete.
- **Arrivals source undefined** (ruling 1): until the AI Team defines it, C stays unavailable.
- **Model-version record:** condition (b) of DEC-21 needs an `ml_model_versions` row for the Phase 1 rule; Contracts line 1226 says a model with no CHAMPION at go-live has no row. Not documented; the worker task must check.
- **TR-12:** if approved as read, partial coverage turns into NULL (ruling 5).

## Contract / decision changes

- DEC-21 is applied unchanged (Closed). The five rulings are interpretations of it, so they go into **one Proposed entry under "AI task decisions" for AI-053** (Owner: AI Team), with a summary-table row, written on this branch. It stays Proposed until the AI Team owner approves. No new `DEC-` or `CT-` ID, and AI task decisions stay in project-ai only.
- Follow-ups recorded there (no change to DEC-21): the arrivals source and the first 28 days after go-live (AI Team); recording the rule version and the returned inputs with each recommendation (AI-058, with the Backend's `ml_model_versions` row); a Proposed change on DEC-21 with the headroom cut-offs when TR-10 is filled; revisiting ruling 5 when DEC-30 TR-12 closes; the model-version row.

## Records

- `docs/tasks/status/AI-053.md` and the tracker row are on this branch.
- The AI-005, AI-050 and DEC-21 status updates are a separate change on `feature/SETUP-status-ai005-ai050-done`, awaiting `APPLY CHANGES`.

## Acceptance criteria

Quoted from the backlog:

1. "Approved rule implemented with tests, or NULL path tested" → the rule (DEC-21, Closed) is implemented in `part2/delay_risk.py` with the boundary, backlog and `max(W, C)` tests, and the NULL path is tested separately.
