# AI-010 · AI code repository and module structure: implementation plan

> **For agentic workers:** implement task by task with superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. ATLANTECH rule: no step stages, commits, pushes or merges. Publishing happens only through `/atlantech-review-and-publish AI-010` after the user's exact `APPLY CHANGES`.

**Goal:** Record the proposed location and module structure of the AI code, and lay down a documentation-only module skeleton (`common`, `edi`, `part1`, `part2`, `part3`) that later tasks (AI-011–AI-016) fill.

**Architecture:** One directory per worker, following invariant I-5 (Parts 1, 2, 3 and the EDI Parser are separate workers) and D18 (one queue per part), plus `common/` for code shared by all workers. Each directory holds only a `README.md` that states its worker, queue, components (with the AI-001 status from DL-001), the tables it writes, and what it must never do. No Python files and no project configuration, because tooling is not decided (OQ-1).

**Tech stack:** Markdown only. No tooling is chosen in this task.

**Spec:** this plan. It argues from backlog §5 AI-010, `ATLANTECH_AI_ARCHITECTURE.md` §2, §4.3, §8.14, §9, §11, §12.2, `Master_Context.md` §5.4 and §9, and DL-001 (AI-001 inventory).

## Task

- **ID:** AI-010, Decide AI code repository and module structure (P0, phase P1 Foundations, complexity S, flag A).
- **Branch:** `feature/AI-010-ai-repository-module-structure`, from `develop` = `origin/develop` = `1cec937`.

## Scope

**In:**
1. `DL-002` (PROPOSED) in `docs/tasks/DECISION_LOG.md`: repository location and module structure.
2. Module skeleton: `common/README.md`, `edi/README.md`, `part1/README.md`, `part2/README.md`, `part3/README.md`.
3. Root `README.md`: a "Repository layout" section, and status notes that bring the component tables in line with DL-001 (A6 future work; C3/C4 and the M-models data-gated).
4. Records: `docs/tasks/status/AI-010.md`, the `WORK_STATUS.md` row, and `DL-001` (already written at planning time).

