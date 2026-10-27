#!/usr/bin/env bash
# Builds disposable git fixtures (repo + bare origin) for the evals in evals.json.
# Usage: build_fixtures.sh <repo-root-with-docs> <output-dir> <scenario-name>...
# Each scenario lands in <output-dir>/<scenario>/w/{repo,origin.git,outputs}.
# Build in place: moving a fixture afterwards breaks its origin path.
set -euo pipefail
SRC="$1"; WS="$2"; shift 2
G() { git -c core.longpaths=true -c user.name=fixture -c user.email=fixture@example.com "$@"; }

status_record() {   # $1 id, $2 title, $3 status, $4 date
  mkdir -p docs/tasks/status
  printf '# %s · %s\n| Field | Value |\n|---|---|\n| Status | %s |\n| Updated | %s |\n' \
    "$1" "$2" "$3" "$4" > "docs/tasks/status/$1.md"
}

init_repo() {       # $1 run dir; leaves cwd in the repo on main
  rm -rf "$1/repo" "$1/origin.git"; mkdir -p "$1/outputs"
  git init -q --bare -b main "$1/origin.git"
  git init -q -b main "$1/repo"
  cd "$1/repo"
  git config core.longpaths true; git config core.autocrlf false
  git config user.name fixture; git config user.email fixture@example.com
  cp -r "$SRC/docs" docs
  # Reference specs only: each scenario sets up its own status records and plans.
  rm -rf docs/tasks/WORK_STATUS.md docs/tasks/status docs/superpowers
  # Drop the recorded AI task decisions, so scenarios that start AI-001 (onboarding,
  # conflicts-closed-decision) don't find it already Closed; each scenario's status records set the rest.
  awk '/^## AI task decisions/{exit} {print}' docs/ref/ATLANTECH_Decisions.md > docs/ref/Decisions.tmp
  mv docs/ref/Decisions.tmp docs/ref/ATLANTECH_Decisions.md
  if grep -q '^### AI-001 ' docs/ref/ATLANTECH_Decisions.md; then
    echo "ATLANTECH_Decisions.md still holds an AI-001 decision after stripping; update the fixture builder" >&2; exit 1
  fi
  printf '# ATLANTECH AI\n' > README.md
}

first_push() {
  G add -A; G commit -qm "chore: initial docs"
  git remote add origin "$(cd .. && pwd)/origin.git"
  G push -q origin main
}

develop_with_ai010() {   # develop with AI-010 merged and AI-001/AI-010 DONE, pushed
  G checkout -qb develop
  G checkout -qb feature/AI-010-ai-repo-module-structure
  mkdir -p src/common src/part1 src/part2 src/part3 src/edi
  for m in common part1 part2 part3 edi; do : > "src/$m/__init__.py"; done
  status_record AI-010 "Decide AI code repository and module structure" DONE 2026-10-20
  status_record AI-001 "Confirm AI scope and component inventory" DONE 2026-10-18
  G add -A; G commit -qm "feat(AI-010): module skeleton"
  G checkout -q develop
  G merge -q --no-ff feature/AI-010-ai-repo-module-structure -m "Merge feature/AI-010-ai-repo-module-structure into develop"
  G branch -qd feature/AI-010-ai-repo-module-structure
  G push -q origin develop
}

