import json
from pathlib import Path

from tools.scenario_generator.generate import generate
from tools.scenario_generator.io import scenario_filename, to_json, write_scenario
from tools.scenario_generator.model import Scenario, ScenarioSize


def test_filename_starts_with_synthetic() -> None:
    assert scenario_filename(ScenarioSize.MINIMUM, 1) == "SYNTHETIC_minimum_seed1.json"
    assert scenario_filename(ScenarioSize.REFERENCE, 20) == "SYNTHETIC_reference_seed20.json"


def test_write_scenario_names_the_file_after_size_and_seed(tmp_path: Path) -> None:
    path = write_scenario(generate(ScenarioSize.MINIMUM, 5, 2), tmp_path / "nested")
    assert path == tmp_path / "nested" / "SYNTHETIC_minimum_seed5.json"
    assert path.is_file()


def test_json_round_trips_to_the_same_scenario() -> None:
    scenario = generate(ScenarioSize.REFERENCE, 3, 2)
    document = json.loads(to_json(scenario))
    assert Scenario(document["metadata"], document["tables"]) == scenario


def test_json_is_stable_text() -> None:
    text = to_json(generate(ScenarioSize.MINIMUM, 3, 2))
    assert text.endswith("}\n")
    assert "\r" not in text
    assert text == to_json(generate(ScenarioSize.MINIMUM, 3, 2))


def test_written_bytes_have_unix_line_endings(tmp_path: Path) -> None:
    path = write_scenario(generate(ScenarioSize.MINIMUM, 3, 2), tmp_path)
    assert b"\r" not in path.read_bytes()
