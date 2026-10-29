"""Datum consistency check (AI-014).

Tide, sea level, channel depth and berth depth must share one datum (Architecture §7.3,
§13.1); the AI refuses to assess on a mismatch. Values are compared exactly, with no
normalisation. Converting between datums (for example LAT to MSL) is not done here: it
depends on DEC-27.
"""


class DatumError(ValueError):
    """Base class for datum errors."""


class MissingDatumError(DatumError):
    """A datum value is missing or empty."""


class DatumMismatchError(DatumError):
    """The datum values are not identical."""


_SOURCES = (
    "tide_constituent_set.datum_reference",
    "navigation_channel.depth_datum",
    "berth.depth_datum",
)


def check_datum_consistency(
    tide_set_datum: str | None, channel_datum: str | None, berth_datum: str | None
) -> str:
    """Return the shared datum, or raise unless all three values are present and identical."""
    values = (tide_set_datum, channel_datum, berth_datum)
    described = ", ".join(f"{s}={v!r}" for s, v in zip(_SOURCES, values, strict=True))
    missing = [s for s, v in zip(_SOURCES, values, strict=True) if v is None or not v.strip()]
    if missing:
        raise MissingDatumError(f"missing datum in {', '.join(missing)} ({described})")
    present = [v for v in values if v is not None]
    if len(set(present)) != 1:
        raise DatumMismatchError(f"datum mismatch: {described}")
    return present[0]
