"""
core/infographic/templates — Template registry.

All templates register here and are discoverable by name.
"""

from core.infographic.templates.base import BaseTemplate
from core.infographic.templates.quote_card import QuoteCard
from core.infographic.templates.tips_list import TipsList
from core.infographic.templates.comparison import Comparison
from core.infographic.templates.step_flow import StepFlow
from core.infographic.templates.stat_highlight import StatHighlight
from core.infographic.templates.code_snippet import CodeSnippet
from core.infographic.templates.minimal_card import MinimalCard

# ── Template Registry ────────────────────────────────────────────────────────

_TEMPLATES: dict[str, BaseTemplate] = {}

def _register(*templates: BaseTemplate) -> None:
    for t in templates:
        _TEMPLATES[t.name] = t

_register(
    QuoteCard(),
    TipsList(),
    Comparison(),
    StepFlow(),
    StatHighlight(),
    CodeSnippet(),
    MinimalCard(),
)


def get_template(name: str) -> BaseTemplate:
    """Get a template by name. Falls back to MinimalCard."""
    return _TEMPLATES.get(name, _TEMPLATES["minimal_card"])


def list_templates() -> list[BaseTemplate]:
    """Return all registered templates."""
    return list(_TEMPLATES.values())


__all__ = [
    "BaseTemplate", "get_template", "list_templates",
    "QuoteCard", "TipsList", "Comparison", "StepFlow",
    "StatHighlight", "CodeSnippet", "MinimalCard",
]
