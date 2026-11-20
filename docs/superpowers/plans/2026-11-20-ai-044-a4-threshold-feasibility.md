# AI-044 · A4 threshold feasibility rules with strictest-wins scope resolution: plan

> Not committed by this workflow. Publishing happens through `/atlantech-review-and-publish AI-044` after the user's `APPLY CHANGES`.

## Approval

Approved by the user on 2026-11-20 ("Approved, with these changes before you start"), with seven changes, all folded into this plan:

1. Three explicit code lists: A4-owned (mapped to forecast fields), owned elsewhere (UKC → AI-045; vessel/berth safety such as LOA → B2/AI-051), and a CONFIGURATION error only for codes in neither. A test checks every seeded code (AI-009) is in exactly one list.
2. No berth is the normal Part 1 case: keep the conservative rule, expose `berth` as an optional input so AI-051 can call the same scope resolution per candidate berth, and record an open question for the Marine Safety Officer.
3. A distinct reason code `MISSING_VALUE` naming the variable; missing-data blocked periods kept separate from limit-exceeded periods.
4. Active periods half-open `[start, end)` in UTC, with a boundary test.
5. Equipment-specific limits: the decision record says AI-051 must apply them.
6. Overlapping blocked periods confirmed; flag to the Frontend Team (P-37 display) as well as the Backend Team.
7. No float tolerance confirmed; a test where a converted m/s value lands just above a knots limit and blocks.

Change found during implementation: the fixture lives in `tests/fixtures/a4/`, not `tests/fixtures/`, because `tests/unit/test_fixture_files.py` requires every top-level `SYNTHETIC_*.json` there to be a registered generator scenario. Two test files were added (`builders.py`, `test_synthetic_cases.py`). The user approved these changes on 2026-11-20, in the review.

Change from the review (2026-11-20, user ruling on an Important finding): IMDG scope matching. Codes are classes (`2`) or divisions (`2.1`); a class row covers its divisions, a division row only itself. Exact matching would have skipped a class limit for division cargo.

## Task

- **ID:** AI-044 · Implement A4 threshold feasibility rules with strictest-wins scope resolution
- **Phase:** P4 (Part 1 deterministic pipeline) · **Priority:** P0 · **Complexity:** M
- **Branch:** `feature/AI-044-a4-threshold-feasibility-rules`, from `develop` at `64cca37`

## Scope

**In:**

1. A pure A4 engine in `part1/feasibility/`: no database, no clock, no queue. The caller passes the constraint types, the safety constraints, the request's scope and the environmental series. The engine returns, for each time step, feasible or blocked with every failing constraint, and the blocked periods.
2. **Input interface (DEC-34):** one step per `valid_at`, with the fields and units of `environment_forecast_points` (`wind_speed`, `wind_gust`, `visibility`, `wave_height`, `current_speed`, `sea_level`) and the units from `forecast_runs` (`wind_speed_unit`, `visibility_unit`, `current_speed_unit`). Two optional derived series, `tide_m` and `surge_m` (metres on the active datum, from A2/A3), so the real feed connects later without changing the rules.
3. **Code registry, three lists** (approval change 1): **A4-owned** codes mapped to a series: `MAX_WIND_KN → wind_speed`, `MAX_WAVE_HEIGHT_M → wave_height`. **Owned elsewhere**, with their owner: `MIN_UKC_M → AI-045 (A5)`; vessel and berth safety codes such as LOA go here with owner B2/AI-051 when they are seeded (none is seeded today, so none is invented). **Neither:** an active code (a row that applies to the scope at some step) in neither list raises `ConfigurationError` (CT-08 `CONFIGURATION_ERROR`). The two lists must be disjoint. A test reads `docs/drafts/ai-payloads/seed-spec.json` and checks every seeded code is in exactly one list. The engine accepts a registry argument, so the tests can use clearly labelled synthetic codes for cases the seed doesn't cover (a `MIN_REQUIRED` limit, a `VESSEL_SAFETY` row).
4. **Categories:** the lists decide, not the category. A4 evaluates every A4-owned code whatever its category; codes owned elsewhere (UKC today) are skipped.
5. **Scope resolution:** `resolve_limit(rows, constraint_type, scope, at)` is public, so AI-051 can call it per candidate berth (approval change 2). The scope is the terminal, an optional berth, the vessel type and a set of IMDG classes. A row applies when each scope column is NULL or matches. With no berth (the normal Part 1 case), every berth-scoped row of that terminal applies (conservative; open question for the Marine Safety Officer). Equipment-scoped rows never apply in A4; AI-051 must apply them (approval change 5). A row is active at step `t` on the half-open UTC interval `[active_from, active_to)`; `active_to` NULL is open-ended (approval change 4). Datetimes must be timezone-aware UTC.
6. **Strictest wins** (Architecture §7.5, Master_Context §7.3): among the applicable rows of one constraint type at one step, the lowest value for `MAX_ALLOWED`, the highest for `MIN_REQUIRED`.
7. **Comparison:** the series value is converted into `constraint_types.unit` with `common.units.convert` (AI-014); a unit of the wrong dimension is a configuration error. `MAX_ALLOWED` passes when `value ≤ limit`; `MIN_REQUIRED` passes when `value ≥ limit`. Equal to the limit passes. No tolerance and no margin (DEC-25: no uncertainty margin in the MVP).
8. **Missing value** (approval change 3): a NULL value at a step, for a series with an applicable limit, blocks the step with reason `MISSING_VALUE`, naming the variable (series) and the constraint. A limit failure has reason `LIMIT_EXCEEDED`. Gap tolerance (DEC-24, Open) stays with the orchestrator, AI-048.
9. **Blocked periods:** one period per (reason, constraint type) per run of adjacent blocked steps (`valid_at` exactly one step length apart), `[first step, last step + step length)`. `MISSING_VALUE` periods are kept separate from `LIMIT_EXCEEDED` periods. Periods for different types or reasons may overlap (confirmed, approval change 6); this is flagged to the Backend Team and the Frontend Team (P-37 display). The step length is an argument (DEC-24 Open; no default). `blocked_periods` has no reason column, so carrying the reason into the database is a follow-up for AI-048 and the Backend.
10. **Synthetic test data (DEC-34):** a table-driven fixture `tests/fixtures/a4/SYNTHETIC_a4_threshold_cases.json`, with `"synthetic": true` and a label in its metadata. Limit values in the tests are synthetic and are not proposals for DEC-30.
11. **AI task decision:** a Proposed entry "AI-044 · A4 threshold feasibility" in the "AI task decisions" section of `docs/ref/ATLANTECH_Decisions.md`, recording items 3, 4, 5, 7, 8 and 9.
12. Status record, tracker row, `part1/README.md` section, and `pyproject.toml` (add `part1` to the mypy files and coverage source).

