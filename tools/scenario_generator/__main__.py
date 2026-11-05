"""Command line: `python -m tools.scenario_generator --size minimum --seed 1`."""

import argparse
from pathlib import Path

from tools.scenario_generator.generate import generate
from tools.scenario_generator.io import write_scenario
from tools.scenario_generator.model import ScenarioSize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.scenario_generator",
        description="Write a SYNTHETIC port scenario file. Not operational data.",
    )
    parser.add_argument("--size", type=ScenarioSize, choices=list(ScenarioSize), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--out", type=Path, default=Path("tests/fixtures"))
    args = parser.parse_args(argv)
    path = write_scenario(generate(args.size, args.seed, args.days), args.out)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
