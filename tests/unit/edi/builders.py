"""Builders for small BAPLIE messages in the AI-030 parser tests."""

from __future__ import annotations

UNA = "UNA:+.? '"
UNB = "UNB+UNOA:2+SENDER+RECEIVER+261101:0800+1'"
D95B = "BAPLIE:D:95B:UN:SMDG22"
TDT = "TDT+20+001A+1++MSC:172:20+++9811000::11:MSC ALEXANDRIA"

CONTAINER_A = (
    "LOC+147+0010282",
    "MEA+WT++KGM:24500",
    "EQD+CN+MSCU1234566+45G1+++5",
    "LOC+11+CNSHA:139:6",
    "LOC+12+EGDAM:139:6",
)


def message_text(*body: str, unh: str = D95B, una: str = UNA, terminator: str = "'") -> str:
    """One interchange with one message; ``UNT`` carries the right segment count."""
    segments = [f"UNH+1+{unh}", *body]
    segments.append(f"UNT+{len(segments) + 1}+1")
    segments.append("UNZ+1+1")
    return una + UNB.replace("'", terminator) + "".join(s + terminator for s in segments)


def message(*body: str, unh: str = D95B) -> bytes:
    return message_text(*body, unh=unh).encode("utf-8")
