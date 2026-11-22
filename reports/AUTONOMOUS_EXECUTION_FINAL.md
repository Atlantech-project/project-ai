# ATLANTECH — AUTONOMOUS EXECUTION FINAL REPORT

Session of 2026-11-21. Repository `Atlantech-project/project-ai`, base `origin/develop` at `3180e90`; PortHub `origin/main` at `a3a1eb3`.

## 1. Executive Summary

- **Implemented:** seven backlog tasks, each tested on its own branch and pushed: AI-065, AI-055, AI-031, AI-060, AI-025, AI-070, AI-092. An eighth branch fixes the records and adds the execution records.
- **Not merged:** nothing from this session is merged. `gh` is not installed here, so no PR was opened. Each task stays `IN REVIEW` until its PR is merged.
- **PortHub:** two commits pushed to `main`. One syncs DEC-34 (Closed) and the AI-051 CT-10 Proposed row; the other moves the `project-ai` pointer to `3180e90`.
- **Stopping condition reached:** every other AI task waits for one of these merges, an open AI Team decision (DEC-31, DEC-07/24, the AI-045 path), another team, or missing data.

## 2. Execution Overview

| Count | Tasks |
|---|---|
| Discovered (backlog) | 76 AI tasks plus SETUP/DEC records |
| Already DONE at start | 23 AI tasks (AI-001–006, 008–016, 023, 030, 044, 050–054), plus DEC-20, DEC-21, DEC-34 and SETUP-001–003. The DEC-34 and AI-051 records were stale; the SETUP branch corrects them |
| Attempted and implemented this session | 7 |
| Pending merge | 7 task branches + 1 SETUP branch |
| Completed (merged) this session | 0 |
| Blocked (decision, merge, other team or data) | All remaining; see `docs/tasks/BLOCKED_TASKS.md` |

## 3. Completed Tasks

"Completed" here means implemented, tested and pushed. None is merged.

| Task | Summary | Main code | Tests | Branch · head |
|---|---|---|---|---|
| AI-065 | B8 specification. Inputs I1–I13 and hard constraints H1–H11 mapped to schema columns and CT-11 reason codes; CT-11 v1.2 names confirmed (Proposed); rulings P1–P8 | `docs/ref/ATLANTECH_Decisions.md` § AI-065 | Document checks (tables, CRLF, IDs) | `feature/AI-065-yard-placement-design` · `5884fad` |
| AI-055 | CP-SAT joint berth, pilot and tug allocation (OR-Tools 9.15). B2 candidates; `NoOverlap` per resource; shift coverage; DEC-20 tug-count and bollard-pull constraints; lexicographic objective (scheduled count, then DEC-23); options 2–3 within the equivalence percentage; B2 re-check of every option | [part2/solver/cpsat.py](../part2/solver/cpsat.py) `solve`; [part2/solver/model.py](../part2/solver/model.py) | 51 unit (known optima, 12-seed property test, time limit, determinism) | `feature/AI-055-b5-cp-sat-allocation-model` · `86ea7d6` |
| AI-031 | Every CT-12 content rule; codes, refs and messages match the AI-023 corpus oracles; staff corrections go through the same `validate` | [edi/rules/checks.py](../edi/rules/checks.py) `validate`, `outcome`; [edi/rules/staged.py](../edi/rules/staged.py) `validate_staged_payload` | 70 unit, 1 skip (corpus case 12) | `feature/AI-031-baplie-validation-rules` · `23d0148` |
| AI-060 | OVERRIDE validation. Changes applied as one plan, checked by B2, returned as the CT-13 / C-06 `validation_result` with message keys and `change_index` | [part2/validation/override.py](../part2/validation/override.py) `validate_override` | 27 unit, each result checked against `c06-completion.schema.json` | `feature/AI-060-override-validation-service` · `4b12897` |
| AI-025 | Ranges, completeness, freshness (48 h inclusive), coverage, datum and trusted-row checks with structured reasons | [common/quality.py](../common/quality.py) | 21 unit (exact 48 h boundary) | `feature/AI-025-data-quality-checks` · `6488341` |
| AI-070 | Champion read, local artefact store with a SHA-256 sidecar, Phase 1 fallback, table definitions | [common/registry.py](../common/registry.py) `load_champion`, `ArtifactStore` | 16 unit; 2 integration (CI only) | `feature/AI-070-model-registry-integration` · `36fdd09` |
| AI-092 | Job log context (`run_id` on every line), `job_metrics` lines and counters, manifest redaction | [common/observability.py](../common/observability.py); [common/runtime/logs.py](../common/runtime/logs.py); `Worker.process_message` | 16 unit | `feature/AI-092-observability-logs-metrics` · `71ce70c` |

