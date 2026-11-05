# AI-015 Test Harness and Synthetic Scenario Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **ATLANTECH override:** no step commits, stages or pushes. Publishing happens only through `/atlantech-review-and-publish AI-015`.

**Goal:** A seeded generator for synthetic port scenarios at two sizes (minimum and reference scale), and a fixture loader that loads them into the real test schema, every dataset labelled SYNTHETIC.

**Architecture:** `tools/scenario_generator/` builds a scenario as plain data (a metadata block plus rows per table) from a seed with `random.Random(seed)`, no wall clock, and writes it as JSON named `SYNTHETIC_<size>_seed<N>.json`. `tests/support/scenarios.py` reads such a file, refuses anything not labelled SYNTHETIC, and inserts the rows into a port database with foreign key checks ON, so parent rows are real (the AI-013 follow-up). Sample files and the seed register live in `tests/fixtures/`.

**Tech Stack:** Python 3.14, stdlib `random`/`json`/`datetime`/`decimal`, PyMySQL (loader, test-only), pytest, the AI-013 `port_db` fixture and `docs/ref/db/schema.sql`.

**Spec:** Backlog entry `AI-015` in `docs/tasks/ATLANTECH_AI_TASKS.md` (§5). Reference figures: `Master_Context.md` §4 (Damietta: 8 terminals, 36 berths, about 26 vessels per day; scales from 1 terminal / 5 berths to 10 / 50) and NFR-CAP-1 (`UML_Context.md` line 183). No separate design document: the user waived the interview and approved the task on 2026-11-05.

## Global Constraints

- Acceptance criteria (verbatim): "Generator reproduces identical scenarios from a seed" · "Both configuration sizes load into the test schema" · "Synthetic label present in file names and metadata".
- "Seeded randomness; store scenario seeds. Never present results on synthetic data as operational performance."
- "Distribution choices are assumptions; document them."
- Locations proposed by the backlog: `tests/fixtures`, `tools/scenario_generator`.
- Minimum scenario: 1 terminal / 5 berths. Reference scenario: 8 terminals / 36 berths, about 26 vessels per day.
- Never uses the real port's name or UN/LOCODE; `port_profiles.port_code` stays NULL.
- Reads the schema in `docs/ref/db/schema.sql` only (mirror at PortHub `b4d2deb`); no schema change.
- Tool config: Ruff line length 100, mypy strict, UTC for every datetime (`common.time`/`datetime.UTC`), no naive datetimes (a scan test exists for production code).
- No commits, pushes or staging.

## Review Focus

- Same seed, different process or different day: identical bytes (no wall clock, no set/dict-order or hash randomisation dependence).
- Different seeds produce different data, so a seed isn't silently ignored.
- Every row passes the schema's CHECK constraints (beam < loa, `max_vessel_loa` <= `length`, Cb in (0.3, 1.0), IMO 7 digits, `departure_draft` > 0) and FK order, proved by loading with foreign key checks on.
- A file without the SYNTHETIC label, or with `synthetic: false`, is refused by the loader.
- Loading twice into the same database fails cleanly or is refused (no half-loaded scenario): the loader runs in one transaction and rolls back on error.
- Vessel draft never exceeds `max_draft`; requested terminal exists and its type can serve the vessel.

---

## Distribution assumptions (documented in `tools/scenario_generator/README.md` and in each file's metadata)

All are assumptions, not Damietta data:
1. **Size shape.** `minimum`: 1 terminal, 5 berths. `reference`: 8 terminals, 36 berths (Master_Context §4). Berths are spread over terminals as evenly as possible; every berth belongs to exactly one terminal.
2. **Terminal types.** Reference: 5 CONTAINER, 3 NON_CONTAINER. Minimum: 1 CONTAINER.
3. **Berths.** Length uniform 180–400 m (container) or 150–300 m (non-container); `max_vessel_loa` = length minus 10 m; depth alongside uniform 11–16 m, datum `LAT`.
4. **Arrivals.** Reference: mean 26 requests per day; minimum: mean 26 × 5/36 ≈ 4 per day (proportional to berths). The daily count is drawn as mean plus integer noise in [-3, +3] (floor 1); ETAs are uniform within the day. Default horizon 7 days from a fixed start date `2026-01-05T00:00:00Z`.
5. **Vessels.** Types GENERAL_CARGO, CONTAINER, BULK_CARRIER, TANKER with weights 0.15/0.55/0.2/0.1 at reference scale. LOA, beam, draft and tonnage are drawn with `random.triangular` inside per-type bounds; beam is always below LOA, arrival draft is 60–95 % of `max_draft`. Block coefficient uniform 0.55–0.85. Each request is for a distinct vessel (IMO numbers are unique); the vessel pool is the request count.
6. **Requests.** Source EXTERNAL via one synthetic external system; status SUBMITTED; the requested terminal is drawn among terminals whose type fits the vessel type (container vessels → CONTAINER terminals).
7. **Tugboats.** Reference 12, minimum 3; power 40–80 tonnes bollard pull, all AVAILABLE.
8. **Channel.** One navigation channel with 4 waypoints, depth 16 m, width 250 m, limit 10 knots, datum `LAT` (equal to berth datum).
9. **Not generated** (no task needs them yet): users, tides, weather, pilots, tug masters, containers and BAPLIE data, recommendations. Later tasks extend the generator; AI-022 supplies real master data.

