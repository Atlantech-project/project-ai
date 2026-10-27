# AI-016 · Set up CI for AI code · Implementation Plan

> Approved by the user (mostafa) on 2026-10-28, with the decisions and conditions below. The text further down is the plan as presented; where it differs, the approval amendments take precedence.
> ATLANTECH override: no commit steps. Publishing happens only through
> `/atlantech-review-and-publish AI-016` after `APPLY CHANGES`.

## Approval amendments (2026-10-28, binding)

- **D2:** Python **3.14**, not 3.12, after verifying the selected tools and the required dependencies. No silent fallback to 3.12; report any incompatibility first.
- **D4:** mypy strict with an explicit scope. PyMySQL and redis-py are test-only. No production DB or Redis client before their implementation tasks.
- **D6:** `redis:7.4` is **provisional** until the Backend confirms its version. Never claim it matches the Backend environment.
- **D7:** Gitleaks CLI with a pinned version. The allowlist covers **only the exact known fake values**, never whole evaluation files or directories. A planted secret is shown to be detected without committing it. GitHub native secret scanning and push protection are enabled and verified where available; never claimed without evidence.
- **D8:** coverage is reported, with no threshold. AC 3 stays outstanding: no scope exception, no DONE while it is unmet.
- **D9:** the user coordinates the admin after `ci-ok` exists. Exact settings are documented, never claimed as applied. AC 2 stays outstanding until verified.
- **Triggers:** every push (all branches) and every pull request, with no path filters.
- **`ci-ok`:** must fail, never succeed or stay skipped, when any needed job fails or is cancelled.
- **Extra record fix:** set SETUP-002 to DONE in `WORK_STATUS.md` and in its status record (PR #4 merged). Only this focused correction.
- **No separate SETUP task:** the Python tooling decisions are recorded under AI-016.
- **Implementation deviations** (details in `docs/tasks/status/AI-016.md`):
  - `.gitleaks.toml` (Task 4) was not created. The history CI scans has no findings, so no allowlist is needed.
  - Task 5's charset choice: neither `ALTER DATABASE` nor a `docker run` step. MySQL 8.4's image defaults (`utf8mb4` / `utf8mb4_0900_ai_ci`) are used, and asserted at database and session level by the smoke tests.

**Goal:** On every pull request, a GitHub Actions workflow runs lint, the type check, unit tests, and integration tests against MySQL 8.4 and Redis service containers, plus a coverage report and a secret scan. One aggregate required check lets branch protection block merges when anything fails.

**Architecture:** One workflow file, `.github/workflows/ci.yml`, with four jobs (`lint`, `typecheck`, `tests`, `secret-scan`) and an aggregate job `ci-ok` that needs all four. Tool configuration lives in one root `pyproject.toml`, and dependencies are locked. No product code is written: the gates run over a small piece of test-support code (service settings from the environment) and the smoke tests that prove the MySQL and Redis wiring. AI-011 to AI-014 add the first real code under these gates.

**Tech stack (PROPOSED, each item needs approval, see D1–D9):** GitHub Actions · Python 3.12 · uv · ruff · mypy · pytest + pytest-cov · PyMySQL and redis-py (test-only) · gitleaks CLI · `mysql:8.4` and `redis:7.4` service images.

**Spec:** backlog `docs/tasks/ATLANTECH_AI_TASKS.md` §5 AI-016; CT-17 §2 (MySQL 8.4, UTC sessions); CT-08 (unprefixed keys, RPUSH/BLPOP); AI-010 task decision (module layout).

## Global constraints
- MySQL engine `MySQL 8.4, InnoDB, utf8mb4 / utf8mb4_0900_ai_ci`; worker sessions use `time_zone = '+00:00'` (CT-17 §2).
- Queues are unprefixed Redis keys; the Backend sends with RPUSH and the worker receives with BLPOP (CT-08).
- Top-level modules stay `common/`, `edi/`, `part1/`, `part2/`, `part3/` (AI-010 task decision, Closed).
- No secrets in the repository. CI credentials are throwaway values used only by the service containers.
- Workflow `permissions: contents: read`; third-party actions are pinned to full commit SHAs.
- The coverage threshold is never invented. It comes from the thresholds register (AI-008 / DEC-30).

## Review focus
1. **A PR with no Python changes (documentation only)** must still produce a green `ci-ok`, not "skipped/pending". A pending required check blocks the merge forever, so the jobs use no path filters.
2. **Services not ready when the tests start:** MySQL takes 10–30 s. Health checks on both services, plus a bounded retry in the connect helper, so the tests fail clearly instead of flaking.
3. **Integration tests that silently skip in CI:** locally they skip without services, but in CI (`ATLANTECH_REQUIRE_SERVICES=1`) a missing service must fail the run.
4. **The secret scan flagging known fake fixtures:** the eval fixtures under `.claude/skills/*/evals/` and the masked contract examples hold deliberate fake values (SETUP-001/002 records). They need a narrow, path-scoped allowlist; never a global disable.
5. **Wrong time zone on a session:** the MySQL smoke test asserts `@@session.time_zone = '+00:00'`, so the CT-17 rule is pinned from the first commit.

---

## Decisions needed (written as a `Proposed` AI-016 entry in the "AI task decisions" section of `docs/ref/ATLANTECH_Decisions.md`; owner AI Team)

| # | Decision | Recommendation | Alternatives | Why it is needed |
|---|---|---|---|---|
| D1 | CI provider | GitHub Actions | none practical | Backlog: "CI provider not documented". The repository is a public GitHub repository, so Actions minutes are free and its checks can be required directly by branch protection |
| D2 | Python version | 3.12 (pinned in `.python-version` and `requires-python = ">=3.12,<3.13"`) | 3.11 (this PC's installed version), 3.13 | OQ-1. Must suit OR-Tools and LightGBM; confirm wheel support when pinning |
| D3 | Dependency management | uv with a committed `uv.lock` | pip + pip-tools; Poetry | OQ-1. CI needs reproducible installs |
| D4 | Lint, type check, test runner | ruff (`check` + `format --check`), mypy (`strict` on new code), pytest + pytest-cov; PyMySQL + redis-py as **dev-only** smoke dependencies | pyright instead of mypy; black + flake8 instead of ruff | OQ-1. The production DB and Redis clients stay AI-011/AI-013's choice |
| D5 | Test location and layout | root `tests/unit/`, `tests/integration/`, `tests/support/`; one root `pyproject.toml`; **no** package layout for the modules yet | decide the OQ-8 package layout now | OQ-7 (tests only). OQ-8 is left to AI-011 |
| D6 | Redis version in CI | `redis:7.4` | whatever the Backend runs | Not documented anywhere. Needs **Backend confirmation** (B coordination); MySQL 8.4 is already fixed by CT-17 |
| D7 | Secret scanning | gitleaks CLI (MIT, pinned release, checksum verified) over the full history on every PR, plus GitHub secret scanning and push protection enabled in the repository settings | TruffleHog; GitHub-native only | AI-012 AC "No secret in the repository (scan in CI)". `gitleaks-action` needs a paid licence for organisation repositories, so the plan runs the binary directly |
| D8 | Coverage gate | **Blocked.** Measure and report coverage now; leave `fail_under` unset until AI-008 / DEC-30 gives the figure | the owner approves a provisional figure now (it must come from them, not from me) | DEC-30 is Open and AI-008 has no status record; AC 3 can't be met yet |
| D9 | Branch protection | the org owner or repository admin protects `develop`, `main` (and `release` once it exists): PR required, required status check `ci-ok`, branch up to date before merge, no bypass | a ruleset with the same rules | Evidence 2026-10-28 (public API): `develop` and `main` `"protected": false`; `rules/branches/develop` = `[]`. I can't change repository settings |

---

## Files

| Path | New/Existing | Purpose |
|---|---|---|
| `.github/workflows/ci.yml` | new | The pipeline |
| `pyproject.toml` | new | Project metadata (no packages), dev dependency group, and ruff, mypy, pytest and coverage configuration |
| `uv.lock` | new | Locked dependencies |
| `.python-version` | new | `3.12` |
| `.gitleaks.toml` | new | Default rules plus a narrow path allowlist for the known fake fixtures |
| `tests/support/services.py` | new | `ServiceSettings`, `load_service_settings()` |
| `tests/unit/test_services_settings.py` | new | Unit tests for the loader |
| `tests/integration/conftest.py` | new | `mysql_conn` and `redis_client` fixtures, skip-or-fail rule |
| `tests/integration/test_services.py` | new | MySQL and Redis smoke tests |
| `.gitignore` | existing | Add `.venv/`, `.coverage`, `coverage.xml`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` |
| `README.md` | existing | "Getting started" (uv setup, local commands, local services via Docker) and a "CI" section naming the required check |
| `docs/ref/ATLANTECH_Decisions.md` | existing (canonical) | New `Proposed` AI-016 entry for D1–D9 in "AI task decisions" |
| `docs/tasks/status/AI-016.md` | new | Status record |
| `docs/tasks/WORK_STATUS.md` | existing | AI-016 row |
| `docs/superpowers/plans/2026-10-28-ai-016-ci-for-ai-code.md` | new | This plan |

Not touched: the `docs/ref/` sources other than the Decisions file, the backlog, CLAUDE.md, `.claude/` (the skill eval scripts stay out of the lint/type scope; extending CI to them would be a follow-up).

---

### Task 1: Python tooling skeleton
**Files:** `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`
- [ ] `pyproject.toml`: `[project] name = "project-ai"`, `requires-python = ">=3.12,<3.13"`, no runtime dependencies; `[dependency-groups] dev = [ruff, mypy, pytest, pytest-cov, pymysql, redis, types-PyMySQL]`, each with a pinned minimum.
  - `[tool.ruff]` `target-version = "py312"`, `line-length = 100`; lint `select = ["E","F","W","I","B","UP","S"]`, with `S101` ignored under `tests/`.
  - `[tool.mypy]` `strict = true`, `files = ["tests"]` (module directories are added as code arrives).
  - `[tool.pytest.ini_options]` `testpaths = ["tests"]`, `markers = ["integration: needs MySQL and Redis"]`, `addopts = "--strict-markers"`.
  - `[tool.coverage.run]` `branch = true`, `source = ["tests/support"]` (extended as modules gain code); **no `fail_under`** (D8).
- [ ] Run `uv lock`, then `uv sync --frozen`. Expected: `.venv` created, exit 0.
- [ ] Run `uv run ruff check . && uv run ruff format --check . && uv run mypy`. Expected: exit 0. (pytest exits 5, "no tests", until Task 2.)

### Task 2: Service settings and unit tests (TDD)
**Files:** `tests/support/services.py`, `tests/unit/test_services_settings.py`
**Produces:** `@dataclass(frozen=True) ServiceSettings(mysql_host: str, mysql_port: int, mysql_user: str, mysql_password: str, mysql_database: str, redis_url: str)`; `load_service_settings(env: Mapping[str, str]) -> ServiceSettings | None`, which returns None when `MYSQL_HOST` is absent and raises `ValueError` naming the missing key when the configuration is partial; `services_required(env) -> bool` (`ATLANTECH_REQUIRE_SERVICES == "1"`).
- [ ] Tests:
  - `test_complete_env_parses`: port `"3306"` becomes `3306`.
  - `test_absent_env_returns_none`.
  - `test_partial_env_raises_naming_key`: `match="MYSQL_PASSWORD"`.
  - `test_bad_port_raises`: `"abc"`.
  - `test_services_required_flag`: only `"1"` is true.
- [ ] `uv run pytest tests/unit -q`. Expected: fail (no module). Implement, rerun. Expected: 5 passed.

### Task 3: Integration smoke tests against MySQL and Redis
**Files:** `tests/integration/conftest.py`, `tests/integration/test_services.py`
**Consumes:** Task 2's interfaces.
- [ ] `conftest.py`: with settings None, skip when `services_required` is false and **fail** when it is true (Review focus 3). Connect with up to 30 × 1 s retries (Review focus 2). PyMySQL uses `init_command="SET time_zone = '+00:00'"`, `charset="utf8mb4"`.
- [ ] Tests, all `@pytest.mark.integration`:
  - `test_mysql_version_is_8_4`: `SELECT VERSION()` starts with `"8.4"`.
  - `test_mysql_session_is_utc`: `@@session.time_zone == "+00:00"`.
  - `test_mysql_charset`: `@@character_set_database == "utf8mb4"`.
  - `test_redis_fifo_unprefixed_key`: RPUSH `a` then `b` to `ci:smoke:<uuid>`; BLPOP twice with a timeout of 1 gives `a`, then `b`; delete the key afterwards.
- [ ] Locally, without services: `uv run pytest -q` gives 5 passed, 4 skipped. With `ATLANTECH_REQUIRE_SERVICES=1` and no services: fails with a clear message.
- [ ] Locally, with Docker: `docker run -d --rm -p 3306:3306 -e MYSQL_ROOT_PASSWORD=ci_only -e MYSQL_DATABASE=ai_ci mysql:8.4 --character-set-server=utf8mb4 --collation-server=utf8mb4_0900_ai_ci` and `docker run -d --rm -p 6379:6379 redis:7.4`, with the env vars set. Expected: 9 passed. Stop the containers afterwards.

### Task 4: Secret scanning configuration
**Files:** `.gitleaks.toml`
- [ ] `[extend] useDefault = true`; `[allowlist]` lists only the exact fixture paths that hold deliberate fake values (find them by running the scan first; record each path and why in the status record).
- [ ] Run a pinned gitleaks release locally (Docker image `zricethezav/gitleaks:<pinned>`): `gitleaks git --config .gitleaks.toml --redact -v .`. Expected: "no leaks found".
- [ ] Negative check in a scratch copy (outside the repository): a file with a fake AWS-style key is reported. Expected: exit 1.

### Task 5: Workflow
**Files:** `.github/workflows/ci.yml`
- [ ] Triggers: `pull_request` (all target branches, no path filters, Review focus 1), `push` to `develop`, `main`, `release`, and `workflow_dispatch`. `permissions: contents: read`. `concurrency: ci-${{ github.ref }}`, `cancel-in-progress: true`. `timeout-minutes` on each job.
- [ ] Jobs, all on `ubuntu-latest`. Shared steps: checkout, then `astral-sh/setup-uv` (pinned SHA) with Python from `.python-version`, then `uv sync --frozen`.
  - `lint`: `uv run ruff check --output-format=github .`, then `uv run ruff format --check .`.
  - `typecheck`: `uv run mypy`.
  - `tests`:
    - services `mysql:8.4` (env `MYSQL_ROOT_PASSWORD: ci_only`, `MYSQL_DATABASE: ai_ci`; options `--health-cmd "mysqladmin ping -h 127.0.0.1 -pci_only" --health-interval 5s --health-retries 20`; ports 3306) and `redis:7.4` (`--health-cmd "redis-cli ping"`; port 6379);
    - env `ATLANTECH_REQUIRE_SERVICES: "1"` and `MYSQL_*` / `REDIS_URL` pointing at 127.0.0.1;
    - run `uv run pytest --cov --cov-report=term-missing --cov-report=xml`;
    - upload `coverage.xml` as an artifact.
    - The MySQL `--character-set-server` and `--collation-server` flags can't be set on a GitHub service container. Set them with `ALTER DATABASE` in the connect fixture instead, or start MySQL with `docker run` in a step. The implementer picks one and records it.
  - `secret-scan`: checkout with `fetch-depth: 0`; download the pinned gitleaks release and verify its SHA-256; run `gitleaks git --config .gitleaks.toml --redact --exit-code 1 .`.
  - `ci-ok`: `needs: [lint, typecheck, tests, secret-scan]`, `if: always()`; fails unless every needed result is `success`. This is the one name branch protection requires.
- [ ] Validate locally with `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:<pinned>`. Expected: no output, exit 0.

### Task 6: Documentation, decision entry, records
**Files:** `README.md`, `docs/ref/ATLANTECH_Decisions.md`, `docs/tasks/status/AI-016.md`, `docs/tasks/WORK_STATUS.md`, plan file
- [ ] README: replace the "Setup steps will be added…" line with the uv setup and local commands. Add a "CI" section with the jobs, the required check `ci-ok`, and the local Docker commands.
- [ ] Decisions: add an `AI-016 · CI tooling and quality gates` row to the summary table and an entry with Status `Proposed`, D1–D9 as decided by you, `Affects: AI-011 – AI-015 · AI-012 (secret scan AC) · DEC-30`, and an Approval row left empty until the AI Team owner approves. Nothing is marked Closed.
- [ ] Status record and WORK_STATUS row: `IN PROGRESS`, then `IN REVIEW` at hand-off.

## Acceptance criteria → verification
| Backlog AC (quoted) | How it is verified | Can it be met in this task? |
|---|---|---|
| "Pipeline runs on every PR" | After `/atlantech-review-and-publish` pushes the branch and a PR is opened: the Actions run for that PR shows all five jobs. Evidence: run URL | Yes, after push (the CI run history is the backlog's evidence) |
| "Failing tests block merge" | (1) An admin applies D9. (2) The API shows `develop` `"protected": true`, with `ci-ok` among the required checks. (3) A throwaway draft PR with a deliberately failing test shows "Merging is blocked", then is closed unmerged | **Depends on an admin (D9).** Not claimed until the evidence exists |
| "Coverage gate enforced at the agreed value" | `fail_under = <value>` in `pyproject.toml`, plus a run that fails below it | **Blocked by AI-008 / DEC-30 (D8)** unless you approve a scope exception |

## Risks
- Branch protection is outside the repository's files. Without an admin, the checks are advisory only.
- The Redis version is unconfirmed (D6), so CI may diverge from production until the Backend confirms it.
- Introducing tooling (D2–D4) fixes OQ-1 for every later task, so changing it later costs a migration.
- Required check names must have run once before GitHub lets an admin select them, so D9 happens after the first PR run.
- The full-history secret scan may flag old fixtures. The allowlist must stay path-scoped and reviewed.
