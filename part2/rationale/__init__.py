"""B6 template rationale and rationale factors (AI-057)."""

from part2.rationale.build import (
    OPTION_PLACEHOLDERS,
    Factor,
    FactorType,
    OptionRationale,
    RationaleError,
    TemplateSelector,
    build_rationales,
    fifo_factors,
    no_template,
    objective_factors,
    option_params,
)
from part2.rationale.templates import (
    EMPTY_CATALOG,
    PLACEHOLDERS,
    RationaleTemplate,
    TemplateCatalog,
    TemplateError,
    placeholders,
    render,
)

__all__ = [
    "EMPTY_CATALOG",
    "OPTION_PLACEHOLDERS",
    "PLACEHOLDERS",
    "Factor",
    "FactorType",
    "OptionRationale",
    "RationaleError",
    "RationaleTemplate",
    "TemplateCatalog",
    "TemplateError",
    "TemplateSelector",
    "build_rationales",
    "fifo_factors",
    "no_template",
    "objective_factors",
    "option_params",
    "placeholders",
    "render",
]