## File Structure

| File | New/Existing | Responsibility |
|---|---|---|
| `tools/__init__.py`, `tools/scenario_generator/__init__.py` | New | Package markers |
| `tools/scenario_generator/model.py` | New | `ScenarioSize` enum, `SizeProfile` (per-size constants), `Scenario` dataclass, `SYNTHETIC_PREFIX`, `GENERATOR_VERSION` |
| `tools/scenario_generator/generate.py` | New | `generate(size, seed, days) -> Scenario` |
| `tools/scenario_generator/io.py` | New | `scenario_filename`, `to_json`, `write_scenario` |
| `tools/scenario_generator/__main__.py` | New | CLI: `python -m tools.scenario_generator --size minimum --seed 1 --out tests/fixtures` |
| `tools/scenario_generator/README.md` | New | Usage, label rule, the assumptions above |
| `tests/support/scenarios.py` | New | `read_scenario`, `load_scenario`, `LOAD_ORDER` |
| `tests/fixtures/scenario_seeds.json` | New | Seed register: scenario name → size, seed, days |
| `tests/fixtures/SYNTHETIC_minimum_seed1.json`, `SYNTHETIC_reference_seed1.json` | New | Sample scenario files (verification evidence) |
| `tests/unit/tools/test_generate.py`, `test_io.py`, `test_cli.py`, `tests/unit/test_scenario_loader.py`, `tests/unit/test_fixture_files.py` | New | Unit tests |
| `tests/integration/test_scenario_load.py` | New | Both sizes into the real schema |
| `pyproject.toml` | Existing | Add `tools` to mypy `files` and coverage `source`; per-file ignore S311 for `tools/scenario_generator/**` (seeded, non-security randomness) |
| `README.md` | Existing | Line 115: tests/fixtures and tools/scenario_generator now exist |
| `docs/ref/ATLANTECH_Decisions.md` | Existing | New "AI task decisions" entry `AI-015`, Status `Proposed` |
| `docs/tasks/status/AI-015.md`, `docs/tasks/WORK_STATUS.md` | New / Existing | Records |

---

### Task 1: Model and generator

**Files:** Create `tools/__init__.py`, `tools/scenario_generator/__init__.py`, `model.py`, `generate.py`; Modify `pyproject.toml`; Test `tests/unit/tools/__init__.py`, `tests/unit/tools/test_generate.py`.

**Interfaces:**
- Produces: `class ScenarioSize(StrEnum): MINIMUM = "minimum"; REFERENCE = "reference"`; `SYNTHETIC_PREFIX: Final = "SYNTHETIC"`; `@dataclass(frozen=True) class Scenario: metadata: dict[str, object]; tables: dict[str, list[dict[str, object]]]`; `def generate(size: ScenarioSize, seed: int, days: int = 7) -> Scenario`.
- `metadata` keys: `synthetic` (True), `label` ("SYNTHETIC — generated test data, not operational data"), `size`, `seed`, `days`, `generator_version`, `start_date`, `counts` (rows per table), `assumptions` (list of strings from the section above).
- `tables` keys, in insert order: `port_profiles, terminals, berths, berth_terminals, navigation_channels, channel_waypoints, tugboats, vessel_types, vessels, external_systems, berthing_requests`. Rows carry explicit integer `id`s (1-based) and explicit foreign keys; datetimes are `"YYYY-MM-DD HH:MM:SS"` UTC strings, decimals are strings.

