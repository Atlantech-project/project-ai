"""BAPLIE versions, segment tags, qualifiers and issue codes (AI-030).

**Unverified against the SMDG guides.** Every qualifier, position and code value below
follows the AI-023 corpus, CT-12 v1.1 and DEC-28. None has been checked against the SMDG
BAPLIE message implementation guides 2.2.1 and 3.1.1, which are not available (DEC-28
item 7, a blocked sub-item of AI-030). When they are, this module is the place to change.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from edi.records import FullEmpty, Version

# CT-12 v1.1: (version, release, agency) of the UNH message identifier. The association
# code is read but not checked; 2.x files of the D.95B family use the 2.2.1 rules.
MESSAGE_TYPE: Final = "BAPLIE"
SUPPORTED_VERSIONS: Final[Mapping[tuple[str, str, str], Version]] = {
    ("D", "95B", "UN"): "D95B",
    ("D", "13B", "UN"): "D13B",
}

# Segments the parser maps or knowingly ignores. Anything else is UNKNOWN_SEGMENT.
HEADER_TAGS: Final = frozenset(
    {"UNA", "UNB", "UNG", "UNE", "UNH", "UNT", "UNZ", "BGM", "DTM", "RFF", "NAD", "TDT"}
    | {"LOC", "FTX", "CNT"}
)
CONTAINER_TAGS: Final = frozenset(
    {"GID", "GDS", "MEA", "DIM", "TMP", "RNG", "EQD", "EQA", "EQN", "NAD", "DGS", "ATT"}
    | {"CTA", "COM", "HAN"}
)
KNOWN_TAGS: Final = HEADER_TAGS | CONTAINER_TAGS

# Field mapping. The same table is used for D.95B and D.13B (the corpus layouts agree).
VESSEL_TDT_QUALIFIER: Final = "20"
VESSEL_ID_ELEMENT: Final = 7  # elements[7] = C222: IMO, -, agency, name
STOWAGE_QUALIFIER: Final = "147"
STOWAGE_DIGITS: Final = 7  # BBBRRTT
PORT_QUALIFIERS: Final[Mapping[str, str]] = {"11": "port_of_load", "12": "port_of_discharge"}
WEIGHT_QUALIFIERS: Final = frozenset({"WT", "VGM"})
WEIGHT_UNIT: Final = "KGM"
CONTAINER_QUALIFIER: Final = "CN"
FULL_EMPTY_ELEMENT: Final = 5  # sixth data element of EQD
FULL_EMPTY_CODES: Final[Mapping[str, FullEmpty]] = {"5": "FULL", "4": "EMPTY"}
TEMPERATURE_QUALIFIER: Final = "2"
TEMPERATURE_UNIT: Final = "CEL"
DG_QUALIFIER: Final = "IMD"
OOG_QUALIFIERS: Final[Mapping[str, str]] = {
    "5": "front_cm",
    "6": "back_cm",
    "7": "right_cm",
    "8": "left_cm",
    "13": "height_cm",
}
OOG_UNIT: Final = "CMT"

# Issue codes for reading-the-file problems. UNKNOWN_SEGMENT and UNREADABLE_FILE are
# proposed in CT-24 (docs/followups/contracts-followup.md) and may be renamed.
UNREADABLE_FILE: Final = "UNREADABLE_FILE"
NOT_EDIFACT: Final = "NOT_EDIFACT"
CORRUPTED_SYNTAX: Final = "CORRUPTED_SYNTAX"
WRONG_MESSAGE_TYPE: Final = "WRONG_MESSAGE_TYPE"
UNSUPPORTED_BAPLIE_VERSION: Final = "UNSUPPORTED_BAPLIE_VERSION"
UNKNOWN_SEGMENT: Final = "UNKNOWN_SEGMENT"

MSG_UNREADABLE: Final = "File is empty or cannot be read"
MSG_TRUNCATED: Final = "File is truncated: last segment is unterminated and UNT/UNZ are missing"
MSG_UNTERMINATED: Final = "File is corrupted: last segment is unterminated"
MSG_NO_UNH: Final = "UNH segment is missing"
MSG_NO_UNT: Final = "File is truncated: UNT is missing"
MSG_NO_UNZ: Final = "File is truncated: UNZ is missing"


def msg_unt_count(declared: str, counted: int) -> str:
    return f"UNT segment count {declared} does not match {counted} segments"


def msg_message_count(count: int) -> str:
    return f"File holds {count} messages; one BAPLIE message per file is expected"


NOT_EDIFACT_FOUND_LENGTH: Final = 3
NOT_EDIFACT_FOUND_NONE: Final = "none"


def msg_unsupported(found: str) -> str:
    # CT-12 v1.1 text, used for an unsupported version, a different message type and a
    # non-EDIFACT file. For a non-EDIFACT file <found> is the first 3 characters of the
    # file as read, or "none" when they hold no readable character (user, 2026-11-10).
    return f"Unsupported BAPLIE version: {found}. Supported: SMDG 2.2.1 (D.95B), SMDG 3.1.1 (D.13B)"


def msg_unknown_segment(tag: str) -> str:
    return f"Unknown segment {tag} ignored; valid containers still loaded"
