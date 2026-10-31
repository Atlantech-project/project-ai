# AI-008 · Agree thresholds register and evaluation baseline · plan (Revision 2)

| Field | Value |
|---|---|
| Task | AI-008 · Agree thresholds register and evaluation baseline (P0 · P1 · M · flags A, X) |
| Branch | `feature/AI-008-thresholds-register-evaluation-baseline`, fast-forwarded to `develop` at `f555913` (SETUP-003 merged) |
| Kind | Decision task. Documents only, no code |
| Status | Approved by the user on 2026-10-31 ("Approved, with one correction first"), with the TR-08 citation corrected |
| Date | 2026-10-31 |

Publishing goes through `/atlantech-review-and-publish AI-008`. This plan has no commit steps.

## 1. Choices made with the user (2026-10-31)

| # | Question | Choice |
|---|---|---|
| Q1 | AC1 refers to plan §9 and §11, and `ATLANTECH_AI_IMPLEMENTATION_PLAN.md` isn't in the repository | **Scope exception.** The inventory is built from the sources in the repository. Checking against plan §9 and §11 is a follow-up |
| Q2 | Where the register lives | **Inside DEC-30** in `docs/ref/ATLANTECH_Decisions.md`: a `Proposed change` row plus a register table under the entry |
| Q3 | Values with no documented figure | Only values with a non-NFR source are Filled. Every other row is DEFERRED with its owner and the task that needs it. No number is invented |
| Q4 | Manual-planning baseline (AC3) | Draft the procedure as a `Proposed change` on DEC-33. The expert-agreed manual rules stay pending |
| R1 | NFR sources | **Ignore every NFR figure and ID** (`NFR-*`, including the UML_Context §10 summary). Architecture §13.5 restates NFR figures, so it isn't an independent source. A row stays Filled only when a non-NFR document states its value |
| R2 | TR-13 | Split it. TR-13a (10 s solver limit) is Filled from CT-18 and CT-10. TR-13b (pipeline ≤ 12 s) is Deferred, owner AI Team, needed by AI-061 |
| R3 | TR-18 | Deferred. Owner AI Team, needed by AI-090. Consulted: Backend Team (CT-16 raises an alert when a worker is DOWN for more than 2 minutes) |
| R4 | TR-08 | **"Out of MVP scope – per DEC-17 Decision row and CT-12 v1.0".** DEC-17's Decision row states that NFR-PERF-2 was removed from the MVP (Leads Council 2026-10-27), and size classes existed only for it. No value and no owner. The follow-ups go in the status record and are not edited by AI-008 |
| R5 | Diff review | TR-19 moves to REFERENCE, because it is not a threshold. The DEC-33 Evidence adds Proposal §12 (Table 8). The DEC-30 Impact adds AI-104 (needed by TR-06) |

## 2. Scope

**In scope**
- **The register table under DEC-30.** Columns: TR ID (local to the register, not an official ID), threshold, value, status, source (non-NFR only), owner, needed by.
- **The statuses:**
  - `FILLED`, with a non-NFR source;
  - `DEFERRED`, with an owner and a consumer task;
  - `OUT OF MVP SCOPE`, with the deciding source;
  - `REFERENCE`, meaning another decision or contract defines the value.
  - `AGREED` replaces `FILLED`/`DEFERRED` only when the AI Team owner approves DEC-30.
- A draft manual-planning baseline procedure as a `Proposed change` on DEC-33.
- The status record and the `WORK_STATUS.md` row.

**Out of scope**
- **No approvals:** DEC-30 and DEC-33 stay `Open`.
- **No new numbers:** any value without a non-NFR source.
- **No other edits:** CT-12, CT-18, CT-24, the backlog, Architecture and `pyproject.toml`.
- **Backend-only targets:** API response times and SSE delivery are not AI thresholds and their only figures are NFR-sourced, so they get no rows.

## 3. Register content (to be written under DEC-30)

### Filled (6)

