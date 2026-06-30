"""
core/infographic/primitives.py — High-performance drawing primitives.

All visual building blocks used by templates. NumPy-optimized where applicable.
Every function operates on an existing PIL Image or ImageDraw context.

Design rules enforced:
- No hardcoded positions (all computed from parameters)
- Consistent spacing scale (8/16/24/32/48)
- Readability over decoration
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from core.constants import FONTS_DIR
from core.logger import get_logger

if TYPE_CHECKING:
    from core.infographic.themes import Theme

logger = get_logger(__name__)

# ── Spacing Scale (8px base) ────────────────────────────────────────────────

SP_XS = 8
SP_SM = 16
SP_MD = 24
SP_LG = 32
SP_XL = 48

# ── Canvas Constants ────────────────────────────────────────────────────────

CANVAS_W = 2400   # 1200 × 2
CANVAS_H = 1260   # 630 × 2
SCALE = 2


def S(val: int | float) -> int:
    """Scale a value by the global SCALE factor."""
    return int(val * SCALE)


# ── Font Loading (cached) ──────────────────────────────────────────────────

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
_system_font_path: str | None = None


def strip_emojis(text: str) -> str:
    """Remove emoji characters that PIL can't render."""
    return re.sub(r"[\U00010000-\U0010ffff]", "", text) if text else ""


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font with caching. Falls back to system font, then default."""
    global _system_font_path
    key = (name, size)
    if key in _font_cache:
        return _font_cache[key]

    # Try project fonts directory
    font_path = FONTS_DIR / name
    if font_path.exists():
        try:
            f = ImageFont.truetype(str(font_path), size)
            _font_cache[key] = f
            return f
        except OSError:
            pass

    # Try system font (cache the lookup)
    if _system_font_path is None:
        try:
            import subprocess
            result = subprocess.run(
                ["fc-match", "--format=%{file}", "Inter,sans-serif"],
                capture_output=True, text=True, timeout=2,
            )
            _system_font_path = result.stdout.strip() if result.stdout else ""
        except (OSError, subprocess.TimeoutExpired):
            _system_font_path = ""

    if _system_font_path:
        try:
            f = ImageFont.truetype(_system_font_path, size)
            _font_cache[key] = f
            return f
        except OSError:
            pass

    f = ImageFont.load_default()
    _font_cache[key] = f
    return f


# ── Gradient Background (NumPy optimized) ──────────────────────────────────

def gradient_bg(
    img: Image.Image,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> None:
    """Fill image with a vertical gradient. ~100x faster than line-by-line."""
    h, w = img.size[1], img.size[0]
    t = np.array(top, dtype=np.float32)
    b = np.array(bottom, dtype=np.float32)
    grad = np.linspace(t, b, h).astype(np.uint8)
    grad = np.tile(grad[:, np.newaxis, :], (1, w, 1))
    img.paste(Image.fromarray(grad, "RGB"), (0, 0))


# ── Glow Effect ────────────────────────────────────────────────────────────

def radial_glow(
    draw: ImageDraw.ImageDraw,
    cx: int, cy: int, radius: int,
    color: tuple[int, int, int],
    intensity: int = 40,
    steps: int = 16,
) -> None:
    """Draw a soft radial glow on an RGBA layer."""
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        a = int(intensity * (i / steps) ** 2.2)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, a))


# ── Glass Panel ────────────────────────────────────────────────────────────

def glass_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int = S(16),
    fill: tuple[int, ...] = (255, 255, 255, 10),
    border: tuple[int, ...] = (255, 255, 255, 25),
    border_width: int = S(1),
    shadow_offset: int = 8,
) -> None:
    """Glassmorphism panel with subtle shadow."""
    x0, y0, x1, y1 = box
    # Shadow
    if shadow_offset > 0:
        draw.rounded_rectangle(
            [x0 + 2, y0 + shadow_offset, x1 + 2, y1 + shadow_offset],
            radius=radius, fill=(0, 0, 0, 35),
        )
    # Panel
    draw.rounded_rectangle(
        [x0, y0, x1, y1], radius=radius,
        fill=fill, outline=border, width=border_width,
    )


# ── Divider Line ───────────────────────────────────────────────────────────

def divider_line(
    draw: ImageDraw.ImageDraw,
    x0: int, y: int, x1: int,
    color: tuple[int, ...] = (255, 255, 255, 30),
    width: int = S(1),
) -> None:
    """Horizontal divider line."""
    draw.line([(x0, y), (x1, y)], fill=color, width=width)


# ── Accent Bar ─────────────────────────────────────────────────────────────

def accent_bar(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, height: int,
    color: tuple[int, ...],
    width: int = S(5),
) -> None:
    """Vertical accent bar (for section markers)."""
    draw.rounded_rectangle(
        [x, y, x + width, y + height],
        radius=width // 2, fill=color,
    )


# ── Number Badge ───────────────────────────────────────────────────────────

def number_badge(
    draw: ImageDraw.ImageDraw,
    cx: int, cy: int, radius: int,
    number: int | str,
    bg_color: tuple[int, ...],
    text_color: tuple[int, ...] = (255, 255, 255),
    font: ImageFont.FreeTypeFont | None = None,
) -> None:
    """Numbered circle badge."""
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=bg_color,
    )
    if font is None:
        font = load_font("Inter-Bold.ttf", int(radius * 1.2))
    text = str(number)
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(
        (cx - tw // 2, cy - th // 2 - S(2)),
        text, font=font, fill=text_color,
    )


# ── Tag Badge ──────────────────────────────────────────────────────────────

def tag_badge(
    draw: ImageDraw.ImageDraw,
    x: int, y: int,
    text: str,
    bg_color: tuple[int, ...],
    text_color: tuple[int, ...] = (255, 255, 255),
    font: ImageFont.FreeTypeFont | None = None,
    padding_h: int = S(14),
    padding_v: int = S(6),
) -> tuple[int, int]:
    """Rounded pill badge. Returns (width, height) of the badge."""
    if font is None:
        font = load_font("Inter-SemiBold.ttf", S(16))
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    w = tw + padding_h * 2
    h = th + padding_v * 2
    draw.rounded_rectangle(
        [x, y, x + w, y + h],
        radius=h // 2, fill=bg_color,
    )
    draw.text((x + padding_h, y + padding_v), text, font=font, fill=text_color)
    return w, h


# ── Check / Cross Marks ───────────────────────────────────────────────────

def checkmark(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple, size: int = S(6)) -> None:
    """Draw a checkmark ✓."""
    draw.line(
        [(cx - size, cy - size // 3), (cx - size // 3, cy + size * 2 // 3), (cx + size * 4 // 3, cy - size)],
        fill=color, width=max(S(3), size // 2),
    )


def crossmark(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple, size: int = S(6)) -> None:
    """Draw an X mark."""
    draw.line([(cx - size, cy - size), (cx + size, cy + size)], fill=color, width=max(S(3), size // 2))
    draw.line([(cx - size, cy + size), (cx + size, cy - size)], fill=color, width=max(S(3), size // 2))


# ── Progress Bar ───────────────────────────────────────────────────────────

def progress_bar(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, width: int, height: int,
    progress: float,
    bg_color: tuple[int, ...] = (255, 255, 255, 15),
    fill_color: tuple[int, ...] = (124, 58, 237),
    radius: int | None = None,
) -> None:
    """Horizontal progress bar (0.0 to 1.0)."""
    if radius is None:
        radius = height // 2
    progress = max(0.0, min(1.0, progress))
    # Background
    draw.rounded_rectangle([x, y, x + width, y + height], radius=radius, fill=bg_color)
    # Fill
    fill_w = int(width * progress)
    if fill_w > radius * 2:
        draw.rounded_rectangle([x, y, x + fill_w, y + height], radius=radius, fill=fill_color)


# ── Arrow ──────────────────────────────────────────────────────────────────

def arrow_right(
    draw: ImageDraw.ImageDraw,
    x: int, cy: int,
    length: int, color: tuple[int, ...],
    thickness: int = S(2),
    head_size: int = S(8),
) -> None:
    """Draw a right-pointing arrow."""
    # Shaft
    draw.line([(x, cy), (x + length - head_size, cy)], fill=color, width=thickness)
    # Arrowhead
    draw.polygon([
        (x + length, cy),
        (x + length - head_size, cy - head_size // 2),
        (x + length - head_size, cy + head_size // 2),
    ], fill=color)


# ── Composite Helper ──────────────────────────────────────────────────────

def composite_layers(base: Image.Image, overlay: Image.Image, blur: int = 6) -> Image.Image:
    """Single-pass alpha composite with optional blur on overlay."""
    if blur > 0:
        overlay = overlay.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


# ── Save Helper ───────────────────────────────────────────────────────────

def save_image(img: Image.Image, path: str) -> str:
    """Save image with directory creation."""
    import os
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return path
