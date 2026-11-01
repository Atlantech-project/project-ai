# AI seed specification (CT-18) · draft 1.0

> **Draft, not yet published.** This is the AI Team's draft of `seed-spec.json` (task AI-009). The CT-18 delivery is the file published to PortHub as `contracts/ai/seed-spec.json`; that publication is a follow-up owned by the AI Team (CT-18 owner) and reviewed by the Backend Team. Until then the Backend seeders must not read this local copy. It sits in `docs/drafts/` because `docs/ref/` holds only copies of published files; the file is mirrored into `docs/ref/ai-payloads/` once published.

| | |
| --- | --- |
| Contract | CT-18 · AI seed data and `port_settings` keys (Approved v1.0) |
| File | `seed-spec.json`, `spec_version` `1.0` |
| Task | AI-009, partial delivery under a scope exception accepted by the user on 2026-11-01 (prerequisite AI-005 not done) |
| Reviewers | Backend Team · AI Team (CT-18) |

## How this file grows

All seven CT-18 sections are present from 1.0. Blocked sections are empty arrays (`[]`). Each blocked item below is added later as **new rows** in an existing section, which is a minor version (1.x) under CT-18 §2. Rows delivered in 1.0 are not changed: CT-18 §3 upserts `constraint_types`, `objective_terms` and `ml_models` by code, so a changed row would silently change seeded data. `tests/unit/contracts/test_seed_spec.py` pins their categories, units, comparators, hard flags, families and values, and the descriptions CT-18 gives verbatim. The descriptions flagged below may still be reworded in review.

## Delivered rows and their sources

### `constraint_types`

| Code | category · unit · comparator · hard | Source | Reviewer flag |
| --- | --- | --- | --- |
| `MAX_WIND_KN` | ENVIRONMENTAL · KNOTS · MAX_ALLOWED · true | CT-18 §2 (row and description verbatim) · CT-10 · AI Architecture I-6 | — |
| `MIN_UKC_M` | UKC · METRES · MIN_REQUIRED · true | CT-13 (code, `is_hard_safety_limit: true`) · AI Architecture §7.6 ("minimum UKC from `safety_constraint`") · I-6 · Master_Context §6.2 | Description "Minimum under-keel clearance" restates the code; please confirm or reword |
| `MAX_WAVE_HEIGHT_M` | ENVIRONMENTAL · METRES · MAX_ALLOWED · true | A4 factor list (AI Architecture §7.1, Master_Context §6.2) · I-6 (wave is a hard limit) · `environment_forecast_point.wave_height` | **New code**, named on the pattern of `MAX_WIND_KN` / `MIN_UKC_M`. **Unit not stated by a source:** METRES is the only `ConstraintUnit` value that fits a wave height, and the code embeds it; please confirm. Description "Maximum wave height for entry" restates the code; please confirm or reword |

B2's LOA, draft and terminal checks use the closed STRUCTURAL code lists of CT-10 and CT-13, which are not `constraint_types` rows. Its Marine Safety Officer check reads the `constraint_types` rows above and the blocked ones below. No source names a code in the `VESSEL_SAFETY` category, including for the gas-carrier constraints of FR-9.6, so none is delivered; the Marine Safety Officer and the AI Team are asked to confirm whether any is needed. The A5 channel speed limit is master data (`navigation_channel.speed_limit_knots`), not a constraint type.

### `objective_terms`

| Code | Name | Source |
| --- | --- | --- |
| `WAITING_TIME` | Vessel waiting time | CT-18 §2 verbatim · DEC-23 (Closed) |
| `RESOURCE_COST` | Resource cost | CT-18 §2 verbatim · DEC-23 (Closed) |

### `ml_models`

| `model_key` | `algorithm_family` | Description | Source | Reviewer flag |
| --- | --- | --- | --- | --- |
| `M2_SERVICE_TIME` | GRADIENT_BOOSTING | Berth service time (P50 / P90) | CT-18 §2 verbatim · AI Architecture §9.4 | — |
| `M3_DEMAND_FORECAST` | GRADIENT_BOOSTING | Arrivals per demand slot (Phase 2) | AI Architecture §9.4, §10 (LightGBM regressor, target arrivals per slot); family as CT-18 gives M2 | Description written from §10; please confirm |
| `M4_DELAY_RISK` | GRADIENT_BOOSTING | Probability of a significant delay deviation (Phase 2) | AI Architecture §9.4, §10 (LightGBM classifier, label a significant `DELAY` deviation); family as CT-18 gives M2 | Description written from §10; please confirm |

### `port_settings`

`value_type`, `value`, `min` and `max` are exactly as in CT-18 §4. CT-18 gives a description only for `solver_time_limit_seconds`; the other eight descriptions are short restatements of the text that defines each key. **All eight are flagged for the Backend reviewer.**

