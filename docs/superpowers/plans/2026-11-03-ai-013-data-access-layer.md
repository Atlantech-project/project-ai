# AI-013 · Implement data-access layer and request worker DB accounts — plan

Written without the Superpowers skills, which are not listed in this session. The user approved this plan in the conversation on 2026-11-03 ("Approved, with additions"), and then settled the accounts and the schema manifest. No step commits: publishing happens through `/atlantech-review-and-publish AI-013`.

Contracts and decisions were read from PortHub `main` at `b4d2deb`.

## Task

- **ID:** AI-013 · Implement data-access layer and request worker DB accounts (P1, P0, complexity L, flag B)
- **Branch:** `feature/AI-013-data-access-layer` (from `develop` at `98dc955`)

## Scope

**In:**
- `common/db/`: a worker connection factory using each worker's own account, in manual commit, with `time_zone = '+00:00'`; a transaction helper; table definitions and column-checked writes for all worker write tables.
- The rules grants can't enforce: own run only; `vessels` NULL-only; `forecast_runs` SCHEDULED or ON_DEMAND; new container numbers only; `lifecycle_status` values; `drift_measurements.notified_at`.
- Typed read models only for what exists today: requests with vessels, tugboats, run rows. An unknown ENUM value is skipped with a warning.
- `docs/ref/db/schema.sql`, a byte-exact PortHub mirror, with `docs/ref/db/schema.sql.source.json` holding its source commit and SHA-256, and `.gitattributes` keeping Git from converting its line endings.
- SQLAlchemy Core, PyMySQL and `cryptography` as pinned runtime dependencies.
- The AI-011 runtime and AI-012 settings under the real accounts.

**Out:**
- Business queries and domain read models for later tasks (AI-047, AI-050, AI-070).
- Migrations and grants, which the Backend owns (CT-17, DEC-08).
- The synthetic port scenario generator (AI-015).
- TLS and deployment settings (AI-090).
- Editing other `docs/ref/` files, or the backlog beyond one note on AI-090, at the user's instruction.

## User decisions (2026-11-03)

