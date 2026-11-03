# AI-012 · Implement configuration management — plan

Written without the Superpowers skills, which are not listed in this session. The user approved this plan with changes on 2026-11-03; this version applies those changes. No step commits: publishing happens only through `/atlantech-review-and-publish AI-012`.

Contracts and decisions were read from PortHub `main` at `e118093`. DEC-12 and CT-18 have the same text in PortHub and `docs/ref/`.

## Task

- **ID:** AI-012 · Implement configuration management (P1 Foundations, P1, complexity S, flag B)
- **Branch:** `feature/AI-012-configuration-management` (from `develop` at `00d95b6`)

## Parked work: AI-003

- By the user's instruction of 2026-11-03, **AI-003 is parked and treated as not done and not started for now**. Its work is saved in commit `0e2c214` on the local, unpushed branch `wip/AI-003`, marked "not for review".
- **AI-011 and AI-013 still wait on AI-003** (backlog §2 and §3). This plan doesn't start them or change that.
- AI-012 doesn't list AI-003 as a prerequisite. The backlog left two things to it, and both are already settled without it:
  - **"Contract v1 port_setting keys":** CT-18 v1.0 §4 (Approved).
  - **"Refresh interval to agree in AI-003":** DEC-12 (Closed) and CT-18 §4: "Workers read `port_settings` per job, without cache." There is no interval to agree.

## Scope

**In:** one module, `common/config.py`, holding:

1. **`ConfigurationError`:** raised for every configuration problem, naming the key and never the value. Carries `error_category = "CONFIGURATION_ERROR"` (CT-08 §7).
2. **Environment loader for secrets and endpoints:** `require_env(env, keys)`, plus `load_env_settings(env, part)` returning a frozen `EnvSettings` holding the database and Redis settings for the worker's own part (D2). All missing keys are reported at once. Secrets are left out of `repr`.
3. **`read_port_settings(connection)`:** one `SELECT setting_key, setting_value, value_type FROM port_settings` through a DB-API connection, returning an immutable `PortSettings` snapshot. It keeps nothing between calls, which is the refresh rule.
4. **Typed access:** `get_int`, `get_decimal`, `get_bool`, `get_str`, `get_json`.
   - A value is parsed only when it is asked for, so a bad unrelated row, such as a tester's `mock_scenario`, can't fail other jobs.
   - The accessor must match the row's `value_type`. There's no coercion and there are no defaults.
   - **INT:** optional minus sign and digits only (`int()` alone would accept `" 5"` and `"1_000"`).
   - **DECIMAL:** `Decimal`, finite only, never `float`.
   - **BOOL:** see D3.
   - **STRING:** as stored.
   - **JSON:** `json.loads`, rejecting `NaN` and `Infinity`.
5. **`AI_SETTING_TYPES`:** the 19 CT-18 §4 keys with their `value_type`. Keys and types only: no values, min or max, because those belong to the seed.
6. **`check_startup_settings(settings, used_keys)`:** checks only the keys the worker uses that are in `KEYS_WITH_APPROVED_VALUE` (the 9 with an approved value in CT-18 today), reporting all failures at once. ⟨AI⟩ keys are skipped.
7. **`check_consistency(settings, used_keys)`:** the two CT-18 §4 cross-field rules a worker can check: `part1_min_window_minutes` is a multiple of `part1_time_step_minutes`, and `validation_result_ttl_seconds` > `validation_timeout_seconds`. A rule applies only when the worker uses both of its keys. Run per job, not at startup.
8. **CI mapping:** the `pytest` step in `.github/workflows/ci.yml` maps the existing `MYSQL_*` and `REDIS_URL` values to the `AI_*` names. The CI variables aren't renamed.

**Out:**

- The worker entry point and the job failure path (AI-011). AI-012 raises; AI-011 stops the process or fails the job.
- Connection handling, pooling and worker DB accounts (AI-013). No runtime DB driver is added.
- Which keys each worker requires. CT-18 doesn't say, so workers pass their own list.
- Setting values, including the 10 ⟨AI⟩ keys still pending under CT-18 §7 (AI-009, DEC-24, DEC-30, DEC-31).
- `min` / `max` checks: they aren't columns of `port_settings`, and the Backend enforces them on save (CT-18 §4).
- The third cross-field rule (`run_stale_after_seconds`): it needs a value the AI Team hasn't computed.
- Reading provider keys (AI-020 does that with `require_env`; only their names are here, per D2), `.env` file loading, and any change to `tests/support/services.py`.
- `common/README.md`'s stale "Pending" items (for example DEC-02 shown as Open). Noted as a follow-up.

