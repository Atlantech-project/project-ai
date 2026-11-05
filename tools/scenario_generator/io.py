"""Scenario files: their names, their JSON text and writing them out."""

import json
from pathlib import Path

from tools.scenario_generator.model import SYNTHETIC_PREFIX, Scenario, ScenarioSize


def scenario_filename(size: ScenarioSize, seed: int) -> str:
    return f"{SYNTHETIC_PREFIX}_{size.value}_seed{seed}.json"


def to_json(scenario: Scenario) -> str:
    """Stable text: sorted keys, two-space indent, a final newline, ASCII only."""
    document = {"metadata": scenario.metadata, "tables": scenario.tables}
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def write_scenario(scenario: Scenario, directory: Path) -> Path:
    size = ScenarioSize(str(scenario.metadata["size"]))
    seed = int(str(scenario.metadata["seed"]))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / scenario_filename(size, seed)
    # newline="\n" keeps the bytes the same on every platform.
    path.write_text(to_json(scenario), encoding="utf-8", newline="\n")
    return path
