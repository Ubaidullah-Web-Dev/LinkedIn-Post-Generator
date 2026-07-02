"""Template 2: Tips List — Numbered circles with connecting lines."""

from __future__ import annotations
from typing import Any
from PIL import ImageDraw

from core.infographic.themes import Theme
from core.infographic.primitives import (
    CANVAS_W, CANVAS_H, S, load_font,
    glass_panel, accent_bar, number_badge, tag_badge, draw_line_alpha,
)
from core.infographic.layout import (
    LayoutBox, compute_regions, wrap_text, measure_text,
    measure_line_height, draw_text_aligned,
)
from core.infographic.templates.base import BaseTemplate


class TipsList(BaseTemplate):
    name = "tips_list"
    display_name = "Tips List"
    required_fields = ["title", "tips"]

    _LAYOUT = {
        "header": {"x": 0.05, "y": 0.03, "w": 0.9, "h": 0.14, "padding": 0.02},
        "body":   {"x": 0.05, "y": 0.18, "w": 0.9, "h": 0.78, "padding": 0.01},
    }

    def _get_regions(self):
        return compute_regions(CANVAS_W, CANVAS_H, self._LAYOUT)

    def _draw_content(self, draw: ImageDraw.ImageDraw, data: dict[str, Any], theme: Theme) -> None:
        regions = self._get_regions()
        r_hdr = regions["header"]
        r_body = regions["body"]

        title = self.clean(data.get("title"), "Tips")
        subtitle = self.clean(data.get("subtitle"), "")
        tips = data.get("tips", [])
        if isinstance(tips, list):
            tips = [self.clean(t) for t in tips if t]

        # Fonts
        f_title = load_font("Inter-Bold.ttf", S(40))
        f_sub = load_font("Inter-Regular.ttf", S(18))
        f_num = load_font("Inter-Bold.ttf", S(20))
        f_head = load_font("Inter-Bold.ttf", S(20))
        f_body = load_font("Inter-Regular.ttf", S(18))

        # Header: accent bar + title
        accent_bar(draw, r_hdr.inner_x, r_hdr.inner_y, S(50),
                   theme.accent_primary, width=S(6))
        draw.text((r_hdr.inner_x + S(20), r_hdr.inner_y + S(4)),
                  title, font=f_title, fill=theme.text_primary)

        if subtitle:
            draw.text((r_hdr.inner_x + S(20), r_hdr.inner_y + S(50)),
                      subtitle, font=f_sub, fill=theme.text_muted)

        # Compute available space and limit tips
        avail_h = r_body.inner_h
        badge_r = S(20)
        badge_cx = r_body.inner_x + S(24)
        text_x = r_body.inner_x + S(60)
        text_max_w = r_body.inner_w - S(70)
        lh_head = int(measure_line_height(draw, f_head) * 1.3)
        lh_body = int(measure_line_height(draw, f_body) * 1.3)

        # Pre-measure each tip's height
        tip_heights: list[int] = []
        for tip in tips:
            hdr, body = self._split_tip(tip)
            h = lh_head  # header line
            if body:
                body_lines = wrap_text(draw, body, f_body, text_max_w, max_lines=2)
                h += len(body_lines) * lh_body
            h = max(h, badge_r * 2 + S(8))  # at least badge height
            tip_heights.append(h + S(12))  # + spacing

        # Trim tips that won't fit
        total = 0
        visible = 0
        for th in tip_heights:
            if total + th > avail_h:
                break
            total += th
            visible += 1
        tips = tips[:max(visible, 1)]
        tip_heights = tip_heights[:max(visible, 1)]

        # Draw connecting line
        y = r_body.inner_y
        if len(tips) > 1:
            first_cy = y + badge_r + S(4)
            last_cy = y + sum(tip_heights[:-1]) + badge_r + S(4)
            img = draw._image if hasattr(draw, '_image') else None
            pts = [(badge_cx, first_cy + badge_r), (badge_cx, last_cy - badge_r)]
            if img is not None and img.mode == "RGBA":
                draw_line_alpha(img, pts, (*theme.text_muted, 60), width=S(2))
            else:
                draw.line(pts, fill=(*theme.text_muted, 60), width=S(2))

        # Draw each tip
        accents = theme.accent_palette
        for i, tip in enumerate(tips):
            col = accents[i % len(accents)]
            hdr, body = self._split_tip(tip)

            cy = y + badge_r + S(4)
            number_badge(draw, badge_cx, cy, badge_r, i + 1, col,
                         theme.text_primary, f_num)

            # Header text
            draw.text((text_x, y + S(4)), hdr, font=f_head, fill=theme.text_primary)
            ty = y + lh_head

            # Body text
            if body:
                for line in wrap_text(draw, body, f_body, text_max_w, max_lines=2):
                    draw.text((text_x, ty), line, font=f_body, fill=theme.text_secondary)
                    ty += lh_body

            y += tip_heights[i]

    @staticmethod
    def _split_tip(tip: str) -> tuple[str, str]:
        """Split a tip into header:body if colon exists early."""
        if ":" in tip and tip.index(":") < 50:
            hdr, body = tip.split(":", 1)
            return hdr.strip(), body.strip()
        return tip, ""
