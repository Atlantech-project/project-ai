# AI-054 · Implement tug-requirement computation — plan

Written without the Superpowers skills, which are not listed in this session. The user approved this plan in the conversation on 2026-11-03 ("Plan approved, with these answers"). No step commits: publishing happens only through `/atlantech-review-and-publish AI-054`.

Contracts and decisions were read from PortHub `main` at `e118093`.

## Task

- **ID:** AI-054 · Implement tug-requirement computation (P5, P0, complexity S, flags A, X)
- **Branch:** `feature/AI-054-tug-requirement-computation` (from `develop` at `0ccebd3`)

## Scope

**In:**
- `part2/tugs.py`: a pure function, one result per berthing request, with `n_min`, `n_cap`, `bp_req`, `eligible_tugs` and `flags`. No solver import.
- `part2/tug_rules.json`: every number, with its `source` and an `interim` note.
- DEC-20 on PortHub: stays Open, with the full Recommendation (provisional, PROPOSED) and "AI lead approval: Menna Gamal (AI lead, @MennaGamal-87), 2026-11-03, pending Leads Council".
- A recorded scope exception for AI-005, in AI-054's status record.

**Out:**
- CP-SAT constraints (AI-055).
- Reading the database (AI-013, AI-050). The caller passes the values.
- Tug availability (AI-055, DEC-32).
- The rationale text for "unvalidated" (AI-057).
- A Backend `pilot_requested` field.
- Thruster credit, and wind-based bollard pull.
- Editing the backlog.
- Editing `docs/ref/`, which is refreshed from PortHub after the merge.

## User decisions (2026-11-03)

1. This work is AI-054. CP-SAT constraints stay in AI-055.
2. DEC-20 stays Open, because the Leads Council closes decisions (user, 2026-11-03, replacing an earlier answer to close it). AI-054 proceeds under a recorded scope exception. The backlog gets only the notes the user asked for, on AI-090 and AI-055.
3. Cb: the request's `block_coefficient`, with the type table if it's missing or outside [0.50, 0.90], and flag `cb_fallback_used`.
4. Draught: `berthing_requests.arrival_draft`, one result per request; if missing, `vessels.max_draft` with flag `max_draft_used`. The term "vessel move" is avoided.
5. `pilot_requested: bool | None`. Zero tugs only when GT is below the threshold and it's `False`. `None` applies the table with `pilot_request_unknown`.
6. Tugs not rated in bollard pull are excluded with `tug_power_not_bollard_pull`, with no conversion.
7. `T_COMPULSORY` = 1000, interim and conservative, until the Alexandria Port Authority confirms.
8. `part2/tug_rules.json`, recorded as a deviation from AI-012.
9. `LNG_CARRIER` stays "other", as a DEC-20 open item for the Tug Manager.
10. LOA bands ≤60, ≤122, ≤200, ≤280; both sets of boundaries are tested.

**Set during implementation, for the user to check:**
- `cb_fallback_used` appears only when Cb is actually used, which means bulk carriers and tankers. Other types use the floor only and don't need Cb.
- A pilot override also applies below the threshold. `N_cap` follows the overridden `N_min`. Eligibility stays by the LOA band.
- `rules_unvalidated` is on every result until the rules file's status is `APPROVED`, as DEC-20's recommendation asks.
- A missing or non-positive LOA, beam, GT or draught raises `ConfigurationError`, because none has a conservative default.

**Sources checked on 2026-11-03:** the MPA PDF, whose vessels-with-power column matches the table; and the seanews page, which confirms the formula and its example but names neither Hensen nor ship types. `BP_floor` is derived, not in MPA.

## Files likely to change

| File | New or existing | Change |
|---|---|---|
| `part2/__init__.py`, `part2/tugs.py`, `part2/tug_rules.json` | New | The module and rules |
| `tests/unit/part2/__init__.py`, `tests/unit/part2/test_tugs.py` | New | Tests |
| `pyproject.toml` | Existing | `part2` in mypy and coverage |
| `part2/README.md` | Existing | How to use it |
| `docs/tasks/status/AI-054.md`, `docs/tasks/WORK_STATUS.md` | New, existing | Records |
| This plan | New | Committed with the task, as with AI-011 |
| `docs/tasks/ATLANTECH_AI_TASKS.md` | Existing | One note on AI-055, at the user's instruction |
| PortHub `contracts/ATLANTECH_Decisions.md` | Existing, another repository | DEC-20 entry and summary row, on its own branch |

## Dependencies

| Item | Status | Evidence |
|---|---|---|
| AI-005 | **Not done; scope exception** | DEC-21, DEC-22 and DEC-28 are Open. DEC-20 is the only part AI-054 needs |
| DEC-20 | Open, and stays Open: AI lead approved, pending the Leads Council | Draft on a local branch |
| DEC-28 | Open | Not used: it defines cargo moves, and AI-054 works per request |
| CT-17 | Approved v1.0 | `vessels`, `berthing_requests`, `tugboats` in `schema.sql` |

**Cross-team (flag X, and Backend):** the Tug Manager and Marine Safety Officer validate the rules; the Backend adds `pilot_requested`; AI-055 consumes this.

## Tests

TDD, unit tests in `tests/unit/part2/test_tugs.py`, with the project's full checks:
```
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -v --cov --cov-report=term-missing
```

## Risks

- **Rules are from literature and unvalidated:** tagged PROPOSED, and flagged on every result.
- **`T_COMPULSORY`:** two official sources disagree. 1000 is the conservative one.
- **A fleet rated in HP or kW:** no tug is eligible, so every request is infeasible. The Tug Manager should enter bollard pull. No fleet data exists yet.
- **`pilot_requested` doesn't exist:** until it does, ships below the threshold always get the table with a flag, never zero tugs.
- **Rules file at deployment:** AI-090 must ship it, or `load_rules` raises. A change needs a deploy.
- **Band jumps:** a ship at GT 75,000 goes from 2 tugs to 4, whatever its length. This is as the table says.
- **Dead ships:** MPA's table has a separate, higher column for vessels without power. It isn't used, because no field says which applies.

## Contract / decision changes

- **DEC-20 (PortHub PR):** stays Open, with a `Proposed change` row and the full Recommendation. The PR asks the Leads Council, including Backend, to review it.
- **No change** to CT-13 (`TUG_COUNT`), CT-17 or CT-18.
- **Deviation from AI-012:** recorded here, in `part2/README.md`, the status record and DEC-20.

## Acceptance criteria

| Criterion (quoted from the backlog) | Verification |
|---|---|
| "Worked examples reproduced" | `test_the_worked_example`: Δ 76,752 t, BP_mass 86.0512, BP_req 87, N_min 2 |
| "Unit handling for tug_power_unit tested" | `test_tugs_not_rated_in_bollard_pull_are_excluded_and_flagged` and neighbours |

Backlog guidance: "Implement exactly the approved formula with its worked examples as tests."
