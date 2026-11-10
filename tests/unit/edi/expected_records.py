"""Hand-written expected records for the PARSED cases of the AI-023 corpus (AI-030).

Every value is copied by hand from the case's ``.edi`` file, never from parser output.
"""

from __future__ import annotations

from decimal import Decimal

from edi.records import Oog, ParsedLine, ParsedVessel, Stowage

LOAD = "LOC+11+CNSHA:139:6"
DISCHARGE = "LOC+12+EGDAM:139:6"


def _vessel(voyage: str) -> ParsedVessel:
    tdt = f"TDT+20+{voyage}+1++MSC:172:20+++9811000::11:MSC ALEXANDRIA"
    return ParsedVessel("9811000", "MSC ALEXANDRIA", None, tdt)


def _line(
    line_no: int,
    *,
    loc147: str,
    stowage: Stowage,
    mea: str,
    weight_kg: int,
    eqd: str,
    container_number: str,
    iso_size_type: str,
    full_empty: str | None = "FULL",
    extra_refs: dict[str, str] | None = None,
    imdg_class: str | None = None,
    reefer_set_temperature: Decimal | None = None,
    oog: Oog | None = None,
) -> ParsedLine:
    refs = {
        "stowage": loc147,
        "weight_kg": mea,
        "container_number": eqd,
        "iso_size_type": eqd,
        "port_of_load": LOAD,
        "port_of_discharge": DISCHARGE,
    }
    if full_empty is not None:
        refs["full_empty"] = eqd
    refs.update(extra_refs or {})
    return ParsedLine(
        line_no=line_no,
        segment_ref=loc147,
        container_number=container_number,
        iso_size_type=iso_size_type,
        full_empty="FULL" if full_empty == "FULL" else None,
        weight_kg=weight_kg,
        imdg_class=imdg_class,
        oog=oog or Oog(),
        reefer_set_temperature=reefer_set_temperature,
        stowage=stowage,
        port_of_load="CNSHA",
        port_of_discharge="EGDAM",
        segment_refs=refs,
        unconverted={},
    )


def _mscu_45g1(line_no: int) -> ParsedLine:
    return _line(
        line_no,
        loc147="LOC+147+0010282",
        stowage=Stowage(1, 2, 82),
        mea="MEA+WT++KGM:24500",
        weight_kg=24500,
        eqd="EQD+CN+MSCU1234566+45G1+++5",
        container_number="MSCU1234566",
        iso_size_type="45G1",
    )


def _cmau_22g1(line_no: int) -> ParsedLine:
    return _line(
        line_no,
        loc147="LOC+147+0010482",
        stowage=Stowage(1, 4, 82),
        mea="MEA+WT++KGM:21800",
        weight_kg=21800,
        eqd="EQD+CN+CMAU3456787+22G1+++5",
        container_number="CMAU3456787",
        iso_size_type="22G1",
    )


EXPECTED: dict[str, tuple[ParsedVessel, tuple[ParsedLine, ...]]] = {
    "01-valid-221": (_vessel("001A"), (_mscu_45g1(1),)),
    "02-valid-311": (_vessel("002A"), (_mscu_45g1(1), _cmau_22g1(2))),
    "03-valid-with-warnings": (
        _vessel("003A"),
        (
            _line(
                1,
                loc147="LOC+147+0010282",
                stowage=Stowage(1, 2, 82),
                mea="MEA+WT++KGM:24500",
                weight_kg=24500,
                eqd="EQD+CN+MSCU1234567+45G1+++5",
                container_number="MSCU1234567",
                iso_size_type="45G1",
            ),
        ),
    ),
    "19-valid-dangerous-goods": (
        _vessel("019A"),
        (
            _line(
                1,
                loc147="LOC+147+0010282",
                stowage=Stowage(1, 2, 82),
                mea="MEA+WT++KGM:24500",
                weight_kg=24500,
                eqd="EQD+CN+MSCU1234566+22G1+++5",
                container_number="MSCU1234566",
                iso_size_type="22G1",
                imdg_class="3",
                extra_refs={"imdg_class": "DGS+IMD+3+1993"},
            ),
        ),
    ),
    "20-valid-reefer": (
        _vessel("020A"),
        (
            _line(
                1,
                loc147="LOC+147+0010282",
                stowage=Stowage(1, 2, 82),
                mea="MEA+WT++KGM:24500",
                weight_kg=24500,
                eqd="EQD+CN+MAEU4567896+45R1+++5",
                container_number="MAEU4567896",
                iso_size_type="45R1",
                reefer_set_temperature=Decimal("-18"),
                extra_refs={"reefer_set_temperature": "TMP+2+-18:CEL"},
            ),
        ),
    ),
    "21-valid-oog": (
        _vessel("021A"),
        (
            _line(
                1,
                loc147="LOC+147+0010282",
                stowage=Stowage(1, 2, 82),
                mea="MEA+WT++KGM:24500",
                weight_kg=24500,
                eqd="EQD+CN+MSCU2345672+45G1+++5",
                container_number="MSCU2345672",
                iso_size_type="45G1",
                oog=Oog(front_cm=20, height_cm=30),
                extra_refs={"oog.front_cm": "DIM+5+CMT:20", "oog.height_cm": "DIM+13+CMT:30"},
            ),
        ),
    ),
    "22-missing-full-empty": (
        _vessel("022A"),
        (
            _line(
                1,
                loc147="LOC+147+0010282",
                stowage=Stowage(1, 2, 82),
                mea="MEA+WT++KGM:24500",
                weight_kg=24500,
                eqd="EQD+CN+MSCU1234566+45G1",
                container_number="MSCU1234566",
                iso_size_type="45G1",
                full_empty=None,
            ),
        ),
    ),
    "23-unknown-segment": (_vessel("023A"), (_mscu_45g1(1), _cmau_22g1(2))),
}
