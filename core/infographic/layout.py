"""
core/infographic/layout.py — Layout engine with auto-scaling, smart wrapping,
overflow prevention, and debug mode.

Design contract:
- ZERO hardcoded pixel positions
- All dimensions computed from LayoutBox regions
- Progressive font reduction on overflow
- Truncation with ellipsis as last resort
- Debug mode draws bounding boxes
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PIL import ImageDraw, ImageFont

from core.infographic.primitives import load_font, S


# ── Layout Box ───────────────────────────────────────────────────────────────

@dataclass
class LayoutBox:
    """A rectangular region on the canvas for content placement."""
    x: int
    y: int
    w: int
    h: int
    padding: int = S(16)
    align: Literal["left", "center", "right"] = "left"

    @property
    def inner_x(self) -> int:
        return self.x + self.padding

    @property
    def inner_y(self) -> int:
        return self.y + self.padding

    @property
    def inner_w(self) -> int:
        return max(0, self.w - self.padding * 2)

    @property
    def inner_h(self) -> int:
        return max(0, self.h - self.padding * 2)

    @property
    def inner_right(self) -> int:
        return self.inner_x + self.inner_w

    @property
    def inner_bottom(self) -> int:
        return self.inner_y + self.inner_h

    @property
    def cx(self) -> int:
        """Horizontal center."""
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        """Vertical center."""
        return self.y + self.h // 2


# ── Text Measurement ────────────────────────────────────────────────────────

def measure_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
) -> tuple[int, int]:
    """Measure text dimensions (width, height)."""
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def measure_line_height(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont,
) -> int:
    """Get consistent line height for a font."""
    _, h = measure_text(draw, "Ayg|", font)
    return h


# ── Smart Text Wrapping ─────────────────────────────────────────────────────

def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int = 0,
    ellipsis: bool = True,
) -> list[str]:
    """
    Word-wrap text to fit within max_width pixels.

    Args:
        max_lines: if > 0, truncate to this many lines
        ellipsis: if True, add '…' when truncated
    """
    if not text:
        return []

    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        test = (current_line + " " + word).strip()
        tw, _ = measure_text(draw, test, font)
        if tw <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            # Check if single word is too wide — break it
            ww, _ = measure_text(draw, word, font)
            if ww > max_width:
                current_line = _truncate_word(draw, word, font, max_width)
            else:
                current_line = word

    if current_line:
        lines.append(current_line)

    # Truncate to max_lines
    if max_lines > 0 and len(lines) > max_lines:
        lines = lines[:max_lines]
        if ellipsis and lines:
            lines[-1] = _add_ellipsis(draw, lines[-1], font, max_width)

    return lines


def _truncate_word(
    draw: ImageDraw.ImageDraw,
    word: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> str:
    """Truncate a single word that's too wide."""
    for i in range(len(word), 0, -1):
        candidate = word[:i] + "…"
        tw, _ = measure_text(draw, candidate, font)
        if tw <= max_width:
            return candidate
    return "…"


def _add_ellipsis(
    draw: ImageDraw.ImageDraw,
    line: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> str:
    """Add ellipsis to a line if it exceeds max_width."""
    test = line + "…"
    tw, _ = measure_text(draw, test, font)
    if tw <= max_width:
        return test
    # Remove words until it fits
    words = line.split()
    while words:
        words.pop()
        candidate = " ".join(words) + "…"
        tw, _ = measure_text(draw, candidate, font)
        if tw <= max_width:
            return candidate
    return "…"


# ── Auto Font Sizing ────────────────────────────────────────────────────────

def auto_font_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_name: str,
    max_width: int,
    max_height: int,
    min_size: int = S(14),
    max_size: int = S(56),
    step: int = 2,
) -> ImageFont.FreeTypeFont:
    """
    Find the largest font size that fits text within dimensions.

    Progressive reduction: starts at max_size, decreases by `step` until
    the text fits or min_size is reached.
    """
    for size in range(max_size, min_size - 1, -step):
        font = load_font(font_name, size)
        lines = wrap_text(draw, text, font, max_width)
        lh = measure_line_height(draw, font)
        total_h = len(lines) * int(lh * 1.4)
        if total_h <= max_height:
            return font
    return load_font(font_name, min_size)


# ── Aligned Text Drawing ───────────────────────────────────────────────────

def draw_text_aligned(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int, y: int,
    font: ImageFont.FreeTypeFont,
    color: tuple[int, ...],
    align: Literal["left", "center", "right"] = "left",
    region_width: int = 0,
) -> int:
    """
    Draw a single line of text with alignment.
    Returns the y position after the text (for chaining).
    """
    tw, th = measure_text(draw, text, font)

    if align == "center" and region_width > 0:
        x = x + (region_width - tw) // 2
    elif align == "right" and region_width > 0:
        x = x + region_width - tw

    draw.text((x, y), text, font=font, fill=color)
    return y + th


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: LayoutBox,
    font: ImageFont.FreeTypeFont,
    color: tuple[int, ...],
    line_spacing: float = 1.4,
    max_lines: int = 0,
    y_offset: int = 0,
) -> int:
    """
    Draw word-wrapped text inside a LayoutBox.
    Returns the y position after the last line.
    """
    lines = wrap_text(draw, text, font, box.inner_w, max_lines=max_lines)
    lh = int(measure_line_height(draw, font) * line_spacing)
    y = box.inner_y + y_offset

    for line in lines:
        if y + lh > box.inner_bottom:
            break
        draw_text_aligned(
            draw, line, box.inner_x, y, font, color,
            align=box.align, region_width=box.inner_w,
        )
        y += lh

    return y


# ── Region Computation ──────────────────────────────────────────────────────

def compute_regions(
    canvas_w: int,
    canvas_h: int,
    layout: dict[str, dict],
) -> dict[str, LayoutBox]:
    """
    Compute LayoutBox regions from a layout specification.

    layout = {
        "header": {"x": 0.05, "y": 0.03, "w": 0.9, "h": 0.15},
        "body":   {"x": 0.05, "y": 0.2,  "w": 0.9, "h": 0.6},
    }

    All values are fractions of canvas dimensions (0.0 - 1.0).
    """
    regions: dict[str, LayoutBox] = {}
    for name, spec in layout.items():
        regions[name] = LayoutBox(
            x=int(spec.get("x", 0) * canvas_w),
            y=int(spec.get("y", 0) * canvas_h),
            w=int(spec.get("w", 1) * canvas_w),
            h=int(spec.get("h", 1) * canvas_h),
            padding=int(spec.get("padding", 0.02) * min(canvas_w, canvas_h)),
            align=spec.get("align", "left"),
        )
    return regions


# ── Debug Mode ──────────────────────────────────────────────────────────────

def draw_debug_bounds(
    draw: ImageDraw.ImageDraw,
    regions: dict[str, LayoutBox],
    color: tuple[int, ...] = (255, 0, 0, 100),
    label_font: ImageFont.FreeTypeFont | None = None,
) -> None:
    """Draw bounding boxes for layout debugging."""
    if label_font is None:
        label_font = load_font("Inter-Regular.ttf", S(12))

    for name, box in regions.items():
        # Outer boundary
        draw.rectangle(
            [box.x, box.y, box.x + box.w, box.y + box.h],
            outline=(255, 0, 0, 180), width=2,
        )
        # Inner boundary
        draw.rectangle(
            [box.inner_x, box.inner_y, box.inner_right, box.inner_bottom],
            outline=(0, 255, 0, 120), width=1,
        )
        # Label
        draw.text((box.x + 4, box.y + 2), name, font=label_font, fill=color)
