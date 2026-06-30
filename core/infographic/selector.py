"""
core/infographic/selector.py — Content-aware template selection with
confidence scoring.

Each pattern match contributes a weighted score. Highest-scoring template
is selected. If confidence is low, falls back to MinimalCard.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SelectionResult:
    """Result of template selection with confidence."""
    template: str
    confidence: float  # 0.0 to 1.0
    reason: str


# ── Pattern Definitions ──────────────────────────────────────────────────────

_STAT_PATTERNS = [
    (r"\d+\s*[%xX×]", 3.0),
    (r"\d+\s*(ms|MB|KB|GB|TB|fps|rpm)", 3.0),
    (r"(?:increased|decreased|reduced|improved|grew|dropped|saved)\s+(?:by\s+)?\d", 2.5),
    (r"\d+\.\d+", 1.5),
    (r"\d{2,}", 1.0),
]

_LIST_PATTERNS = [
    (r"^\s*\d+[\.\)]\s", 3.0),            # "1. item" or "1) item"
    (r"^\s*[-•*]\s", 2.5),                 # bullet points
    (r"(?:tip|trick|hack|rule|lesson)\s*#?\d", 2.0),
    (r"(?:here are|top|best)\s+\d+\s", 2.0),
    (r"(?:tips|tricks|hacks|rules|lessons|ways|things)\s", 1.5),
]

_STEP_PATTERNS = [
    (r"step\s*\d", 3.5),
    (r"(?:first|second|third|then|next|finally|lastly|after that)", 2.5),
    (r"(?:how to|guide|tutorial|walkthrough)", 2.0),
    (r"^\s*\d+[\.\)]\s.*(?:then|next|after)", 2.0),
]

_COMPARISON_PATTERNS = [
    (r"\bvs\.?\b", 4.0),
    (r"\bversus\b", 4.0),
    (r"\bcompared\s+to\b", 3.0),
    (r"\bbetter\s+than\b", 2.5),
    (r"\bworse\s+than\b", 2.5),
    (r"\bpros?\s+(?:and|&)\s+cons?\b", 3.0),
    (r"\badvantages?\s+(?:and|&|over)\b", 2.0),
]

_QUOTE_PATTERNS = [
    (r'^"[^"]{20,}"', 4.0),               # starts with a quote
    (r'["""][^"""]{20,}["""]', 3.0),       # contains a substantial quote
    (r"(?:once said|famous quote|reminded me)", 2.5),
    (r"—\s*\w+", 2.0),                    # attribution dash
]

_CODE_PATTERNS = [
    (r"`[^`]+`", 3.0),                    # inline code
    (r"```", 4.0),                        # code block
    (r"(?:function|const|let|var|def|class|import)\s", 2.5),
    (r"\.(?:js|ts|py|css|html|jsx|tsx)\b", 2.5),
    (r"(?:npm|pip|yarn|git)\s+(?:install|run|add|commit)", 2.0),
    (r"(?:API|SDK|CLI|ORM|SQL)\b", 1.5),
]

_TEMPLATES_PATTERNS = {
    "stat_highlight": _STAT_PATTERNS,
    "tips_list": _LIST_PATTERNS,
    "step_flow": _STEP_PATTERNS,
    "comparison": _COMPARISON_PATTERNS,
    "quote_card": _QUOTE_PATTERNS,
    "code_snippet": _CODE_PATTERNS,
}


# ── Scoring Engine ───────────────────────────────────────────────────────────

def select_template(text: str) -> SelectionResult:
    """
    Analyze post text and select the best template.

    Returns SelectionResult with template name, confidence (0-1), and reason.
    """
    if not text or not text.strip():
        return SelectionResult("minimal_card", 0.0, "Empty text")

    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}

    for template_name, patterns in _TEMPLATES_PATTERNS.items():
        total_score = 0.0
        matched: list[str] = []

        for pattern, weight in patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            if matches:
                # Diminishing returns for multiple matches of same pattern
                match_score = weight * min(len(matches), 3)
                total_score += match_score
                matched.append(f"{pattern[:20]}({len(matches)})")

        scores[template_name] = total_score
        reasons[template_name] = matched

    # Find the winner
    if not scores or max(scores.values()) == 0:
        return SelectionResult("minimal_card", 0.1, "No patterns matched")

    best = max(scores, key=scores.get)  # type: ignore
    best_score = scores[best]

    # Normalize confidence: score of 8+ = full confidence
    confidence = min(best_score / 8.0, 1.0)

    # Low confidence threshold
    if confidence < 0.25:
        return SelectionResult(
            "minimal_card", confidence,
            f"Low confidence ({confidence:.0%}), best was {best}",
        )

    reason_str = f"Matched: {', '.join(reasons[best][:3])}"
    return SelectionResult(best, confidence, reason_str)


def suggest_template(text: str) -> list[tuple[str, float]]:
    """
    Return all templates ranked by confidence score.
    Useful for UI template override suggestions.
    """
    if not text:
        return [("minimal_card", 1.0)]

    scores: dict[str, float] = {}
    for template_name, patterns in _TEMPLATES_PATTERNS.items():
        total = 0.0
        for pattern, weight in patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            if matches:
                total += weight * min(len(matches), 3)
        scores[template_name] = total

    # Always include minimal_card as fallback
    scores.setdefault("minimal_card", 0.5)

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    max_score = max(s for _, s in ranked) or 1.0
    return [(name, min(score / max_score, 1.0)) for name, score in ranked]