1. SQLAlchemy Core and PyMySQL, pinned in the lock file, plus `cryptography`, because MySQL 8.4 uses `caching_sha2_password`. If AI-011 opens connections another way, move it to the new layer and test it.
2. Repository scope as proposed.
3. Tests run on our own CI services, a recorded deviation from CT-17. Load the full `schema.sql` including the worker roles section, and create the accounts with their roles as default roles, as `php artisan atlantech:worker-accounts` does.
4. All six accounts: `w_part1`, `w_part2`, `w_yard`, `w_edi`, `w_validate`, `w_part3`.
5. `docs/ref/` stays byte-exact, so no header goes inside the copy. The source commit and SHA-256 live outside it. The test checks the hash with no network access. A refresh updates both, so a grants change shows up in the diff.
6. Test both sides of `table-ownership.md`: each worker can do what it lists and is refused everything else (DELETE, DDL, other workers' tables, `audit_logs`).

**Set during implementation, for the user to check:**
- AI-011's production code opens no connections: `run_worker` takes a `connect_with`. `connect_worker` is that function, and the AI-011 integration tests and `fake_worker` now use it. One runtime line changes: `_is_check_violation` also reads SQLAlchemy's `orig`, closing AI-011's M16.
- `WorkerConnection` serves both the runtime's raw cursors and the repositories on one transaction, so handlers and the guarded final update commit together.
- Pool of one with one overflow and a pre-ping, because the runtime asks for a connection before each `BLPOP`.
- ENUM columns read as text, because SQLAlchemy's `Enum` raises on a value it doesn't know, which CT-17 §6 forbids.
- JSON `None` is stored as SQL NULL, not JSON `null`.

**Independent review fixes (user, 2026-11-04):** "Go ahead with your recommendations", with these additions. See the status record's Review findings.
- `recommendations` starts as `PENDING_REVIEW`, citing DEC-06, CT-10 and the CT-20 example, Proposed for Backend to confirm.
- Aware datetimes convert to UTC; naive ones are accepted as UTC. Our own code never creates naive datetimes, with a test for it.
- The matrix counts as Backend-approved (MennaGamal-87, AI lead, 2026-11-04), except `yard_runs.retry_count`, pending its PortHub Proposed change.

## Files likely to change

**New:** `.gitattributes`; `common/db/{__init__,connection,rights,tables,repository,read_models}.py`; `docs/ref/db/schema.sql`; `docs/ref/db/schema.sql.source.json`; `tests/support/port_db.py`; `tests/integration/test_worker_accounts.py`; `tests/integration/test_db_layer.py`; `tests/integration/test_runtime_real_accounts.py`; `tests/unit/common/db/`; `docs/tasks/status/AI-013.md`; this plan.

**New, from the review:** `tests/unit/common/test_no_naive_datetimes.py`.

**Existing:** `pyproject.toml`; `uv.lock`; `common/runtime/worker.py`; `common/README.md`; `tests/integration/conftest.py`; `tests/integration/fake_worker.py`; `tests/integration/test_worker_runtime.py`; `tests/unit/common/runtime/test_failure_paths.py`; `docs/tasks/WORK_STATUS.md`; `docs/tasks/ATLANTECH_AI_TASKS.md` (one note on AI-090); `docs/ref/ATLANTECH_Decisions.md` (AI task decisions only).

## Dependencies

- **AI-010:** DONE. **AI-003:** DONE (PR #15 merged). **AI-011:** merged (PR #16, `b9e18be`); its record still says IN REVIEW. It isn't a backlog prerequisite; the user asked to wait for the merge.
- **Backend:** `database/grants/workers.sql` and `atlantech:worker-accounts` are delivered, so no account request is outstanding.

## Tests

- **Schema:** a fresh database from the full `schema.sql`; users created as the Backend command does, with random passwords, and removed afterwards.
- **Identity:** each worker logs in through `connect_worker` as itself, with only its role.
- **Both sides of the matrix:** `SHOW GRANTS` for each role compared exactly with `table-ownership.md`; every table and column probed for every account; hidden tables and columns; DDL and administration; a real write for every listed INSERT and UPDATE.
- **End to end:** DONE, FAILED and retry paths for each job type, validation, per-job settings and `run_worker` under real accounts.
- **Mutation run** on a scratch copy.

Commands, with CI's environment: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest -v --cov --cov-report=term-missing`, and the Gitleaks 8.30.1 container.

## Risks

- **Stale mirror:** the hash proves the copy matches its manifest, not that it matches PortHub today. Nothing in CI notices a newer PortHub schema until someone refreshes the mirror.
- **Foreign keys in tests:** the write tests turn foreign key checks off in the worker's session, because parent rows aren't under test. AI-015 brings real seed data.
- **Run time:** loading the schema takes about 30 s, once per test run.
- **TLS:** found during implementation. PyMySQL 1.2.3 asks for TLS by default, without checking the certificate, so a login on a server offering TLS never uses `cryptography`. Without TLS, the first login crashes inside PyMySQL even with `cryptography` installed, because `caching_sha2_password_auth` has no final `return`. The user decided on 2026-11-03: keep `cryptography`, record this as a deployment risk on AI-090, patch no driver, and ask the Backend whether MySQL offers TLS to the worker accounts. If not, it must be fixed before deployment.

## Contract/decision changes

- **Recorded deviations:** CT-17 §6 (own CI services instead of the Backend's docker compose, and no CT-18 seed); the backlog's "PortSync.md DDL" read as `contracts/db/schema.sql`.
- **AI task decisions:** a new `AI-013` entry, Proposed.
- **No change** to CT-15, CT-17 or DEC-08.

## Acceptance criteria

| Criterion | Verification |
|---|---|
| "Integration tests run against a schema created from the PortSync.md DDL" | `port_db` fixture loads the verified mirror; `test_the_schema_has_the_tables_the_matrix_expects` and `test_each_definition_matches_the_real_table` |
| "Each worker connects with its own account" | `test_each_worker_logs_in_as_itself_with_only_its_role` and the end-to-end tests |
| "Write attempts outside the agreed tables fail in tests" | `test_the_server_allows_exactly_the_published_matrix`, the hidden-table and DDL tests, and the repository refusals |