The links point to files on each task's own branch.

## 4. Technical Decisions

Each one is written as a `Proposed` entry in "AI task decisions", keyed by its task. None is marked approved.

- **AI-055:**
  - `RESOURCE_COST` = tugs ÷ `N_cap`. Berth occupancy would be constant, because B3 depends on the terminal.
  - `WAITING_TIME` is normalised over the window's start minutes, on a conservative whole-minute grid.
  - The model schedules as many requests as it can before it minimises cost.
  - Option 1 is always the joint solution; alternatives differ by berth.
  - One time limit covers the whole solve, with one worker and seed 0.
- **AI-065:** reason-code precedence, ties, general containers kept out of special zones, unsupported lengths, ISO 668 dimensions for OOG, and two `port_settings` key names, with no values.
- **AI-031:**
  - Six new issue codes.
  - A missing IMO counts as `IMO_MISMATCH`.
  - Only the schema's stowage bounds are enforced.
  - Correction payload values of the wrong type count as malformed.
- **AI-060:**
  - A start change keeps the option's duration.
  - A change that does not fit the option is `PRECONDITION_FAILED`.
  - Message-key list and `change_index` rules.
- **AI-025:**
  - 48 h is inclusive; a future timestamp is not usable.
  - Gap tolerance comes only from the caller (DEC-24).
  - A NULL trust flag is excluded.
- **AI-070:**
  - The hash goes in a sidecar file, because the schema has no hash column.
  - A damaged champion raises; it never falls back silently.
  - Artefact paths are confined to the store root.
- **AI-092:**
  - Metrics are exported as log lines, because no metrics tool is documented.
  - Negative queue wait (clock skew) is kept.
  - Redacted keys list.

## 5. Contract Updates

No contract was changed or marked approved.

- **CT-10:** the AI-051 Proposed change row was copied to PortHub, so its owner can see it. It stays Proposed, awaiting the Backend Team.
- **CT-11 v1.2 (Backend-owned, Proposed):** the AI-065 entry recommends that the AI Team confirm the names CT-11 leaves "to confirm with the AI Team". v1.2 itself still needs the Backend Team.
- **CT-13 (AI-owned):** message keys proposed in the AI-060 entry. Backend review is pending.
- **CT-24 (QA-owned):** six new codes requested from the QA Team (INT-Q2). CT-24 itself was not edited.

## 6. PortHub Synchronization

| Commit on `main` | Change | Verified |
|---|---|---|
| `38dd6b5` | DEC-34 summary, Status and Decision rows (3 lines); CT-10 AI-051 Proposed change row (1 line) | Decisions head SHA-256 is the same in both repos (`c18d941e…`) |
| `a3a1eb3` | `project-ai` gitlink `b2431f2` → `3180e90` | Only the gitlink changed; pushed `5860967..a3a1eb3` |

Each project-ai merge from this session will need another pointer commit.

## 7. External Integration Requirements

Full self-contained list: `docs/tasks/INTEGRATION_TASKS.md`.

- **Backend Team:**
  - INT-B1: approve the CT-10 Proposed change (gates AI-058).
  - INT-B2: approve CT-11 v1.2.
  - INT-B3: deliver the DEC-29 data gaps G-01, G-02, G-04 and G-06.
  - INT-B4: separate pilot and tug job intervals.
  - INT-B5: review the CT-13 message keys.
  - Later or optional: INT-B6 retraining grants, INT-B7 a hash column, INT-B8 an issue `code` column.
- **QA Team:**
  - INT-Q1: give the stowage upper bounds, or fix corpus case 12.
  - INT-Q2: propose the new codes in CT-24.
  - INT-Q3: provide real payloads for the DEC-34 gate.
- **Frontend Team:** INT-F1, translate the validation message keys.
- **Leads Council, Terminal operations:**
  - INT-L1: the import dwell value.
  - INT-L2: the yard solver time limit.
  - INT-L3: a real BAPLIE with onward-vessel data.
  - INT-L4: a Damietta source for compulsory pilotage.
  - INT-L5: Damietta's yard bay numbering.
- **Mobile Team:** nothing new from this session (DEC-29 G-02 is already planned with the Backend).

