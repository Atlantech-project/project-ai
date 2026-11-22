"""B6 template rationale and rationale factors (AI-057).

Every port value is SYNTHETIC (B2 builders). Template texts here are test fixtures marked
`SYNTHETIC`: they exercise the engine and are not proposals for the seed (INT-Q4 supplies those).
"""

import json
import random
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from part2.outcomes import SolveOutcome, handle_solve
from part2.rationale import (
    OPTION_PLACEHOLDERS,
    PLACEHOLDERS,
    FactorType,
    OptionRationale,
    RationaleError,
    RationaleTemplate,
    TemplateCatalog,
    TemplateError,
    build_rationales,
    objective_factors,
    option_params,
    placeholders,
    render,
)
from part2.solver import TERM_RESOURCE_COST, TERM_WAITING_TIME, TermValue
from part2.state.model import PortState
from tests.unit.part2.filter.builders import (
    BERTH,
    HOUR,
    OTHER_BERTH,
    OTHER_REQUEST,
    OTHER_TERMINAL,
    REQUEST,
    T0,
    berth,
    cargo,
    context,
    request,
    window,
)
from tests.unit.part2.solver.test_cpsat import (
    FOUR_HOURS,
    SETTINGS,
    random_instance,
    requirements,
    two_requests,
)
from tests.unit.part2.test_outcomes import timed_out

SEED_SPEC = (
    Path(__file__).resolve().parents[4] / "docs" / "drafts" / "ai-payloads" / "seed-spec.json"
)
SAMPLE: dict[str, object] = {
    "vessel": "SYNTHETIC VESSEL",
    "berth": "B11",
    "etb": "2026-01-05T00:00:00Z",
    "waiting_minutes": 0,
    "tug_count": 2,
    "window_start": "2026-01-05T00:00:00Z",
    "window_end": "2026-01-05T06:00:00Z",
}
FULL = "SYNTHETIC {vessel} at {berth} from {etb}, {waiting_minutes} min, {tug_count} tugs."


def template(text: str = FULL, code: str = "SYNTHETIC_BEST", **changes: Any) -> RationaleTemplate:
    return replace(RationaleTemplate(7, code, 1, text), **changes)


def solved(port: PortState | None = None, ids: tuple[int, ...] = (REQUEST,)) -> SolveOutcome:
    return handle_solve(port or two_requests(), ids, context(), FOUR_HOURS, SETTINGS)


def fifo(port: PortState | None = None) -> SolveOutcome:
    return handle_solve(
        port or two_requests(), [REQUEST], context(), FOUR_HOURS, SETTINGS, solve_fn=timed_out
    )


def always(code: str) -> Any:
    return lambda _source, _request, _option: code


# --- placeholders and templates (CT-18 §6) -----------------------------------------------------


def test_placeholders_are_read_in_first_use_order_once() -> None:
    assert placeholders("{berth} for {vessel}, again {berth}") == ("berth", "vessel")
    assert placeholders("No placeholder.") == ()


def test_every_ct18_placeholder_is_accepted() -> None:
    text = " ".join(f"{{{name}}}" for name in sorted(PLACEHOLDERS))
    assert set(placeholders(text)) == PLACEHOLDERS
    assert len(PLACEHOLDERS) == 13


@pytest.mark.parametrize(
    "text", ["{vessel_name}", "{}", "{Vessel}", "open { brace", "close } brace", "{{vessel}}"]
)
def test_a_placeholder_outside_ct18_or_a_stray_brace_is_a_seed_error(text: str) -> None:
    with pytest.raises(TemplateError):
        placeholders(text)


