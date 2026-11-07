# AI-052 · Implement B3 service time Phase 1 formula — Implementation Plan

APPROVED 2026-11-07 by Mostafa Rashwan (Leads Council), rulings 1 to 5 as proposed; ruling 4 is also recorded as a known limitation, and DEC-28 open item 4 stays open. Implemented as written, plus one review fix: `ProductivityProfile` rejects a non-positive rate, a negative overhead and an inverted period. No step commits; publishing happens through `/atlantech-review-and-publish AI-052`. Written with the Superpowers writing-plans skill; the brainstorming skill was not run as a dialogue (the open points are the rulings below).

> **For agentic workers:** use superpowers:executing-plans (this session implements inline). Steps use checkbox syntax.

**Goal:** a pure function that gives B3 its Phase 1 service time for one request × candidate terminal: `service_time_p50_hours`, method `FORMULA`, P90 `NULL`, or an exclusion with a reason.

**Architecture:** `part2/service_time.py`, same style as `part2/tugs.py` (AI-054) and `part2/delay_risk.py` (AI-053): plain frozen values in, plain result out, no database, no clock, no solver import. The caller (AI-055/056) reads the profiles and the BAPLIE and passes them. Formula (Architecture §8.6, Master_Context B3): `hours = moves / productivity_rate + fixed_overhead_minutes / 60`. No number lives in the module except the unit conversion 60 and the DEC-28 constants.

**Tech Stack:** Python, `decimal.Decimal`, pytest, ruff, mypy strict (as AI-053).

**Spec:** backlog AI-052 (§5); DEC-28 (Closed 2026-11-05, "Decision detail" rules 1 to 7); Architecture §8.6; `docs/ref/db/schema.sql` `terminal_productivity_profiles` (lines 1576–1595) and `recommendation_options` `chk_ro_p90`, `chk_ro_values` (1177–1178).

Missing from the workspace and not reconstructed: `ATLANTECH_AI_IMPLEMENTATION_PLAN.md` (plan OD-14, read through DEC-28, whose source is OD-14).

## Task

