"""UN/EDIFACT syntax layer for the BAPLIE parser (AI-030).

Splits EDIFACT text into segments, data elements and components, honouring the ``UNA``
service string advice and the release character. It knows nothing about BAPLIE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

_BOM = "﻿"


@dataclass(frozen=True)
class ServiceChars:
    """The separators of one interchange (from ``UNA``, or the defaults)."""

    component: str
    element: str
    decimal: str
    release: str
    terminator: str

    DEFAULT: ClassVar[ServiceChars]


ServiceChars.DEFAULT = ServiceChars(":", "+", ".", "?", "'")


@dataclass(frozen=True)
class Segment:
    """One segment.

    ``elements[0]`` is the first data element after the tag; each element is a tuple of
    components with release characters resolved. ``text`` is the segment as written,
    without its terminator, release characters kept. ``index`` is 0-based, ``UNA``
    excluded.
    """

    tag: str
    elements: tuple[tuple[str, ...], ...]
    text: str
    index: int


class SyntaxProblem(Exception):
    """The text cannot be split into complete segments."""

    def __init__(self, reason: Literal["UNTERMINATED", "NO_SEGMENTS"], detail: str) -> None:
        super().__init__(detail)
        self.reason: Literal["UNTERMINATED", "NO_SEGMENTS"] = reason


def tokenize(text: str) -> tuple[ServiceChars, list[Segment]]:
    """Split ``text`` into segments. Raises ``SyntaxProblem`` on an incomplete text."""
    body = text.removeprefix(_BOM)
    chars = ServiceChars.DEFAULT
    if body.startswith("UNA") and len(body) >= 9:
        advice = body[3:9]
        chars = ServiceChars(advice[0], advice[1], advice[2], advice[3], advice[5])
        body = body[9:]

    segments: list[Segment] = []
    raw: list[str] = []
    released = False
    for char in body:
        if released:
            raw.append(char)
            released = False
        elif char == chars.release:
            raw.append(char)
            released = True
        elif char == chars.terminator:
            written = "".join(raw).strip()
            if written:
                segments.append(_segment(written, chars, len(segments)))
            raw = []
        else:
            raw.append(char)

    leftover = "".join(raw).strip()
    if leftover:
        raise SyntaxProblem("UNTERMINATED", f"unterminated segment: {leftover!r}")
    if not segments:
        raise SyntaxProblem("NO_SEGMENTS", "no segments")
    return chars, segments


def _segment(written: str, chars: ServiceChars, index: int) -> Segment:
    # Characters are collected in lists and joined once per component, so a long
    # element costs linear time (string += on a list item is quadratic).
    elements: list[list[str]] = []
    components: list[str] = []
    current: list[str] = []
    released = False
    for char in written:
        if released:
            current.append(char)
            released = False
        elif char == chars.release:
            released = True
        elif char == chars.element:
            components.append("".join(current))
            elements.append(components)
            components, current = [], []
        elif char == chars.component:
            components.append("".join(current))
            current = []
        else:
            current.append(char)
    components.append("".join(current))
    elements.append(components)
    return Segment(
        tag=elements[0][0],
        elements=tuple(tuple(element) for element in elements[1:]),
        text=written,
        index=index,
    )