| TR | Threshold | Value | Source (non-NFR) |
|---|---|---|---|
| TR-06 | C3 Champion/Challenger guard | Challenger promoted only if not worse on both MAE and override rate, on held-out time-based data (no numeric margin) | Arch §9.3; UML AD-16 P6/D3 |
| TR-12 | Stored environmental data freshness | 48 h, and the data must cover the horizon | CT-18 v1.0 `part1_stored_data_max_age_hours` = 48; DEC-12 (Closed); Arch §7.2; UML 2.10 |
| TR-13a | CP-SAT solver time limit | 10 s (configurable default; min 1, max 120) | CT-18 v1.0 `solver_time_limit_seconds`; CT-10 |
| TR-15 | Option equivalence | 10 % | DEC-23 (Closed); CT-18; CT-10 |
| TR-16 | Validation timeout and result TTL | 15 s / 600 s | CT-13; CT-18 |
| TR-17 | Part 1 retries | 3 | DEC-04 (Closed); CT-08 v1.0 (Approved 2026-10-30); CT-18 |

### Deferred (13)

| TR | Threshold | Owner | Needed by | Note (non-NFR source) |
|---|---|---|---|---|
| TR-01 | Drift PSI threshold (`drift_psi_threshold`) | AI Team | AI-072; CT-18 seed | CT-18 ⟨AI⟩ value, DEC-30 |
| TR-02 | Drift rolling-MAE threshold (`drift_mae_threshold`) | AI Team | AI-072; CT-18 seed | CT-18 has one key for M2, M3 and M4, which have different units (follow-up) |
| TR-03 | Rolling-MAE window length | AI Team | AI-072 | Arch §9.1 (C2) |
| TR-04 | Data sufficiency per model (M2, M3, M4, C4) | AI Team | AI-024 (records the criteria here) | Arch §9.5 gives an estimate (≈ 9,500 calls a year, "several months"), not a threshold |
| TR-05 | Phase 2 promotion margin over the Phase 1 baseline (M2, M3, M4) | AI Team | AI-101, AI-102, AI-103 | Arch §10. The meaning of "MAE" for the M4 classifier is open (OD-16) |
| TR-07 | Tide prediction tolerance and test period | AI Team (with the DEC-27 source) | AI-021 | DEC-27 says the tolerance is set in DEC-30 |
| TR-09 | Test coverage gate | AI Team | AI-016 (`fail_under`) | AI-016 acceptance criterion "Coverage gate enforced at the agreed value"; AI-016 task decision item (8); DEC-30 topic |
| TR-10 | Port-wide `safety_constraints` defaults (wind, gust, visibility, wave, minimum UKC …) | AI Team (seed) · input: Marine Safety Officer through CT-25 (QA Team) | AI-044; CT-18 seed | CT-18 §1 and §7 |
| TR-11 | Window-accuracy definition (C1) | AI Team | AI-071 | OD-16 |
| TR-13b | Total Part 2 pipeline time | AI Team | AI-061 | No non-NFR source (R2) |
| TR-14a | Recommendation latency percentiles under concurrency | AI Team | AI-061 | No non-NFR source |
| TR-14b | Parallel solves | AI Team | AI-061 | No non-NFR source |
| TR-18 | Worker restart time and availability | AI Team · consulted: Backend Team | AI-090 | No non-NFR source (R3). CT-16 alerts on a worker DOWN for more than 2 minutes |

### Out of MVP scope (1)

| TR | Threshold | Basis |
|---|---|---|
| TR-08 | BAPLIE size classes and parse-time targets | Out of MVP scope – per DEC-17 Decision row and CT-12 v1.0. No value, no owner |

### Reference rows (7, defined elsewhere or not a threshold)

| TR | Item | Defined by |
|---|---|---|
| TR-19 | Evaluation key question (not a threshold): can the port handle more than about 26 vessels a day; assessed experimentally, not a pass/fail limit | Master_Context §4 (Port Authority daily bulletin); used by AI-084 |
| TR-20 | Deviation significance per operation type (UML AD-16 D1) | DEC-09 (Backend Team, Open, Sprint 6); Port Admin setting |
| TR-21 | Part 1 horizon, time step, minimum window, demand slot, gap tolerance | DEC-24 (Open) |
| TR-22 | Uncertainty margin and window confidence | DEC-25 (Open; MVP zero margin, `confidence` NULL) |
| TR-23 | Tug count per vessel | DEC-20 (Open) |
| TR-24 | `run_stale_after_seconds` | CT-18 §4 and §7 (AI Team supplies it with its calculation) |
| TR-25 | Clock-skew suspect rule | Backend (ClassDiagram OI-06) |

## 4. Draft DEC-33 procedure (Proposed change)