**Out:**

- Reading constraints or forecasts from the database, persisting `blocked_periods` and `feasible_windows`, the run outcome and window formation (AI-048).
- UKC and squat (AI-045); the uncertainty margin (AI-046, DEC-25); the surge computation (AI-043); tide (AI-042); provider ingestion (AI-040/041).
- New production constraint codes (gust, visibility, tide/surge: AI-009 criterion 1, Marine Safety Officer) and limit values (DEC-30).
- Extending the AI-015 generator to environmental series (not needed: the fixture above covers the tests).
- Editing the backlog (it still lists AI-043 as a prerequisite; DEC-34 changed that), PortHub, and CLAUDE.md.

## Files likely to change

| File | New / existing |
|---|---|
| `part1/__init__.py` | new (empty) |
| `part1/feasibility/__init__.py` | new: public API |
| `part1/feasibility/model.py` | new: `ConstraintTypeRow`, `SafetyConstraintRow`, `AssessmentScope`, `EnvironmentStep`, `SeriesUnits`, `StepResult`, `Failure`, `BlockedPeriod` (frozen dataclasses) |
| `part1/feasibility/series.py` | new: the code-to-series registry and its series names |
| `part1/feasibility/scope.py` | new: applicability and strictest-wins |
| `part1/feasibility/evaluate.py` | new: per-step assessment and blocked periods |
| `tests/unit/part1/__init__.py`, `tests/unit/part1/feasibility/__init__.py` | new |
| `tests/unit/part1/feasibility/test_comparators.py` | new |
| `tests/unit/part1/feasibility/test_scope.py` | new |
| `tests/unit/part1/feasibility/test_hard_limits.py` | new |
| `tests/unit/part1/feasibility/test_evaluate.py` | new: missing values, units, errors, blocked periods, fixture cases |
| `tests/unit/part1/feasibility/test_registry.py` | new: the three lists against the seed |
| `tests/unit/part1/feasibility/builders.py` | new: SYNTHETIC test builders (added during implementation) |
| `tests/unit/part1/feasibility/test_synthetic_cases.py` | new: runs the fixture (added during implementation; the plan had it in `test_evaluate.py`) |
| `tests/fixtures/a4/SYNTHETIC_a4_threshold_cases.json` | new |
| `part1/README.md` | existing: A4 section |
| `pyproject.toml` | existing: `part1` in `[tool.mypy] files` and `[tool.coverage.run] source` |
| `docs/ref/ATLANTECH_Decisions.md` | existing: Proposed AI-044 task decision only |
| `docs/tasks/status/AI-044.md`, `docs/tasks/WORK_STATUS.md` | new / existing |
| `docs/superpowers/plans/2026-11-20-ai-044-a4-threshold-feasibility.md` | new: this plan, committed with the task at the user's direction (review, 2026-11-20) |

The fixture is read with `json.load`, so its line endings don't matter.

## Dependencies

