# Synthetic scenario generator (AI-015)

Makes repeatable port scenarios for testing Parts 2 and 3 before real data exists. **Everything it writes is SYNTHETIC test data. Results measured on it are never operational performance.**

## Use

```
uv run python -m tools.scenario_generator --size minimum --seed 1 --out tests/fixtures
uv run python -m tools.scenario_generator --size reference --seed 1 --days 7 --out tests/fixtures
```

- `--size minimum`: 1 terminal and 5 berths. `--size reference`: 8 terminals and 36 berths, about 26 requests a day (Master_Context §4, NFR-CAP-1).
- The same size, seed and days always give the same bytes. The start date is fixed (2026-01-05 00:00:00 UTC) and nothing reads the clock.
- Output: `SYNTHETIC_<size>_seed<N>.json`. Its `metadata` block says `synthetic: true`, carries the label, seed, size, row counts and the assumptions below; the rest holds rows per table, in insert order.
- The seeds of the committed samples are in `tests/fixtures/scenario_seeds.json`. A test regenerates each and compares it byte for byte with the file.

## Loading into a test schema

`tests/support/scenarios.py`: `read_scenario(path)` refuses a file whose name doesn't start with `SYNTHETIC_` or whose metadata isn't labelled; `load_scenario(conn, scenario)` loads it into a port database with foreign key checks on, in one transaction. The schema is the copy in `docs/ref/db/schema.sql`.

## Label rule

File names start with `SYNTHETIC_`. Metadata says `synthetic: true`. Every terminal, berth, tug, vessel, channel and external system name starts with "SYNTHETIC". The port has no UN/LOCODE and sits at latitude 0, longitude 0. IMO numbers have a deliberately wrong check digit, so none can be a real ship.

## Distribution assumptions

These are assumptions, not data from any real port (also in each file's metadata).

| Area | Assumption |
| --- | --- |
| Size | Minimum: 1 terminal, 5 berths. Reference: 8 terminals, 36 berths. Berths are spread over terminals as evenly as possible. |
| Terminal types | Reference: 5 CONTAINER, 3 NON_CONTAINER. Minimum: 1 CONTAINER. |
| Berths | Length uniform 180–400 m (container) or 150–300 m (non-container); `max_vessel_loa` is length minus 10 m; depth alongside uniform 11–16 m, datum LAT. |
| Arrivals | Mean 26 requests a day (reference) or 4 (minimum, 26 × 5/36 rounded), plus integer noise in [−3, +3], floor 1. ETAs uniform within the day. Default horizon 7 days. |
| Vessels | One vessel per request. GENERAL_CARGO, CONTAINER, BULK_CARRIER, TANKER with weights 0.15, 0.55, 0.20, 0.10 when a non-container terminal exists; minimum has container vessels only. LOA, beam ratio and max draft are triangular inside the per-type bounds below. Arrival draft is 60–95% of max draft. Block coefficient uniform 0.55–0.85. GT = 0.25 × LOA × beam × max draft; DWT = 1.4 × GT. |
| Per-type bounds | LOA in m low–high (mode); beam as a share of LOA; max draft in m low–high (mode). GENERAL_CARGO 90–200 (140), 0.15–0.18, 5–10 (7.5). CONTAINER 150–400 (300), 0.14–0.16, 8–16 (13). BULK_CARRIER 150–290 (220), 0.15–0.17, 9–17 (13). TANKER 120–250 (180), 0.15–0.17, 7–14 (10). Net tonnage = 0.6 × GT. |
| Fit | Vessel-to-berth fit is **not** guaranteed: a vessel's LOA or draft can exceed every berth, or the 16 m channel. Feasibility tests must filter or expect that. |
| IMO numbers | Random, unique, with a deliberately wrong check digit. |
| Requests | Source EXTERNAL through one synthetic external system; status SUBMITTED. Container vessels ask for CONTAINER terminals, the others for NON_CONTAINER ones. |
| Tugboats | 12 (reference) or 3 (minimum); 40–80 tonnes bollard pull; all AVAILABLE. |
| Channel | One, depth 16 m, width 250 m, 10 knots, datum LAT, 4 waypoints. |
| Not generated | Users, tides, weather, pilots, tug masters, containers, BAPLIE data, recommendations. Real reference-port master data is AI-022. |

## Reproducibility note

The bytes depend on Python's `random` module (3.14 here). A Python upgrade can change them; `test_committed_samples_match_regeneration` then fails, and the samples are regenerated from the register.
