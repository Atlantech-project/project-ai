"""The committed sample scenarios are exactly what the register's seeds regenerate."""

import json
from pathlib import Path
from typing import Final

import pytest

from tools.scenario_generator.generate import generate
from tools.scenario_generator.io import scenario_filename, to_json
from tools.scenario_generator.model import ScenarioSize

FIXTURES: Final = Path(__file__).resolve().parents[1] / "fixtures"
REGISTER: Final = FIXTURES / "scenario_seeds.json"


def _entries() -> dict[str, dict[str, object]]:
    return dict(json.loads(REGISTER.read_text(encoding="utf-8")))


def test_the_register_covers_both_sizes() -> None:
    assert {entry["size"] for entry in _entries().values()} == {"minimum", "reference"}


@pytest.mark.parametrize("name", sorted(_entries()))
def test_committed_samples_match_regeneration(name: str) -> None:
    entry = _entries()[name]
    size = ScenarioSize(str(entry["size"]))
    seed, days = int(str(entry["seed"])), int(str(entry["days"]))
    path = FIXTURES / scenario_filename(size, seed)
    assert path.read_bytes() == to_json(generate(size, seed, days)).encode("utf-8")


def test_every_fixture_file_is_synthetic_or_the_register() -> None:
    names = {path.name for path in FIXTURES.iterdir() if path.is_file()}
    assert REGISTER.name in names
    assert all(n == REGISTER.name or n.startswith("SYNTHETIC_") for n in names)


def test_every_scenario_file_is_in_the_register() -> None:
    registered = {
        scenario_filename(ScenarioSize(str(e["size"])), int(str(e["seed"])))
        for e in _entries().values()
    }
    on_disk = {path.name for path in FIXTURES.glob("SYNTHETIC_*.json")}
    assert on_disk == registered