- [ ] **Step 1: Failing tests** in `test_generate.py`:
  - `test_minimum_has_one_terminal_and_five_berths` and `test_reference_has_eight_terminals_and_thirty_six_berths` (counts from `tables`, and `berth_terminals` has one row per berth).
  - `test_reference_averages_about_26_requests_a_day`: `days=7` → total requests between 26*7-21 and 26*7+21.
  - `test_same_seed_gives_identical_scenarios` (`==` on both fields, also equal `json` text) and `test_different_seeds_differ`.
  - `test_metadata_is_labelled_synthetic` (`synthetic is True`, `label` starts with "SYNTHETIC", `assumptions` non-empty, `seed` and `size` recorded, `counts` equal real counts).
  - `test_rows_satisfy_schema_checks`: beam < loa, `max_vessel_loa` <= length, 0.3 < Cb < 1.0, IMO matches `^[0-9]{7}$` and is unique, arrival draft <= vessel `max_draft`, `departure_draft` None.
  - `test_foreign_keys_resolve_inside_the_scenario` (every `*_id` points at an existing row) and `test_container_vessels_request_container_terminals`.
  - `test_no_real_port_identity`: `port_profiles[0]["port_code"] is None` and its name starts with "SYNTHETIC".
  - `test_names_carry_the_label`: vessel and terminal names start with "SYNTHETIC".
  - `test_rejects_bad_arguments`: `days < 1` raises `ValueError`.
