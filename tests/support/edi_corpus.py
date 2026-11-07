"""Helpers for checking the BAPLIE test corpus in ``tests/edi_corpus``.

These are corpus-integrity helpers only. They are not the BAPLIE parser (AI-030).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CORPUS_ROOT = Path(__file__).resolve().parents[1] / "edi_corpus"

_UNA = "UNA:+.? '"
_LETTER_VALUES: dict[str, int] = {}


def _build_letter_values() -> None:
    value = 10
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if value % 11 == 0:
            value += 1
        _LETTER_VALUES[letter] = value
        value += 1


_build_letter_values()


def iso6346_check_digit(container_number: str) -> int:
    """Return the ISO 6346 check digit for the first 10 characters of the number."""
    total = 0
    for position, char in enumerate(container_number[:10]):
        value = _LETTER_VALUES[char] if char.isalpha() else int(char)
        total += value * (2**position)
    return total % 11 % 10


def split_segments(text: str) -> list[str]:
    """Split EDIFACT text into segments (without terminators), dropping ``UNA``.

    Raises ``ValueError`` when the text has no complete segment or ends with an
    unterminated segment.
    """
    body = text[len(_UNA) :] if text.startswith(_UNA) else text
    segments: list[str] = []
    current: list[str] = []
    released = False
    for char in body:
        if released:
            current.append(char)
            released = False
        elif char == "?":
            current.append(char)
            released = True
        elif char == "'":
            segments.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if "".join(current).strip():
        raise ValueError(f"unterminated segment: {''.join(current).strip()!r}")
    if not segments:
        raise ValueError("no segments")
    return segments


def container_numbers(segments: list[str]) -> list[str]:
    """Container numbers of the ``EQD+CN+`` segments, in order."""
    found = []
    for segment in segments:
        match = re.match(r"EQD\+CN\+([^+]+)", segment)
        if match:
            found.append(match.group(1))
    return found


@dataclass(frozen=True)
class CorpusCase:
    name: str
    edi_path: Path
    oracle: dict[str, Any]


def load_cases(root: Path = CORPUS_ROOT) -> list[CorpusCase]:
    """Load every ``<name>.expected.json`` with its ``<name>.edi`` path, sorted by name."""
    cases = []
    for oracle_path in sorted(root.glob("*.expected.json")):
        name = oracle_path.name.removesuffix(".expected.json")
        cases.append(
            CorpusCase(
                name=name,
                edi_path=root / f"{name}.edi",
                oracle=json.loads(oracle_path.read_text(encoding="utf-8")),
            )
        )
    return cases
