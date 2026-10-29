import pytest

from common.datum import (
    DatumError,
    DatumMismatchError,
    MissingDatumError,
    check_datum_consistency,
)

SOURCES = (
    "tide_constituent_set.datum_reference",
    "navigation_channel.depth_datum",
    "berth.depth_datum",
)


def test_equal_values_return_the_datum() -> None:
    assert check_datum_consistency("LAT", "LAT", "LAT") == "LAT"


@pytest.mark.parametrize("position", range(3))
def test_single_mismatch_raises_with_all_values_and_sources(position: int) -> None:
    values = ["LAT", "LAT", "LAT"]
    values[position] = "MSL"
    with pytest.raises(DatumMismatchError) as info:
        check_datum_consistency(*values)
    assert isinstance(info.value, DatumError)
    message = str(info.value)
    for source, value in zip(SOURCES, values, strict=True):
        assert f"{source}={value!r}" in message


@pytest.mark.parametrize(("left", "right"), [("LAT", "lat"), ("LAT", "LAT "), ("LAT", " LAT")])
def test_no_normalisation(left: str, right: str) -> None:
    with pytest.raises(DatumMismatchError):
        check_datum_consistency(left, left, right)


@pytest.mark.parametrize("missing", [None, "", "  "])
@pytest.mark.parametrize("position", range(3))
def test_missing_datum_raises(missing: str | None, position: int) -> None:
    values: list[str | None] = ["LAT", "LAT", "LAT"]
    values[position] = missing
    with pytest.raises(MissingDatumError) as info:
        check_datum_consistency(*values)
    assert isinstance(info.value, DatumError)
    message = str(info.value)
    assert SOURCES[position] in message
    for source, value in zip(SOURCES, values, strict=True):
        assert f"{source}={value!r}" in message


def test_all_missing_raises_missing_not_mismatch() -> None:
    with pytest.raises(MissingDatumError):
        check_datum_consistency(None, None, None)