**Out:**
- Any Python file (`__init__.py`, modules, tests), and any project configuration or tooling: `pyproject.toml`, `requirements*.txt`, lock files, `setup.cfg`, `Dockerfile`, compose files, CI configuration, linters, `.python-version`. All of these wait for OQ-1.
- Directories for schemas, an API service, tests, tools or model artefacts (OQ-2, OQ-3, OQ-7).
- The work of AI-011 (runtime), AI-012 (config), AI-013 (db), AI-014 (units/time), AI-015 (harness) and AI-016 (CI).
- Edits to `docs/ref/`, the backlog, `ATLANTECH_Contracts.md`, `ATLANTECH_Decisions.md` and `CLAUDE.md`.
- Repository settings on GitHub (branch protection), recording the AI-002 decision, and fixing the stale SETUP-001 row in `WORK_STATUS.md` (it still says `IN REVIEW` although PR #2 is merged). These are follow-ups for the user.

## Files likely to change

| Path | New / existing |
|---|---|
| `common/README.md`, `edi/README.md`, `part1/README.md`, `part2/README.md`, `part3/README.md` | new |
| `README.md` | existing |
| `docs/tasks/DECISION_LOG.md` | existing (DL-001 added at planning; DL-002 in Task 1) |
| `docs/tasks/status/AI-010.md` | new (written at planning) |
| `docs/tasks/WORK_STATUS.md` | existing (AI-010 row added at planning) |
| `docs/superpowers/plans/2026-10-27-ai-010-repository-module-structure.md` | new (this plan) |

## Dependencies

| Item | Status | Evidence |
|---|---|---|
| AI-001 (prerequisite) | Treated as resolved for planning: supplied record says `Closed`, approved by AI Lead · Team Lead; date blank | DL-001 (PROPOSED until the date is confirmed) |
| AI-002 | Not an AI-010 prerequisite (backlog line 468 lists AI-001 only). Used as context; not changed | User-supplied record; DEC-01, DEC-02 recommendations; DEC-54 Closed |
| SETUP-001 | Merged into `develop` (PR #2, `1cec937`) | `git log origin/develop` |
| DEC-10 FastAPI scope | Open: affects whether an API module exists (OQ-3) | `ATLANTECH_Decisions.md` |
| DEC-31 Part 3 scheduling host | Open: noted in `part3/README.md` only (OQ-4) | `ATLANTECH_Decisions.md` |
| Contracts location | Proposed as `PortHub/contracts/` (OQ-2) | `ATLANTECH_Contracts.md` line 12 |
| Missing sources | "Plan F-18" is in `ATLANTECH_AI_IMPLEMENTATION_PLAN.md`, not in the repository | `CLAUDE.md` list of missing documents |

## Open questions (unresolved; not decided by this plan)

| ID | Question | Who decides | Effect on AI-010 |
|---|---|---|---|
| OQ-1 | Python tooling, Python version, dependency management, development environment (local, Docker or both) | AI Team (team discussion; pending at the user's request, 2026-10-27) | No Python or config files in the skeleton; READMEs say "pending OQ-1" where setup would go |
| OQ-2 | Where AI-owned JSON Schemas (CT-08, CT-13–CT-16) live: this repository or `PortHub/contracts/` as proposed | AI Team with the contract reviewers (Backend) | No `schemas/` directory created |
| OQ-3 | Whether an internal FastAPI module exists and where (DEC-10, Open) | AI Team | No `api/` directory created; `common/README.md` notes it |
| OQ-4 | Part 3 scheduling host (DEC-31, Open) | AI Team | `part3/README.md` notes it |
| OQ-5 | Approval of `project-ai` as the AI code location (DL-002), and adding it to `Master_Context.md` §5.4 by that file's owner | AI Lead · Team Lead; organisation owner if a repository-level approval is required (backlog AI-010 note) | Acceptance criterion 1 stays unmet until approved |
| OQ-6 | Branch protection on `develop`, `main`, `release` and the PR flow: do they match the team convention? | Repository admin | Can't be verified here (`gh` not installed); acceptance criterion 2 stays unverified |
| OQ-7 | Locations for tests, tools and model-artefact tooling (AI-015 proposes `tests/fixtures`, `tools/scenario_generator`) | Later tasks, after OQ-1 | Not created; listed as planned in the root README |
| OQ-8 | Python package and import layout (package files, import root name) | AI Team, with OQ-1 | Not created |

## Contract / decision changes

- **Existing IDs touched:** none edited. Referenced: DEC-10, DEC-21, DEC-25, DEC-29, DEC-31, DEC-55; CT-08, CT-13–CT-16; D18; I-5.
- **DL-001 (PROPOSED, written):** AI-001 inventory as supplied.
- **DL-002 (PROPOSED, Task 1):** exact text in Task 1.
- **CONTRACT_LOG:** no entry. OQ-2 may need one later, once the team chooses a schema location.

## Tests (document checks; there is no code)

Run these from the repository root in Git Bash. Expected results are given in Task 4.

1. Scope: `git status --short` lists only the paths in "Files likely to change".
2. No tooling added: `git status --short --untracked-files=all | grep -E '\.(py|toml|cfg|ini|lock|ya?ml)$|requirements|Dockerfile|compose|Makefile|\.python-version'` prints nothing.
3. Inventory coverage: every component ID appears as a table row in exactly one module README (script in Task 4).
4. Links: every relative link in the new and changed READMEs resolves to an existing path.
5. `git diff --check` prints nothing.
6. Log integrity: `DL-001` and `DL-002` both have a Status row starting with `PROPOSED`, and no entry is marked `APPROVED` (the word appears only in the log's header rules, as on `origin/develop`).

## Risks

- **Approval risk:** DL-002 may be rejected or changed (for example, schemas moved to PortHub). Mitigation: the skeleton is documentation only, so changing it is cheap.
- **Over-reach:** a README could read as if it settles an Open decision. Mitigation: each README lists open items as "pending DEC-xx / OQ-x" and copies component status only from DL-001.
- **Record drift:** DL-001 rests on a record with a blank date; if the date or content changes, DL-001 and the module READMEs must change with it.
- **Coordination:** Backend and QA reference `project-ai` paths later (CT-26 asks for `ai@<commit>`). Any later rename of a module costs them updates.
- **Data and performance:** none; no code runs.

## Acceptance criteria (quoted from backlog §5 AI-010) and verification

| Criterion | Verification | Expected state at the end of this task |
|---|---|---|
| "Location approved and created" | Created: `git remote -v` shows `Atlantech-project/project-ai`. Approved: DL-002 status | Created: yes. Approved: **not met**. DL-002 stays PROPOSED until OQ-5 is answered |
| "Branch protection and PR flow match the team convention" | Repository admin checks the GitHub settings (OQ-6) | **Unverified** in this task; the result is recorded in the status record when available |
| "Module skeleton committed" | After `APPLY CHANGES`: `git ls-tree --name-only HEAD common edi part1 part2 part3` lists the five READMEs | Met only after review-and-publish commits it |
| Verification evidence: "Repository link and first merged PR" | The user's PR into `develop` and its merge | Outside this session |

## Review focus

- A README that names a method or value for an Open decision (DEC-10, -21, -25, -29, -31) instead of "pending".
- A component listed with a status that differs from DL-001 (for example, A6 shown as built, or C3 shown as MVP).
- A file that implies a tooling choice (a Python file, a config file, a setup command in a README).
- A README that claims a worker writes a table the AI doesn't own (Architecture §11 and §12.2), for example `berthing_request.status`, `audit_log` or `notification_log`.
- The root README "Getting started" still promising setup steps without saying they wait on OQ-1.

---

### Task 1: DL-002 · Repository location and module structure

**Files:** Modify `docs/tasks/DECISION_LOG.md` (append after DL-001).

- [ ] **Step 1: Append this entry exactly**

```
### DL-002 · AI code repository location and module structure (AI-010)
| Field | Value |
|---|---|
| Status | PROPOSED |
| Related | AI-010, AI-001 (DL-001), AI-011–AI-016, DEC-10, DEC-31, CT-08, CT-13–CT-16, D18 |
| Owner | AI Team |
| Reviewers | AI Lead · Team Lead; organisation owner if a repository-level approval is required (backlog AI-010 note) |
| Proposed by / date | mostafa, 2026-10-27 |
| Evidence | `Master_Context.md` §5.4 lists `project-backend`, `project-frontend` and `project-mobile` but no AI repository; `Atlantech-project/project-ai` exists and is this repository's `origin`; `ATLANTECH_AI_ARCHITECTURE.md` I-5 and §4.3 (four separate workers, one queue each); backlog AI-010 expected outputs (modules `common, edi, part1, part2, part3`, marked PROPOSED) |
| Change | (1) AI code lives in `Atlantech-project/project-ai`, with `feature/<task>` branches from `develop` merged by PR. (2) Top-level modules: `common/` (shared by all workers), `edi/` (EDI Parser, B1, `queue:edi`), `part1/` (A1–A7, `queue:part1` plus internal scheduler), `part2/` (B2–B8, `queue:part2`), `part3/` (C1–C4, periodic). Each part is one deployable worker (D18). (3) Not decided here: Python tooling, version, dependency management and environment (OQ-1); schema location (OQ-2, `PortHub/contracts/` proposed in `ATLANTECH_Contracts.md`); FastAPI module (DEC-10); Part 3 scheduling host (DEC-31); test, tool and model-artefact locations (OQ-7) |
| Reason | The documented repositories don't include the Python workers (backlog AI-010) |
| Impact | AI-011–AI-016 place their code under these modules. `Master_Context.md` §5.4 would need its owner to add `project-ai`. Backend and QA reference `project-ai` commits (CT-26) |
```

- [ ] **Step 2: Check** `grep -c '^### DL-' docs/tasks/DECISION_LOG.md` prints `2`.

### Task 2: Module skeleton

**Files:** Create `common/README.md`, `edi/README.md`, `part1/README.md`, `part2/README.md`, `part3/README.md`.

Every module README uses the same headings, in this order: `# <module>`, one-line purpose, `## Worker and queue`, `## Components` (table: `| ID | Component | Status |`, statuses copied from DL-001: `MVP`, `DATA-GATED`, `FUTURE WORK`), `## Writes` (tables from Architecture §12.2), `## Never` (the invariants that bind this worker), `## Pending` (OQ and DEC items), `## References`. Use the architecture's wording; add no method or value that the sources don't state. `common/README.md` has no Components or Writes tables.

- [ ] **Step 1: `edi/README.md`.** Worker: EDI Parser, `queue:edi`. Components: `| B1 | BAPLIE parser | MVP |`. Writes: `baplie_file` (status fields), `baplie_parse_issue`, `container`, `container_manifest_entry`, `vessel` (fill-empty); the Backend creates the file row. Never: I-11 (deterministic, all-or-nothing; not AI). Pending: OQ-1, OQ-2 (CT-12 schema).
- [ ] **Step 2: `part1/README.md`.** Worker: AI Part 1, `queue:part1` plus the internal scheduler (weather every 6 h, daily tide). Components: A1, A2, A3, A4, A5, A7 Phase 1 aggregation as `MVP`; `| A6 | Uncertainty margin | FUTURE WORK |` with the note "MVP: zero margin, `confidence` = NULL (DEC-25, Open)"; M3 LightGBM (A7 Phase 2) as `DATA-GATED`, written in A7's row note, not as a separate ID row. Writes: per §12.2 (`forecast_run`, `environment_forecast_point`, `tide_prediction_run`, `tide_prediction_point`, `demand_forecast_slot`, `part1_run` updates, `entry_window_proposal`, `feasible_window`, `blocked_period`). Never: I-2, I-6, I-10, I-15. Pending: OQ-1, DEC-25.
- [ ] **Step 3: `part2/README.md`.** Worker: AI Part 2, `queue:part2`. Components: B2, B3 Phase 1 formula, B4 Phase 1 rule ("or NULL until DEC-21 is approved"), B5 with FIFO fallback, B6, B7, B8 (note: "new identifier; method set by DEC-29, Open") as `MVP`; M2 (B3) and M4 (B4) noted as `DATA-GATED` in their rows. Writes: per §12.2 (`solver_run`, `solver_run_model_version`, `recommendation`, `recommendation_option`, `recommendation_option_tug`, `recommendation_rationale_factor`, `terminal_recommendation` generation result, `yard_placement_item`). Never: I-3 (sole allocator), I-7, I-8, I-9, and "never changes `yard_slot.container_id`" (§8.14). Pending: OQ-1, DEC-21, DEC-29.
- [ ] **Step 4: `part3/README.md`.** Worker: AI Part 3, periodic, no user queue. Components: C1, C2 as `MVP`; C3, C4 as `DATA-GATED`. Writes: `evaluation_metric`, `drift_measurement`; `ml_model_version`, `retraining_run` (data-gated). Never: I-4, I-6, I-13. Pending: OQ-1, DEC-31 (scheduling host), OQ-7 (model-artefact tooling; artefacts stay on the local file volume, §9.4).
- [ ] **Step 5: `common/README.md`.** Purpose: code shared by every worker; no worker logic. List the planned contents only as text, with their tasks: runtime (AI-011), config (AI-012), db (AI-013), units and time (AI-014). State the shared rule that all workers write only the tables in Architecture §12.2, never `berthing_request.status`, `audit_log` or `notification_log` (§11; DEC-02). Pending: OQ-1, OQ-3 (DEC-10 FastAPI), OQ-8.
- [ ] **Step 6: Check** `ls common edi part1 part2 part3` shows exactly one `README.md` in each.

### Task 3: Root README

**Files:** Modify `README.md`.

- [ ] **Step 1:** Insert a `## Repository layout` section between "Stack" and "Getting started": a tree of the five module directories, each with one line and a link to its README. Below it, one line stating that schemas, an API service, tests, tools and model-artefact tooling have no directory yet (OQ-2, OQ-3, OQ-7) and that the structure is proposed in DL-002.
- [ ] **Step 2:** In the Part 1 table, append " (future work; the MVP uses zero margin)" to the "Safety margin" row. In the Part 3 table, append " (data-gated)" to the "Retraining" and "Bias correction" rows. Change no other rows.
- [ ] **Step 3:** Replace the line "Setup steps will be added here as each worker takes shape." with "Setup steps will be added once the team decides the Python tooling and environment (open question OQ-1 in AI-010)."

### Task 4: Verify and update the record

**Files:** Modify `docs/tasks/status/AI-010.md`.

- [ ] **Step 1: Scope and tooling checks** (Tests 1, 2, 5). Expected: only the planned paths; the grep prints nothing; `git diff --check` prints nothing.
- [ ] **Step 2: Inventory coverage** (Test 3). Run:

```bash
for id in A1 A2 A3 A4 A5 A6 A7 B1 B2 B3 B4 B5 B6 B7 B8 C1 C2 C3 C4; do
  n=$(grep -l "^| $id |" common/README.md edi/README.md part1/README.md part2/README.md part3/README.md | wc -l)
  echo "$id $n"
done
```

Expected: every line ends in `1`.
- [ ] **Step 3: Links** (Test 4). For each `](path)` that isn't a URL in `README.md` and the five module READMEs, `test -e` the path relative to that file. Expected: no failures.
- [ ] **Step 4: Log integrity** (Test 6). `grep -n '| Status |' docs/tasks/DECISION_LOG.md` shows both entries starting with `PROPOSED`; `grep -c APPROVED docs/tasks/DECISION_LOG.md` counts only the header and rules text. Compare it with the count on `origin/develop` (`git show origin/develop:docs/tasks/DECISION_LOG.md | grep -c APPROVED`); the two must be equal.
- [ ] **Step 5:** Update `docs/tasks/status/AI-010.md` with the actual output of Steps 1–4, set Status to `IN REVIEW`, update the `WORK_STATUS.md` row to match, and direct the user to `/atlantech-review-and-publish AI-010`.
