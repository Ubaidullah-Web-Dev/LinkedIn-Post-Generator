"""Template 4: Step Flow — Horizontal flow with numbered steps and arrows."""

from __future__ import annotations
from typing import Any
from PIL import ImageDraw

from core.infographic.themes import Theme
from core.infographic.primitives import (
    CANVAS_W, CANVAS_H, S, load_font,
    glass_panel, number_badge, arrow_right, accent_bar, tag_badge,
)
from core.infographic.layout import (
    LayoutBox, wrap_text, measure_text, measure_line_height,
    draw_text_aligned,
)
from core.infographic.templates.base import BaseTemplate


class StepFlow(BaseTemplate):
    name = "step_flow"
    display_name = "Step-by-Step Flow"
    required_fields = ["title", "steps"]

    def _draw_content(self, draw: ImageDraw.ImageDraw, data: dict[str, Any], theme: Theme) -> None:
        f_title = load_font("Inter-Bold.ttf", S(38))
        f_sub = load_font("Inter-Regular.ttf", S(18))
        f_step_num = load_font("Inter-Bold.ttf", S(22))
        f_step_title = load_font("Inter-Bold.ttf", S(18))
        f_step_body = load_font("Inter-Regular.ttf", S(15))

        title = self.clean(data.get("title"), "Steps")
        subtitle = self.clean(data.get("subtitle"), "")
        steps = data.get("steps", [])
        if isinstance(steps, list):
            steps = [self.clean(s) for s in steps if s]

        # Limit steps to what fits horizontally
        max_steps = min(len(steps), 5)
        steps = steps[:max_steps]
        if not steps:
            steps = ["Step 1"]

        # Header
        PAD = S(50)
        y = S(30)
        accent_bar(draw, PAD, y, S(50), theme.accent_primary, width=S(6))
        draw.text((PAD + S(20), y + S(4)), title, font=f_title, fill=theme.text_primary)
        y += S(56)
        if subtitle:
            draw.text((PAD + S(20), y), subtitle, font=f_sub, fill=theme.text_muted)
            y += S(32)

        # Flow area
        flow_y = y + S(30)
        flow_h = CANVAS_H - flow_y - S(40)
        avail_w = CANVAS_W - PAD * 2

        # Calculate card dimensions
        n = len(steps)
        arrow_space = S(40)
        total_arrow_space = (n - 1) * arrow_space
        card_w = min((avail_w - total_arrow_space) // n, S(350))
        total_w = card_w * n + total_arrow_space
        start_x = PAD + (avail_w - total_w) // 2

        accents = theme.accent_palette
        badge_r = S(22)

        for i, step in enumerate(steps):
            col = accents[i % len(accents)]
            cx = start_x + i * (card_w + arrow_space)

            # Glass card
            glass_panel(
                draw,
                (cx, flow_y, cx + card_w, flow_y + flow_h),
                radius=S(14), fill=theme.card_fill, border=theme.card_border,
            )

            # Number badge at top center
            badge_cx = cx + card_w // 2
            badge_cy = flow_y + S(30)
            number_badge(draw, badge_cx, badge_cy, badge_r, i + 1, col,
                         theme.text_primary, f_step_num)

            # Step text
            hdr, body = self._split_step(step)
            text_x = cx + S(16)
            text_w = card_w - S(32)
            text_y = badge_cy + badge_r + S(16)

            # Title
            for line in wrap_text(draw, hdr, f_step_title, text_w, max_lines=2):
                draw_text_aligned(draw, line, text_x, text_y, f_step_title,
                                  theme.text_primary, "center", text_w)
                text_y += int(measure_line_height(draw, f_step_title) * 1.3)

            # Body
            if body:
                text_y += S(8)
                for line in wrap_text(draw, body, f_step_body, text_w, max_lines=3):
                    draw_text_aligned(draw, line, text_x, text_y, f_step_body,
                                      theme.text_secondary, "center", text_w)
                    text_y += int(measure_line_height(draw, f_step_body) * 1.3)

            # Arrow between cards
            if i < n - 1:
                arrow_x = cx + card_w + S(6)
                arrow_y = flow_y + flow_h // 2
                arrow_right(draw, arrow_x, arrow_y, arrow_space - S(12),
                            (*theme.text_muted, 120), thickness=S(2), head_size=S(10))

    @staticmethod
    def _split_step(step: str) -> tuple[str, str]:
        if ":" in step and step.index(":") < 40:
            hdr, body = step.split(":", 1)
            return hdr.strip(), body.strip()
        return step, ""