| Item | Status | Evidence |
|---|---|---|
| DEC-34 | Closed 2026-11-20, Option 1 | `develop` `64cca37` (PR #38) |
| AI-043 | Not a prerequisite since DEC-34; not started | DEC-34 Decision row. The backlog still lists it (follow-up) |
| AI-009 | DONE by Leads ruling; criterion 1 open | Tracker; user choice 2026-11-20: generic engine on the 3 seeded codes |
| AI-014 | DONE (PR #7) | Tracker; `common/units.py` |
| AI-015 | DONE | Fixture conventions (`SYNTHETIC_` names) |
| DEC-25 | Closed: no margin | Decisions file |
| DEC-24 | Open: horizon, step, gap tolerance | Not needed by the pure engine; the step length is an argument |
| DEC-30 | Open: no limit values | Tests use synthetic values |
| DEC-26, DEC-27 | Open | Only the AI-048 real-data gate needs them |

Cross-team: the Marine Safety Officer and AI Team (new codes, wave unit), the QA Team (synthetic labelling and real-data re-test, DEC-34), the Backend Team (for information: overlapping blocked periods, no schema change).

## Tests (TDD)

Write each test first, see it fail, then implement.

1. **Comparators** (table): `MAX_ALLOWED` below / equal / above; `MIN_REQUIRED` below / equal / above.
2. **Categories** (table): A4-owned `ENVIRONMENTAL` and `VESSEL_SAFETY` codes are evaluated; a `UKC` code owned elsewhere is skipped; a code in neither list raises `ConfigurationError`, but only when one of its rows applies.
3. **Registry**: the two lists are disjoint; every seeded code (AI-009 seed spec) is in exactly one list.
4. **Strictest wins**: port-wide + terminal + berth + vessel-type + IMDG rows overlapping; the strictest applicable value wins, for both comparators; non-matching scopes don't apply; no berth → every berth-scoped row of the terminal applies; a given berth → only that berth's rows; equipment-scoped rows never apply.
5. **Active period boundary**: a row applies at `active_from`, not at `active_to`, and from `active_from` on when `active_to` is NULL.
6. **Hard limits never loosened**: adding a looser, more specific row never turns a blocked step feasible (a table over every scope combination).
7. **Units**: knots, m/s and km/h wind against a `KNOTS` limit; a wrong-dimension unit raises; a converted m/s value just above a knots limit blocks (no tolerance).
8. **Missing values**: NULL with a limit → `MISSING_VALUE` naming the variable; NULL with no applicable limit → no effect.
9. **Blocked periods**: adjacent steps merge; different types overlap; `MISSING_VALUE` and `LIMIT_EXCEEDED` periods stay separate; a feasible step or a time gap splits a period; a period ends one step after its last step.
10. **Input validation**: naive or non-UTC datetimes, unsorted or duplicate steps, and a non-positive step length raise.
11. **Fixture**: every case in `SYNTHETIC_a4_threshold_cases.json` gives its expected result; the file's metadata says synthetic.

Commands (the project's CI gates, README "Getting started"):

```
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov
```

## Risks

- **Synthetic only (DEC-34):** passing tests prove the rules, not real-world behaviour. AI-048 can't be Done until these tests pass on real provider payloads (AI-020) and the real tide (AI-042).
- **Float conversion at the boundary:** a value converted from m/s can land a hair above a knots limit. No tolerance is added, because a tolerance would loosen a hard limit (I-6), so the result errs on the blocking side. Documented in the module and the task decision.
- **Registry drift:** a code added to the seed without a registry entry fails the run loudly, by design. The registry must follow AI-009's new codes (gust, visibility, tide/surge).
- **Wave unit:** `MAX_WAVE_HEIGHT_M` assumes metres, which no source states (AI-009 R-7). `wave_height` is stored in metres, so no conversion is involved.
- **Conservative berth rule:** with no berth, a berth-specific limit blocks the whole terminal. This may block more than the Marine Safety Officer expects; it's recorded in the task decision for review.
- **Overlapping blocked periods:** the schema allows them, but the Backend and the Frontend (P-37) may assume one period per time. Flagged to both in the task decision.
- **No reason column:** `blocked_periods` can't store `MISSING_VALUE` versus `LIMIT_EXCEEDED`; AI-048 and the Backend need to settle how a missing-data period is shown.

## Contract / decision changes

- **Existing IDs, used and unchanged:** DEC-34, DEC-25, DEC-24, DEC-30, CT-18 (seed codes), CT-10/CT-13 (SAFETY codes, referenced only).
- **New (Proposed):** "AI-044 · A4 threshold feasibility" in the "AI task decisions" section of `docs/ref/ATLANTECH_Decisions.md`, with Status `Proposed`, Owner AI Team, Awaiting AI Team (owner), and the Marine Safety Officer for the berth rule and the registry. No contract change.

## Acceptance criteria (backlog §5, quoted)

| Criterion | Verification |
|---|---|
| "Table-driven tests for every comparator and category" | Tests 1 and 2 (`test_comparators.py`, parametrised tables) |
| "Strictest-wins tests with overlapping scopes" | Tests 4 and 5 (`test_scope.py`) |
| "No rule can loosen a hard limit (test)" | Test 6 (`test_hard_limits.py`) |

Verification evidence (backlog): test report, from the four commands above.
