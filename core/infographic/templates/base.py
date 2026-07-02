"""
core/infographic/templates/base.py — Abstract base template.

Every template follows these design rules:
- Clear visual hierarchy: Title > Body > Metadata
- Consistent 8/16/24px spacing scale
- Intentional alignment (no accidental centering)
- Readability over decoration
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from PIL import Image, ImageDraw

from core.infographic.themes import Theme
from core.infographic.primitives import (
    CANVAS_W, CANVAS_H, S,
    gradient_bg, radial_glow, composite_layers, save_image, strip_emojis,
)
from core.infographic.layout import LayoutBox


class BaseTemplate(ABC):
    """Abstract infographic template."""

    name: str = "base"
    display_name: str = "Base Template"
    required_fields: list[str] = []

    def validate_data(self, data: dict[str, Any]) -> bool:
        """Check that all required fields are present and non-empty."""
        for field in self.required_fields:
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                return False
            if isinstance(val, list) and len(val) == 0:
                return False
        return True

    def render(
        self,
        data: dict[str, Any],
        theme: Theme,
        save_path: str,
        debug: bool = False,
    ) -> str:
        """
        Render the infographic. Returns the saved file path.

        Steps:
        1. Create canvas with themed gradient background
        2. Create RGBA overlay for glow effects
        3. Composite layers
        4. Call _draw_content() on the final image
        5. (Optional) Draw debug bounding boxes
        6. Save and return path
        """
        # 1. Base canvas
        img = Image.new("RGBA", (CANVAS_W, CANVAS_H))
        gradient_bg(img, theme.bg_top, theme.bg_bottom)

        # 2. Glow overlay (controlled by theme intensity)
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        self._draw_glows(odraw, theme)

        # 3. Composite
        img = composite_layers(img, overlay, blur=8)

        # 4. Draw content
        draw = ImageDraw.Draw(img)
        self._draw_content(draw, data, theme)

        # 5. Debug mode
        if debug:
            from core.infographic.layout import draw_debug_bounds
            regions = self._get_regions()
            if regions:
                # Need RGBA draw for debug
                debug_overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
                ddraw = ImageDraw.Draw(debug_overlay)
                draw_debug_bounds(ddraw, regions)
                img = composite_layers(img, debug_overlay, blur=0)

        # 6. Save
        return save_image(img.convert("RGB"), save_path)

    def _draw_glows(self, draw: ImageDraw.ImageDraw, theme: Theme) -> None:
        """Default glow placement — templates can override."""
        intensity = theme.glow_intensity
        if intensity <= 0:
            return
        radial_glow(draw, CANVAS_W // 4, CANVAS_H // 2, S(300),
                     theme.accent_primary, intensity)
        radial_glow(draw, 3 * CANVAS_W // 4, CANVAS_H // 3, S(250),
                     theme.accent_secondary, int(intensity * 0.7))

    @abstractmethod
    def _draw_content(
        self,
        draw: ImageDraw.ImageDraw,
        data: dict[str, Any],
        theme: Theme,
    ) -> None:
        """Draw the template-specific content onto the canvas."""
        ...

    def _get_regions(self) -> dict[str, LayoutBox] | None:
        """Return layout regions for debug visualization. Override in subclass."""
        return None

    @staticmethod
    def clean(text: str | None, default: str = "") -> str:
        """Strip emojis and provide fallback."""
        if not text:
            return default
        return strip_emojis(text).strip()