## 8. User Decisions Required

Details and trade-offs: `docs/tasks/DECISION_RECOMMENDATIONS.md`.

- **R1:** accept this session's seven Proposed task decisions. Mainly the AI-055 `RESOURCE_COST` definition.
- **R2:** DEC-31, Option 1: a scheduler inside the Part 3 worker. Unblocks AI-073.
- **R3:** build AI-045 on labelled synthetic data under DEC-34's gates. Lets AI-055 close. It needs a source for the squat coefficients.
- **R4:** close DEC-07 with Option 1, already marked "agreed" in the entry. DEC-24 still needs values from DEC-30.
- **R5:** keep DEC-22 Open.

## 9. Remaining Tasks

Every task not listed in §3 is blocked. Per-task reasons are in `docs/tasks/BLOCKED_TASKS.md`. In short:

- **Waiting for a merge:** AI-032, AI-056, AI-057, AI-074, AI-071, AI-072.
- **Waiting for a decision:** AI-073 (DEC-31), AI-007, AI-046, AI-047, AI-048 (DEC-07, DEC-24), AI-045 (R3).
- **Waiting for data:** AI-020, AI-021, AI-022, AI-024, AI-042, AI-100 to AI-106.
- **Later waves:** they wait on the chains above (AI-058 onwards).

## 10. Technical Risks

| Risk | Severity | Note |
|---|---|---|
| UKC not enforced in Part 2 until AI-045 | High | A vessel with draft = water depth can be placed. Already a known follow-up from AI-051 |
| DEC-32 interim intervals over-reserve pilots and tugs for the whole berth stay | Medium | Long stays may come out `NOT_PLACED`. Needs INT-B4 |
| Append-at-end conflicts in `ATLANTECH_Decisions.md` and `WORK_STATUS.md` across 8 PRs | Low | Resolve by keeping both sides |
| AI-070 integration tests and the new table-parity cases not run locally | Low | CI runs them against MySQL. The column order was checked against `schema.sql` by hand |
| `ortools` adds `numpy`, `pandas`, `protobuf`, `absl-py` to the runtime image | Low | Hash-locked in `uv.lock`; AI-090 should size the image |
| `common/README.md` still lists quality, registry and observability as "planned" | Low | Update once these branches are merged (one line) |

## 11. GitHub Delivery Summary

| Operation | Status |
|---|---|
| Commits | Done, 8 branches. The SHAs in §3 are verified with `git log`; the SETUP head is given in the session's last message |
| Pushes | Verified with the remote branch listings |
| PRs | **Not created.** `gh` is not installed |
| Merges | **None.** No local merges were made, as the rules require |
| CI | Not observed from here. It starts on each push (`ci.yml` runs on every push) |

To open the PRs, use these compare links, each against `develop`:

- https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-065-yard-placement-design
- https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-025-data-quality-checks
- https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-031-baplie-validation-rules
- https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-070-model-registry-integration
- https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-092-observability-logs-metrics
- https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-055-b5-cp-sat-allocation-model
- https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-060-override-validation-service
- https://github.com/Atlantech-project/project-ai/compare/develop...feature/SETUP-autonomous-execution-records

## 12. Verification Summary

| Check | Baseline `3180e90` | On each task branch |
|---|---|---|
| `pytest -m "not integration"` | 1433 passed, 47 skipped | AI-055: 1484 passed · AI-031: 1503 passed, 48 skipped · AI-060: 1460 · AI-025: 1454 · AI-070: 1449 · AI-092: 1449 (no failures) |
| `ruff check .`, `ruff format --check .`, `mypy` | clean | clean on every branch |
| Integration (MySQL, Redis) | not run locally (Docker daemon down) | not run locally; CI only |
| Document tasks (AI-065, SETUP) | — | `git diff --check` clean; table cell counts; CRLF kept |

## 13. Current Project State

- **Local repository:**
  - On the SETUP branch, with nothing left uncommitted from the session.
  - Untracked and deliberately not committed: `reports/status-2026-11-19.md` (earlier session) and `reports/CHECKPOINT.md` (scratch).
  - The pre-session work is preserved: the original AI-065 record lives on its branch, and the backup is in `_backups/2026-11-21-preflight/`.
- **Next steps:**
  1. Open and merge the eight PRs, in the order in `docs/tasks/AUTONOMOUS_EXECUTION_PLAN.md` §1.
  2. Move the PortHub pointer after each merge.
  3. Answer R1–R4.
  4. Then AI-056 and AI-057 (after AI-055), AI-032 (after AI-031) and AI-074 (after AI-025) become ready.