| Key | value_type · value · min · max | Description | Description source |
| --- | --- | --- | --- |
| `part1_stored_data_max_age_hours` | INT · 48 · 1 · 168 | Maximum age of stored environmental data usable by Part 1 | CT-18 §4 · DEC-12 (Closed) · Decisions file, stale-data rule ("computed at read time from the age of the latest SUCCESS run against `part1_stored_data_max_age_hours` (48)") |
| `solver_time_limit_seconds` | INT · 10 · 1 · 120 | CP-SAT time limit per solve | CT-18 §2 verbatim (not flagged) |
| `solver_options_per_request` | INT · 3 · 1 · 3 | Maximum number of options per request | DEC-23 ("1 to 3 options per request") · CT-10 (`options_count`) · CT-18 §4 ("Maximum") |
| `solver_option_equivalence_pct` | DECIMAL · 10 · 0 · 50 | Options 2 and 3 only within this percentage of option 1 | DEC-23 · CT-10 ("Options 2 and 3 are returned only within `solver_option_equivalence_pct` of option 1") |
| `objective_weight_waiting_time` | DECIMAL · 1.0 · 0 · 10 | Weight of the WAITING_TIME objective term | DEC-23 · CT-18 §5 |
| `objective_weight_resource` | DECIMAL · 1.0 · 0 · 10 | Weight of the RESOURCE_COST objective term | DEC-23 · CT-18 §4, §5 |
| `part1_max_retries` | INT · 3 · 0 · 10 | Maximum retries of a Part 1 job | DEC-04 ("Part 1 up to `part1_max_retries` (3)") · CT-08 queue table |
| `validation_timeout_seconds` | INT · 15 · 5 · 60 | Wait for a validation result before the change is refused | CT-13 ("no result within `validation_timeout_seconds` (15) → … the change is refused") |
| `validation_result_ttl_seconds` | INT · 600 · 60 · 3600 | How long a validation result is kept | CT-13 ("keeps the result for `validation_result_ttl_seconds`") |

**Is `port_settings.description` nullable?** Not determinable from this repository. `docs/ref/db/` holds only `table-names.md`; the generated `schema.sql` is published in PortHub as `contracts/db/schema.sql` (CT-17 §5) and is not mirrored here, and `ClassDiagramContext.md` lists `description` on `PortSetting` without a nullability marker. Every row therefore carries a description; the Backend reviewer is asked to confirm the column definition against `contracts/db/schema.sql`.

## Blocked items

| Item | Section | Blocked on | Owner |
| --- | --- | --- | --- |
| `MAX_GUST_KN` | `constraint_types` | Hard-limit flag not documented (I-6 lists wind, wave, visibility, UKC only) | Marine Safety Officer · AI Team |
| Visibility code | `constraint_types` | Unit not documented; the code embeds the unit, so a wrong unit would force a breaking code change | Marine Safety Officer · AI Team |
| Tide/surge limit (A4) | `constraint_types` | Quantity, unit and comparator not documented | Marine Safety Officer · AI Team |
| Port-wide defaults | `safety_constraints` | DEC-30 (Open); register row TR-10 proposed in AI-008 | AI Team, input from the Marine Safety Officer through CT-25 (QA Team) |
| Tug content (`{tug_count}` templates, tug factors, tug codes) | `rationale_templates` · `constraint_types` | DEC-20 (Open) | AI Team, input from the Tug Manager / Marine Safety Officer |
| Delay-risk templates and factors | `rationale_templates` | DEC-21 (Open) | AI Team |
| Financial-impact ranking content | `rationale_templates` · `objective_terms` | DEC-22 (Open) | AI Team |
| Service-time / moves templates and factors | `rationale_templates` | DEC-28 (Open) | AI Team |
| All templates | `rationale_templates` | The four decisions above; domain review (AI-009 criterion 3); whether rationale is bilingual (open) | AI Team · domain reviewer |
| `FORECAST_BIAS_CORRECTION` | `ml_models` | C4 method undecided ("regression or quantile mapping", AI Architecture §9.1) and data-gated (§9.5) | AI Team |
| CHAMPION rows, `artifact_path` | `ml_model_versions` | No model has a CHAMPION at go-live (AI Architecture §9.5: ML data-gated in the MVP; CT-18 §2: no row then) | AI Team (AI-070) |
| `weather_pull_hours` | `port_settings` | CT-18 §4 / §7 ⟨AI⟩ value, min and max; no decision sets them. AI Architecture §7.1 states a 6 h schedule but no min / max | AI Team |
| `tide_horizon_days` | `port_settings` | CT-18 §4 / §7 ⟨AI⟩ value, min and max; no decision sets them. AI Architecture §7.1 says only "a multi-day horizon" | AI Team |
| `part1_assessment_horizon_hours` · `part1_time_step_minutes` · `part1_min_window_minutes` · `demand_slot_minutes` | `port_settings` | DEC-24 (Open) | AI Team |
| `run_stale_after_seconds` | `port_settings` | CT-18 §4 / §7 calculation (register TR-24) | AI Team |
| `part3_evaluation_cron` | `port_settings` | DEC-31 (Open) | AI Team |
| `drift_psi_threshold` · `drift_mae_threshold` | `port_settings` | DEC-30 (Open); register TR-01, TR-02 | AI Team |

## AI-009 acceptance criteria

| Criterion | State at 1.0 |
| --- | --- |
| Every constraint factor used by A4, A5, B2 has a constraint_type code | Open: gust, visibility, tide/surge blocked |
| Every objective term used by B5 has a code | Met for DEC-23; reopens only if DEC-22 adds a term |
| Templates reviewed by a domain reviewer | Open: templates blocked |
| ml_model rows defined for the four documented keys | Open: `FORECAST_BIAS_CORRECTION` blocked (C4 method undecided, data-gated) |

## Follow-ups

- Publish to PortHub `contracts/ai/seed-spec.json` (the actual CT-18 delivery), with Backend review, then mirror it into `docs/ref/ai-payloads/`.
- Fill each blocked item as its decision closes, as a minor version.
