Note: citations R-1 and R-5 were later corrected; see docs/tasks/status/AI-009.md.

# AI-009 · Specify AI seed data — plan

Written without the Superpowers skills, which are not installed in this session. AI-009 runs under a scope exception the user accepted on 2026-11-01 (prerequisite AI-005 is not done); the user's conditions and their answers of 2026-11-01 are applied here and recorded in `docs/tasks/status/AI-009.md`. No step commits: publishing happens only through `/atlantech-review-and-publish AI-009` after the user's `APPLY CHANGES`. AI-009 is not marked DONE by this plan; it ends IN REVIEW with blocked parts open.

## Task

- **ID:** AI-009 · Specify AI seed data: constraint types, objective terms, rationale templates v1, model registry rows (P0 Decisions and contracts, priority P1, complexity M, flags B, X)
- **Branch:** `feature/AI-009-ai-seed-data-specification` (from `develop` at `f555913`)

## Scope

**In** (only content a source already states):

1. **`docs/ref/ai-payloads/seed-spec.json`**, `spec_version` `"1.0"`, in the CT-18 §2 shape. All seven CT-18 sections are present from 1.0, so filling a blocked section later adds rows (minor bump, CT-18 §2) and never adds a section (major bump):
   - `constraint_types`:

     | code | category | unit | comparator | is_hard_safety_limit | description | Source |
     |---|---|---|---|---|---|---|
     | `MAX_WIND_KN` | ENVIRONMENTAL | KNOTS | MAX_ALLOWED | true | "Maximum sustained wind for entry" | CT-18 §2 (row verbatim) · CT-10 · Arch I-6 |
     | `MIN_UKC_M` | UKC | METRES | MIN_REQUIRED | true | "Minimum under-keel clearance" | CT-13 (code, hard flag) · Arch §7.6 ("minimum UKC from `safety_constraint`") · Arch I-6 · Master_Context §185 |
     | `MAX_WAVE_HEIGHT_M` | ENVIRONMENTAL | METRES | MAX_ALLOWED | true | "Maximum wave height for entry" | Arch §7.1 A4 · Arch I-6 · `environment_forecast_point.wave_height`. New code following the CT-18 / CT-13 naming pattern |

     B2 adds no rows: its LOA, draft and terminal checks use the closed STRUCTURAL codes of CT-10 / CT-13, which are not `constraint_types` rows, and its Marine Safety Officer check reuses the rows above. The `description` texts for `MIN_UKC_M` and `MAX_WAVE_HEIGHT_M` are plain restatements of the code; the reviewer may reword them.
   - `safety_constraints`: `[]` (blocked).
   - `objective_terms`: `WAITING_TIME` "Vessel waiting time", `RESOURCE_COST` "Resource cost" (CT-18 §2 verbatim, DEC-23).
   - `rationale_templates`: `[]` (blocked).
   - `ml_models`: `M2_SERVICE_TIME` GRADIENT_BOOSTING "Berth service time (P50 / P90)" (CT-18 §2 verbatim); `M3_DEMAND_FORECAST` GRADIENT_BOOSTING "Arrivals per demand slot (Phase 2)"; `M4_DELAY_RISK` GRADIENT_BOOSTING "Probability of a significant delay deviation (Phase 2)" (Arch §10: LightGBM regressor / classifier, the same family CT-18 gives M2).
   - `ml_model_versions`: `[]`. Arch §9.5 makes all ML data-gated in the MVP, so no model has a CHAMPION at go-live; CT-18 §2: such a model has no row.
   - `port_settings` (scope extension approved 2026-11-01), values as strings as in the CT-18 §2 example, `value_type`, `min`, `max` exactly as in CT-18 §4:

     | setting_key | value_type | value | min | max |
     |---|---|---|---|---|
     | `part1_stored_data_max_age_hours` | INT | "48" | 1 | 168 |
     | `solver_time_limit_seconds` | INT | "10" | 1 | 120 |
     | `solver_options_per_request` | INT | "3" | 1 | 3 |
     | `solver_option_equivalence_pct` | DECIMAL | "10" | 0 | 50 |
     | `objective_weight_waiting_time` | DECIMAL | "1.0" | 0 | 10 |
     | `objective_weight_resource` | DECIMAL | "1.0" | 0 | 10 |
     | `part1_max_retries` | INT | "3" | 0 | 10 |
     | `validation_timeout_seconds` | INT | "15" | 5 | 60 |
     | `validation_result_ttl_seconds` | INT | "600" | 60 | 3600 |

     `description`: see open point P-1.
2. **`docs/ref/ai-payloads/seed-spec.md`**, the companion: states at the top that this is a **draft, not yet published** to PortHub `contracts/ai/seed-spec.json`, and that the PortHub publication is the actual CT-18 delivery (follow-up, CT-18 owner AI Team); the source of every delivered row; the blocked register below; the extension rule (rows only, minor bump); the open acceptance criteria.
3. **`tests/unit/contracts/__init__.py`** and **`tests/unit/contracts/test_seed_spec.py`** (below).
4. **Records:** `docs/tasks/status/AI-009.md` and the `WORK_STATUS.md` row.