approved_plan() {   # task branch with an approved, deliberately narrow AI-014 plan
  G checkout -qb feature/AI-014-unit-datum-time-utilities develop
  mkdir -p docs/superpowers/plans
  cat > docs/superpowers/plans/2026-10-25-ai-014-units.md <<'EOF'
# AI-014 (part 1) · Unit conversion — implementation plan

> ATLANTECH override: no commit steps. The user reviews and commits.

- **Task:** AI-014 · Implement unit, datum and time utilities · branch `feature/AI-014-unit-datum-time-utilities`
- **Scope (in):** speed conversion between KNOTS, METRES_PER_SECOND, KM_PER_HOUR; distance conversion between NAUTICAL_MILES, KILOMETRES, METRES; reject unknown units and speed<->distance conversion.
- **Scope (out):** UTC/port-time and port_shift utilities, datum checks, CI. These follow in a separate plan.
- **Files likely to change:** `src/common/units.py` (new), `tests/common/test_units.py` (new), `tests/__init__.py` and `tests/common/__init__.py` (new, empty), `docs/tasks/status/AI-014.md`.
- **Dependencies:** AI-010 DONE (merged into develop).
- **Tests:** standard-library unittest (pytest is not installed). Command: `python -m unittest discover -s tests -t . -v` with `PYTHONPATH=src`.
- **Risks:** float tolerance in round trips; unit codes must match the schema enums exactly.
- **Contract/decision changes:** none.
- **Acceptance criteria mapped:** "Conversion tests for every enum pair used" -> one test per pair; "Round-trip tests within float tolerance" -> round-trip tests with assertAlmostEqual.

## Steps
1. Write failing tests for every speed pair and every distance pair, plus rejection cases.
2. Implement `convert_speed(value, from_unit, to_unit)` and `convert_distance(value, from_unit, to_unit)` in `src/common/units.py`.
3. Run the test command and record the real result in the status record.
EOF
  cat > docs/tasks/status/AI-014.md <<'EOF'
# AI-014 · Implement unit, datum and time utilities
| Field | Value |
|---|---|
| Status | IN PROGRESS |
| Branch | feature/AI-014-unit-datum-time-utilities |
| Plan | docs/superpowers/plans/2026-10-25-ai-014-units.md · approved: pending |
| Updated | 2026-10-25 |

## Prerequisites and dependencies
AI-010 DONE.
## Contract / decision items (existing IDs, Proposed changes in the canonical documents)
None.
## References inspected
Backlog §5 AI-014; ClassDiagramContext enums.
## Validation results (actual)
Not run yet.
## Open questions / follow-ups
Time utilities in a follow-up plan.
EOF
  G add -A; G commit -qm "docs(AI-014): plan and status record"
}

build() {           # $1 scenario name
  local sc="$1" run="$WS/$1/w"
  init_repo "$run"
  case "$sc" in
    claude-md-proposal)
      printf '# ATLANTECH AI — project instructions\n\n- Branch from develop as feature/<task-id>-<slug>.\n- Commits and pushes only through atlantech-review-and-publish, after the exact `APPLY CHANGES`.\n- Python code lives under src/ (see AI-010).\n' > CLAUDE.md ;;
  esac
  first_push
  case "$sc" in
    missing-develop)
      status_record AI-010 "Decide AI code repository and module structure" DONE 2026-10-20
      status_record AI-001 "Confirm AI scope and component inventory" DONE 2026-10-18
      G add -A; G commit -qm "docs: AI-001 and AI-010 done"; G push -q origin main ;;
    onboarding)
      G checkout -qb develop; G push -q origin develop ;;
    *)
      develop_with_ai010 ;;
  esac
  case "$sc" in
    existing-branch)
      G checkout -qb feature/AI-014-unit-datum-time-utilities
      printf '# wip\n' > src/common/units.py
      G add -A; G commit -qm "wip(AI-014): units"
      G push -q origin feature/AI-014-unit-datum-time-utilities
      G checkout -q develop
      G branch -qD feature/AI-014-unit-datum-time-utilities ;;   # remote only
  esac
  if [ "$sc" = "conflicting-status-evidence" ]; then
    # Second authoritative source on develop that disagrees with the AI-010 status record.
    printf '# AI team tracker\n\n| Task | Status | Note |\n|---|---|---|\n| AI-001 | DONE | |\n| AI-010 | IN REVIEW | module-structure PR still under review |\n' > docs/tasks/TEAM_TRACKER.md
    G add -A; G commit -qm "docs: team tracker"; G push -q origin develop
  fi
  if [ "$sc" = "post-approval-implementation" ]; then
    approved_plan            # stays checked out on the task branch
  else
    G checkout -q main
  fi
  if [ "$sc" = "develop-not-yet-fetched" ]; then
    # develop exists on origin, but this clone has neither the branch nor the tracking ref.
    G branch -qD develop
    git update-ref -d refs/remotes/origin/develop
  fi
  if [ "$sc" = "dirty-tree" ]; then
    printf '\nLocal notes in progress.\n' >> README.md
    printf 'scratch\n' > notes-wip.txt
  fi
  local base
  case "$sc" in
    develop-local-ahead)      # local develop has a commit origin lacks
      G checkout -q develop
      printf 'local note\n' > docs/LOCAL_NOTE.md
      G add -A; G commit -qm "local: unpushed note on develop"
      G checkout -q main ;;
    develop-diverged)         # local and origin develop each have a commit the other lacks
      base=$(git rev-parse develop)
      G checkout -q develop
      printf 'local note\n' > docs/LOCAL_NOTE.md
      G add -A; G commit -qm "local: unpushed note on develop"
      G checkout -q -b tmp-teammate "$base"
      printf 'teammate change\n' > docs/TEAMMATE.md
      G add -A; G commit -qm "remote: teammate change on develop"
      G push -q origin tmp-teammate:develop
      G checkout -q main; G branch -qD tmp-teammate
      git update-ref refs/remotes/origin/develop "$base" ;;   # clone hasn't fetched it yet
    fetch-fails)              # the configured origin is unreachable for every remote command
      mv "$run/origin.git" "$run/origin.git.offline" ;;
    ls-remote-fails)          # first two remote calls succeed, every later one fails
      cat > "$run/flaky-upload-pack.sh" <<'EOF'
