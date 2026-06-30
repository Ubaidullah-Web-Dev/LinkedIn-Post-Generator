"""
core/infographic — Deterministic infographic engine.

The InfographicEngine is the single entry point for all image generation.
It orchestrates: content analysis → template selection → theme application → render → validate.

Usage:
    engine = InfographicEngine()
    path = engine.render(
        data={"title": "5 React Tips", "tips": ["Tip 1", "Tip 2"]},
        template="auto",     # or "tips_list", "comparison", etc.
        theme="random",      # or "cyberpunk_neon", "minimal_mono", etc.
        save_path="output.png",
    )
"""

from __future__ import annotations

import os
from typing import Any

from core.infographic.themes import Theme, get_theme, list_themes, random_theme, validate_theme
from core.infographic.templates import get_template, list_templates, BaseTemplate
from core.infographic.selector import select_template, suggest_template, SelectionResult
from core.infographic.validator import validate_image, ValidationResult
from core.constants import GENERATED_DIR
from core.logger import get_logger

logger = get_logger(__name__)


class InfographicEngine:
    """
    Main infographic rendering engine.

    Modes:
    - template="auto": content-aware selection
    - template="tips_list" etc: explicit template
    - theme="random": random theme each render
    - theme="cyberpunk_neon" etc: explicit theme
    """

    def render(
        self,
        data: dict[str, Any],
        template: str = "auto",
        theme: str = "random",
        save_path: str | None = None,
        debug: bool = False,
    ) -> str | None:
        """
        Render an infographic. Returns the saved file path, or None on failure.

        Args:
            data: structured data for the template (title, tips, etc.)
            template: template name or "auto" for content-aware selection
            theme: theme name or "random"
            save_path: output file path (auto-generated if None)
            debug: draw layout bounding boxes
        """
        # Resolve theme
        theme_obj = self._resolve_theme(theme)

        # Validate theme readability
        theme_warnings = validate_theme(theme_obj)
        for w in theme_warnings:
            logger.warning("Theme '%s': %s", theme_obj.name, w)

        # Resolve template
        tpl_obj, selection = self._resolve_template(template, data)

        logger.info(
            "Rendering: template=%s theme=%s confidence=%.0f%%",
            tpl_obj.name, theme_obj.name, selection.confidence * 100,
        )

        # Generate save path
        if not save_path:
            os.makedirs(str(GENERATED_DIR), exist_ok=True)
            from uuid import uuid4
            uid = uuid4().hex[:8]
            save_path = str(GENERATED_DIR / f"{tpl_obj.name}_{theme_obj.name}_{uid}.png")

        # Render
        try:
            result_path = tpl_obj.render(data, theme_obj, save_path, debug=debug)
        except Exception as e:
            logger.error("Render failed (%s/%s): %s", tpl_obj.name, theme_obj.name, e)
            # Fallback to minimal card
            if tpl_obj.name != "minimal_card":
                logger.info("Falling back to minimal_card")
                fallback = get_template("minimal_card")
                try:
                    result_path = fallback.render(data, theme_obj, save_path, debug=debug)
                except Exception as e2:
                    logger.error("Fallback render also failed: %s", e2)
                    return None
            else:
                return None

        # Validate output
        validation = validate_image(result_path)
        if not validation.passed:
            for err in validation.errors:
                logger.error("Validation error: %s", err)
        for w in validation.warnings:
            logger.warning("Validation warning: %s", w)

        return result_path

    def render_with_info(
        self,
        data: dict[str, Any],
        template: str = "auto",
        theme: str = "random",
        save_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Render and return detailed info about the result.
        Useful for UI display.
        """
        theme_obj = self._resolve_theme(theme)
        _, selection = self._resolve_template(template, data)

        path = self.render(data, template, theme, save_path)

        return {
            "path": path,
            "template": selection.template if template == "auto" else template,
            "theme": theme_obj.name,
            "confidence": selection.confidence,
            "reason": selection.reason,
            "success": path is not None,
        }

    def _resolve_theme(self, theme: str) -> Theme:
        """Resolve theme name to Theme object."""
        if theme == "random":
            return random_theme()
        return get_theme(theme)

    def _resolve_template(
        self, template: str, data: dict[str, Any]
    ) -> tuple[BaseTemplate, SelectionResult]:
        """Resolve template name to template object + selection info."""
        if template == "auto":
            # Use content-aware selection on available text fields
            text_for_analysis = " ".join(
                str(v) for v in data.values()
                if isinstance(v, str)
            )
            # Also check list fields
            for v in data.values():
                if isinstance(v, list):
                    text_for_analysis += " " + " ".join(str(i) for i in v)

            selection = select_template(text_for_analysis)
            tpl = get_template(selection.template)
            return tpl, selection
        else:
            tpl = get_template(template)
            return tpl, SelectionResult(template, 1.0, "Explicit selection")

    @staticmethod
    def available_templates() -> list[dict[str, str]]:
        """Return list of available templates with names."""
        return [
            {"name": t.name, "display_name": t.display_name}
            for t in list_templates()
        ]

    @staticmethod
    def available_themes() -> list[dict[str, str]]:
        """Return list of available themes with names."""
        return [
            {"name": t.name, "display_name": t.display_name}
            for t in list_themes()
        ]
