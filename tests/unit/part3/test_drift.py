"""C2 drift monitor (AI-072). Distributions are SYNTHETIC; thresholds are test values only,
not proposals for DEC-30 TR-01 / TR-02."""

import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from common.config import ConfigurationError, PortSettings
from part3.drift import (
    EMPTY_BIN_SHARE,
    Thresholds,
    alerts,
    measure,
    psi,
    rolling_mae,
    write_measurements,
)

NOW = datetime(2026, 11, 21, tzinfo=UTC)
TEST_THRESHOLDS = Thresholds(psi=Decimal("0.2"), mae=Decimal("1.5"))  # test values only
REFERENCE = [float(i) for i in range(100)]


def test_identical_distributions_have_zero_psi() -> None:
    assert psi(REFERENCE, REFERENCE) == Decimal("0.00000")


def test_psi_matches_the_formula_on_a_known_shift() -> None:
    # Reference deciles 0..99 → bins of 10; current puts everything in the top bin.
    current = [95.0] * 50
    expected = 9 * (EMPTY_BIN_SHARE - 0.1) * math.log(EMPTY_BIN_SHARE / 0.1) + (1 - 0.1) * math.log(
        1 / 0.1
    )
    assert psi(REFERENCE, current) == Decimal(repr(expected)).quantize(Decimal("0.00001"))


def test_psi_grows_with_the_shift() -> None:
    small = psi(REFERENCE, [v + 5 for v in REFERENCE])
    large = psi(REFERENCE, [v + 40 for v in REFERENCE])
    assert Decimal(0) < small < large


def test_psi_with_few_distinct_values_merges_bins() -> None:
    assert psi([1.0] * 50 + [2.0] * 50, [1.0] * 50 + [2.0] * 50) == Decimal("0.00000")


@pytest.mark.parametrize(
    ("reference", "current"),
    [([], [1.0]), ([1.0], []), ([1.0, float("nan")], [1.0]), ([1.0], [float("inf")])],
)
def test_psi_refuses_empty_or_non_finite_input(
    reference: list[float], current: list[float]
) -> None:
    with pytest.raises(ValueError):
        psi(reference, current)


def test_rolling_mae() -> None:
    assert rolling_mae([1.0, 2.0, 3.0], [1.5, 2.0, 1.0]) == Decimal("0.83333")
    assert rolling_mae([4.0], [4.0]) == Decimal("0.00000")
    with pytest.raises(ValueError, match="predictions"):
        rolling_mae([1.0, 2.0], [1.0])


def test_above_threshold_produces_an_alert() -> None:
    rows = measure(
        7,
        {"moves": (REFERENCE, [v + 60 for v in REFERENCE])},
        ([10.0, 12.0], [7.0, 9.0]),  # MAE 3.0
        TEST_THRESHOLDS,
        NOW,
    )
    assert [(m.metric_type, m.is_drifted) for m in rows] == [("PSI", True), ("ROLLING_MAE", True)]
    assert alerts(rows) == rows


def test_healthy_case_is_stored_as_not_drifted() -> None:
    rows = measure(7, {"moves": (REFERENCE, REFERENCE)}, ([1.0], [1.0]), TEST_THRESHOLDS, NOW)
    assert [m.is_drifted for m in rows] == [False, False]
    assert alerts(rows) == ()
    assert rows[0].row() == {
        "model_version_id": 7,
        "metric_type": "PSI",
        "feature_name": "moves",
        "metric_value": Decimal("0.00000"),
        "threshold": Decimal("0.2"),
        "measured_at": NOW,
    }
    assert rows[1].row()["feature_name"] is None  # chk_dm_feature


def test_value_equal_to_threshold_is_not_drifted() -> None:
    """Same as the schema: `is_drifted = metric_value > threshold`."""
    rows = measure(7, {}, ([3.0], [1.5]), Thresholds(Decimal(1), Decimal("1.5")), NOW)
    assert rows[0].metric_value == Decimal("1.50000") and not rows[0].is_drifted


def test_bad_inputs_are_refused() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        measure(7, {}, None, TEST_THRESHOLDS, NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="1 to 60"):
        measure(7, {"x" * 61: ([1.0], [1.0])}, None, TEST_THRESHOLDS, NOW)


def test_thresholds_only_from_port_settings() -> None:
    with pytest.raises(ConfigurationError):
        Thresholds.from_port_settings(PortSettings([]))  # DEC-30 TR-01 / TR-02 deferred
    rows = [("drift_psi_threshold", "0.2", "DECIMAL"), ("drift_mae_threshold", "1.5", "DECIMAL")]
    assert Thresholds.from_port_settings(PortSettings(rows)) == TEST_THRESHOLDS


def test_write_inserts_rows() -> None:
    calls: list[Any] = []

    class Repo:
        def insert_many(self, table: str, rows: list[dict[str, object]]) -> None:
            calls.append((table, rows))

    rows = measure(7, {"moves": (REFERENCE, REFERENCE)}, None, TEST_THRESHOLDS, NOW)
    write_measurements(Repo(), rows)  # type: ignore[arg-type]
    assert calls[0][0] == "drift_measurements" and len(calls[0][1]) == 1
