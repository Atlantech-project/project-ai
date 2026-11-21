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
