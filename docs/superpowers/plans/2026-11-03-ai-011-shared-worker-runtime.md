# AI-011 · Implement shared worker runtime — plan

Written without the Superpowers skills, which are not listed in this session. The user approved this plan with changes on 2026-11-03; this version applies those changes. No step commits: publishing happens only through `/atlantech-review-and-publish AI-011`.

Contracts and decisions were read from PortHub `main` at `e118093`.

## Task

- **ID:** AI-011 · Implement shared worker runtime (queue consumer, idempotent claim, retries, logging) (P1 Foundations, P0, complexity L, flag B)
- **Branch:** `feature/AI-011-shared-worker-runtime` (from `develop` at `0ccebd3`)

## Scope

**In:** a library every worker uses, following CT-08 §6 step by step.

1. **Startup:** load the environment and check settings through AI-012, and exit non-zero if either fails, before any job is taken. This completes AI-012's first criterion.
2. **Consume (§6 step 1):** `BLPOP` one unprefixed queue, with a short timeout so shutdown is noticed.
3. **Validate (steps 2 and 3):** JSON parse, `envelope.schema.json` plus payload, `job_type` against the queue, supported major version. For a failure:
   - **`run_id` readable and `job_type` matches the queue:** claim, finish as FAILED / `INVALID_ENVELOPE`, send C-06.
   - **`VALIDATION` with a readable `job_id`:** send C-06 FAILED.
   - **Otherwise:** log the raw message, capped in length, and drop it (D1 covers the wrong-queue case).
   - **`job_id` unusable but the run claimable:** finish the run and send nothing, because no valid C-06 can be built. The Backend's 30 s poller picks up the FAILED run (CT-14).
4. **Claim (step 4):** the exact conditional `UPDATE`, checking affected rows. 0 rows: log and send nothing. `VALIDATION` has no claim.
5. **Run with retries (step 5):**
   - **Limits (DEC-04):** Part 1 up to `part1_max_retries`, read per job; Part 2, yard and EDI once; `VALIDATION` never.
   - **Retried categories (§7):** `DATA_UNAVAILABLE`, `TIMEOUT` and `INTERNAL_ERROR`, except Part 2 `TIMEOUT` and `SOLVER_ERROR`, which CT-10 sends to the FIFO fallback.
   - **Between attempts:** roll back, then increment `retry_count` where granted, guarded by `status = 'RUNNING'`. 0 rows: stop, send nothing.
6. **Complete (steps 6 and 7):** one transaction ending in a guarded final update. 0 rows: roll back everything, send nothing. C-06 is built and validated against its schema **before** the commit, and pushed only after it.
7. **Per-table rules,** taken from `schema.sql` and CT-10 to CT-15. The failed path also sets `terminal_recommendations` to `GENERATION_FAILED` (guarded on `YARD_REC_REQUESTED`, CT-11) and `baplie_files.parse_status` to `FAILED` (CT-12):

   | Run table | FAILED written as | C-06 FAILED `outcome` | `error_category` column | `retry_count` | Extra read from the run row |
   |---|---|---|---|---|---|
   | `part1_runs` | `FAILED` | `null` | none | yes | — |
   | `solver_runs` | `ERROR`, with `result_detail.failure_reason` | `GENERATION_FAILED` | none | none | — |
   | `yard_runs` | `FAILED`, `outcome = GENERATION_FAILED` | `GENERATION_FAILED` | yes | D2 | `terminal_recommendation_id` |
   | `baplie_parse_runs` | `FAILED`, `outcome = NULL` | `null` | yes | yes | `baplie_file_id` |

   Reading the extra id from the run row means a C-06 can still be built when the payload is the invalid part. Column names from a handler are checked against the CT-15 grants, so a handler can't write outside them.