- [ ] **Step 2:** Run `uv run --frozen pytest tests/unit/tools/test_generate.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3:** Implement `model.py` and `generate.py` per the assumptions section. Use one `random.Random(seed)` created inside `generate`; draw in a fixed order; sort nothing by hash; compute ETAs from the fixed start date with `timedelta`.
- [ ] **Step 4:** Add `"tools"` to mypy `files` and coverage `source`; add the S311 per-file ignore with a one-line comment. Run the Step 2 command. Expected: PASS.

### Task 2: Files, seed register and CLI

**Files:** Create `io.py`, `__main__.py`, `README.md`, `tests/fixtures/scenario_seeds.json`, the two sample files; Test `tests/unit/tools/test_io.py`, `test_cli.py`, `tests/unit/test_fixture_files.py`.

**Interfaces:**
- Consumes: `generate`, `Scenario`, `ScenarioSize`.
- Produces: `scenario_filename(size: ScenarioSize, seed: int) -> str` (`SYNTHETIC_<size>_seed<seed>.json`); `to_json(scenario: Scenario) -> str` (`json.dumps(..., indent=2, sort_keys=True)` plus trailing newline); `write_scenario(scenario: Scenario, directory: Path) -> Path`; `main(argv: list[str] | None = None) -> int` with `--size`, `--seed`, `--days`, `--out`.

- [ ] **Step 1: Failing tests:**
  - `test_filename_starts_with_synthetic`.
  - `test_write_scenario_writes_a_synthetic_named_file_and_returns_its_path`.
  - `test_json_round_trips_to_the_same_scenario`.
  - `test_cli_writes_the_file_and_prints_its_path` and `test_cli_same_arguments_write_identical_bytes` (two temp dirs, byte equality).
  - `test_cli_rejects_unknown_size` (argparse exit code 2).
  - `test_committed_samples_match_regeneration`: for each entry in `scenario_seeds.json`, regenerating gives exactly the bytes of the committed file, and every file in `tests/fixtures/` starting with anything other than `SYNTHETIC_` fails (only `scenario_seeds.json` is exempt).
- [ ] **Step 2:** Run `uv run --frozen pytest tests/unit/tools -v`. Expected: FAIL.
- [ ] **Step 3:** Implement `io.py` and `__main__.py`. Seed register format: `{"minimum_seed1": {"size": "minimum", "seed": 1, "days": 7}, "reference_seed1": {...}}`. Generate the two sample files with the CLI; do not hand-edit them.
- [ ] **Step 4:** Write `README.md` (usage, the label rule, never present results as operational performance, the assumptions list). Run Step 2 command. Expected: PASS.

### Task 3: Fixture loader

**Files:** Create `tests/support/scenarios.py`; Test `tests/unit/test_scenario_loader.py`.

**Interfaces:**
- Produces: `LOAD_ORDER: Final[tuple[str, ...]]` (the table order above); `class ScenarioNotSyntheticError(ValueError)`; `def read_scenario(path: Path) -> Scenario` (refuses a file whose name doesn't start with `SYNTHETIC_`, or whose metadata lacks `synthetic: true` or a label starting "SYNTHETIC"); `def load_scenario(conn: pymysql.connections.Connection[Any], scenario: Scenario) -> dict[str, int]` (sets `foreign_key_checks = 1` for the session, inserts in `LOAD_ORDER` inside one transaction, rolls back and re-raises on error, returns rows inserted per table).

- [ ] **Step 1: Failing tests** (no DB; fake connection recording SQL): refuses wrong filename; refuses `synthetic: false`; refuses missing label; inserts tables in `LOAD_ORDER`; enables foreign key checks before the first insert; rolls back and re-raises when an insert fails; returns the counts.
- [ ] **Step 2:** Run `uv run --frozen pytest tests/unit/test_scenario_loader.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement with parameterised `INSERT` statements built from column names taken from the row keys (identifiers are the scenario's own keys, validated against `^[a-z_]+$`).
- [ ] **Step 4:** Run the Step 2 command. Expected: PASS.

### Task 4: Real-schema integration

**Files:** Test `tests/integration/test_scenario_load.py`.

- [ ] **Step 1: Failing tests** (marked `integration`, own database per module via `create_port_database` / `drop_port_database`; the session `root()` connection):
  - `test_minimum_scenario_loads_into_the_real_schema` and `test_reference_scenario_loads_into_the_real_schema`: load the committed sample files; `SELECT COUNT(*)` per table equals the metadata counts; for the reference file 8 terminals and 36 berths.
  - `test_loaded_rows_satisfy_foreign_keys`: with foreign key checks on, a join finds no `berthing_requests` row without its vessel and terminal.
  - `test_a_failed_load_leaves_nothing_behind`: corrupt one row (beam >= loa); `load_scenario` raises `pymysql.err.IntegrityError`-family error and every table count stays 0.
  - `test_loading_the_same_scenario_twice_is_refused`: second load raises and counts are unchanged.
- [ ] **Step 2:** Run with services: `$env:ATLANTECH_REQUIRE_SERVICES="1"; uv run --frozen pytest tests/integration/test_scenario_load.py -v`. Expected: FAIL before Task 3 is in place, PASS after. If MySQL/Redis are not available locally, state that the integration tests were skipped and run them in CI; do not claim they passed.

### Task 5: Records, documentation and gates

**Files:** Modify `README.md:115`, `docs/ref/ATLANTECH_Decisions.md` (new `AI-015` entry in "AI task decisions" and its summary row), `docs/tasks/status/AI-015.md`, `docs/tasks/WORK_STATUS.md`.

- [ ] **Step 1:** README line 115: tests live in `tests/unit`, `tests/integration`, `tests/support`, `tests/fixtures`; `tools/scenario_generator/` exists.
- [ ] **Step 2:** Decisions entry `AI-015 · Test harness and scenario generator`, Status `Proposed`, a `Proposed change` row recording: locations (OQ-7 for tests and tools), JSON format and naming, label rule, seed register, assumptions summary, loader runs with foreign key checks on; Approval row: "Task justification (PROPOSED in the backlog) approved by Mostafa Rashwan, Lead Council, 2026-11-05, to proceed with implementation. Not approved as a team decision." Nothing marked Closed.
- [ ] **Step 3:** Update the status record with actual validation output; update the tracker row.
- [ ] **Step 4: Full gates**, report actual output: `uv run --frozen ruff check .`, `ruff format --check .`, `mypy`, `pytest -v --cov --cov-report=term-missing`, and the Gitleaks check used for AI-013 on each changed file if a container runtime is available (otherwise say it was not run).
- [ ] **Step 5:** Stop. Direct the user to `/atlantech-review-and-publish AI-015`. No commit.

## Acceptance criteria → verification

| Criterion | Verified by |
|---|---|
| Generator reproduces identical scenarios from a seed | `test_same_seed_gives_identical_scenarios`, `test_cli_same_arguments_write_identical_bytes`, `test_committed_samples_match_regeneration` |
| Both configuration sizes load into the test schema | `test_minimum_…` and `test_reference_scenario_loads_into_the_real_schema` |
| Synthetic label present in file names and metadata | `test_filename_starts_with_synthetic`, `test_metadata_is_labelled_synthetic`, loader refusal tests |

## Self-review

- Spec coverage: fixture loader (Task 3), both sizes (Tasks 1, 4), labelling (Tasks 1–3), seeds stored (Task 2), assumptions documented (README, metadata, Decisions entry). Real DDL is the mirror, since `PortSync.sql` isn't in the repository.
- Types: `Scenario`, `ScenarioSize`, `generate`, `LOAD_ORDER`, `load_scenario` are used with the same names throughout.
- Out of scope: real Damietta master data (AI-022), tides/weather/pilots/containers, any worker handler, CI workflow changes.