## Files likely to change

| File | New or existing | Change |
|---|---|---|
| `common/config.py` | New | The module above |
| `tests/unit/common/test_config.py` | New | Unit tests |
| `tests/integration/test_port_settings.py` | New | Real MySQL tests, using the existing `mysql_conn` fixture |
| `.github/workflows/ci.yml` | Existing | Map `MYSQL_*` and `REDIS_URL` to the `AI_*` names on the `pytest` step |
| `common/README.md` | Existing | Move config from "Planned contents" to "Contents", and state the refresh rule |
| `docs/ref/ATLANTECH_Decisions.md` | Existing | AI-012 row and entry under "AI task decisions", `Proposed` |
| `docs/tasks/status/AI-012.md` | New | Status record |
| `docs/tasks/WORK_STATUS.md` | Existing | AI-012 row only; no AI-003 edit |
| This plan | New | Committed with the task (D4) |

No `pyproject.toml` or `uv.lock` change: only the standard library, and PyMySQL is already in the test group.

## Dependencies

| Item | Status | Evidence |
|---|---|---|
| AI-010 (only prerequisite) | DONE | Status record and tracker on `develop`; merge `9edc32e` |
| DEC-12 | Closed | PortHub `e118093` |
| CT-18 v1.0 | Approved 2026-10-27 | PortHub `e118093` |
| CT-08 v1.0 §7 | Approved 2026-10-30 | PortHub `e118093` |
| DEC-08 | Closed: workers read from the primary | PortHub `e118093` |
| CT-17 `port_settings` DDL | `contracts/db/schema.sql` | PortHub `e118093`; every `r_*` role has SELECT |
| AI-003 | Parked; not a prerequisite | See above |
| AI-016 secret scan | Job on `develop` | AI-016 is itself IN REVIEW over two other criteria |

**Cross-team (flag B), questions for the Backend:** confirm the environment names (D2), and confirm what Laravel writes for BOOL values (D3). Neither blocks this task, because no CT-18 key is BOOL today.

## Decisions at approval (user, 2026-11-03)

- **D1 · Missing settings:**
  - **Environment:** a missing database or Redis variable stops the worker at startup.
  - **Startup keys:** only keys the worker actually uses **and** that have an approved value in seed-spec / CT-18 today. Keys still ⟨AI⟩ aren't checked at startup, otherwise no worker can start.
  - **During a job:** ⟨AI⟩ keys are read when a job needs them. A problem fails that job with `CONFIGURATION_ERROR`, and the worker keeps running.
  - **Refresh rule:** read `port_settings` per job with no cache (CT-18 §4).
- **D2 · Environment names, Proposed, awaiting Backend confirmation:** not `MYSQL_*`, because DEC-08 gives each worker its own account. From AIBD §6.1 as quoted by the user: `AI_DB_HOST`, `AI_DB_USER_<PART>`, `AI_REDIS_URL`, `AI_PROVIDER_PRIMARY_KEY`, `AI_PROVIDER_SECONDARY_KEY`, `AI_ARTIFACT_DIR`, `AI_BAPLIE_VOLUME`, plus a matching `AI_DB_PASSWORD_<PART>`.
  - The AIBD document isn't in the repository, so these weren't checked against it.
  - **Added during implementation, not in the user's list:** `AI_DB_PORT` and `AI_DB_NAME`, because a connection needs them and code holds no defaults. The user approved them on 2026-11-03. They stay marked as the implementer's addition, Proposed, awaiting Backend confirmation with the other names.
  - `<PART>` is `PART1`, `PART2`, `YARD`, `EDI`, `VALIDATE` or `PART3`, one per DEC-08 account.
- **D3 · BOOL text:** `1`, `0`, `true`, `false`; anything else is an error. The Backend is asked what Laravel writes.
- **D4 · Commit this plan:** yes.
- **DECIMAL:** parsed with `Decimal`, not `float`.

## Tests

TDD, unit tests first.

