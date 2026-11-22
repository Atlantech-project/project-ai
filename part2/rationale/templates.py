"""B6 rationale templates (AI-057): CT-18 §6 placeholder grammar, active catalogue, renderer.

CT-18 §6: the worker writes `rationale_template_id` (one code + version row) and `rationale_params`;
the Backend renders `template_text` at display time. `render` exists so every seeded template can be
checked and rendered in tests exactly as the Backend will fill it; the worker never stores text.

Template texts come only from the `rationale_templates` seed (AI-009, INT-Q4). None is written here.
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final

from common.config import ConfigurationError

# CT-18 §6: the only placeholders a template may use. "A placeholder outside this list is a seed
# error."
PLACEHOLDERS: Final = frozenset(
    {
        "vessel",
        "berth",
        "terminal",
        "etb",
        "waiting_minutes",
        "delta_minutes",
        "tug_count",
        "window_start",
        "window_end",
        "constraint",
        "value",
        "limit",
        "unit",
    }
)

_BRACED: Final = re.compile(r"\{([^{}]*)\}")


class TemplateError(ConfigurationError):
    """A template row the worker cannot use: a seed or configuration error (CT-08
    `CONFIGURATION_ERROR`), never a reason to write free text instead."""


def placeholders(text: str) -> tuple[str, ...]:
    """The CT-18 placeholders of a template text, in first-use order, each once.

    A name outside CT-18 §6, an empty `{}` or an unpaired brace is a `TemplateError`.
    """
    names: list[str] = []
    for match in _BRACED.finditer(text):
        name = match.group(1)
        if name not in PLACEHOLDERS:
            raise TemplateError(f"placeholder {{{name}}} is not in the CT-18 §6 list")
        if name not in names:
            names.append(name)
    rest = _BRACED.sub("", text)
    if "{" in rest or "}" in rest:
        raise TemplateError(f"unpaired brace in template text: {text!r}")
    return tuple(names)


@dataclass(frozen=True)
class RationaleTemplate:
    """One `rationale_templates` row."""

    id: int
    code: str
    version: int
    template_text: str
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.version < 1:  # chk_rt_version
            raise TemplateError(f"template {self.code}: version must be positive: {self.version}")
        if not self.template_text.strip():
            raise TemplateError(f"template {self.code} v{self.version} has no text")
        placeholders(self.template_text)

    @property
    def placeholders(self) -> tuple[str, ...]:
        return placeholders(self.template_text)


class TemplateCatalog:
    """The active templates by code: one active version per code (backlog guidance; `active_code`).

    Inactive rows are kept out: old recommendations keep their template id, new ones never use them.
    """

    def __init__(self, rows: Iterable[RationaleTemplate]) -> None:
        active: dict[str, RationaleTemplate] = {}
        for row in rows:
            if not row.is_active:
                continue
            if row.code in active:
                raise TemplateError(
                    f"template {row.code} has two active versions: "
                    f"{active[row.code].version} and {row.version}"
                )
            active[row.code] = row
        self._active = active

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(sorted(self._active))

    def require(self, code: str) -> RationaleTemplate:
        try:
            return self._active[code]
        except KeyError:
            raise TemplateError(f"no active rationale template with code {code}") from None


EMPTY_CATALOG: Final = TemplateCatalog(())


def render(template: RationaleTemplate, params: Mapping[str, object]) -> str:
    """The text the Backend shows: every placeholder replaced by its parameter's `str` value.

    A placeholder without a parameter is a `TemplateError`; extra parameters are ignored.
    """
    missing = [name for name in template.placeholders if name not in params]
    if missing:
        raise TemplateError(
            f"template {template.code} v{template.version} needs {', '.join(missing)}"
        )
    return _BRACED.sub(lambda match: str(params[match.group(1)]), template.template_text)
