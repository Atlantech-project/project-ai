import runpy
import sys
from pathlib import Path

import pytest

from tools.scenario_generator.__main__ import main


def test_cli_writes_the_file_and_prints_its_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--size", "minimum", "--seed", "1", "--days", "2", "--out", str(tmp_path)]) == 0
    expected = tmp_path / "SYNTHETIC_minimum_seed1.json"
    assert expected.is_file()
    assert capsys.readouterr().out.strip() == str(expected)


def test_cli_same_arguments_write_identical_bytes(tmp_path: Path) -> None:
    for name in ("a", "b"):
        main(["--size", "reference", "--seed", "9", "--days", "2", "--out", str(tmp_path / name)])
    first = (tmp_path / "a" / "SYNTHETIC_reference_seed9.json").read_bytes()
    assert first == (tmp_path / "b" / "SYNTHETIC_reference_seed9.json").read_bytes()


def test_cli_rejects_unknown_size(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--size", "huge", "--seed", "1", "--out", str(tmp_path)])
    assert exit_info.value.code == 2


def test_cli_requires_a_seed(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--size", "minimum", "--out", str(tmp_path)])
    assert exit_info.value.code == 2


def test_running_the_package_as_a_script_exits_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    argv = ["scenario_generator", "--size", "minimum", "--seed", "2", "--days", "1"]
    monkeypatch.setattr("sys.argv", [*argv, "--out", str(tmp_path)])
    # runpy warns when the module it is about to run is already imported (this file imports it).
    monkeypatch.delitem(sys.modules, "tools.scenario_generator.__main__")
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("tools.scenario_generator", run_name="__main__")
    assert exit_info.value.code == 0
    assert (tmp_path / "SYNTHETIC_minimum_seed2.json").is_file()
