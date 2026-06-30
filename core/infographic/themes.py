"""
core/infographic/themes.py — Dynamic theme engine with 5 themes.

Each theme defines a complete visual language: colors, typography, spacing,
and glow behaviour. Themes are validated for readability contrast.

Design rules:
- Text contrast must pass readability threshold
- Accent colors must not overpower content
- Glow limited to key highlights only
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Complete visual theme for infographic rendering."""

    name: str
    display_name: str

    # Background gradient
    bg_top: tuple[int, int, int]
    bg_bottom: tuple[int, int, int]

    # Accent colors
    accent_primary: tuple[int, int, int]
    accent_secondary: tuple[int, int, int]

    # Text colors
    text_primary: tuple[int, int, int]
    text_secondary: tuple[int, int, int]
    text_muted: tuple[int, int, int]

    # Card / panel
    card_fill: tuple[int, int, int, int]      # RGBA
    card_border: tuple[int, int, int, int]     # RGBA

    # Success / Error
    color_success: tuple[int, int, int]
    color_error: tuple[int, int, int]

    # Glow
    glow_intensity: int  # 0-80, lower = more subtle

    # Accent palette (for lists, badges, numbered items)
    accent_palette: tuple[tuple[int, int, int], ...] = ()

    def __post_init__(self) -> None:
        # Auto-generate accent palette if not provided
        if not self.accent_palette:
            object.__setattr__(self, "accent_palette", (
                self.accent_primary,
                self.accent_secondary,
                self.color_success,
                (245, 158, 11),  # amber
                (236, 72, 153),  # pink
            ))


# ── Theme Definitions ────────────────────────────────────────────────────────

CYBERPUNK_NEON = Theme(
    name="cyberpunk_neon",
    display_name="Cyberpunk Neon",
    bg_top=(8, 12, 22),
    bg_bottom=(14, 20, 38),
    accent_primary=(124, 58, 237),      # purple
    accent_secondary=(6, 182, 212),     # cyan
    text_primary=(248, 250, 252),
    text_secondary=(203, 213, 225),
    text_muted=(100, 116, 150),
    card_fill=(15, 23, 42, 180),
    card_border=(255, 255, 255, 25),
    color_success=(16, 185, 129),
    color_error=(239, 68, 68),
    glow_intensity=45,
    accent_palette=(
        (124, 58, 237), (6, 182, 212), (16, 185, 129),
        (245, 158, 11), (236, 72, 153),
    ),
)

MINIMAL_MONO = Theme(
    name="minimal_mono",
    display_name="Minimal Monochrome",
    bg_top=(18, 18, 18),
    bg_bottom=(10, 10, 10),
    accent_primary=(200, 200, 200),
    accent_secondary=(140, 140, 140),
    text_primary=(240, 240, 240),
    text_secondary=(180, 180, 180),
    text_muted=(100, 100, 100),
    card_fill=(30, 30, 30, 200),
    card_border=(60, 60, 60, 150),
    color_success=(160, 220, 160),
    color_error=(220, 120, 120),
    glow_intensity=15,
    accent_palette=(
        (200, 200, 200), (150, 150, 150), (180, 180, 180),
        (130, 130, 130), (170, 170, 170),
    ),
)

SOFT_PASTEL = Theme(
    name="soft_pastel",
    display_name="Soft Pastel",
    bg_top=(30, 25, 40),
    bg_bottom=(20, 18, 32),
    accent_primary=(167, 139, 250),     # soft violet
    accent_secondary=(129, 230, 217),   # soft teal
    text_primary=(245, 243, 255),
    text_secondary=(200, 195, 220),
    text_muted=(130, 120, 160),
    card_fill=(40, 35, 60, 160),
    card_border=(167, 139, 250, 40),
    color_success=(134, 239, 172),
    color_error=(252, 165, 165),
    glow_intensity=30,
    accent_palette=(
        (167, 139, 250), (129, 230, 217), (252, 176, 217),
        (253, 224, 137), (134, 239, 172),
    ),
)

GLASSMORPHISM = Theme(
    name="glassmorphism",
    display_name="Glassmorphism",
    bg_top=(10, 15, 30),
    bg_bottom=(5, 10, 22),
    accent_primary=(20, 184, 166),      # teal
    accent_secondary=(245, 158, 11),    # amber
    text_primary=(248, 250, 252),
    text_secondary=(196, 210, 230),
    text_muted=(100, 120, 155),
    card_fill=(255, 255, 255, 12),
    card_border=(255, 255, 255, 35),
    color_success=(52, 211, 153),
    color_error=(248, 113, 113),
    glow_intensity=35,
    accent_palette=(
        (20, 184, 166), (245, 158, 11), (52, 211, 153),
        (99, 102, 241), (236, 72, 153),
    ),
)

BOLD_CONTRAST = Theme(
    name="bold_contrast",
    display_name="Bold High-Contrast",
    bg_top=(5, 5, 5),
    bg_bottom=(0, 0, 0),
    accent_primary=(255, 107, 53),      # vivid orange
    accent_secondary=(255, 59, 48),     # vivid red
    text_primary=(255, 255, 255),
    text_secondary=(220, 220, 220),
    text_muted=(120, 120, 120),
    card_fill=(20, 20, 20, 220),
    card_border=(255, 107, 53, 60),
    color_success=(50, 215, 75),
    color_error=(255, 69, 58),
    glow_intensity=50,
    accent_palette=(
        (255, 107, 53), (255, 59, 48), (50, 215, 75),
        (255, 214, 10), (191, 90, 242),
    ),
)

# ── Theme Registry ───────────────────────────────────────────────────────────

_THEMES: dict[str, Theme] = {
    t.name: t for t in [
        CYBERPUNK_NEON, MINIMAL_MONO, SOFT_PASTEL, GLASSMORPHISM, BOLD_CONTRAST,
    ]
}

DEFAULT_THEME = "cyberpunk_neon"


def get_theme(name: str) -> Theme:
    """Get a theme by name. Falls back to default."""
    return _THEMES.get(name, _THEMES[DEFAULT_THEME])


def list_themes() -> list[Theme]:
    """Return all available themes."""
    return list(_THEMES.values())


def random_theme() -> Theme:
    """Return a random theme."""
    import random
    return random.choice(list(_THEMES.values()))


# ── Theme Validation ─────────────────────────────────────────────────────────

def _luminance(color: tuple[int, int, int]) -> float:
    """Calculate relative luminance (WCAG formula)."""
    r, g, b = (c / 255.0 for c in color)
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    """WCAG contrast ratio between foreground and background."""
    l1 = _luminance(fg) + 0.05
    l2 = _luminance(bg) + 0.05
    return max(l1, l2) / min(l1, l2)


def validate_theme(theme: Theme) -> list[str]:
    """Validate theme for readability. Returns list of warnings."""
    warnings: list[str] = []
    # Check primary text against background (WCAG AA = 4.5:1)
    bg_avg = tuple((a + b) // 2 for a, b in zip(theme.bg_top, theme.bg_bottom))
    cr = contrast_ratio(theme.text_primary, bg_avg)
    if cr < 4.5:
        warnings.append(
            f"Primary text contrast too low ({cr:.1f}:1, need 4.5:1)"
        )
    cr_sec = contrast_ratio(theme.text_secondary, bg_avg)
    if cr_sec < 3.0:
        warnings.append(
            f"Secondary text contrast too low ({cr_sec:.1f}:1, need 3.0:1)"
        )
    return warnings
