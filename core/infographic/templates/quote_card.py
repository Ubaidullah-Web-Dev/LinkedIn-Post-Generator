"""Template 1: Quote Card — Large centered quote with accent bar and attribution."""

from __future__ import annotations
from typing import Any
from PIL import ImageDraw

from core.infographic.themes import Theme
from core.infographic.primitives import CANVAS_W, CANVAS_H, S, load_font, glass_panel, accent_bar
from core.infographic.layout import (
    LayoutBox, compute_regions, draw_wrapped_text, draw_text_aligned,
    auto_font_size, wrap_text, measure_line_height,
)
from core.infographic.templates.base import BaseTemplate


class QuoteCard(BaseTemplate):
    name = "quote_card"
    display_name = "Quote Card"
    required_fields = ["quote"]

    _LAYOUT = {
        "badge":  {"x": 0.06, "y": 0.06, "w": 0.88, "h": 0.08, "padding": 0.01, "align": "left"},
        "quote":  {"x": 0.06, "y": 0.18, "w": 0.88, "h": 0.55, "padding": 0.03, "align": "left"},
        "author": {"x": 0.06, "y": 0.78, "w": 0.88, "h": 0.08, "padding": 0.01, "align": "right"},
        "footer": {"x": 0.06, "y": 0.88, "w": 0.88, "h": 0.08, "padding": 0.01, "align": "left"},
    }

    def _get_regions(self):
        return compute_regions(CANVAS_W, CANVAS_H, self._LAYOUT)

    def _draw_content(self, draw: ImageDraw.ImageDraw, data: dict[str, Any], theme: Theme) -> None:
        regions = self._get_regions()
        r_quote = regions["quote"]
        r_author = regions["author"]
        r_footer = regions["footer"]

        # Giant opening quotation mark
        f_quote_mark = load_font("Inter-Bold.ttf", S(120))
        draw.text(
            (r_quote.inner_x - S(8), r_quote.inner_y - S(40)),
            "\u201C", font=f_quote_mark,
            fill=(*theme.accent_primary, 80),
        )

        # Accent bar
        accent_bar(draw, r_quote.inner_x - S(16), r_quote.inner_y + S(10),
                   r_quote.inner_h - S(20), theme.accent_primary, width=S(5))

        # Quote text — auto-sized
        quote_text = self.clean(data.get("quote"), "Words of wisdom")
        f_quote = auto_font_size(
            draw, quote_text, "Inter-SemiBold.ttf",
            r_quote.inner_w - S(30), r_quote.inner_h,
            min_size=S(22), max_size=S(48),
        )
        quote_box = LayoutBox(
            r_quote.inner_x + S(20), r_quote.inner_y,
            r_quote.inner_w - S(30), r_quote.inner_h,
            padding=0, align="left",
        )
        draw_wrapped_text(draw, quote_text, quote_box, f_quote,
                          theme.text_primary, max_lines=6)

        # Author
        author = self.clean(data.get("author"), "")
        if author:
            f_author = load_font("Inter-Regular.ttf", S(20))
            draw_text_aligned(
                draw, f"— {author}", r_author.inner_x, r_author.inner_y,
                f_author, theme.text_secondary,
                align="right", region_width=r_author.inner_w,
            )

        # Footer tag
        tag = self.clean(data.get("tag"), "#Inspiration")
        f_tag = load_font("Inter-SemiBold.ttf", S(16))
        from core.infographic.primitives import tag_badge
        tag_badge(draw, r_footer.inner_x, r_footer.inner_y,
                  tag, (*theme.accent_primary, 180),
                  theme.text_primary, f_tag)