@pytest.mark.parametrize(
    ("changes", "message"),
    [({"version": 0}, "version"), ({"template_text": "  "}, "no text")],
)
def test_template_row_checks(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(TemplateError, match=message):
        template(**changes)


def test_catalog_keeps_one_active_version_per_code() -> None:
    old = template(id=1, version=1, is_active=False)
    new = template(id=2, version=2)
    catalog = TemplateCatalog([old, new, template(id=3, code="SYNTHETIC_ALT")])

    assert catalog.require("SYNTHETIC_BEST") is new
    assert catalog.codes == ("SYNTHETIC_ALT", "SYNTHETIC_BEST")
    with pytest.raises(TemplateError, match="two active versions"):
        TemplateCatalog([template(id=1), template(id=2, version=2)])
    with pytest.raises(TemplateError, match="no active rationale template"):
        TemplateCatalog([old]).require("SYNTHETIC_BEST")


def test_render_fills_every_placeholder_and_needs_all_of_them() -> None:
    text = render(template(), SAMPLE)
    assert text == "SYNTHETIC SYNTHETIC VESSEL at B11 from 2026-01-05T00:00:00Z, 0 min, 2 tugs."
    with pytest.raises(TemplateError, match="needs tug_count"):
        render(template(), {k: v for k, v in SAMPLE.items() if k != "tug_count"})


def _seeded_templates() -> list[dict[str, Any]]:
    seed = json.loads(SEED_SPEC.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = seed["rationale_templates"]
    return rows


@pytest.mark.parametrize(
    "row", _seeded_templates(), ids=lambda row: f"{row['code']}-v{row['version']}"
)
def test_every_seeded_template_parses_and_renders(row: dict[str, Any]) -> None:
    """Rendering test per template (backlog criterion 2). Empty until INT-Q4 seeds the rows."""
    seeded = RationaleTemplate(1, row["code"], row["version"], row["template_text"])
    params = {name: f"<{name}>" for name in PLACEHOLDERS}
    text = render(seeded, params)
    assert "{" not in text and "}" not in text
    for name in seeded.placeholders:
        assert f"<{name}>" in text


def test_the_seed_has_no_template_yet() -> None:
    """Records the INT-Q4 gap: when rows arrive this fails, and the test above takes over."""
    assert _seeded_templates() == []


# --- factors (AI options) ----------------------------------------------------------------------


def test_objective_factors_are_score_shares_largest_first() -> None:
    terms = (
        TermValue(TERM_WAITING_TIME, Decimal(1) / 3, Decimal("1.0")),
        TermValue(TERM_RESOURCE_COST, Decimal("0.5"), Decimal("2.0")),
    )
    factors = objective_factors(terms)

    assert [(f.code, f.factor_value, f.display_order) for f in factors] == [
        (TERM_RESOURCE_COST, Decimal("1000.0000"), 1),
        (TERM_WAITING_TIME, Decimal("333.3333"), 2),
    ]
    assert {f.factor_type for f in factors} == {FactorType.OBJECTIVE_TERM}


def test_equal_shares_are_ordered_by_code() -> None:
    terms = (
        TermValue(TERM_WAITING_TIME, Decimal(0), Decimal(1)),
        TermValue(TERM_RESOURCE_COST, Decimal(0), Decimal(1)),
    )
    assert [f.code for f in objective_factors(terms)] == [TERM_RESOURCE_COST, TERM_WAITING_TIME]


def test_every_ai_option_has_a_factor_and_the_shares_make_its_score() -> None:
    outcome = solved()
    rationales = build_rationales(two_requests(), outcome)
    options = {(r.request_id, o.rank): o for r in outcome.requests for o in r.options}

    assert [(r.request_id, r.rank) for r in rationales] == sorted(options)
    for rationale in rationales:
        assert len(rationale.factors) >= 1
        planned = options[(rationale.request_id, rationale.rank)]
        assert planned.objective_score is not None
        total = sum((f.factor_value or Decimal(0) for f in rationale.factors), Decimal(0))
        # Each share is rounded to 4 decimals, the score once: at most half a unit each apart.
        assert abs(total - planned.objective_score) <= Decimal("0.0001")


@pytest.mark.parametrize("seed", range(6))
def test_every_ai_option_has_a_factor_on_random_instances(seed: int) -> None:
    rng = random.Random(seed)  # noqa: S311 (seeded test data)
    port, ids, times = random_instance(rng, requests=8, berths=2, tugs=4, pilots=2)
    outcome = handle_solve(port, ids, context(tug_requirements=requirements(ids)), times, SETTINGS)
    assert outcome.source == "AI"

    rationales = build_rationales(port, outcome)
    assert len(rationales) == sum(len(r.options) for r in outcome.requests)
    assert all(len(r.factors) >= 1 for r in rationales)


def test_ai_option_without_terms_is_refused() -> None:
    outcome = solved()
    first = outcome.requests[0]
    bare = replace(first, options=(replace(first.options[0], terms=()),))
    with pytest.raises(RationaleError, match="no objective terms"):
        build_rationales(two_requests(), replace(outcome, requests=(bare,)))


def test_unknown_source_is_refused() -> None:
    with pytest.raises(RationaleError, match="unknown recommendation source"):
        build_rationales(two_requests(), replace(solved(), source="MANUAL"))


# --- FIFO options (R11 (a) open) ---------------------------------------------------------------


def test_fifo_options_get_no_factor_until_r11_is_decided() -> None:
    outcome = fifo()
    assert outcome.source == "FIFO" and outcome.requests[0].options

    rationales = build_rationales(two_requests(), outcome)
    assert [r.factors for r in rationales] == [()]
    assert [(r.template, r.params) for r in rationales] == [(None, None)]


def test_fifo_options_take_the_same_placeholder_values() -> None:
    outcome = fifo()
    rationales = build_rationales(
        two_requests(), outcome, TemplateCatalog([template()]), always("SYNTHETIC_BEST")
    )
    option = outcome.requests[0].options[0].option
    assert rationales[0].params == {
        name: value
        for name, value in option_params(two_requests(), option).items()
        if name in template().placeholders
    }


# --- placeholder values and the template link --------------------------------------------------


def test_option_params_come_from_the_option_request_berth_and_window() -> None:
    late = replace(solved().requests[0].options[0].option, start=T0 + 90 * HOUR / 60 + HOUR)
    params = option_params(two_requests(), late)

    assert params == {
        "vessel": "SYNTHETIC VESSEL",
        "berth": f"B{late.berth_id}",
        "etb": "2026-01-05T02:30:00Z",
        "waiting_minutes": 150,
        "tug_count": len(late.tug_ids),
        "window_start": "2026-01-05T00:00:00Z",
        "window_end": "2026-01-05T06:00:00Z",
    }
    assert set(params) == OPTION_PLACEHOLDERS


def test_waiting_minutes_match_the_solver_waiting_term() -> None:
    outcome = solved()
    for planned in outcome.requests[0].options:
        params = option_params(two_requests(), planned.option)
        waiting = next(t for t in planned.terms if t.code == TERM_WAITING_TIME)
        # Window T0 to T0 + 6 h: start minutes 0 to 359, so the term is minutes / 359.
        assert waiting.normalised * 359 == params["waiting_minutes"]


def test_no_template_selected_leaves_link_and_params_null() -> None:
    rationales = build_rationales(two_requests(), solved())
    assert rationales
    assert all(r.template is None and r.params is None for r in rationales)
    assert all(r.rationale_template_id is None for r in rationales)


def test_selected_template_links_its_row_and_writes_only_its_placeholders() -> None:
    short = template("SYNTHETIC {vessel} at {berth}.")
    outcome = solved()
    rationales = build_rationales(
        two_requests(), outcome, TemplateCatalog([short]), always("SYNTHETIC_BEST")
    )
    first: OptionRationale = rationales[0]
    berth_id = outcome.requests[0].options[0].option.berth_id

    assert first.rationale_template_id == 7
    assert first.params == {"vessel": "SYNTHETIC VESSEL", "berth": f"B{berth_id}"}
    assert first.template is not None and first.params is not None
    assert render(first.template, first.params).startswith("SYNTHETIC SYNTHETIC VESSEL at B")


@pytest.mark.parametrize("name", sorted(PLACEHOLDERS - OPTION_PLACEHOLDERS))
def test_a_placeholder_the_worker_cannot_fill_is_refused(name: str) -> None:
    catalog = TemplateCatalog([template(f"SYNTHETIC {{{name}}}.")])
    with pytest.raises(TemplateError, match=f"uses {name}"):
        build_rationales(two_requests(), solved(), catalog, always("SYNTHETIC_BEST"))


def test_selecting_a_code_without_an_active_row_is_a_configuration_error() -> None:
    with pytest.raises(TemplateError, match="no active rationale template"):
        build_rationales(two_requests(), solved(), TemplateCatalog([]), always("SYNTHETIC_BEST"))


def test_an_option_without_its_window_is_refused() -> None:
    option = solved().requests[0].options[0].option
    with pytest.raises(RationaleError, match="windows=0"):
        option_params(two_requests(confirmed_windows=(window(OTHER_REQUEST),)), option)


# --- isolation (backlog criterion 3; Architecture §8.11) ---------------------------------------


def test_no_other_terminal_data_appears_in_an_option_rationale() -> None:
    port = two_requests(
        requests=(
            request(vessel_name="SYNTHETIC ALPHA"),
            request(
                request_id=OTHER_REQUEST,
                vessel_id=OTHER_REQUEST,
                requested_terminal_id=OTHER_TERMINAL,
                vessel_name="SYNTHETIC BRAVO",
            ),
        ),
        berths=(
            berth(BERTH, code="SYN-ALPHA-QUAY"),
            berth(OTHER_BERTH, code="SYN-BRAVO-QUAY", terminal_ids=frozenset({OTHER_TERMINAL})),
        ),
        confirmed_windows=(window(REQUEST), window(OTHER_REQUEST, T0 + HOUR, T0 + 7 * HOUR)),
        manifest_entries=(cargo("1.1", OTHER_REQUEST),),
    )
    outcome = solved(port, (REQUEST, OTHER_REQUEST))
    assert {r.request_id for r in outcome.requests if r.options} == {REQUEST, OTHER_REQUEST}
    catalog = TemplateCatalog([template(" ".join(f"{{{n}}}" for n in sorted(OPTION_PLACEHOLDERS)))])

    for rationale in build_rationales(port, outcome, catalog, always("SYNTHETIC_BEST")):
        assert rationale.params is not None
        dumped = json.dumps(rationale.params)
        own, other = ("ALPHA", "BRAVO") if rationale.request_id == REQUEST else ("BRAVO", "ALPHA")
        assert own in dumped and other not in dumped
        assert "1.1" not in dumped  # the other request's cargo never appears
        assert set(rationale.params) <= OPTION_PLACEHOLDERS
