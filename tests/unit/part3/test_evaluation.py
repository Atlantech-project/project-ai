"""C1 evaluation rows (AI-071). Values are SYNTHETIC; no metric definition is proposed here."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from part3.evaluation import DatasetType, EvaluationMetric, MetricName, mae_metric, write_metrics

START = datetime(2026, 11, 1, tzinfo=UTC)
END = START + timedelta(days=7)
NOW = END + timedelta(hours=1)


def metric(name: MetricName, version: int | None, **changes: Any) -> EvaluationMetric:
    values: dict[str, Any] = {
        "metric_name": name,
        "dataset_type": DatasetType.PRODUCTION,
        "metric_value": Decimal("1.5"),
        "period_start": START,
        "period_end": END,
        "computed_at": NOW,
        "model_version_id": version,
    }
    values.update(changes)
    return EvaluationMetric(**values)


def test_mae_reproduces_a_hand_computed_value() -> None:
    # |10-12| + |8-7| + |5-5.5| = 3.5 over 3 pairs = 1.16666..., rounded half-up to 5 decimals.
    row = mae_metric(9, [10.0, 8.0, 5.0], [12.0, 7.0, 5.5], DatasetType.ROLLING, (START, END), NOW)

    assert row is not None
    assert row.metric_value == Decimal("1.16667")
    assert row.row() == {
        "model_version_id": 9,
        "retraining_run_id": None,
        "metric_name": "MAE",
        "dataset_type": "ROLLING",
        "metric_value": Decimal("1.16667"),
        "period_start": START,
        "period_end": END,
        "computed_at": NOW,
    }


def test_no_pairs_is_no_metric_not_zero() -> None:
    assert mae_metric(9, [], [], DatasetType.PRODUCTION, (START, END), NOW) is None


@pytest.mark.parametrize(
    ("actual", "predicted", "message"),
    [([1.0], [], "1 actual values but 0"), ([float("nan")], [1.0], "not finite")],
)
def test_bad_mae_input_is_refused(
    actual: list[float], predicted: list[float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        mae_metric(9, actual, predicted, DatasetType.PRODUCTION, (START, END), NOW)


@pytest.mark.parametrize(
    ("name", "version", "allowed"),
    [
        (MetricName.MAE, 9, True),
        (MetricName.MAE, None, False),
        (MetricName.OVERRIDE_RATE, None, True),
        (MetricName.OVERRIDE_RATE, 9, False),
        (MetricName.WAIT_TIME, None, True),
        (MetricName.WAIT_TIME, 9, False),
        (MetricName.WINDOW_ACCURACY, None, True),
        (MetricName.WINDOW_ACCURACY, 9, True),
    ],
)
def test_scope_follows_chk_em_scope(name: MetricName, version: int | None, allowed: bool) -> None:
    if allowed:
        assert metric(name, version).model_version_id == version
    else:
        with pytest.raises(ValueError, match="chk_em_scope"):
            metric(name, version)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"period_end": START}, "chk_em_period"),
        ({"period_start": START.replace(tzinfo=None)}, "timezone-aware"),
        ({"computed_at": NOW.replace(tzinfo=None)}, "timezone-aware"),
        ({"metric_value": Decimal("NaN")}, "finite"),
        ({"metric_value": Decimal(1_000_000_000)}, r"decimal\(14,5\)"),
        ({"metric_value": Decimal("0.123456")}, "more than 5 decimals"),
    ],
)
def test_row_checks(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        metric(MetricName.MAE, 9, **changes)


def test_largest_storable_value_is_accepted() -> None:
    value = Decimal("999999999.99999")
    assert metric(MetricName.MAE, 9, metric_value=value).metric_value == value


class FakeRepo:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[dict[str, object]]]] = []

    def insert_many(self, table: str, rows: list[dict[str, object]]) -> None:
        self.calls.append((table, rows))


def test_write_inserts_into_evaluation_metrics_and_skips_an_empty_batch() -> None:
    repo = FakeRepo()
    write_metrics(repo, [])  # type: ignore[arg-type]
    write_metrics(repo, [metric(MetricName.MAE, 9)])  # type: ignore[arg-type]

    assert [table for table, _ in repo.calls] == ["evaluation_metrics"]
    assert repo.calls[0][1][0]["metric_name"] == "MAE"
