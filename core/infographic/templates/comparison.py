"""Template 3: Comparison — Split glass panels with feature rows and ✓/✗."""

from __future__ import annotations
from typing import Any
from PIL import ImageDraw

from core.infographic.themes import Theme
from core.infographic.primitives import (
    CANVAS_W, CANVAS_H, S, load_font,
    glass_panel, divider_line, checkmark, crossmark, tag_badge,
    draw_rounded_rect_alpha, draw_line_alpha,
)
from core.infographic.layout import (
    LayoutBox, compute_regions, draw_text_aligned, measure_text,
    measure_line_height,
)
from core.infographic.templates.base import BaseTemplate


class Comparison(BaseTemplate):
    name = "comparison"
    display_name = "Comparison"
    required_fields = ["title"]

    def _draw_content(self, draw: ImageDraw.ImageDraw, data: dict[str, Any], theme: Theme) -> None:
        # Fonts
        f_title = load_font("Inter-Bold.ttf", S(36))
        f_sub = load_font("Inter-Regular.ttf", S(18))
        f_hdr = load_font("Inter-Bold.ttf", S(22))
        f_feat = load_font("Inter-Regular.ttf", S(18))
        f_score = load_font("Inter-SemiBold.ttf", S(16))

        title = self.clean(data.get("title"), "Comparison")
        subtitle = self.clean(data.get("subtitle"), "")
        left_name = self.clean(data.get("left", {}).get("name") if isinstance(data.get("left"), dict) else None, "A")
        right_name = self.clean(data.get("right", {}).get("name") if isinstance(data.get("right"), dict) else None, "B")
        rows = data.get("rows", [])[:7]

        # Layout metrics
        PAD = S(50)
        TOP = S(105)
        ROW_H = S(48)

        feat_x = PAD + S(16)
        feat_end = PAD + S(380)
        mid_x = feat_end + (CANVAS_W - PAD - feat_end) // 2
        la_x0, la_x1 = feat_end + S(10), mid_x - S(10)
        rb_x0, rb_x1 = mid_x + S(10), CANVAS_W - PAD - S(10)
        table_h = ROW_H * (len(rows) + 2) + S(16)

        # Glass container
        overlay_img = draw._image if hasattr(draw, '_image') else None
        glass_panel(
            draw,
            (PAD - S(8), TOP - S(8), CANVAS_W - PAD + S(8), TOP + table_h + S(8)),
            radius=S(16), fill=theme.card_fill, border=theme.card_border,
        )

        # Title + subtitle
        draw_text_aligned(draw, title, S(20), S(20), f_title,
                          theme.text_primary, "center", CANVAS_W)
        if subtitle:
            draw_text_aligned(draw, subtitle, S(20), S(64), f_sub,
                              theme.text_muted, "center", CANVAS_W)

        # Column headers
        draw.rounded_rectangle(
            [la_x0 - S(4), TOP + S(4), la_x1 + S(4), TOP + ROW_H - S(4)],
            radius=S(10), fill=(*theme.accent_primary, 80),
        )
        draw.rounded_rectangle(
            [rb_x0 - S(4), TOP + S(4), rb_x1 + S(4), TOP + ROW_H - S(4)],
            radius=S(10), fill=(*theme.accent_secondary, 80),
        )

        draw.text((feat_x, TOP + S(12)), "Feature", font=f_hdr, fill=theme.text_muted)
        draw_text_aligned(draw, left_name, la_x0, TOP + S(12), f_hdr,
                          theme.text_primary, "center", la_x1 - la_x0)
        draw_text_aligned(draw, right_name, rb_x0, TOP + S(12), f_hdr,
                          theme.text_primary, "center", rb_x1 - rb_x0)

        # Rows
        lw = rw = 0
        for i, row in enumerate(rows):
            y = TOP + (i + 1) * ROW_H + S(6)
            feat = self.clean(row.get("feature") if isinstance(row, dict) else str(row), "")
            lv = row.get("left", False) if isinstance(row, dict) else False
            rv = row.get("right", False) if isinstance(row, dict) else False

            if i % 2 == 0:
                img = draw._image if hasattr(draw, '_image') else None
                box = [PAD - S(4), y, CANVAS_W - PAD + S(4), y + ROW_H - S(2)]
                if img is not None and img.mode == "RGBA":
                    draw_rounded_rect_alpha(img, box, radius=S(6), fill=(255, 255, 255, 6))
                else:
                    draw.rounded_rectangle(box, radius=S(6), fill=(255, 255, 255, 6))

            divider_line(draw, PAD, y, CANVAS_W - PAD, (*theme.text_muted, 25))
            draw.text((feat_x, y + S(13)), feat, font=f_feat, fill=theme.text_primary)

            # Left value
            lcx = la_x0 + (la_x1 - la_x0) // 2
            lcy = y + ROW_H // 2
            if isinstance(lv, bool):
                if lv:
                    checkmark(draw, lcx, lcy, theme.color_success); lw += 1
                else:
                    crossmark(draw, lcx, lcy, theme.color_error)
            else:
                draw_text_aligned(draw, self.clean(str(lv)), y + S(10),
                                  la_x0, f_feat, theme.text_secondary, "center", la_x1 - la_x0)

            # Right value
            rcx = rb_x0 + (rb_x1 - rb_x0) // 2
            rcy = y + ROW_H // 2
            if isinstance(rv, bool):
                if rv:
                    checkmark(draw, rcx, rcy, theme.color_success); rw += 1
                else:
                    crossmark(draw, rcx, rcy, theme.color_error)
            else:
                draw_text_aligned(draw, self.clean(str(rv)), y + S(10),
                                  rb_x0, f_feat, theme.text_secondary, "center", rb_x1 - rb_x0)

        # Column dividers
        divider_line(draw, feat_end, TOP, feat_end, (*theme.text_muted, 30))
        img = draw._image if hasattr(draw, '_image') else None
        pts1 = [(feat_end, TOP), (feat_end, TOP + table_h)]
        pts2 = [(mid_x, TOP), (mid_x, TOP + table_h)]
        if img is not None and img.mode == "RGBA":
            draw_line_alpha(img, pts1, (*theme.text_muted, 30), width=S(1))
            draw_line_alpha(img, pts2, (*theme.text_muted, 30), width=S(1))
        else:
            draw.line(pts1, fill=(*theme.text_muted, 30), width=S(1))
            draw.line(pts2, fill=(*theme.text_muted, 30), width=S(1))

        # Scores
        n = max(len(rows), 1)
        sy = TOP + (len(rows) + 1) * ROW_H + S(12)
        divider_line(draw, PAD, sy - S(2), CANVAS_W - PAD, (*theme.text_muted, 30))
        draw_text_aligned(draw, f"{lw}/{n}", sy + S(4), la_x0, f_score,
                          theme.color_success if lw >= rw else theme.text_muted,
                          "center", la_x1 - la_x0)
        draw_text_aligned(draw, f"{rw}/{n}", sy + S(4), rb_x0, f_score,
                          theme.color_success if rw >= lw else theme.text_muted,
                          "center", rb_x1 - rb_x0)