8. **Errors:** a `JobError` carrying a CT-08 category; `ConfigurationError` maps to `CONFIGURATION_ERROR`; a rejected CHECK (MySQL 3819) maps to `CONFIGURATION_ERROR` without retry (CT-17); anything unexpected maps to `INTERNAL_ERROR`. A failure while handling a job never stops the worker.
9. **Per-job settings:** `read_port_settings`, then commit straight away so the read can't hold a stale snapshot (AI-012's rule).
10. **Structured logs:** JSON lines with `run_id`, `job_id`, `job_type`, `contract_version` and the queue. No raw payloads except the capped invalid-message log the contract requires.
11. **Graceful shutdown:** on SIGTERM or SIGINT, finish the current job, take no new one, exit 0.
12. **OQ-8:** keep `common.<module>` imports with `package = false`, and run workers as `python -m <module>` from the repository root. `common/runtime/` becomes the first subpackage.

**Out:**

- **Sweeping stale runs:** the backlog lists a "stale-run sweep", but CT-08 §6, CT-14 and DEC-08 make it the Backend's. Here the worker only reacts through the guarded update.
- Handlers and business logic for any job type (later tasks). Tests use fake handlers.
- Heartbeats and `DRAINING` (AI-091, CT-16), metrics (AI-092).
- Connection pooling, repositories, worker accounts and the driver choice (AI-013). The runtime takes a connection factory.
- Part 1 and Part 3 schedulers and `PART3_EVALUATION` (DEC-31, AI-040, AI-073), though the C-06 builder handles its fields.
- `READ_ONLY` handling: DEC-54 is future work, and the Backend refuses new runs (Architecture §11.1).
- A job time limit: `TIMEOUT` comes from handlers.
- Where the yard and validation workers live (AI-010 follow-up), and the stale "Pending" list in `common/README.md`.
- `docs/ref/` contract and DEC entries, which are refreshed from PortHub.

## Files likely to change

| File | New or existing | Change |
|---|---|---|
| `common/runtime/__init__.py`, `envelope.py`, `runs.py`, `completion.py`, `errors.py`, `logs.py`, `worker.py` | New | The library |
| `tests/unit/common/runtime/` | New | Unit tests |
| `tests/integration/test_worker_runtime.py` | New | Real MySQL and Redis tests |
| `tests/support/run_tables.sql` | New | The four run tables copied from `schema.sql` `e118093`, with CHECKs and generated columns, without foreign keys; plus trimmed `terminal_recommendations` and `baplie_files` |
| `pyproject.toml`, `uv.lock` | Existing | `jsonschema` and `rfc3339-validator` as runtime dependencies; `redis` moves from test to runtime; `types-jsonschema` for mypy |
| `common/config.py`, `tests/unit/common/test_config.py` | Existing | `AI_SCHEMA_DIR` in `OptionalEnvVar` |
| `tests/integration/fake_worker.py` | New | A real worker process for the process-level tests |
| `tests/support/runtime_messages.py` | New | Valid test messages |
| `docs/tasks/ATLANTECH_AI_TASKS.md` | Existing | One note on AI-090, at the user's instruction: the schema files must ship |
| `common/README.md` | Existing | Move runtime to "Contents", how to use it, OQ-8 |
| `docs/ref/ATLANTECH_Decisions.md` | Existing | AI-011 row and entry under "AI task decisions", `Proposed` |
| `docs/tasks/status/AI-011.md`, `docs/tasks/WORK_STATUS.md` | New, existing | Records |
| `docs/tasks/status/AI-012.md` | Existing | Evidence for its first criterion; its status stays the user's call |
| This plan | New | Committed with the task, if the user agrees (D6) |

## Dependencies

| Item | Status | Evidence |
|---|---|---|
| AI-010 | DONE | Status record, tracker, merge `9edc32e` |
| AI-003 | DONE | Confirmed by MennaGamal-87 (AI lead), 2026-11-03; PR #14, `0ccebd3`. The record update is on its own branch |
| AI-012 | Merged, `IN REVIEW` | PR #13, `af0a7b6`; `common/config.py` |
| CT-08 v1.0 | Approved | Lead approval and date still to reach PortHub through #34; the text doesn't change |
| CT-10, CT-11, CT-12, CT-13, CT-14, CT-15, CT-16 | Approved v1.1 | PortHub |
| CT-17, CT-18 | Approved v1.0 | PortHub. PR #28 proposes CT-18 v1.1, which doesn't touch this plan |
| DEC-01, 02, 04, 08, 11 | Closed | PortHub |

