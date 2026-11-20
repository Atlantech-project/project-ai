# AI-051 · B2 constraint filter: plan

> Not committed by this workflow. Publishing happens through `/atlantech-review-and-publish AI-051` after the user's `APPLY CHANGES`.

## Task

- **ID:** AI-051 · Implement B2 constraint filter
- **Phase:** P5 (Part 2 AI Engine) · **Priority:** P0 · **Complexity:** M · **Flags:** none
- **Branch:** `feature/AI-051-b2-constraint-filter`, from `develop` at `bc83f0b`

## Approval

Approved by the user on 2026-11-20 ("Approved, with these changes"), with seven changes, folded in below:

1. **CT-10 codes:** no hold-back logic in AI-058. The CT-10 change (`PILOT_RANK_LIMIT`, `TUG_COUNT`, minor version) goes to the Backend Team now, and its approval is a merge gate for AI-058; hiding the reasons would make `NO_FEASIBLE_PLAN` unexplainable to staff. (In this task: the Proposed change row in CT-10, the merge gate in the task decision and the status record, and a message for the user to send. Nothing is sent to PortHub or the Backend Team by this task without the user's go-ahead.)
2. **Equipment-specific limits:** a blocked follow-up on both task decisions (AI-044 and AI-051), stating the blocker and what unblocks it, with its owner.
3. **MAX_DRAFT:** the skipped UKC test includes `arrival_draft == water_depth`, which `MAX_DRAFT` passes but must be rejected once AI-045 is enabled.
4. **TUG_COUNT:** when AI-054's result carries `rules_unvalidated` (rules not `APPROVED`, DEC-20 interim tables), the reason detail says the count is unvalidated.
5. **ENTRY_WINDOW:** half-open `[start, end)` in UTC, consistent with AI-044, with a boundary test.
6. **AI-044 tracker row:** updated from `IN REVIEW` to its merged status in this PR (and the AI-044 record's Status row with it, so the two agree).
7. **AI-009 follow-up:** Marine Safety Officer limit codes must be seeded before the Marine Safety Officer rules are active in production.

## User choices (2026-11-20, before the plan)

1. **Draft:** static `MAX_DRAFT` only (`arrival_draft > berth.water_depth` removes the berth). UKC stays entirely with A5 (AI-045). The gap is tracked explicitly: a skipped test "B2 rejects a berth that fails MIN_UKC_M via AI-045", enabled once AI-045 exists; the status record says UKC is not yet enforced; AI-045 becomes a prerequisite for marking AI-055 Done and for any Part 2 demo.
2. **Option check:** the pairing rules, plus the confirmed window and live availability (berth, pilot, tugs), reusing AI-050's availability functions.
3. **CT-10:** a Proposed change adding `PILOT_RANK_LIMIT` and `TUG_COUNT` to the STRUCTURAL list.
4. **Inputs:** constraint types and a `vessel_type_code → id` map are explicit arguments; no AI-050 loader change.

## Scope

**In** (pure functions in `part2/filter/`; no database, clock or queue):

1. **Pre-solve pairing filter** `filter_candidates(state, request, ...)`: for one request, every berth is kept or removed with all its reasons; per-request reasons apply to every berth. Rules:
   - `TERMINAL_COMPATIBILITY`: `request.requested_terminal_id` not in `berth.terminal_ids` (`berth_terminals`).
   - `BERTH_UNAVAILABLE`: `berth.status` in AI-050's `BERTH_OUT_OF_SERVICE` (`MAINTENANCE`, `INACTIVE`).
   - `MAX_LOA`: `vessel.loa > berth.max_vessel_loa`.
   - `MAX_DRAFT`: `request.arrival_draft > berth.water_depth` (static; choice 1).
   - `ENTRY_WINDOW` (per request): the request has no confirmed Part 1 window in the snapshot. Windows are half-open `[start, end)` in UTC (approval change 5).
   - `PILOT_RANK_LIMIT` (per request): no active pilot (`is_active` and an active `MARINE_PILOT` role) whose rank's `pilot_rank_limits.max_vessel_loa` is NULL or ≥ the vessel's LOA. A rank with no `pilot_rank_limits` row counts as not allowed (missing master data never passes).
   - `TUG_COUNT` (per request): fewer eligible tugs in service (in AI-054's `eligible_tugs` and status not in `TUG_OUT_OF_SERVICE`) than `n_min`, from the AI-054 `TugRequirement` the caller passes. When it carries `rules_unvalidated`, the detail says the count is unvalidated (DEC-20 interim tables; approval change 4).
   - **SAFETY (Marine Safety Officer limits):** B2-owned codes compare a vessel or request attribute (LOA, beam, draft, gross tonnage, deadweight) with the strictest applicable `safety_constraints` row, found with A4's `resolve_limit` for that candidate berth, on the request's IMDG classes (from its manifest entries) and vessel type id. Applicability is checked over the request's confirmed window (a row active at any moment of `[window start, window end)` applies). **The B2 list is empty in production** (no such code is seeded, AI-009 criterion 1); tests use labelled synthetic codes. A code that is in none of the B2, A4-owned and owned-elsewhere lists fails with `CONFIGURATION_ERROR` (CT-08); A4-owned codes are not rechecked (Part 1 applied them with every berth of the terminal, so a per-berth recheck could only loosen); codes owned elsewhere (UKC) are skipped.
2. **Binding reasons for `NO_FEASIBLE_PLAN`:** when no berth is left, `binding_constraints()` returns one item per distinct reason, shaped as CT-10 `binding_constraints`: `kind` (`STRUCTURAL` or `SAFETY`), `constraint_type_code`, and `detail` (English, at most 255 characters, naming the berths). Deterministic order.
3. **Option check** `check_option(state, option, ...)` for every emitted option, AI or FIFO (choice 2): the pairing rules for the option's berth, plus:
   - `ENTRY_WINDOW`: the option start lies in the confirmed window `[start, end)` in UTC (Architecture §8.8: "start within the confirmed window"); at `start` passes, at `end` fails.
   - `BERTH_OCCUPIED`: the berth is busy (`is_busy`, holds after `without_requests` for the run's own requests).
   - `PILOT_UNAVAILABLE`: `is_pilot_available` (DEC-32 rule 1) fails; `PILOT_RANK_LIMIT`: the option's pilot's rank may not take this LOA.
   - `TUG_UNAVAILABLE`: any option tug fails `is_tug_available` (DEC-32 rule 2); `TUG_COUNT`: fewer eligible option tugs than `n_min` (an option tug outside `eligible_tugs` doesn't count), with the same unvalidated note.
   - **Within one plan:** the caller passes the other requests' chosen options as extra holds, so a FIFO plan that double-books a berth, pilot or tug is caught.
4. **UKC gap tracked (choice 1):** a test marked `skip` with the reason "enabled once AI-045 exists", covering a berth that fails `MIN_UKC_M` and a berth where `arrival_draft == water_depth` (approval change 3).
5. **Proposed records:** an "AI-051 · B2 constraint filter" task decision (Proposed) in "AI task decisions", with the AI-058 merge gate, the equipment blocker and the AI-009 seeding follow-up; a `Proposed change` row in CT-10 (choice 3); the equipment blocker added to the AI-044 task decision's follow-ups.
6. Status record, tracker row, `part2/README.md` section; the AI-044 tracker row and record Status set to merged (approval change 6); a follow-up line in the AI-009 status record (approval change 7).

**Out:**

- UKC with tide and squat (AI-045); environmental limits per berth (A4 already applied them conservatively in Part 1).
- **Equipment-specific limits (blocked, approval change 2).** The AI-044 task decision says AI-051 must apply them. Blocker: the snapshot has no berth–equipment link. The schema links equipment only to a terminal (`equipment.terminal_id`, `equipment_category_id`), with no berth column, and the AI-050 snapshot loads no equipment rows at all; the limits are also weather-dependent (for example cranes stop above a wind limit). Unblocking needs either an AI-050 loader change to load terminal equipment, if terminal-level application is enough (owner: AI Team), or a schema change adding a berth–equipment link (owner: Backend Team, schema owner).
- The solver (AI-055), the FIFO builder (AI-056), persisting `binding_constraints` in `solver_runs.result_detail` (AI-058), the tug-count computation (AI-054, called by the caller), loader changes (choice 4), the backlog (AI-055 prerequisite text) and PortHub.

## Files likely to change

| File | New / existing |
|---|---|
| `part2/filter/__init__.py` | new: public API |
| `part2/filter/model.py` | new: `Reason`, `Kind`, `Removal`, `BerthResult`, `Candidates`, `BindingConstraint`, `Option`, `OptionCheck` |
| `part2/filter/codes.py` | new: the B2 code list (empty in production) and the vessel attributes it can compare |
| `part2/filter/pairing.py` | new: pre-solve rules, `filter_candidates`, `binding_constraints` |
| `part2/filter/option.py` | new: `check_option` |
| `tests/unit/part2/filter/__init__.py`, `builders.py` | new: SYNTHETIC snapshot builders |
| `tests/unit/part2/filter/test_pairing_rules.py` | new: each pre-solve rule, positive and negative |
| `tests/unit/part2/filter/test_safety.py` | new: SAFETY codes, strictest wins per berth, code lists, the skipped UKC test |
| `tests/unit/part2/filter/test_binding.py` | new: reasons for `NO_FEASIBLE_PLAN` |
| `tests/unit/part2/filter/test_option.py` | new: each option rule, including a FIFO plan that double-books |
| `part2/README.md` | existing: B2 section |
| `docs/ref/ATLANTECH_Decisions.md` | existing: Proposed AI-051 task decision |
| `docs/ref/ATLANTECH_Contracts.md` | existing: Proposed change row in CT-10 only |
| `docs/tasks/status/AI-051.md`, `docs/tasks/WORK_STATUS.md` | new / existing (AI-051 row; AI-044 row set to merged) |
| `docs/tasks/status/AI-044.md` | existing: Status row set to merged (approval change 6) |
| `docs/tasks/status/AI-009.md` | existing: one follow-up line (approval change 7) |
| this plan | new |

`pyproject.toml` needs no change: `part2` is already in the mypy files and coverage source.

## Dependencies

| Item | Status | Evidence |
|---|---|---|
| AI-050 | DONE | PR #26, `9e0ae86`; the snapshot model and availability functions are on `develop` |
| AI-044 | Merged | PR #39, `bc83f0b`. The tracker still says `IN REVIEW`; the record says it becomes `DONE` on merge |
| AI-054 | DONE | Tug count passed in by the caller |
| AI-045 | Not started | UKC not enforced by B2 (choice 1) |
| DEC-32, DEC-06 | Closed | Availability rules reused, not changed |
| DEC-20 | Closed | `TUG_COUNT` meaning |
| CT-10 | Approved v1.1; Proposed v1.2 (Backend draft) | New codes Proposed (choice 3) |
| CT-13 | Approved v1.1 | Codes reused |
| AI-044 task decision | Proposed | Code lists and `resolve_limit` reused |

Cross-team: the Backend Team (CT-10 owner; the same codes in the P5-M1 override check), the Marine Safety Officer (B2 codes when seeded), and the AI Team (AI-045 timing, AI-055 prerequisite).

## Tests (TDD)

Write each test first and see it fail.

1. **Pre-solve rules** (`test_pairing_rules.py`), each with a pass case and a fail case, at the boundary where one exists (equal LOA and equal draft pass): `TERMINAL_COMPATIBILITY`, `BERTH_UNAVAILABLE` (both statuses), `MAX_LOA`, `MAX_DRAFT`, `ENTRY_WINDOW`, `PILOT_RANK_LIMIT` (NULL limit, missing rank row, inactive pilot, ended role), `TUG_COUNT` (ineligible and out-of-service tugs don't count; the unvalidated note appears exactly when AI-054 flags `rules_unvalidated`). A berth failing several rules keeps every reason.
2. **SAFETY** (`test_safety.py`): a synthetic `MAX_ALLOWED` and `MIN_REQUIRED` code; strictest wins per candidate berth (a berth-only limit removes only that berth); vessel-type and IMDG scope; active during the window; A4-owned codes not rechecked; UKC skipped; a code in no list raises `CONFIGURATION_ERROR`; every seeded code is in exactly one of the lists. **Skipped:** "B2 rejects a berth that fails MIN_UKC_M via AI-045", including `arrival_draft == water_depth`.
3. **Binding reasons** (`test_binding.py`): no berth left gives one item per distinct reason, `kind` correct, `detail` at most 255 characters, a stable order; a request with a berth left has none.
4. **Option check** (`test_option.py`): each option rule pass and fail (window start boundaries in UTC: just before `start` fails, at `start` passes, just before `end` passes, at `end` fails; non-UTC raises; busy berth, own-run holds dropped, unavailable or under-ranked pilot, unavailable tug, too few tugs); a FIFO plan whose two requests share a berth, a pilot or a tug at overlapping times fails; an option that passes has no reasons.

Commands (the CI gates):

```
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov
```

## Risks

- **UKC not enforced** until AI-045: Part 2 can propose a berth where the vessel's under-keel clearance is too small at low tide. Mitigations: the skipped test, the status record, AI-045 as a prerequisite for AI-055 Done and any Part 2 demo (choice 1).
- **No B2 codes seeded:** the SAFETY path runs only on synthetic codes until AI-009 criterion 1 adds vessel-safety codes.
- **Equipment limits not applied** (no data); recorded on both task decisions.
- **CT-10 codes Proposed:** B2 returns them as they are; there is no hold-back. The CT-10 approval by the Backend Team is a merge gate for AI-058 (approval change 1).
- **Pilot rank at the snapshot:** a pilot whose rank has no `pilot_rank_limits` row is treated as not allowed. This is conservative, but could block every pilot if the table is empty; the reason says so.

## Contract / decision changes

- **CT-10 (Proposed change row):** `2026-11-20 · AI-051 · add PILOT_RANK_LIMIT and TUG_COUNT to the STRUCTURAL binding_constraints list (minor: v1.3, or folded into the pending v1.2 draft at the owner's choice) · Reason: B2 removes candidates for these reasons, which CT-13 already names for overrides, but CT-10's closed list for NO_FEASIBLE_PLAN does not · Evidence: part2/filter/ and its tests on this branch; CT-13 STRUCTURAL OVERRIDE list · Impact: AI-058 (result_detail), Backend (NO_FEASIBLE_PLAN display), Frontend · Awaiting: Backend Team (owner), AI Team (reviewer)`.
- **AI task decision "AI-051 · B2 constraint filter"** (Proposed): the rules and their codes, the conservative pilot-rank rule, the window-applicability rule for SAFETY codes, the three code lists, UKC not enforced until AI-045 (with the AI-055 and demo prerequisite), the CT-10 approval as a merge gate for AI-058, equipment limits blocked (blocker and owners), and the AI-009 seeding follow-up.
- **AI-044 task decision:** the equipment blocker added to its follow-ups (approval change 2); nothing else in it changes.
- Used, unchanged: DEC-06, DEC-20, DEC-32, CT-08, CT-13, the AI-044 and AI-050 task decisions.

## Acceptance criteria (backlog §5, quoted)

| Criterion | Verification |
|---|---|
| "Each rule has tests" | Tests 1, 2 and 4: each rule has a pass and a fail case |
| "Filter applied to FIFO output (test)" | Test 4: a FIFO plan by arrival order that double-books is rejected; one that doesn't passes |
| "Reasons usable for NO_FEASIBLE_PLAN" | Test 3: CT-10-shaped `binding_constraints` |