---

# Round 2 — post-merge verification and continued execution (2026-11-21)

## R2.1 Merge verification

| PR | Task | Merge commit | Merged (UTC) | CI on merge commit |
|---|---|---|---|---|
| #41 | SETUP-autonomous-execution-records | `6ed8c91` | 2026-11-21 19:16 | green |
| #42 | AI-070 | `78c1590` | 2026-11-21 19:20 | green |
| #43 | AI-025 | `1a996e0` | 2026-11-21 19:26 | green |
| #44 | AI-092 | `fec76df` | 2026-11-21 19:30 | green |
| #45 | AI-031 | `4408065` | 2026-11-21 19:34 | green |
| #46 | AI-055 | `c7e60f1` | 2026-11-21 19:38 | green |
| #47 | AI-060 | `8b955ed` | 2026-11-21 19:41 | green |
| — | AI-065 | **not merged: no PR opened** | — | branch CI green |

- `develop` = `8b955ed`; locally 1634 unit tests pass (1433 + 201), ruff and mypy clean.
- Found in the merge round: a duplicate, stale AI-051 row in `WORK_STATUS.md`. No duplicate decision entries or status files.
- Status after verification:
  - DONE: AI-025, AI-031, AI-092, the first SETUP branch.
  - BLOCKED: AI-055 (AI-045 gate) and AI-070 (registration needs grants).
  - IN PROGRESS: AI-060 (queue handler).

## R2.2 PortHub

- Commits `38dd6b5` and `a3a1eb3` were verified on `main`.
- Pointer commit `e06e102` moves `project-ai` to `8b955ed`.
- No shared Decisions or Contracts changed in this round, so nothing else was synced.

## R2.3 Round-2 branches

| Task | Head | Tests | State |
|---|---|---|---|
| AI-065 | `62f3af0` | document task | `develop` merged in, conflicts resolved; awaiting PR |
| AI-056 | `ac3f51a` | 19 unit | awaiting PR; CI green |
| AI-074 | `57b3817` | 8 unit + 1 integration | awaiting PR |
| SETUP-post-merge-records | see branch | — | merge last |
| AI-032 | `6ae3ce7` | 35 unit + 2 integration | awaiting PR; first CI run failed on a test seed (fixed; full suite with MySQL passes locally) |
| AI-072 | `f3483fb` | 15 unit + 1 integration | awaiting PR; full suite with MySQL passes locally |

## R2.4 Contract finding

- **AI-032 criterion 3** asks that the previous ACTIVE file become REPLACED in the same transaction.
- CT-12 step 5 and DEC-08 give that write to the Backend: the worker never writes `baplie_files.status`.
- I follow the contract and recorded this as R6.

---

# Round 3 — delivery queue and continued work (2026-11-21)

## R3.1 Verified state

- `origin/develop` = `8b955ed`, unchanged since round 2.
- No PRs are open and `gh` is not installed, so the PRs below must be opened in the browser.
- `ci-ok` is green on every head listed (AI-060 handler: pushed last; check its CI).

## R3.2 PRs to open (task branches in any order; SETUP last)

| Task | Head | Compare link | Description | Evidence |
|---|---|---|---|---|
| AI-065 | `62f3af0` | https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-065-yard-placement-design | B8 constraint-to-table mapping (Proposed AI task decision) | Document checks; CI green |
| AI-056 | `ac3f51a` | https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-056-solver-outcome-handling | CT-10 outcomes, FIFO fallback, reasons for unplaced requests | 19 unit; CI green |
| AI-074 | `57b3817` | https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-074-trusted-data-selection | Trusted-only reads of field events for Part 3 | 8 unit + 1 MySQL; CI green |
| AI-032 | `6ae3ce7` | https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-032-baplie-commit-quarantine | All-or-nothing BAPLIE commit and quarantine; worker never writes file status (R6) | 35 unit + 2 MySQL incl. fault injection; CI green |
| AI-072 | `f3483fb` | https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-072-drift-monitor | PSI, rolling MAE, drift rows; thresholds only from CT-18 keys | 15 unit + 1 MySQL; CI green |
| AI-060 handler | `4add5e0` | https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-060-validate-queue-handler | `queue:validate` handler and the shared B2 `FilterContext` loader | 12 unit + 2 MySQL; full suite with services: 2105 passed |
| SETUP | this branch | https://github.com/Atlantech-project/project-ai/compare/develop...feature/SETUP-post-merge-records | Records. **Merge last**; refreshed by merging `develop` into it after the others | Docs only |

