"""OVERRIDE validation (AI-060). Every port value is SYNTHETIC (the B2 builders)."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from part2.filter import Kind, Option
from part2.state.model import PendingHold, ResourceKind, Shift
from part2.validation import (
    Change,
    OverrideMismatchError,
    apply_changes,
    parse_changes,
    validate_override,
)
from part2.validation import override as module
from tests.unit.part2.filter.builders import (
    BERTH,
    HOUR,
    OTHER_BERTH,
    OTHER_PILOT,
    PILOT,
    REQUEST,
    SYN_MAX_BEAM,
    T0,
    TUG_A,
    TUG_B,
    TUG_C,
    berth,
    context,
    limit,
    option,
    pilot,
    shift,
    state,
    tug,
)

SUBJECT = 9031
SCHEMA_PATH = (
    Path(__file__).resolve().parents[4] / "docs/ref/ai-payloads/c06-completion.schema.json"
)
_C06 = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
RESULT_SCHEMA = Draft202012Validator(
    {"$ref": "#/$defs/validation_result", "$defs": _C06["$defs"]},
)

# An option inside the window [T0, T0 + 6 h) that passes B2 as it is.
BASE = option(start=T0 + HOUR, end=T0 + 5 * HOUR)


def run(*changes: Change, port: Any = None, ctx: Any = None, base: Option = BASE) -> Any:
    result = validate_override(
        port if port is not None else state(),
        SUBJECT,
        base,
        list(changes),
        ctx if ctx is not None else context(),
    )
    RESULT_SCHEMA.validate(result.validation_result())
    return result


def codes(result: Any) -> list[str]:
    return [v.constraint_type_code for v in result.violations]


def test_unchanged_option_is_valid() -> None:
    result = run(Change("PILOT", override_pilot_user_id=PILOT))

    assert result.outcome == "VALID"
    assert result.validation_result() == {
        "validation_type": "OVERRIDE",
        "subject_id": SUBJECT,
        "valid": True,
        "violations": [],
    }


# --- BERTH ------------------------------------------------------------------------------------


def test_berth_valid() -> None:
    result = run(Change("BERTH", override_berth_id=OTHER_BERTH))

    assert result.outcome == "VALID"
    assert result.option.berth_id == OTHER_BERTH


def test_berth_too_short_for_loa() -> None:
    port = state(berths=(berth(BERTH), berth(OTHER_BERTH, max_vessel_loa=150)))
    result = run(Change("BERTH", override_berth_id=OTHER_BERTH), port=port)

    assert codes(result) == ["MAX_LOA"]
    violation = result.violations[0]
    assert violation.kind is Kind.STRUCTURAL
    assert violation.is_hard_safety_limit is False
    assert violation.message_key == "validation.berth.loa_exceeded"
    assert violation.change_index == 0


def test_berth_draft_uses_the_ct13_example_key() -> None:
    port = state(berths=(berth(BERTH), berth(OTHER_BERTH, water_depth=9)))
    result = run(Change("BERTH", override_berth_id=OTHER_BERTH), port=port)

    assert codes(result) == ["MAX_DRAFT"]
    assert result.violations[0].message_key == "validation.berth.draft_exceeded"


def test_berth_occupied_by_another_pending_option_one() -> None:
    hold = PendingHold(
        ResourceKind.BERTH, OTHER_BERTH, T0, T0 + 3 * HOUR, 77, 5, "PENDING_REVIEW", 7, 1
    )
    result = run(Change("BERTH", override_berth_id=OTHER_BERTH), port=state(pending_holds=(hold,)))

    assert codes(result) == ["BERTH_OCCUPIED"]
    assert result.violations[0].change_index == 0


def test_own_recommendation_holds_are_ignored() -> None:
    own = PendingHold(
        ResourceKind.BERTH, OTHER_BERTH, T0, T0 + 6 * HOUR, REQUEST, 5, "PENDING_REVIEW", 7, 1
    )
    result = run(Change("BERTH", override_berth_id=OTHER_BERTH), port=state(pending_holds=(own,)))

    assert result.outcome == "VALID"


# --- PILOT ------------------------------------------------------------------------------------


def test_pilot_valid() -> None:
    assert run(Change("PILOT", override_pilot_user_id=OTHER_PILOT)).outcome == "VALID"


def test_pilot_off_shift() -> None:
    shifts = (shift(PILOT), Shift(OTHER_PILOT, 9, T0 + 8 * HOUR, T0 + 16 * HOUR, True))
    result = run(
        Change("PILOT", override_pilot_user_id=OTHER_PILOT), port=state(pilot_shifts=shifts)
    )

    assert codes(result) == ["PILOT_UNAVAILABLE"]
    assert result.violations[0].message_key == "validation.pilot.unavailable"
    assert result.violations[0].change_index == 0


def test_pilot_rank_too_low() -> None:
    port = state(pilots=(pilot(PILOT), pilot(OTHER_PILOT, rank="THIRD")))
    result = run(Change("PILOT", override_pilot_user_id=OTHER_PILOT), port=port)

    assert codes(result) == ["PILOT_RANK_LIMIT"]
    assert result.violations[0].change_index == 0


# --- TUG --------------------------------------------------------------------------------------


def test_tug_replaced_valid() -> None:
    result = run(Change("TUG", original_tugboat_id=TUG_B, override_tugboat_id=TUG_C))

    assert result.outcome == "VALID"
    assert result.option.tug_ids == (TUG_A, TUG_C)


def test_tug_replaced_by_one_in_maintenance() -> None:
    port = state(tugs=(tug(TUG_A), tug(TUG_B), tug(TUG_C, status="MAINTENANCE")))
    result = run(Change("TUG", original_tugboat_id=TUG_B, override_tugboat_id=TUG_C), port=port)

    assert codes(result) == ["TUG_UNAVAILABLE"]
    assert result.violations[0].change_index == 0


def test_tug_removed_below_n_min_comes_from_the_combination() -> None:
    result = run(Change("TUG", original_tugboat_id=TUG_B, override_tugboat_id=None))

    assert codes(result) == ["TUG_COUNT"]
    assert result.violations[0].message_key == "validation.tug.count_below_minimum"
    assert result.violations[0].change_index is None


def test_tug_added_valid() -> None:
    result = run(Change("TUG", original_tugboat_id=None, override_tugboat_id=TUG_C))

    assert result.outcome == "VALID"
    assert result.option.tug_ids == (TUG_A, TUG_B, TUG_C)


@pytest.mark.parametrize(
    "change",
    [
        Change("TUG", original_tugboat_id=TUG_C, override_tugboat_id=TUG_A),  # TUG_C not in option
        Change("TUG", original_tugboat_id=None, override_tugboat_id=TUG_A),  # already there
        Change("TUG"),
        Change("BERTH"),
        Change("SPEED", override_berth_id=1),
    ],
)
def test_changes_that_do_not_fit_the_option_are_refused(change: Change) -> None:
    with pytest.raises(OverrideMismatchError):
        apply_changes(BASE, [change])


# --- START_TIME ---------------------------------------------------------------------------------


def test_start_time_valid_keeps_the_duration() -> None:
    result = run(Change("START_TIME", override_start=T0 + 2 * HOUR))

    assert result.outcome == "VALID"
    assert (result.option.start, result.option.end) == (T0 + 2 * HOUR, T0 + 6 * HOUR)


def test_start_time_outside_the_window() -> None:
    result = run(Change("START_TIME", override_start=T0 + 7 * HOUR))

    assert codes(result) == ["ENTRY_WINDOW"]
    assert result.violations[0].message_key == "validation.start.outside_entry_window"
    assert result.violations[0].change_index == 0


def test_start_at_the_window_end_is_outside_half_open() -> None:
    assert codes(run(Change("START_TIME", override_start=T0 + 6 * HOUR))) == ["ENTRY_WINDOW"]
    assert run(Change("START_TIME", override_start=T0)).outcome == "VALID"


# --- combinations and SAFETY --------------------------------------------------------------------


def test_berth_and_start_validated_together() -> None:
    hold = PendingHold(
        ResourceKind.BERTH, OTHER_BERTH, T0, T0 + 5 * HOUR, 77, 5, "PENDING_REVIEW", 7, 1
    )
    port = state(pending_holds=(hold,))
    move = Change("BERTH", override_berth_id=OTHER_BERTH)

    alone = run(move, port=port)
    assert codes(alone) == ["BERTH_OCCUPIED"]
    assert alone.violations[0].change_index == 0  # the one BERTH change

    later = run(move, Change("START_TIME", override_start=T0 + 5 * HOUR), port=port)
    assert later.outcome == "VALID"


def test_safety_limit_on_the_new_berth() -> None:
    narrow = limit(SYN_MAX_BEAM, "25.00", berth_id=OTHER_BERTH)
    result = run(
        Change("BERTH", override_berth_id=OTHER_BERTH), port=state(safety_constraints=(narrow,))
    )

    assert codes(result) == [SYN_MAX_BEAM.code]
    violation = result.violations[0]
    assert violation.kind is Kind.SAFETY
    assert violation.is_hard_safety_limit is SYN_MAX_BEAM.is_hard_safety_limit
    assert violation.message_key == "validation.safety.synthetic_max_beam_m"
    assert violation.change_index == 0
    payload = result.validation_result()
    assert payload["valid"] is False
    assert payload["violations"][0]["manifest_entry_id"] is None


def test_violations_are_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "MAX_VIOLATIONS", 1)
    port = state(berths=(berth(BERTH), berth(OTHER_BERTH, max_vessel_loa=150, water_depth=9)))
    result = run(Change("BERTH", override_berth_id=OTHER_BERTH), port=port)

    assert len(result.violations) == 1
    assert result.validation_result()["violations_truncated"] is True


def test_every_structural_code_has_a_message_key() -> None:
    from part2.filter import Code

    assert set(Code) <= set(module.MESSAGE_KEYS)
    assert all(len(k) <= 120 for k in module.MESSAGE_KEYS.values())


# --- payload parsing ----------------------------------------------------------------------------


def test_parse_changes_from_the_c05_payload() -> None:
    proposed = {
        "changes": [
            {"component_type": "BERTH", "override_berth_id": 14},
            {"component_type": "TUG", "original_tugboat_id": 7, "override_tugboat_id": 11},
            {"component_type": "PILOT", "override_pilot_user_id": 41},
            {"component_type": "START_TIME", "override_start": "2026-01-05T03:00:00Z"},
        ]
    }
    changes = parse_changes(proposed)

    assert changes[0] == Change("BERTH", override_berth_id=14)
    assert changes[1] == Change("TUG", original_tugboat_id=7, override_tugboat_id=11)
    assert changes[2] == Change("PILOT", override_pilot_user_id=41)
    assert changes[3].override_start == T0 + 3 * HOUR


def test_start_without_offset_is_refused() -> None:
    with pytest.raises(OverrideMismatchError, match="offset"):
        parse_changes(
            {"changes": [{"component_type": "START_TIME", "override_start": "2026-01-05T03:00:00"}]}
        )
