# SETUP-003 · PortHub contracts and decisions synchronization
| Field | Value |
|---|---|
| Status | IN REVIEW |
| Owner | AI Team |
| Branch | feature/SETUP-003-porthub-contracts-decisions-sync |
| Plan | docs/superpowers/plans/2026-10-31-setup-003-porthub-sync.md · approval: explicit user approval in this conversation after Revision 2 was presented ("I approve SETUP-003 Revision 2 with the following final decisions", 2026-10-31); the plan file is a transcription written after that approval |
| Updated | 2026-10-31 |

Setup task, not in the official AI backlog. Documentation, schemas and eval tooling only; no production AI code. The permanent synchronization policy (`CLAUDE.md`, skills, workflow text) is **SETUP-004** and is not part of this task.

## Summary of the change
PortHub `main` at `c84d2a4` (re-fetched before implementation; unchanged) is the source of truth for shared Contracts and Decisions. Shared items were adopted item by item; nothing was copied wholesale.

- **Decisions** (`docs/ref/ATLANTECH_Decisions.md`): range `DEC-01`–`DEC-57`; DEC-05, 13, 35, 36, 47 set to PortHub's Closed text (Summary, Status, Decision); DEC-57 added; DEC-04 records the CT-08 approval of 2026-10-30 and loses its "Open dependency" row; `w_edi` gains `retry_count` with PortHub's 2026-10-28 note.
- **Contracts** (`docs/ref/ATLANTECH_Contracts.md`): CT-08 Approved v1.0 (2026-10-30); CT-01 in PortHub's short form with reviewers "critical changes only (DEC-57)"; CT-02 Approved v1.0.0 (2026-10-30); CT-03 Approved v1.0 (2026-10-31), `username`, example role `PORT_STAFF`. Links to PortHub-only files (`api-conventions.md`, `error-codes.md`, `auth-web.md`) are written as "PortHub `contracts/<file>`" because those files are not mirrored. The "Local reference copies" paragraph lists the new mirrors and says `schema.sql` is not mirrored.
- **Schemas and references** (`docs/ref/ai-payloads/`, identical to PortHub): `c01-part1-run`, `c02-part2-solve`, `c03-yard`, `c04-baplie` (so the envelope `$ref`s now resolve), `table-ownership.md` (CT-15 matrix), `contract-v1-record.md`. `db/schema.sql` is **not** mirrored (user decision); read it from PortHub `contracts/db/schema.sql`.
- **Dependents:** task-workflow eval 5 (`unresolved-contract`) assumed CT-08 Proposed. `build_fixtures.sh` now pins CT-08 to Proposed for that scenario only, and `evals.json` says so.
- **Records:** AI-014 set to DONE (PR #7, merge `2f3b89e`). AI-016 stays IN REVIEW with PR #5 (`451daff`) recorded as merge evidence; its two outstanding criteria are preserved (no scope exception). `WORK_STATUS.md` updated.
- **Preserved, untouched:** the whole "AI task decisions" section (AI-001, AI-010 Closed; AI-016, AI-014 Proposed), both single-source-of-truth rule blocks, and every other local-only text. Task completion statuses and the status of AI-owned decisions are separate: the AI-014 task decision stays `Proposed` although the AI-014 task is DONE.

## Prerequisites and dependencies
- **SETUP-002:** DONE (PR #4, `ea51824`).
- **AI-003 is no longer blocked by CT-08** (now Approved). It is not started and nothing here marks it, AI-011, AI-013, AI-048 or AI-080 as done.

## Contract / decision items
Existing IDs adopted from PortHub: CT-01, CT-02, CT-03, CT-08; DEC-04, 05, 13, 35, 36, 47, 57. CT-15 only through the mirrored matrix. No `Proposed change` rows, no new IDs, no local approvals invented; approvers are recorded as PortHub names them.

## References inspected
- **Read in full:** PortHub `contracts/ai/contract-v1-record.md`, `contracts/README.md`, the normalized diffs of both canonical files against PortHub, the AI-014 and AI-016 records, `WORK_STATUS.md`, the task-workflow `build_fixtures.sh` scenario code.
- **Read sections:** `table-ownership.md` (header and rules), `api-conventions.md` and `error-codes.md` (headers), the `evals.json` entry for eval 5.
- **Not read in full:** `contracts/db/schema.sql`, `contracts/openapi/port-api.yaml`, `contracts/auth-web.md`, and the bodies of `table-ownership.md` §1 onward. They were not mirrored or changed.

## Validation results (actual, 2026-10-31)
- **PortHub re-fetch:** `c84d2a4`, unchanged.
- **Normalized diff vs PortHub** (`diff --strip-trailing-cr -w`): Decisions has no PortHub-only lines; the differences are exactly the local-only rule block and the "AI task decisions" section. Contracts differs only by the local rule block and the intended link rewrites (PortHub `contracts/<file>` instead of relative links).
- **Mirrored files:** 10 files in `docs/ref/ai-payloads/` and `db/table-names.md` identical to PortHub.
- **IDs:** DEC-01..57 and CT-01..26 each have an entry and a summary row; 57 Decisions summary rows, 0 Status mismatches against their entries; no Closed entry with a blank Decision.
- **Stale text grep** (`PORT_AUTHORITY_STAFF`, "proposed: username", "awaiting Backend Team sign", CT-08 Proposed): only the eval 5 setup text, which is intentional.
- **Links:** all relative link targets in the edited and mirrored docs exist.
- **Schemas** (`jsonschema` installed in the scratchpad, not the project): all 8 schemas pass the metaschema check; all 5 envelope `$ref` targets exist; generated sample envelopes validate for PART1_RUN, PART2_SOLVE, YARD_PLACEMENT and BAPLIE_PARSE, and an empty payload is rejected for all five job types.
- **C-05 VALIDATION, explicit cases** (inside the full envelope, `date-time` format checking on): a valid OVERRIDE (BERTH, PILOT, a TUG swap, a TUG add, START_TIME) and a valid YARD_ADJUSTMENT (including a null `yard_slot_id`) pass. 10 invalid cases are rejected: OVERRIDE with yard placements, YARD_ADJUSTMENT with `changes`, a TUG with both ids null, empty `changes`, 9 changes (max 8), an unknown `component_type`, a missing `subject_id`, an unknown `validation_type`, an extra property, and a non-date-time start. 12 of 12 behave as expected. Limit, by the schema's own description: "at most one BERTH, one PILOT and one START_TIME" is not enforced by the schema (a second BERTH item is accepted).
- **Fixture builder:** `build_fixtures.sh` built `unresolved-contract` (CT-08 line reads Proposed) and `normal-unblocked` (still Approved).
- **Repo tools, project environment** (after `python -m uv sync --frozen`, which installed `tzdata==2026.6` and changed no tracked file; Windows, CPython 3.14.10): `ruff check` passes, `ruff format --check` passes (49 files), `mypy` reports no issues in 16 source files, and `pytest` gives **245 passed, 5 skipped** (the 5 skips are the MySQL/Redis integration tests, which need services). An earlier run before `uv sync` had 15 failures from the missing `tzdata` in the stale `.venv`; that run is superseded and no scratchpad workaround is used for the final result. No Python file was changed by this task.
- **Task-workflow evals** (22 scenarios in `evals.json`): all 22 fixtures built with `build_fixtures.sh` and snapshotted. Agent runs were done for three, each judged with `check_state.sh compare` (all reported SAFE). **Harness gap:** the fixtures use a local bare `origin`, but the skill's Phase 1 requires the GitHub URL, so the first runs of evals 5 and 1 stopped at Phase 1 (no branch, nothing written). They were resumed with an explicit runner note that the local bare repo stands in for `origin`; the eval 22 agent applied that stand-in on its own and said so.
  - **Eval 5 `unresolved-contract` (updated):** stopped at Phase 2 step 6, no branch, tree unchanged. It named AI-003 as an unfinished prerequisite and CT-08 as `Proposed v1.0`, wrote nothing Approved, and created no log. All 7 assertions are met. It also cited the newly mirrored `contract-v1-record.md` as conflicting evidence, which strengthens the stop.
  - **Eval 1 `normal-unblocked`:** reached the Phase 7 approval gate on `feature/AI-014-…` from the develop tip; nothing pushed, no `src/` change, status record written, plan sections covered. Deviation: the agent wrote the plan itself instead of invoking the brainstorming and writing-plans skills, and did not create a plan file.
  - **Eval 22 `decision-change-canonical`:** no log or DL-/CL- entry, said the logs were retired, drafted the `Proposed change` for CT-18 in its reply (not written to the file), CT-18 Status unchanged, named the AI Team and Backend Team approvals. Assertion not met as written: it stopped at Phase 6 with a clarifying question instead of at the plan-approval gate.
- **Not run:** GitHub CI (nothing pushed) and the agent runs for the other 19 eval scenarios.

## Open questions / follow-ups
- **SETUP-004:** durable policy in `CLAUDE.md`, the skills and workflow text; includes the rule for preparing shared AI decisions as PortHub PRs.
- **Review PortHub's two "our reading" additions** (contract-v1-record.md): C-01 `manual_forecast_run_id` required with `MANUAL_DATA` and forbidden otherwise; C-02 `berthing_request_ids` has unique items. PortHub #23 records an AI Team approval; confirm they match what the workers expect.
- **CT-05** still names `contracts/realtime-sse.md`, which is not in PortHub `contracts/`. Ask the Backend Team.
- **Redis version:** PortHub states none; `redis:7.4` stays provisional (AI-016).
- **Eval harness:** make the fixtures satisfy the skill's Phase 1 remote check (for example a git `url.insteadOf` for the GitHub URL) so evals run end to end without a runner note, and decide whether eval 22 should accept a clarifying question. Both belong to a later task, not SETUP-003.
- **AI-016** keeps two outstanding criteria (branch protection, coverage figure).
- **`gh` is not installed;** PR merges were confirmed from Git history, not the GitHub PR pages.
