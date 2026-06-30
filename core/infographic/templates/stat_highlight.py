"""Template 5: Stat Highlight — Giant stat number with context."""

from __future__ import annotations
from typing import Any
from PIL import ImageDraw

from core.infographic.themes import Theme
from core.infographic.primitives import (
    CANVAS_W, CANVAS_H, S, load_font,
    glass_panel, accent_bar, divider_line, tag_badge, progress_bar,
)
from core.infographic.layout import (
    LayoutBox, compute_regions, draw_text_aligned, draw_wrapped_text,
    measure_text, auto_font_size,
)
from core.infographic.templates.base import BaseTemplate


class StatHighlight(BaseTemplate):
    name = "stat_highlight"
    display_name = "Stat Highlight"
    required_fields = ["stat"]

    _LAYOUT = {
        "tag":     {"x": 0.06, "y": 0.05, "w": 0.88, "h": 0.06, "padding": 0.01},
        "stat":    {"x": 0.06, "y": 0.14, "w": 0.88, "h": 0.35, "padding": 0.02, "align": "center"},
        "label":   {"x": 0.06, "y": 0.50, "w": 0.88, "h": 0.08, "padding": 0.01, "align": "center"},
        "divider": {"x": 0.15, "y": 0.60, "w": 0.70, "h": 0.01, "padding": 0.0},
        "body":    {"x": 0.08, "y": 0.64, "w": 0.84, "h": 0.28, "padding": 0.02, "align": "center"},
    }

    def _get_regions(self):
        return compute_regions(CANVAS_W, CANVAS_H, self._LAYOUT)

    def _draw_content(self, draw: ImageDraw.ImageDraw, data: dict[str, Any], theme: Theme) -> None:
        regions = self._get_regions()

        stat = self.clean(data.get("stat"), "0")
        label = self.clean(data.get("label"), "")
        body = self.clean(data.get("body"), "")
        tag = self.clean(data.get("tag"), "#Stats")

        # Tag badge
        r_tag = regions["tag"]
        f_tag = load_font("Inter-SemiBold.ttf", S(16))
        tag_badge(draw, r_tag.inner_x, r_tag.inner_y, tag,
                  (*theme.accent_primary, 180), theme.text_primary, f_tag)

        # Giant stat — auto-sized to fill the region
        r_stat = regions["stat"]
        f_stat = auto_font_size(
            draw, stat, "Inter-Bold.ttf",
            r_stat.inner_w, r_stat.inner_h,
            min_size=S(48), max_size=S(120),
        )
        draw_text_aligned(
            draw, stat, r_stat.inner_x, r_stat.inner_y + S(10),
            f_stat, theme.accent_primary,
            align="center", region_width=r_stat.inner_w,
        )

        # Label below stat
        if label:
            r_label = regions["label"]
            f_label = load_font("Inter-SemiBold.ttf", S(22))
            draw_text_aligned(
                draw, label, r_label.inner_x, r_label.inner_y,
                f_label, theme.text_secondary,
                align="center", region_width=r_label.inner_w,
            )

        # Divider
        r_div = regions["divider"]
        divider_line(draw, r_div.x, r_div.y, r_div.x + r_div.w,
                     (*theme.accent_primary, 60), width=S(2))

        # Body text
        if body:
            r_body = regions["body"]
            f_body = load_font("Inter-Regular.ttf", S(20))
            draw_wrapped_text(draw, body, r_body, f_body,
                              theme.text_secondary, max_lines=5)

        # Optional progress bar
        progress = data.get("progress")
        if progress is not None:
            try:
                pval = float(progress)
                bar_y = CANVAS_H - S(60)
                bar_w = int(CANVAS_W * 0.6)
                bar_x = (CANVAS_W - bar_w) // 2
                progress_bar(
                    draw, bar_x, bar_y, bar_w, S(12), pval,
                    bg_color=(*theme.text_muted, 30),
                    fill_color=theme.accent_primary,
                )
            except (ValueError, TypeError):
                pass