#!/bin/sh
cnt="$(dirname "$0")/upload-pack.count"
c=$(cat "$cnt" 2>/dev/null || echo 0); c=$((c+1)); echo "$c" > "$cnt"
if [ "$c" -ge 3 ]; then echo "fatal: simulated network failure (remote call $c)" >&2; exit 128; fi
exec git upload-pack "$@"
EOF
      git config remote.origin.uploadpack "sh $run/flaky-upload-pack.sh" ;;
    wrong-origin)             # origin points at another project's repository
      git init -q --bare -b main "$run/other-project.git"
      base=$(G commit-tree "$(git mktree </dev/null)" -m "other project")
      G push -q "$run/other-project.git" "$base:refs/heads/main" "$base:refs/heads/develop"
      git remote set-url origin "$run/other-project.git" ;;
    develop-local-only)       # develop deleted on origin; the clone keeps local develop and a stale tracking ref
      git -C "$run/origin.git" update-ref -d refs/heads/develop ;;
    pull-ff-fails)            # origin develop is one commit ahead; remote calls fail once the clone is on develop
      base=$(git rev-parse develop)
      G checkout -q -b tmp-teammate develop
      printf 'teammate change\n' > docs/TEAMMATE.md
      G add -A; G commit -qm "remote: teammate change on develop"
      G push -q origin tmp-teammate:develop
      G checkout -q main; G branch -qD tmp-teammate
      git update-ref refs/remotes/origin/develop "$base"   # clone hasn't fetched it yet
      cat > "$run/pull-fails-upload-pack.sh" <<EOF
#!/bin/sh
case "\$(cat '$run/repo/.git/HEAD')" in
  *refs/heads/develop) echo "fatal: simulated network failure while on develop" >&2; exit 128 ;;
esac
exec git upload-pack "\$@"
EOF
      git config remote.origin.uploadpack "sh $run/pull-fails-upload-pack.sh" ;;
  esac
  # Commits made by the run under evaluation show up as eval-agent.
  git config user.name eval-agent; git config user.email eval-agent@example.com
  cd - >/dev/null
  bash "$(dirname "$0")/check_state.sh" snapshot "$run"
}

for sc in "$@"; do
  case "$sc" in
    normal-unblocked|dirty-tree|missing-develop|existing-branch|unresolved-contract|\
    conflicts-closed-decision|unknown-task-id|setup-unconfirmed|setup-confirmed|\
    claude-md-proposal|onboarding|post-approval-implementation|conflicting-status-evidence|\
    develop-not-yet-fetched|develop-local-ahead|develop-diverged|fetch-fails|ls-remote-fails|\
    wrong-origin|develop-local-only|pull-ff-fails|decision-change-canonical) build "$sc" ;;
    *) echo "unknown scenario: $sc" >&2; exit 1 ;;
  esac
done
echo built
