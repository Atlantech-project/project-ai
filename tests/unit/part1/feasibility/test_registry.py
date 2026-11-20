"""The three code lists (AI-044): A4-owned, owned elsewhere, and neither."""

import json
from pathlib import Path
from typing import Any, Final

import pytest

from part1.feasibility import DEFAULT_REGISTRY, CodeRegistry, Series

SEED_SPEC: Final = (
    Path(__file__).resolve().parents[4] / "docs" / "drafts" / "ai-payloads" / "seed-spec.json"
)


def _seeded_codes() -> list[str]:
    with SEED_SPEC.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return [str(row["code"]) for row in data["constraint_types"]]


def test_the_seed_has_constraint_codes() -> None:
    assert _seeded_codes()


@pytest.mark.parametrize("code", _seeded_codes())
def test_every_seeded_code_is_in_exactly_one_list(code: str) -> None:
    lists = [code in DEFAULT_REGISTRY.a4, code in DEFAULT_REGISTRY.elsewhere]
    assert lists.count(True) == 1, code


def test_the_a4_list() -> None:
    assert dict(DEFAULT_REGISTRY.a4) == {
        "MAX_WIND_KN": Series.WIND_SPEED,
        "MAX_WAVE_HEIGHT_M": Series.WAVE_HEIGHT,
    }


def test_ukc_is_owned_by_a5() -> None:
    assert "AI-045" in DEFAULT_REGISTRY.elsewhere["MIN_UKC_M"]


def test_the_lists_must_be_disjoint() -> None:
    with pytest.raises(ValueError, match="MAX_WIND_KN"):
        CodeRegistry(a4={"MAX_WIND_KN": Series.WIND_SPEED}, elsewhere={"MAX_WIND_KN": "B2"})
