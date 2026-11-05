"""Production code must never create a naive datetime.

`datetime.now()` on a Windows machine returns Cairo time, and every datetime column holds UTC
(CT-17 §2). `datetime.now(UTC)` is the only way to read the clock. The database's own values come
back naive and are UTC; those are read, not created, so they don't appear here.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_DIRS = ("common", "edi", "part1", "part2", "part3")
ALWAYS_LOCAL = {"utcnow", "utcfromtimestamp", "today", "strptime"}
# Wall-clock values on their way into `to_utc`, the conversion itself (AI-014). Nothing else.
ALLOWED = {("common/time.py", "combine"), ("common/time.py", "replace")}


def _needs_tz(call: ast.Call, position: int) -> bool:
    has_keyword = any(keyword.arg in {"tz", "tzinfo"} for keyword in call.keywords)
    return not has_keyword and len(call.args) <= position


def naive_datetime_calls(source: str, path: str = "<test>") -> list[str]:
    """Each call in `source` that creates a naive datetime, as `line:name`."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = ""
        if isinstance(node.func, ast.Name) and node.func.id == "datetime":
            name = "datetime" if _needs_tz(node, 7) else ""
        elif isinstance(node.func, ast.Attribute):
            attribute = node.func.attr
            owner = node.func.value
            on_datetime = isinstance(owner, ast.Name) and owner.id in {"datetime", "date"}
            if on_datetime and attribute in ALWAYS_LOCAL:
                name = attribute
            elif on_datetime and attribute == "now" and _needs_tz(node, 0):
                name = attribute
            elif on_datetime and attribute == "fromtimestamp" and _needs_tz(node, 1):
                name = attribute
            elif on_datetime and attribute == "combine" and _needs_tz(node, 2):
                name = attribute
            elif attribute == "replace" and any(
                keyword.arg == "tzinfo"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is None
                for keyword in node.keywords
            ):
                name = attribute
        if name and (path, name) not in ALLOWED:
            found.append(f"{node.lineno}:{name}")
    return found


def test_production_code_creates_no_naive_datetime() -> None:
    problems: dict[str, list[str]] = {}
    scanned = 0
    for directory in PRODUCTION_DIRS:
        for file in (REPO_ROOT / directory).rglob("*.py"):
            scanned += 1
            path = file.relative_to(REPO_ROOT).as_posix()
            calls = naive_datetime_calls(file.read_text(encoding="utf-8"), path)
            if calls:
                problems[path] = calls
    assert scanned > 0
    assert problems == {}


@pytest.mark.parametrize(
    "source",
    [
        "datetime.now()",
        "datetime.utcnow()",
        "datetime.today()",
        "date.today()",
        "datetime.utcfromtimestamp(1)",
        "datetime.fromtimestamp(1)",
        "datetime.strptime('1', '%S')",
        "datetime.combine(a, b)",
        "datetime(2026, 11, 3)",
        "value.replace(tzinfo=None)",
    ],
)
def test_each_naive_form_is_caught(source: str) -> None:
    assert naive_datetime_calls(source)


@pytest.mark.parametrize(
    "source",
    [
        "datetime.now(UTC)",
        "datetime.now(tz=UTC)",
        "datetime.fromtimestamp(1, UTC)",
        "datetime.combine(a, b, UTC)",
        "datetime(2026, 11, 3, tzinfo=UTC)",
        "datetime(2026, 11, 3, 1, 2, 3, 4, UTC)",
        "value.replace(tzinfo=UTC)",
        "value.replace(hour=1)",
        "text.replace('a', 'b')",
    ],
)
def test_each_aware_form_passes(source: str) -> None:
    assert naive_datetime_calls(source) == []


def test_only_common_time_may_build_wall_clock_values() -> None:
    assert naive_datetime_calls("datetime.combine(a, b)", "common/time.py") == []
    assert naive_datetime_calls("datetime.combine(a, b)", "common/other.py")
