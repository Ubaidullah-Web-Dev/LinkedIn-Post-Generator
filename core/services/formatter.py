"""
core/services/formatter.py — Unicode formatting for LinkedIn posts.

Pure functions — no class, no state, easily testable.
Handles bold, italic, bold-italic, monospace conversions and
bullet/header stripping for LinkedIn's plain-text format.
"""

from __future__ import annotations

import re


# ── Unicode Character Maps ───────────────────────────────────────────────────

def _to_bold(text: str) -> str:
    """Convert ASCII text to Unicode Mathematical Bold."""
    return "".join(
        chr(ord(c) - 65 + 0x1D400) if 65 <= ord(c) <= 90
        else chr(ord(c) - 97 + 0x1D41A) if 97 <= ord(c) <= 122
        else chr(ord(c) - 48 + 0x1D7CE) if 48 <= ord(c) <= 57
        else c
        for c in text
    )


def _to_italic(text: str) -> str:
    """Convert ASCII text to Unicode Mathematical Italic."""
    return "".join(
        chr(ord(c) - 65 + 0x1D434) if 65 <= ord(c) <= 90
        else chr(0x210E) if c == "h"
        else chr(ord(c) - 97 + 0x1D44E) if 97 <= ord(c) <= 122
        else c
        for c in text
    )


def _to_bold_italic(text: str) -> str:
    """Convert ASCII text to Unicode Mathematical Bold Italic."""
    return "".join(
        chr(ord(c) - 65 + 0x1D468) if 65 <= ord(c) <= 90
        else chr(ord(c) - 97 + 0x1D482) if 97 <= ord(c) <= 122
        else c
        for c in text
    )


def _to_monospace(text: str) -> str:
    """Convert ASCII text to Unicode Mathematical Monospace."""
    return "".join(
        chr(ord(c) - 65 + 0x1D670) if 65 <= ord(c) <= 90
        else chr(ord(c) - 97 + 0x1D68A) if 97 <= ord(c) <= 122
        else chr(ord(c) - 48 + 0x1D7F6) if 48 <= ord(c) <= 57
        else c
        for c in text
    )


# ── Markdown-to-LinkedIn Formatter ───────────────────────────────────────────

_PATTERN = re.compile(
    r"\*\*\*(.+?)\*\*\*"   # bold-italic
    r"|\*\*(.+?)\*\*"      # bold
    r"|\*(.+?)\*"          # italic
    r"|`(.+?)`",           # monospace
    re.DOTALL,
)


def _replacer(m: re.Match) -> str:
    if m.group(1):
        return _to_bold_italic(m.group(1))
    if m.group(2):
        return _to_bold(m.group(2))
    if m.group(3):
        return _to_italic(m.group(3))
    if m.group(4):
        return _to_monospace(m.group(4))
    return m.group(0)


def format_for_linkedin(raw_text: str) -> str:
    """
    Convert markdown-formatted AI output to LinkedIn-compatible Unicode text.

    Transformations:
    - `- item` / `* item` → `• item`
    - `# Header` → stripped
    - `**bold**` → Unicode bold
    - `*italic*` → Unicode italic
    - `***bold-italic***` → Unicode bold-italic
    - `` `code` `` → Unicode monospace
    - Strips outer quotes if entire text is quoted
    """
    # Bullets
    text = re.sub(r"^[ \t]*[-*]\s+", "• ", raw_text, flags=re.MULTILINE)
    # Headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Inline formatting
    text = _PATTERN.sub(_replacer, text).strip()
    # Strip outer quotes
    text = re.sub(r'^"([^"]*)"$', r"\1", text)
    return text


# ── Post Validation ──────────────────────────────────────────────────────────

def validate_post(text: str) -> tuple[bool, str]:
    """
    Validate a post before publishing.
    Returns (is_valid, text_or_error_message).
    """
    if not text or not text.strip():
        return False, "Post text is empty."
    if len(text) < 30:
        return False, f"Post too short ({len(text)} chars, minimum 30)."
    if len(text) > 3000:
        return False, f"Post too long ({len(text)} chars, limit 3000)."
    return True, text