**Out:** `MAX_GUST_KN`, the visibility code, the tide/surge limit, `safety_constraints` values, `rationale_templates`, `ml_model_versions` rows, the `FORECAST_BIAS_CORRECTION` row, every ⟨AI⟩ `port_settings` key, Backend `reference-seed.json`, seeders (AIBD-036), any change to CT-18 or a decision, and the PortHub publication itself.

### Blocked register (goes into `seed-spec.md`)

| Item | Blocked on | Owner |
|---|---|---|
| `MAX_GUST_KN` | Hard-limit flag not documented (Arch I-6 lists wind, wave, visibility, UKC) | Marine Safety Officer · AI Team |
| Visibility code | Unit not documented; the code embeds the unit, so a wrong unit would be a breaking code change | Marine Safety Officer · AI Team |
| Tide/surge limit (A4) | Quantity, unit and comparator not documented | Marine Safety Officer · AI Team |
| `safety_constraints` defaults | DEC-30 (Open), register row TR-10 (AI-008, Proposed) | AI Team, input from the Marine Safety Officer through CT-25 (QA Team) |
| Tug content (`{tug_count}` templates, tug factors, tug codes) | DEC-20 (Open) | AI Team, input from the Tug Manager / Marine Safety Officer |
| Delay-risk templates and factors | DEC-21 (Open) | AI Team |
| Financial-impact ranking content | DEC-22 (Open) | AI Team |
| Service-time / moves templates and factors | DEC-28 (Open) | AI Team |
| `rationale_templates` (all) | The four decisions above; domain review (acceptance criterion 3); bilingual question open | AI Team · domain reviewer |
| `FORECAST_BIAS_CORRECTION` (`ml_models`) | C4 method undecided ("regression or quantile mapping", Arch §9.1) and data-gated (Arch §9.5) | AI Team |
| `ml_model_versions` CHAMPION rows, `artifact_path` | No model has a CHAMPION at go-live (Arch §9.5); filled by AI-070 / C3 | AI Team |
| `weather_pull_hours`, `tide_horizon_days` | CT-18 §7 ⟨AI⟩ values (providers DEC-26, tide DEC-27, both Open) | AI Team |
| `part1_assessment_horizon_hours`, `part1_time_step_minutes`, `part1_min_window_minutes`, `demand_slot_minutes` | DEC-24 (Open) | AI Team |
| `run_stale_after_seconds` | CT-18 §4 / §7 calculation (TR-24) | AI Team |
| `part3_evaluation_cron` | DEC-31 (Open) | AI Team |
| `drift_psi_threshold`, `drift_mae_threshold` | DEC-30 (Open), TR-01 / TR-02 | AI Team |

## Files likely to change

| File | New / existing |
|---|---|
| `docs/ref/ai-payloads/seed-spec.json` | New (approved 2026-11-01) |
| `docs/ref/ai-payloads/seed-spec.md` | New (approved 2026-11-01) |
| `tests/unit/contracts/__init__.py` | New (empty, like the other test packages) |
| `tests/unit/contracts/test_seed_spec.py` | New |
| `docs/tasks/status/AI-009.md` | Existing (created on this branch) |
| `docs/tasks/WORK_STATUS.md` | Existing |

No change to `pyproject.toml`: `tests` is already in mypy `files` and pytest `testpaths`.

## Dependencies

| Item | Status |
|---|---|
| AI-001 | DONE (status record and tracker on `develop`) |
| AI-005 | Not done: DEC-20, DEC-21, DEC-22, DEC-28 Open; DEC-23 Closed. Covered by the 2026-11-01 scope exception |
| DEC-30 / AI-008 | DEC-30 Open; AI-008 register Proposed, unmerged (`3322dbe`) |
| CT-18 v1.0 | Approved; Owner AI Team (`seed-spec.json`), Reviewers Backend Team · AI Team |
| Backend (B) | Seeders consume the published PortHub file (AIBD-036); the Backend reviews the PortHub PR |
| Domain (X) | Template review deferred with `rationale_templates` |

## Tests

TDD: write `test_seed_spec.py` first, run it against the missing file (fails), add the JSON, run again.

Checks, each a separate test:

