"""Template 6: Code Snippet — Terminal-style panel with syntax colors."""

from __future__ import annotations
from typing import Any
from PIL import ImageDraw

from core.infographic.themes import Theme
from core.infographic.primitives import (
    CANVAS_W, CANVAS_H, S, load_font,
    glass_panel, accent_bar, tag_badge,
)
from core.infographic.layout import (
    LayoutBox, compute_regions, wrap_text, measure_line_height,
    draw_text_aligned, draw_wrapped_text, auto_font_size,
)
from core.infographic.templates.base import BaseTemplate


class CodeSnippet(BaseTemplate):
    name = "code_snippet"
    display_name = "Code Snippet Card"
    required_fields = ["title"]

    _LAYOUT = {
        "header":   {"x": 0.04, "y": 0.03, "w": 0.55, "h": 0.40, "padding": 0.02},
        "terminal": {"x": 0.60, "y": 0.02, "w": 0.38, "h": 0.96, "padding": 0.02},
        "body":     {"x": 0.04, "y": 0.45, "w": 0.55, "h": 0.30, "padding": 0.02},
        "footer":   {"x": 0.04, "y": 0.80, "w": 0.55, "h": 0.16, "padding": 0.02},
    }

    def _get_regions(self):
        return compute_regions(CANVAS_W, CANVAS_H, self._LAYOUT)

    def _draw_content(self, draw: ImageDraw.ImageDraw, data: dict[str, Any], theme: Theme) -> None:
        regions = self._get_regions()
        r_hdr = regions["header"]
        r_term = regions["terminal"]
        r_body = regions["body"]
        r_footer = regions["footer"]

        title = self.clean(data.get("title"), "Code")
        body = self.clean(data.get("body"), "")
        tag = self.clean(data.get("tag"), "#Dev")
        code = data.get("code", [])

        # Fonts
        f_title = auto_font_size(draw, title, "Inter-Bold.ttf",
                                 r_hdr.inner_w, r_hdr.inner_h - S(40),
                                 min_size=S(28), max_size=S(46))
        f_body = load_font("Inter-Regular.ttf", S(20))
        f_code = load_font("Inter-Regular.ttf", S(15))
        f_tag = load_font("Inter-SemiBold.ttf", S(16))

        # Tag badge
        tag_badge(draw, r_hdr.inner_x, r_hdr.inner_y, tag,
                  (*theme.accent_primary, 180), theme.text_primary, f_tag)

        # Title
        title_y = r_hdr.inner_y + S(40)
        draw_wrapped_text(
            draw, title,
            LayoutBox(r_hdr.inner_x, title_y, r_hdr.inner_w, r_hdr.inner_h - S(40), padding=0),
            f_title, theme.text_primary, max_lines=3,
        )

        # Body
        if body:
            draw_wrapped_text(draw, body, r_body, f_body,
                              theme.text_secondary, max_lines=4)

        # Terminal panel
        glass_panel(
            draw,
            (r_term.x, r_term.y, r_term.x + r_term.w, r_term.y + r_term.h),
            radius=S(14),
            fill=(10, 15, 28, 220),
            border=(255, 255, 255, 35),
        )

        # Traffic light dots
        dots_y = r_term.y + S(16)
        for j, col in enumerate([(239, 68, 68), (245, 158, 11), (16, 185, 129)]):
            draw.ellipse([
                r_term.inner_x + S(j * 18), dots_y,
                r_term.inner_x + S(12 + j * 18), dots_y + S(12),
            ], fill=col)

        # Code lines
        code_y = dots_y + S(30)
        lh = int(measure_line_height(draw, f_code) * 1.5)
        max_code_y = r_term.y + r_term.h - S(16)

        # Generate default code if none provided
        if not code:
            code = self._default_code(tag, theme)

        for token_line in code:
            if code_y + lh > max_code_y:
                break
            if isinstance(token_line, str):
                # Plain text line
                draw.text((r_term.inner_x, code_y), token_line,
                          font=f_code, fill=theme.text_muted)
            elif isinstance(token_line, list):
                # List of (text, color_key) tuples
                tx = r_term.inner_x
                for token in token_line:
                    if isinstance(token, (list, tuple)) and len(token) == 2:
                        text, color = str(token[0]), self._resolve_color(token[1], theme)
                        draw.text((tx, code_y), text, font=f_code, fill=color)
                        tw, _ = draw.textbbox((0, 0), text, font=f_code)[2:4]
                        # Fix: textbbox returns (x0, y0, x2, y2), width = x2
                        bb = draw.textbbox((0, 0), text, font=f_code)
                        tx += bb[2] - bb[0]
                    elif isinstance(token, str):
                        draw.text((tx, code_y), token, font=f_code, fill=theme.text_muted)
                        bb = draw.textbbox((0, 0), token, font=f_code)
                        tx += bb[2] - bb[0]
            code_y += lh

        # Footer
        f_footer = load_font("Inter-Regular.ttf", S(14))
        draw.text((r_footer.inner_x, r_footer.inner_y + S(8)),
                  "// Built with passion", font=f_footer, fill=theme.text_muted)

    @staticmethod
    def _resolve_color(key: str, theme: Theme) -> tuple:
        """Resolve a semantic color key to an RGB tuple."""
        mapping = {
            "keyword": theme.accent_primary,
            "string": theme.color_success,
            "number": theme.accent_secondary,
            "comment": theme.text_muted,
            "type": theme.accent_secondary,
            "func": theme.accent_primary,
            "var": theme.text_primary,
            "op": theme.text_secondary,
        }
        return mapping.get(key, theme.text_muted)

    @staticmethod
    def _default_code(tag: str, theme: Theme) -> list:
        """Generate a default code snippet based on the tag."""
        topic = tag.strip("#") if tag else "Dev"
        return [
            [("const ", "keyword"), (f"create{topic}", "func"), (" = () => {{", "op")],
            [("  const ", "keyword"), ("config", "var"), (" = {", "op")],
            [("    name:", "var"), (f' "{topic}"', "string"), (",", "op")],
            [("    version:", "var"), (' "2.0"', "string"), (",", "op")],
            [("    optimized:", "var"), (" true", "number"), (",", "op")],
            [("  };", "op")],
            "",
            [("  return ", "keyword"), ("build", "func"), ("(config);", "op")],
            [("};", "op")],
            "",
            [("// Ship it!", "comment")],
        ]