- **ID:** AI-052 · Implement B3 service time Phase 1 formula (P5, P0, complexity S, flag A)
- **Branch:** `feature/AI-052-b3-service-time-phase-1` (from `develop` at `09f7dfe`)
- **Prerequisites:** AI-050 DONE (PR #26, `9e0ae86`) and AI-005 DONE (Leads Council, 2026-11-06); records on `develop` say so.

## Global Constraints

- Backlog: "Resolve profile by date and vessel type with terminal default fallback." Output: `service_time_p50_hours`, method `FORMULA`, P90 `NULL`.
- DEC-28: moves = discharge + loading, one container one move; discharge counted from the ACTIVE BAPLIE rows whose `port_of_discharge` equals `port_profiles.port_code`; loading = optional request field, else equal to discharge with flag `loading_estimated`; no ACTIVE BAPLIE → moves NULL, request left out with reason `MISSING_MOVES`; moves are never guessed; unset `port_code` → `CONFIGURATION_ERROR`, never discharge 0; each result records discharge, loading and `loading_estimated`.
- Schema: `chk_ro_p90` (method `ML` ⇔ P90 not null; P90 ≥ P50), `chk_ro_values` (P50 > 0), `decimal(6,2)` hours; `chk_tpp_unit` (`CONTAINER` terminal ⇔ `MOVES_PER_HOUR`); `chk_tpp_values` (rate > 0, overhead ≥ 0).
- Never guess (AI-014 style): unknown or missing input raises or excludes with a reason.

## Rulings needed (Leads Council) — recorded as a Proposed AI-052 entry under "AI task decisions"

These are interpretations of DEC-28 and the backlog, not changes to them.

1. **Reference date for the profile.** The backlog says "by date", and B3 runs before the solver, so there is no planned start. Proposal: the caller passes the **port-local date (Africa/Cairo, `port_profiles.timezone`) of the start of the request's earliest confirmed window**. Profiles change rarely, so one date per request × terminal is used, even if the stay crosses a change.
2. **Rounding.** P50 is rounded **up** to 0.01 h (`ROUND_CEILING`), so service time errs long, as DEC-28 and DEC-20 do. Rounding happens once, at the end.
3. **Profile choice.** A valid row is `valid_from ≤ date` and (`valid_to` NULL or `date ≤ valid_to`), for the candidate terminal. A row for the vessel's type beats the terminal default (`vessel_type_id` NULL). Two valid rows of the same specificity (the Backend rejects overlaps, so this means bad data) → excluded with `AMBIGUOUS_PROFILE`, never a pick.
4. **Non-container vessels** (DEC-28 open item 4, not set). No cargo-quantity field exists on `berthing_requests`, so there is nothing to divide by. Proposal: excluded with reason `BASIS_UNDEFINED`, never a guessed quantity. **Consequence for you to accept:** until a basis is agreed, no non-container vessel gets a service time, so none gets a recommendation (`NO_FEASIBLE_PLAN` with this reason).
5. **A container vessel whose profile unit is not `MOVES_PER_HOUR`** → `PROFILE_UNIT_MISMATCH` (cannot happen for a container terminal because of `chk_tpp_unit`; a safety net). A result that rounds to zero or less (0 moves and 0 overhead) → `NON_POSITIVE_SERVICE_TIME`, because `chk_ro_values` needs P50 > 0.

## Scope

**In:**
- `part2/service_time.py`: `count_moves`, `resolve_profile`, `compute_service_time` and their value types (below).
- Unit tests with hand values, a drift test for `chk_ro_p90` / `chk_ro_values`, a README section, a status record, a tracker row, a Proposed AI-052 entry in the Decisions file.

**Out (other tasks, or the caller's):**
- Reading `terminal_productivity_profiles`, `baplie_files`, `container_manifest_entries`, `port_profiles` from the database (AI-055/056; `common/db/tables.py` has no `terminal_productivity_profiles` yet). The loader's `ManifestEntry` has no `port_of_discharge`, so the caller needs a different read; recorded as a follow-up.
- P90 and ML service time (Phase 2, M2); the solver (AI-055); writing `recommendation_options` (AI-058); the rationale (AI-057).
- The `loading_estimated` field on `berthing_requests` (Backend, CT-17), the BAPLIE gate in CT-10, `port_code` seed (CT-18): DEC-28 follow-ups, not ours.
- Editing `docs/ref/` other than the one Proposed entry; CLAUDE.md.

## File structure

| File | New / existing | Responsibility |
|---|---|---|
| `part2/service_time.py` | new | the three functions and value types |
| `tests/unit/part2/test_service_time.py` | new | all tests |
| `part2/README.md` | existing | one section "Service time, Phase 1 (AI-052, DEC-28)" |
| `docs/ref/ATLANTECH_Decisions.md` | existing | one Proposed entry "AI-052 · …" under "AI task decisions" |
| `docs/tasks/status/AI-052.md`, `docs/tasks/WORK_STATUS.md` | new / existing | records |
| this plan | new | committed with the task if the approved scope lists it |

## Review Focus

1. A container vessel with no ACTIVE BAPLIE → excluded `MISSING_MOVES`, never moves 0 (test in Task 1).
2. `port_code` unset or empty → `ConfigurationError`, never discharge 0 (Task 1).
3. Loading count 0 given explicitly is a real 0, not "empty" (so `loading_estimated` is False) (Task 1).
4. Profile edges: `valid_from` = date, `valid_to` = date (both inclusive), `valid_to` = yesterday (expired), vessel-type row beats the default, two equal rows → ambiguous (Task 2).
5. Rounding up at the 0.01 edge, and the result never violating `chk_ro_p90` / `chk_ro_values` (Task 3).

---

### Task 1: Moves (DEC-28)

**Files:** Create `part2/service_time.py`; Test `tests/unit/part2/test_service_time.py`

**Interfaces — Produces:**
- `@dataclass(frozen=True) class Moves: discharge: int; loading: int; loading_estimated: bool` with property `total -> int`.
- `count_moves(*, has_active_baplie: bool, discharge_ports: Iterable[str | None], port_code: str | None, loading_count: int | None) -> Moves | None`. `None` means moves unknown (the caller excludes with `MISSING_MOVES`).

- [ ] **Step 1: failing tests.** `test_discharge_counts_only_this_port` (ports `["EGDAM","EGDAM","CNSHA",None]`, `port_code="EGDAM"`, `loading_count=None` → discharge 2, loading 2, `loading_estimated` True, total 4). `test_given_loading_is_used` (`loading_count=5` → loading 5, `loading_estimated` False, total 7). `test_zero_loading_is_a_real_zero` (`loading_count=0` → loading 0, estimated False). `test_no_active_baplie_gives_none` (`has_active_baplie=False` → `None`, even if ports are passed). `test_unset_port_code_raises` (`None` and `""` → `common.config.ConfigurationError`). `test_negative_loading_raises` (`ValueError`).
- [ ] **Step 2:** `pytest tests/unit/part2/test_service_time.py -q` → fails (module missing).
- [ ] **Step 3:** implement `Moves` and `count_moves`. Order of checks: BAPLIE not active → `None`; `port_code` unset → raise; then count (compare after `.strip().upper()` is **not** done: the code is compared exactly, as stored).
- [ ] **Step 4:** the same command → all pass.

### Task 2: Profile resolution

**Interfaces — Produces:**
- `@dataclass(frozen=True) class ProductivityProfile: id: int; terminal_id: int; vessel_type_id: int | None; productivity_rate: Decimal; rate_unit: str; fixed_overhead_minutes: int; valid_from: date; valid_to: date | None`.
- `resolve_profile(profiles: Iterable[ProductivityProfile], *, terminal_id: int, vessel_type_id: int, on_date: date) -> tuple[ProductivityProfile | None, str | None]`, returning `(profile, None)`, `(None, "NO_VALID_PROFILE")` or `(None, "AMBIGUOUS_PROFILE")`.

- [ ] **Step 1: failing tests** (names and values): `test_valid_from_and_valid_to_are_inclusive` (dates equal to each edge resolve; the day before `valid_from` and the day after `valid_to` give `NO_VALID_PROFILE`); `test_open_ended_profile_is_valid` (`valid_to=None`); `test_vessel_type_row_beats_terminal_default`; `test_default_used_when_no_type_row`; `test_other_terminal_and_other_type_ignored`; `test_two_equal_rows_are_ambiguous`; `test_no_profiles_gives_no_valid_profile`.
- [ ] **Step 2:** run → fails.
- [ ] **Step 3:** implement. Filter by terminal and date; split into exact-type and default; if the exact-type set is non-empty use it, else the default set; 0 → `NO_VALID_PROFILE`, 1 → the row, more → `AMBIGUOUS_PROFILE`.
- [ ] **Step 4:** run → pass.

### Task 3: The formula and the result

**Interfaces — Consumes:** Tasks 1 and 2. **Produces:**
- `@dataclass(frozen=True) class ServiceTimeResult: p50_hours: Decimal | None; p90_hours: None; method: str` (always `"FORMULA"`); `excluded_reason: str | None`; `flags: tuple[str, ...]`; `inputs: Mapping[str, object]` (discharge, loading, loading_estimated, moves, profile_id, productivity_rate, rate_unit, fixed_overhead_minutes, on_date).
- `compute_service_time(*, vessel_type_code: str, vessel_type_id: int, terminal_id: int, moves: Moves | None, profiles: Iterable[ProductivityProfile], on_date: date) -> ServiceTimeResult`.
- Constants: `CONTAINER_VESSEL_TYPE = "CONTAINER"`, flag `loading_estimated`, reasons `MISSING_MOVES`, `NO_VALID_PROFILE`, `AMBIGUOUS_PROFILE`, `BASIS_UNDEFINED`, `PROFILE_UNIT_MISMATCH`, `NON_POSITIVE_SERVICE_TIME`.

- [ ] **Step 1: failing tests.** `test_hand_value_whole_hours`: discharge 450, loading 450 (moves 900), rate `25.00` MOVES_PER_HOUR, overhead 30 min → `p50_hours == Decimal("36.50")`, `p90_hours is None`, `method == "FORMULA"`. `test_rounds_up`: moves 100, rate `30.00`, overhead 15 → 3.3333 + 0.25 = 3.5833 → `Decimal("3.59")`. `test_exact_value_not_bumped`: moves 60, rate `30.00`, overhead 0 → `Decimal("2.00")`. `test_loading_estimated_flag_is_carried` (flag in `flags`, `inputs["loading_estimated"]` True). `test_inputs_record_discharge_loading_moves_and_profile`. `test_moves_none_excluded_missing_moves` (reason, `p50_hours is None`). `test_no_profile_excluded_with_reason` (`NO_VALID_PROFILE`). `test_ambiguous_profile_excluded`. `test_non_container_excluded_basis_undefined` (`vessel_type_code="BULK_CARRIER"`, even with a valid profile; reason `BASIS_UNDEFINED`). `test_container_with_non_moves_unit_excluded`. `test_zero_moves_zero_overhead_excluded_non_positive`. `test_zero_moves_with_overhead_is_overhead_only` (overhead 30 → `Decimal("0.50")`). `test_non_container_with_moves_none_is_basis_undefined` (order: the vessel-type check comes before the moves check, so the reason names the real cause).
- [ ] **Step 2:** run → fails.
- [ ] **Step 3:** implement. Order: not container → `BASIS_UNDEFINED`; moves `None` → `MISSING_MOVES`; resolve profile; unit check; compute `Decimal(moves.total) / rate + Decimal(overhead) / 60` with an explicit `Context(prec=28)`; `quantize(Decimal("0.01"), rounding=ROUND_CEILING)`; `<= 0` → `NON_POSITIVE_SERVICE_TIME`.
- [ ] **Step 4:** run → pass.
- [ ] **Step 5 (schema check, criterion 3):** `test_result_satisfies_schema_checks`: for every non-excluded result in a small grid, a Python mirror of `chk_ro_p90` (`method == "ML"` ⇔ P90 not None, and P90 None or ≥ P50) and `chk_ro_values` (P50 > 0, fits `decimal(6,2)`: < 10000) holds. `test_schema_checks_have_not_drifted`: read `docs/ref/db/schema.sql` and assert the `chk_ro_p90` and `chk_ro_values` lines still contain the expressions the mirror encodes (so a schema change fails the test instead of silently breaking the mirror). **No MySQL integration test is added**: the function writes nothing.

### Task 4: Docs and records

- [ ] **Step 1:** README section "Service time, Phase 1 (AI-052, DEC-28)": signature, inputs the caller supplies, exclusion reasons, the rounding, the non-container consequence.
- [ ] **Step 2:** the Proposed `AI-052 · Service time Phase 1: …` entry in `docs/ref/ATLANTECH_Decisions.md` ("AI task decisions", Status `Proposed`, Owner AI Team, rulings 1 to 5 as a `Proposed change` row in the template format, follow-ups below). DEC-28 is **not** edited.
- [ ] **Step 3:** `docs/tasks/status/AI-052.md`, and the AI-052 row in `docs/tasks/WORK_STATUS.md`, set to `IN PROGRESS` now and `IN REVIEW` before publishing.
- [ ] **Step 4:** run the full checks (below) and record the actual results.

## Tests and commands

```
ruff check .
ruff format --check .
mypy
pytest tests/unit/part2/test_service_time.py -q
pytest tests/unit -q
pytest -q          # integration tests are skipped without MySQL and Redis; say so in the record
```

## Acceptance criteria → verification

| Criterion (backlog, exact) | Verified by |
|---|---|
| "Formula tests with hand values" | Task 3 `test_hand_value_whole_hours`, `test_rounds_up`, `test_exact_value_not_bumped` |
| "No valid profile → candidate excluded with reason" | Task 3 `test_no_valid_profile_excluded…`; Task 2 edge tests; also `AMBIGUOUS_PROFILE`, `MISSING_MOVES` |
| "P90 NULL for FORMULA (schema check passes)" | Task 3 Step 5: `p90_hours is None`, the `chk_ro_p90` mirror, and the drift test against `schema.sql` |

## Dependencies

- AI-050: DONE (PR #26, `9e0ae86`, record on `develop`). Not used by the function.
- AI-005: DONE (record on `develop`). DEC-28 Closed 2026-11-05 (the moves rule). DEC-20 / DEC-21 not used.
- Cross-team: Backend (CT-17 loading-count field; CT-10 BAPLIE gate and `MISSING_MOVES` value; CT-18 `port_code`), as DEC-28 open items 1 to 3 and 6. Terminal operations: loading ≈ discharge for Damietta (open item 5).

## Risks

- **Non-container vessels get no service time** (ruling 4): a coordination risk for AI-055 and the demo data; it needs the Leads Council's acceptance or a basis.
- **Early solves without a BAPLIE** are excluded with `MISSING_MOVES` and nothing re-triggers them (DEC-28 open item 2, Backend).
- **The caller needs a read that doesn't exist yet** (profiles, discharge ports by BAPLIE, `port_code`): AI-055/056 must add it; the loader's `ManifestEntry` lacks `port_of_discharge`.
- **Loading ≈ discharge** may be wrong for Damietta: service time then errs in either direction; the flag keeps the estimate visible.
- **Reference-date choice** (ruling 1) may differ from what the Backend expects; low impact while profiles change rarely.
- No performance risk: O(profiles) per request × terminal.

## Contract / decision changes

- One new **Proposed** entry "AI-052" under "AI task decisions" in `docs/ref/ATLANTECH_Decisions.md` (rulings 1 to 5). No new official ID. DEC-28 (Closed) is applied, not changed; no contract changes.
- Not done by this task, listed as follow-ups: DEC-28 open items 1 to 7 (owners as in DEC-28), and "Implementation: AI-052 (not yet implemented)" in DEC-28 is a Closed entry I will not edit; the Leads Council can update it after merge.