**Cross-team (flag B):** D2 and D3 below need the Backend. AI-013 runs in parallel and supplies connections.

## Decisions at approval (user, 2026-11-03)

**The user's answers, which win over the options further down:**

- **D1:** log at ERROR with `job_type`, `run_id` and queue, drop, never claim. It deviates from approved CT-08, so it's recorded in the status record, with a Proposed change to CT-08 in a PortHub PR.
- **D2:** approved, with a Proposed change to CT-15 and DEC-08 in the same PortHub PR, awaiting Backend.
- **D3:** send an `ai-request` to the Backend. Meanwhile no clamping: a value above 3 is a `CONFIGURATION_ERROR` with a clear message.
- **D4:** retry immediately; "retry delay undefined" is an open question.
- **D5:** load from `AI_SCHEMA_DIR` (Proposed, like the AI-012 names), defaulting to `docs/ref/ai-payloads/` only for development and CI. A missing schema stops the worker. A test checks every job type's schema loads, and AI-090 notes the files must ship.
- **D6:** commit the plan.

**Set during implementation, for the user to check:**
- "Development and CI" means a Git checkout: the default applies only when `.git` exists, with a warning. A deployment without `.git` must set `AI_SCHEMA_DIR`.
- A message with no `job_type` at all isn't a wrong queue, so CT-08 step 3 applies. Any other value that doesn't match is.

**Added at the user's instruction to fix what the independent review confirmed (2026-11-03):** the connection is opened before `BLPOP`; lost connections are replaced; `connect_redis` outlasts `BLPOP`; `$ref`s are resolved at load; Redis and `worker_version` are checked at startup; exception text isn't logged; and `result_detail.failure_reason` is written for EDI too (CT-12). `tests/unit/common/runtime/test_failure_paths.py` is new.

**The options as presented:**

- **D1 · A job on the wrong queue (recommended: log and drop, and propose a clarification).** CT-08 §6 step 3 says to claim and finish when `run_id` can be read. But `run_id` points at the message's own job type's table (§2), and a worker has no UPDATE on another worker's run table. Claiming in its own table by that id could fail an **unrelated** run with the same number. So the literal step can't be done safely.
  - **Recommended:** log and drop; the Backend's stale and QUEUED sweepers cover the run. Add a `Proposed change` to CT-08 through a PortHub PR, awaiting Backend and AI Team.
- **D2 · `yard_runs.retry_count` (recommended: approve).** `schema.sql` already grants it to the yard role, but `table-ownership.md` says this "needs AI Team approval with a CT-15 / DEC-08 update". DEC-04 gives yard one retry. Without it, yard retries still work but aren't counted. If approved, the CT-15 and DEC-08 text needs updating on PortHub. CT-08 §9's note on `retry_count` is also out of date.
- **D3 · `part1_max_retries` against a CHECK (recommended: raise with Backend, no workaround).** CT-18 allows up to 10, but `chk_p1r_retry` on `part1_runs` allows only 0 to 3. A setting above 3 would make the update fail, and the run would end as `CONFIGURATION_ERROR`. I won't clamp silently. Fix through an `ai-request` to the Backend: either CT-18's max becomes 3 or the CHECK widens.
- **D4 · Retry timing (recommended: immediate, no backoff).** No contract defines a delay, and I won't invent a number. Later tasks can add one where a provider needs it, through `port_settings`.
- **D5 · Schema location, OQ-2 (recommended: read `docs/ref/ai-payloads/` at runtime).** It avoids a second copy, and the mirror is refreshed from PortHub. A missing or broken schema stops the worker at startup. AI-090 must ship those files.
- **D6 · Commit this plan?** Recommended: yes, as with AI-012.

**DB driver, no decision needed now:** the runtime uses a DB-API connection factory, so AI-013 can pick the driver. CT-17's `mysql.BIGINT` suggests SQLAlchemy, whose raw connection fits. Tests keep using PyMySQL.

## Tests

TDD, unit tests first, with fake handlers.

