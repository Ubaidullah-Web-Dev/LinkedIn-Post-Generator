"""Template 7: Minimal Card — Clean fallback for any content type."""

from __future__ import annotations
from typing import Any
from PIL import ImageDraw

from core.infographic.themes import Theme
from core.infographic.primitives import (
    CANVAS_W, CANVAS_H, S, load_font,
    glass_panel, accent_bar, divider_line, tag_badge,
)
from core.infographic.layout import (
    LayoutBox, compute_regions, draw_wrapped_text, draw_text_aligned,
    auto_font_size,
)
from core.infographic.templates.base import BaseTemplate


class MinimalCard(BaseTemplate):
    name = "minimal_card"
    display_name = "Minimal Card"
    required_fields = ["title"]

    _LAYOUT = {
        "tag":    {"x": 0.08, "y": 0.08, "w": 0.84, "h": 0.06, "padding": 0.01},
        "title":  {"x": 0.08, "y": 0.18, "w": 0.84, "h": 0.30, "padding": 0.02},
        "divider":{"x": 0.08, "y": 0.50, "w": 0.84, "h": 0.01, "padding": 0.0},
        "body":   {"x": 0.08, "y": 0.54, "w": 0.84, "h": 0.36, "padding": 0.02, "align": "left"},
    }

    def _get_regions(self):
        return compute_regions(CANVAS_W, CANVAS_H, self._LAYOUT)

    def _draw_glows(self, draw, theme):
        """Minimal glow — subtler than other templates."""
        from core.infographic.primitives import radial_glow
        intensity = max(theme.glow_intensity // 2, 10)
        radial_glow(draw, CANVAS_W // 3, CANVAS_H, S(350),
                     theme.accent_primary, intensity)

    def _draw_content(self, draw: ImageDraw.ImageDraw, data: dict[str, Any], theme: Theme) -> None:
        regions = self._get_regions()

        title = self.clean(data.get("title"), "Untitled")
        body = self.clean(data.get("body"), "")
        tag = self.clean(data.get("tag"), "#Dev")

        # Central glass card
        card_pad = S(40)
        glass_panel(
            draw,
            (card_pad, card_pad, CANVAS_W - card_pad, CANVAS_H - card_pad),
            radius=S(20), fill=theme.card_fill, border=theme.card_border,
        )

        # Tag
        r_tag = regions["tag"]
        f_tag = load_font("Inter-SemiBold.ttf", S(16))
        tag_badge(draw, r_tag.inner_x, r_tag.inner_y, tag,
                  (*theme.accent_primary, 160), theme.text_primary, f_tag)

        # Title — auto-sized for impact
        r_title = regions["title"]
        f_title = auto_font_size(
            draw, title, "Inter-Bold.ttf",
            r_title.inner_w, r_title.inner_h,
            min_size=S(24), max_size=S(52),
        )
        # Accent bar
        accent_bar(draw, r_title.inner_x - S(12), r_title.inner_y,
                   r_title.inner_h, theme.accent_primary, width=S(5))

        draw_wrapped_text(draw, title, r_title, f_title,
                          theme.text_primary, max_lines=4)

        # Divider
        r_div = regions["divider"]
        divider_line(draw, r_div.x, r_div.y, r_div.x + r_div.w,
                     (*theme.accent_primary, 50), width=S(2))

        # Body
        if body:
            r_body = regions["body"]
            f_body = load_font("Inter-Regular.ttf", S(20))
            draw_wrapped_text(draw, body, r_body, f_body,
                              theme.text_secondary, max_lines=7)