`git merge-tree` check: the six task branches merge cleanly with each other; only SETUP conflicts (tracker rows).

## R3.3 Work this round

- **Shared B2 context loader** (`part2/context.py`):
  - built from `constraint_types` (new table definition), `vessel_types` and the AI-054 tug requirements;
  - no schema change needed; the missing DEC-20 inputs are requested as INT-B9.
- **AI-060 handler** (`part2/validation/job.py`): built on the loader.
- **AI-057 investigated:**
  - `seed-spec.json` has `rationale_templates: []`;
  - AI-009 was closed by a Leads ruling with criterion 3 (domain-reviewed templates) open;
  - no template text exists, so per-template rendering tests can't be met (INT-Q4). Not started.
- **AI-033:** waits for AI-032 to merge.
- **AI-066:** waits for AI-032, AI-058 and the Backend's DEC-29 gaps (INT-B3). Nothing safe to build beyond the AI-065 mapping.
- **AI-073:** waits for DEC-31 (R2). Planned approach, per the R2 recommendation:
  - a scheduler inside the Part 3 worker;
  - cadence from `port_settings`;
  - a one-run lock.

  Not started, by rule.
- **AI-045:** needs R3 (synthetic path) plus a sourced squat coefficient (flag X). Not started.
- **AI-072, three states:**
  - code complete and tested;
  - not production-ready (no thresholds, R8; no model version, OD-17);
  - task criteria met in code; the "stored" criterion is proven in MySQL.

## R3.4 Exact next action

1. Open and merge the six task PRs.
2. Merge `develop` into the SETUP branch, keeping every task's own row; push; check CI; merge.
3. Move the PortHub pointer.
4. Start AI-033 (after AI-032 merges). AI-058 then needs AI-056, AI-057 and INT-B1.

---

# Round 4 — round-3 merge verification (2026-11-22)

## R4.1 Merges verified

| Task | PR | Merge commit | Merged (UTC) | Status now |
|---|---|---|---|---|
| AI-065 | #48 | `7fc6954` | 2026-11-22 09:29 | IN REVIEW (Proposed mapping; R7) |
| AI-056 | #49 | `44fd4ec` | 2026-11-22 09:29 | DONE |
| AI-074 | #50 | `8b2032c` | 2026-11-22 09:29 | DONE |
| AI-032 | #51 | `44e4b95` | 2026-11-22 09:29 | BLOCKED (criterion 3: R6, INT-B10) |
| AI-060 handler | #53 | `7042ceb` | 2026-11-22 09:30 | DONE (with service PR #47) |
| AI-072 | #52 | `b98024a` | 2026-11-22 09:32 | DONE (production values: R8) |
| SETUP-post-merge-records | #54 | `ddfb551` | 2026-11-22 09:33 | DONE |

CI on `develop` `ddfb551`: all checks success.

## R4.2 Work this round

- **Tracker clean-up:** the SETUP merge kept every row, so seven stale duplicates were removed and the statuses above set, each with its merge evidence.
- **AI-033:** `DEFERRED (DEC-17)`. NFR-PERF-2 was removed from the MVP (Leads Council, 2026-10-27), so there is nothing to build (R10).
- **AI-071:** investigated. The metric definitions are missing (R9), so it was not started.
- **CT-12 `flag_state`:** checked. The worker may fill it, but the parsed records don't carry it; this was already recorded in the AI-032 decision entry, so it isn't a new gap.
- **PortHub:** the `project-ai` pointer moved to `ddfb551`.

## R4.3 Exact next action

1. Merge `feature/SETUP-round3-merge-records`.
2. Decide R2, R3, R4, R6, R7, R8 and R9.
3. Deliver INT-Q4, INT-B1 and INT-B10.

---

# Round 5 — full backlog audit and handoff (2026-11-22)

## R5.1 Verified state

- **`develop`:** `ddfb551`, CI green.
- **`feature/SETUP-round3-merge-records`:** at `dafda7b` with CI green, but **not merged**. No PR exists for it (GitHub pulls API, filtered by head branch).
- **PortHub:** `project-ai` points at `ddfb551` = `develop` HEAD (PortHub `e24424e`).
- **Shared documents:**
  - The Decisions shared part is identical in both repositories (sha256 `07472a76…`).
  - `ATLANTECH_Contracts.md` differs only in project-ai's local header (canonical-file rules) and in rewritten PortHub links.
  - Every `contracts/ai/` file matches `docs/ref/ai-payloads/`.