**Unit:** invalid JSON, non-UTF-8, schema failures, wrong queue, unsupported major and accepted `1.x`; the drop or finish path for each; retry limits and categories per job type; Part 2 no-retry; `part1_max_retries` read per job; error mapping including MySQL 3819; each table's FAILED columns; C-06 output validated against `c06-completion.schema.json` for every job type; a C-06 that fails validation never commits; column allow-lists; log fields; a handler crash leaves the loop running; shutdown flag.

**Integration (`tests/integration/test_worker_runtime.py`, MySQL 8.4 and Redis 7.4):**
- The same message pushed twice runs the handler once, and sends one C-06.
- Two workers racing on one message: one claim wins.
- An invalid envelope, then a valid job: the first is rejected and logged, the second still runs.
- A row set to `FAILED` / `TIMEOUT` by a second connection during the handler: inserted rows roll back, no C-06.
- A `REPLACED` run behaves the same.
- A run no longer `QUEUED` is not claimed.
- C-06 appears on `queue:ai-results` only after the commit.
- Retries increment `retry_count` and send one C-06 after the last attempt.
- Every table's CHECK constraints accept what the runtime writes.
- A worker process with a missing variable exits non-zero (subprocess). SIGTERM during a job finishes it, then exits 0 (POSIX in CI; Windows signal behaviour is noted if it differs).

**Commands (same as CI), with the service containers locally:**
```
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -v --cov --cov-report=term-missing
```
Plus Gitleaks in the pinned container. `common/runtime` is already covered by the `common` entries in `pyproject.toml`.

## Risks

- **Lost jobs:** `BLPOP` removes a message on receipt, so a crash before the claim leaves the run `QUEUED`, and after it `RUNNING`. The Backend covers these (P3-I2 sweeper, `run_stale_after_seconds`). The runtime adds no second acknowledgement. Backlog's "Never acknowledge a job before the result transaction commits" is met as "C-06 only after commit".
- **`run_stale_after_seconds` is still ⟨AI⟩:** the sweeper could mark a long retry stale. The guarded update handles it safely, but the value needs setting (AI-009).
- **C-06 lost after commit:** a Redis failure is logged, and the Backend's poller covers run jobs. `VALIDATION` has no poller; its timeout covers it (CT-14).
- **Test tables drifting from `schema.sql`:** copied at `e118093`, named in the file header. AI-013 tests against the real schema and grants.
- **Handlers holding transactions:** handlers must not commit; the runtime owns commit and rollback. Documented, not enforced.
- **Overlap with AI-013 and AI-092:** kept small by the connection factory and the minimal logger.
- **Missing sources:** `ATLANTECH_AI_IMPLEMENTATION_PLAN.md` (§8.3–8.4); `database/grants/workers.sql` in `project-backend`, though `schema.sql` holds the role grants.

## Contract / decision changes

- **Changes to DEC-04, CT-08, CT-14 or CT-15 here:** none in this repository.
- **Written on this branch:** an AI-011 row and entry under "AI task decisions", `Proposed`, awaiting the AI Team owner, covering the D answers, OQ-8, OQ-2 and the module layout.
- **PortHub, only if you approve (D1, D2):** a separate branch with `Proposed change` rows on CT-08 and CT-15. Pushed the same way as #34, and nothing marked approved.

## Acceptance criteria

| Criterion (quoted from the backlog) | Verification |
|---|---|
| "Duplicate delivery of a job executes once (test)" | Integration: same message twice, and two racing workers |
| "Invalid envelope is rejected and logged without crashing the worker" | Unit for each failure type; integration: invalid then valid message |
| "Stale RUNNING run is swept per contract" | Per CT-08, the Backend sweeps. Integration: run set to FAILED / TIMEOUT mid-job, results roll back, no C-06. **Reads the criterion through CT-08**, for your approval |
| "Logs contain run id and contract version" | Log-capture test on every job path, parsed as JSON |

Backlog verification evidence: "Integration test report against Redis and MySQL". Backlog guidance: "Claim with a conditional UPDATE and check affected rows. Never acknowledge a job before the result transaction commits."