This follows DEC-33 option 1:
- **Scenarios:** replay agreed scenarios from the reference-port data (CT-25 / AI-022).
- **Rules:** apply the documented manual planning rules, agreed with a domain expert (pending; QA-AI1).
- **Comparison:** run the same scenarios through the AI and the FIFO fallback.
- **Indicators:** compare on the six Master_Context §4 indicators, which match Proposal §12 (Table 8).
- **Roles:** QA prepares, the expert agrees the rules, and the AI Team runs AI-084.

DEC-33's Status and Decision rows stay unchanged.

## 5. Files likely to change

| File | New / existing | Change |
|---|---|---|
| `docs/ref/ATLANTECH_Decisions.md` | existing | DEC-30: `Proposed change` row plus the register under the entry. DEC-33: `Proposed change` row. Status, Decision and summary rows unchanged |
| `docs/tasks/status/AI-008.md` | new | Status record |
| `docs/tasks/WORK_STATUS.md` | existing | AI-008 row |
| `docs/superpowers/plans/2026-10-31-ai-008-thresholds-register-evaluation-baseline.md` | new | This plan |

## 6. Dependencies

- **Prerequisites:** none in the backlog.
- **Linked decisions and contracts:**
  - DEC-30 (Open; AI-008 closes it once approved) and DEC-33 (Open).
  - CT-18 (Approved v1.0; waits on DEC-30) and CT-25 (QA inputs, not in the repository).
  - DEC-17 Decision row and CT-12 v1.0 (size classes out of the MVP).
  - DEC-09, DEC-20, DEC-24, DEC-25 and DEC-27 (references).
- **Cross-team:** the Marine Safety Officer and domain experts (TR-10, the DEC-33 rules); QA (CT-25, QA-AI1, CT-24); Backend (TR-18 consulted, DEC-09).
- **Downstream:** AI-016, AI-021, AI-023, AI-024, AI-044, AI-061, AI-071, AI-072, AI-084, AI-090, AI-101 to AI-103 and AI-104.

## 7. Tests (document checks; no code)

1. **Table shape:** every row of each new table has as many cells as its header (scratchpad script).
2. **Completeness:** each backlog-named threshold (drift PSI, rolling MAE, data sufficiency, improvement margin, tide tolerance, size classes, coverage) has a TR row.
3. **CT-18 cross-check:** each CT-18 key whose note says DEC-30 appears in the register.
4. **No NFR in the register:** a grep for `NFR-` inside the DEC-30 register finds nothing. TR-08 cites the DEC-17 Decision row and CT-12 v1.0, not the NFR itself.
5. **Status rules:** each FILLED row has a non-NFR source; each DEFERRED row has an owner and a consumer task; the OUT OF MVP SCOPE row has its basis.
6. **Counts:** 6 FILLED, 13 DEFERRED, 1 OUT OF MVP SCOPE and 7 REFERENCE, in both the register and the DEC-30 Proposed change row.
7. **No approvals:** the DEC-30 and DEC-33 Status and Decision rows are unchanged, and no new `DEC-`/`CT-` IDs appear.
8. **Diff scope:** only the files in §5 change.

## 8. Risks

- **No approved register yet.** DEC-30 needs whole-team approval, so AI-008 isn't DONE until that approval or a user-approved scope exception.
- **Most values are deferred.** AI-016, AI-021, AI-044, AI-061, AI-072 and AI-090 stay blocked on figures.
- **Downstream tasks still carry NFR figures.** AI-033 (NFR-PERF-2), AI-061 and AI-090 cite NFRs in the backlog. The register doesn't adopt those figures, so their targets need agreement through DEC-30.
- **Missing sources:** the implementation plan (§3.3, §9, §11), Proposal §12, CT-25 outputs and `ATLANTECH_FRD_v3`.

## 9. Contract and decision changes

- **DEC-30:** `Proposed change` row plus the register. Awaiting: AI Team owner, with whole-team approval per DEC-30.
- **DEC-33:** `Proposed change` row with the draft procedure. Awaiting: AI Team owner, with the QA Team and a domain expert for the manual rules.
- No contract edits and no new official IDs.

## 10. Acceptance criteria (backlog §5 AI-008)

| Criterion (quoted) | Verification |
|---|---|
| "Register lists every threshold named in plan §9 and §11" | **Scope exception (user, 2026-10-31):** checked against the in-repository sources (checks 2, 3). The plan check is a follow-up |
| "Each has a value and approver, or is explicitly deferred" | Checks 5 and 6. Values become AGREED on approval |
| "Manual baseline procedure documented" | DEC-33 Proposed change present. Expert rules marked pending |