- **Gap found and fixed:** the pinned `docs/ref/db/schema.sql` was PortHub `b4d2deb`, but PortHub is at `d55a263`. It is re-pinned on `feature/AI-050-dec28-dec32-schema-followups` (see R5.3).
- **Tracker:** at `dafda7b`, `WORK_STATUS.md` has exactly one row per task (script check: no duplicate IDs).

## R5.2 Every backlog task (76), classified

| Class | Tasks |
|---|---|
| DONE (30) | AI-001 to AI-006, AI-008 to AI-016, AI-023, AI-025, AI-030, AI-031, AI-044, AI-050 to AI-054, AI-056, AI-060, AI-072, AI-074, AI-092 |
| IN REVIEW, merged, awaiting decision approval (1) | AI-065 (R7) |
| BLOCKED_DECISION (7) | AI-007 (R4) · AI-073 (R2) · AI-045 (R3 plus a sourced squat coefficient) · AI-055 close (R3 → AI-045) · AI-071 (R9) · AI-032 close (R6 plus INT-B10) · AI-057 (R11 plus INT-Q4) |
| BLOCKED_EXTERNAL (6) | AI-020, AI-021, AI-022, AI-024 (data, flag D) · AI-042 (needs AI-021) · AI-070 close (INT-B6 grants) |
| DEFERRED (1) | AI-033 (DEC-17) |
| WAITING on unfinished prerequisites (31) | Part 1 chain: AI-040, AI-041, AI-043, AI-046 to AI-049 · Part 2: AI-058, AI-059, AI-061, AI-062 · yard: AI-066, AI-067, AI-068 · integration and ops: AI-080 to AI-084, AI-090, AI-091, AI-093 to AI-095 · ML: AI-100 to AI-106 |
| READY (0) | none |

**How it was checked:** a script read every backlog section's prerequisites against the `DONE` rows of `WORK_STATUS.md`. Each task whose prerequisites are all met was then checked against its flags, its acceptance criteria and the decisions it depends on. No independently executable AI-owned task is left, apart from the item below, which has now been done.

## R5.3 Overlooked item found and done: DEC-28 / DEC-32 schema follow-ups

- **What changed:** the Backend delivered G-14 (per-job pilot and tug intervals, INT-B4) and G-09 (`loading_container_count`) in PortHub `schema.sql` `d55a263`.
- **The AI side, on branch `feature/AI-050-dec28-dec32-schema-followups` (`6e9f23e`, pushed):**
  - schema re-pinned;
  - five columns added to `tables.py`;
  - pending pilot and tug holds use their own job interval (else the option window, DEC-32 rule 4);
  - the request read carries the loading count.
- **Tests:** full suite with MySQL and Redis: 2192 passed, 50 skipped, 1 xfailed. Ruff and Mypy are clean.
- **PR:** https://github.com/Atlantech-project/project-ai/compare/develop...feature/AI-050-dec28-dec32-schema-followups
- **Status:** AI-050 stays DONE; this is recorded as a follow-up in its status record and decision entry.

## R5.4 Exact next actions

1. **Merge `feature/SETUP-round3-merge-records`** (records; carries rounds 4 and 5).
2. **Merge `feature/AI-050-dec28-dec32-schema-followups`** (code). The two touch different files except `INTEGRATION_TASKS.md`, which only the AI-050 branch edits.
3. **Tell me once they're merged.** I'll then move the PortHub pointer, verify CI and set the records.
4. **Decide R1 to R11** (handoff in `DECISION_RECOMMENDATIONS.md`). What each one unblocks:

   | Decision | Unblocks |
   |---|---|
   | R9 | AI-071 |
   | R2 | AI-073 |
   | R3 | AI-045, then closing AI-055 |
   | R4 | AI-007, then AI-046 to AI-048 |
   | R6 | closing AI-032 |
   | R7 | closing AI-065 |
   | R8 | AI-072 in production |
   | R11 | starting AI-057's factor slice |

5. **Ask the other teams for INT-Q4, INT-B1, INT-B10 and INT-B6.** These are external deliverables, not decisions, so they sit outside R1–R11 (see the handoff).