1. The file parses; top-level keys are exactly `spec_version` and the seven CT-18 sections, in the CT-18 order; `spec_version` matches `^1\.\d+$`.
2. Every section is a list; no object anywhere has a key `id` or ending in `_id` (codes, never ids).
3. `constraint_types`: keys exactly `code, category, unit, comparator, is_hard_safety_limit, description`; `category` ∈ ConstraintCategory, `unit` ∈ ConstraintUnit, `comparator` ∈ ConstraintComparator (ClassDiagramContext line 139); `code` unique, upper snake case, ≤ 60 characters; `is_hard_safety_limit` boolean.
4. Every `constraint_type_code` anywhere in the file exists in `constraint_types`.
5. `objective_terms`: keys `code, name`; codes unique; exactly the DEC-23 codes.
6. `ml_models`: `model_key` ∈ ModelKey; unique; `algorithm_family` non-empty, ≤ 40 characters.
7. `ml_model_versions`: every `model_key` exists in `ml_models`; `status` ∈ ModelVersionStatus; at most one CHAMPION per model.
8. `rationale_templates`: every `{placeholder}` is in the CT-18 §6 list; `(code, version)` unique; `version` > 0.
9. `port_settings`: `value_type` ∈ SettingValueType; `value` is a string; `min` / `max` absent for STRING, JSON, BOOL; for INT / DECIMAL the value parses and `min ≤ value ≤ max`; keys unique; `validation_result_ttl_seconds` > `validation_timeout_seconds` when both are present (CT-18 §4).
10. The delivered values equal the CT-18 rows listed in Scope (guards against drift from the contract).

Tests 7 and 8 run on empty sections today; they guard the later minor versions.

Commands:

```
uv run pytest tests/unit/contracts -v
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run mypy
python -m json.tool docs/ref/ai-payloads/seed-spec.json
```

## Risks

- **Partial delivery:** downstream tasks (AI-044, AI-045, AI-055, AI-057, AI-070) cannot rely on this spec for blocked content. Mitigation: the blocked register names each owner and decision.
- **New code names** (`MAX_WAVE_HEIGHT_M`, and the restated descriptions) are AI Team naming, reviewed by the Backend under CT-18. Renaming a code later is breaking. Mitigation: names follow the two codes the contracts already use.
- **Draft vs publication:** `docs/ref/` mirrors PortHub; the local file is not the delivery. Mitigation: the `.md` says so and lists the PortHub publication as a follow-up.
- **Upsert semantics:** CT-18 §3 upserts `constraint_types` by code, so a later change to a delivered row silently changes data. Mitigation: condition 4 forbids it; test 10 pins the delivered rows.
- **Description for `port_settings`:** see P-1.

## Contract / decision changes

None. CT-18 v1.0 is used as approved; DEC-20, DEC-21, DEC-22, DEC-23, DEC-24, DEC-26, DEC-27, DEC-28, DEC-30, DEC-31 are referenced, not changed. No `Proposed change` rows.

## Open point for approval

- **P-1 `port_settings.description`.** CT-18 §4 gives no description column; its "Note" column holds references ("DEC-23", "CT-13 · greater than the timeout"), and only `solver_time_limit_seconds` has a description ("CP-SAT time limit per solve", §2). CT-18 marks `min` / `max` optional but says nothing on `description`. **Recommendation:** include `description` only for `solver_time_limit_seconds` and omit the key for the other eight, so nothing is invented; the `.md` flags it to the Backend reviewer. Alternative: copy the Note text verbatim as `description`.

**P-1 as approved (2026-11-01):** neither option above. Each of the nine keys gets a short description taken from the text that defines it (CT-13 for the validation keys, DEC-04 / CT-08 for `part1_max_retries`, DEC-23 / CT-10 for the solver and objective keys, CT-18 §4 and DEC-12 for `part1_stored_data_max_age_hours`); "CP-SAT time limit per solve" stays verbatim. `seed-spec.md` lists each description's source, flags them for the Backend reviewer, and records whether `port_settings.description` is nullable per CT-17 / `schema.sql`.

## Acceptance criteria

| Criterion (quoted) | Verification | Expected state after this plan |
|---|---|---|
| "Every constraint factor used by A4, A5, B2 has a constraint_type code" | Tests 3–4; blocked register | **Open:** gust, visibility, tide/surge blocked |
| "Every objective term used by B5 has a code" | Test 5 | Met for DEC-23; open only if DEC-22 adds a term |
| "Templates reviewed by a domain reviewer" | — | **Open:** templates blocked |
| "ml_model rows defined for the four documented keys" | Test 6 | **Open:** `FORECAST_BIAS_CORRECTION` blocked (C4 method undecided, data-gated) |

Verification evidence ("Reviewed seed specification"): the review in `/atlantech-review-and-publish AI-009`, then the PortHub PR review by the Backend Team.

## Steps

1. Create `tests/unit/contracts/__init__.py` and `test_seed_spec.py`; run `uv run pytest tests/unit/contracts -v` and record the failure.
2. Write `seed-spec.json` as in Scope; run the tests until they pass.
3. Write `seed-spec.md`.
4. Run the full command list; record the actual output in the status record.
5. Update `docs/tasks/status/AI-009.md` (plan approval, results, open criteria) and the `WORK_STATUS.md` row (IN PROGRESS, or IN REVIEW once handed to review).
6. Stop and point to `/atlantech-review-and-publish AI-009`.