**Unit (`tests/unit/common/test_config.py`), using fake connections:**
- Environment: complete; one missing; several missing all named; bad port; the password isn't in `repr` or in error text.
- Each `value_type` accepted and rejected: `" 5"`, `"1_000"`, `"1.5"` as INT; `"NaN"`, `"Infinity"` as DECIMAL; `"yes"`, `"TRUE"` as BOOL; `"{"` and `NaN` as JSON; an unknown `value_type`.
- Wrong accessor for the row's type raises; a missing key raises naming the key; there's no default path.
- A bad unrelated row doesn't affect reading a good key.
- `check_startup_settings` reports every failure at once, rejects a row whose type differs from `AI_SETTING_TYPES`, and ignores ⟨AI⟩ keys and keys the worker doesn't use.
- `check_consistency`: both rules pass and fail, the boundary (TTL equal to timeout fails), a time step of 0 raises instead of dividing by zero, unused rules are skipped, and a used key that is missing raises.
- `AI_SETTING_TYPES` has the 19 keys and agrees with the 9 in `docs/drafts/ai-payloads/seed-spec.json`.
- Two reads with changed rows return the new value, and the module keeps no state between them.
- `ConfigurationError.error_category == "CONFIGURATION_ERROR"`.

**Integration (`tests/integration/test_port_settings.py`), real MySQL 8.4:**
- A table built from the CT-17 `port_settings` DDL, without the `users` foreign key. Read, change the value from a second connection, read again: the new value appears with no restart.
- An open REPEATABLE READ transaction keeps returning the old value, proving the risk below, so the documented rule is tested.
- CI's `AI_*` mapping resolves for all six parts to the service container's values.

**Commands (the same as CI):**
```
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -v --cov --cov-report=term-missing
```
Integration tests skip locally unless MySQL is configured, and they fail in CI if it's missing. If they can't be run here, I'll report them as skipped, not passed. Gitleaks isn't installed on this machine.

## Risks

- **Stale reads:** on a non-autocommit connection, PyMySQL's default, the read itself opens a transaction, and MySQL's default REPEATABLE READ then returns old values until it ends. That would silently break the refresh rule. The caller must use an autocommit connection, or commit or roll back after every read; this is documented in `common/README.md`, tested, and handed to AI-011 and AI-013, because AI-013 owns connections.
- **Criterion 1 can't be fully shown until AI-011:** no worker process exists yet. This task proves the check raises; AI-011 has to call it at startup and exit. It is recorded as a follow-up.
- **Seed not published:** `seed-spec.json` isn't on PortHub, and 10 keys have no value. The startup check skips them (D1), and code never holds a fallback value. `KEYS_WITH_APPROVED_VALUE` must be updated as those values are approved.
- **Environment names can change:** they're Proposed and weren't checked against the AIBD document. The names sit in one module and the CI mapping, so a change stays small.
- **Per-job query cost:** one read of a small table per job, as DEC-12 requires. Accepted.
- **Name mismatch:** the backlog says `port_setting`; the table is `port_settings` (CT-17, `table-names.md`). The code uses the table name.
- **Missing sources:** `ATLANTECH_FRD_v3` (NFR-SEC-5) and `ATLANTECH_AI_IMPLEMENTATION_PLAN.md` (§8.5) aren't in the repository. The secret rule comes from Architecture line 648 instead.

## Contract / decision changes

- **No change** to DEC-12, CT-08 or CT-18; no new `DEC-` or `CT-` ID.
- **Written on this branch:** an AI-012 row and entry under "AI task decisions" in `docs/ref/ATLANTECH_Decisions.md`, Status `Proposed`, with the same shape as AI-014's, carrying the D1 to D3 answers.

- **PortHub gap:** PortHub is read first for contracts and decisions, but its Decisions file has no "AI task decisions" section, so this entry goes in `docs/ref/` as `CLAUDE.md` requires. Nothing is pushed to PortHub.

## Acceptance criteria

| Criterion (quoted from the backlog) | Verification |
|---|---|
| "Missing required setting stops the worker with a clear error" | Unit tests: `load_env_settings` and `check_startup_settings` raise, naming every missing key. **Partial until AI-011** calls them at startup (D1) |
| "Changing a port_setting value takes effect without redeploy (documented refresh rule)" | Integration test: the value changes between reads with no restart. Rule stated in `common/README.md` |
| "No secret in the repository (scan in CI)" | The existing `secret-scan` job runs on the branch after push. Before that, a pattern scan of staged files. Tests use the existing throwaway CI values only |

Backlog verification evidence: "Unit tests; CI secret scan".
