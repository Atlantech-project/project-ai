"""The schema mirror and the code's rights table, held to their published sources, offline."""

from pathlib import Path

import pytest

from common.db.rights import WRITE_RIGHTS
from tests.support.port_db import (
    ACCOUNTS,
    MANIFEST_PATH,
    REPO_ROOT,
    SCHEMA_PATH,
    expected_role_grants,
    load_ownership,
    mirror_problem,
    parse_ownership,
    parse_role_grants,
)


def test_the_schema_copy_matches_its_manifest() -> None:
    assert mirror_problem(SCHEMA_PATH, MANIFEST_PATH) is None


def test_a_changed_schema_copy_is_caught(tmp_path: Path) -> None:
    copy = tmp_path / "schema.sql"
    copy.write_bytes(SCHEMA_PATH.read_bytes() + b"-- GRANT\n")
    problem = mirror_problem(copy, MANIFEST_PATH)
    assert problem is not None
    assert "SHA-256" in problem


def test_a_line_ending_conversion_is_caught(tmp_path: Path) -> None:
    copy = tmp_path / "schema.sql"
    copy.write_bytes(SCHEMA_PATH.read_bytes().replace(b"\n", b"\r\n"))
    assert mirror_problem(copy, MANIFEST_PATH) is not None


def test_a_manifest_without_a_full_commit_is_caught(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    commit = text.split('"source_commit": "')[1].split('"')[0]
    manifest.write_text(text.replace(commit, commit[:7]), encoding="utf-8")
    problem = mirror_problem(SCHEMA_PATH, manifest)
    assert problem is not None
    assert "source_commit" in problem


def test_git_never_converts_the_schema_copy() -> None:
    attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert "docs/ref/db/schema.sql -text" in attributes


@pytest.mark.parametrize("part", list(WRITE_RIGHTS))
def test_the_rights_table_equals_the_published_matrix(part: object) -> None:
    ownership = load_ownership()
    account = ACCOUNTS[part][0]  # type: ignore[index]
    rights = WRITE_RIGHTS[part]  # type: ignore[index]
    assert rights.insert == ownership.inserts[account]
    assert dict(rights.update) == dict(ownership.updates[account])


def test_the_parser_reads_every_section() -> None:
    ownership = load_ownership()
    assert len(ownership.readable) == 88
    assert ownership.readable["vessels"] is None
    assert ownership.readable["users"] == frozenset({"id", "name", "is_active"})
    assert ownership.readable["license_states"] == frozenset({"mode", "read_only_reason"})
    assert ownership.hidden == {
        "audit_logs",
        "notification_logs",
        "recommendation_reviews",
        "user_devices",
    }
    assert set(ownership.inserts) == {user for user, _role in ACCOUNTS.values()}
    assert ownership.inserts["w_validate"] == frozenset()
    assert ownership.updates["w_edi"]["vessels"] == {"call_sign", "flag_state"}


def test_the_parser_refuses_an_unknown_read_rule() -> None:
    text = "\n".join(
        [
            "## 1. A",
            "| Table | AI read |",
            "| --- | --- |",
            "| `t` | Some workers |",
            "## 2. B",
            "## 3. C",
            "## 4. D",
            "## 5. E",
            "## 6. F",
        ]
    )
    with pytest.raises(ValueError, match="unknown read rule"):
        parse_ownership(text)


def test_the_parser_refuses_a_missing_section() -> None:
    with pytest.raises(ValueError, match="no section 1"):
        parse_ownership("nothing here")


def test_show_grants_lines_parse_to_tables_privileges_and_columns() -> None:
    lines = [
        "GRANT USAGE ON *.* TO `r_part1`@`%`",
        "GRANT SELECT, INSERT ON `db`.`feasible_windows` TO `r_part1`@`%`",
        "GRANT SELECT (`id`, `is_active`), INSERT ON `db`.`users` TO `r_part1`@`%`",
        "GRANT SELECT, UPDATE (`outcome`, `status`) ON `db`.`part1_runs` TO `r_part1`@`%`",
    ]
    assert parse_role_grants(lines, "db") == {
        "feasible_windows": {"SELECT": None, "INSERT": None},
        "users": {"SELECT": frozenset({"id", "is_active"}), "INSERT": None},
        "part1_runs": {"SELECT": None, "UPDATE": frozenset({"outcome", "status"})},
    }


def test_any_other_grant_scope_is_kept_so_it_can_fail_the_comparison() -> None:
    lines = [
        "GRANT PROCESS, FILE ON *.* TO `r_part1`@`%`",
        "GRANT EVENT ON `db`.* TO `r_part1`@`%`",
    ]
    assert parse_role_grants(lines, "db") == {
        "*.*": {"PROCESS": None, "FILE": None},
        "`db`.*": {"EVENT": None},
    }


def test_an_unknown_grant_line_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown grant line"):
        parse_role_grants(["REVOKE ALL"], "db")


def test_the_matrix_gives_each_role_its_expected_grants() -> None:
    ownership = load_ownership()
    expected = expected_role_grants(ownership, "w_part3")
    assert expected["evaluation_metrics"] == {"SELECT": None, "INSERT": None}
    assert expected["users"] == {"SELECT": frozenset({"id", "name", "is_active"})}
    assert "audit_logs" not in expected
    edi = expected_role_grants(ownership, "w_edi")
    assert edi["vessels"] == {"SELECT": None, "UPDATE": frozenset({"call_sign", "flag_state"})}
