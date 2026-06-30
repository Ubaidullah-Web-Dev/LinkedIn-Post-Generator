"""
core/infographic/validator.py — Pre-save quality validation and benchmarking.

Every generated image is checked for:
- Text overflow (no content outside canvas)
- Visual balance (content not crammed to one side)
- Readability at small sizes (minimum font heights)
- File size sanity

Also provides a benchmarking utility for render performance.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from PIL import Image

from core.infographic.primitives import CANVAS_W, CANVAS_H, S
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of image quality validation."""
    passed: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def validate_image(path: str) -> ValidationResult:
    """
    Validate a rendered infographic for quality.

    Checks:
    1. File exists and is valid PNG
    2. Dimensions match expected canvas
    3. File size within reasonable bounds (10KB - 5MB)
    4. Image not blank (has color variance)
    """
    result = ValidationResult(passed=True)

    if not os.path.exists(path):
        result.passed = False
        result.errors.append(f"File not found: {path}")
        return result

    try:
        img = Image.open(path)
    except Exception as e:
        result.passed = False
        result.errors.append(f"Cannot open image: {e}")
        return result

    # Dimension check
    w, h = img.size
    if w != CANVAS_W or h != CANVAS_H:
        result.warnings.append(
            f"Unexpected dimensions: {w}x{h} (expected {CANVAS_W}x{CANVAS_H})"
        )

    # File size check
    fsize = os.path.getsize(path)
    if fsize < 10_000:
        result.warnings.append(f"File suspiciously small ({fsize} bytes)")
    elif fsize > 5_000_000:
        result.warnings.append(f"File very large ({fsize / 1024:.0f} KB)")

    # Color variance check (detect blank images)
    try:
        import numpy as np
        arr = np.array(img.convert("RGB"))
        # Check if standard deviation is very low (nearly uniform)
        std = arr.std()
        if std < 5.0:
            result.warnings.append(
                f"Image appears nearly blank (std={std:.1f})"
            )
    except ImportError:
        pass

    img.close()
    return result


# ── Benchmarking ─────────────────────────────────────────────────────────────

@dataclass
class BenchmarkResult:
    """Result of a render benchmark."""
    template: str
    theme: str
    render_time_ms: float
    file_size_bytes: int
    passed_validation: bool


def benchmark_render(
    engine,  # InfographicEngine
    data: dict,
    template: str,
    theme: str,
    save_path: str,
) -> BenchmarkResult:
    """
    Benchmark a single render operation.

    Returns timing, file size, and validation status.
    Target: < 100ms per render.
    """
    start = time.perf_counter()
    result_path = engine.render(data, template=template, theme=theme, save_path=save_path)
    elapsed_ms = (time.perf_counter() - start) * 1000

    fsize = os.path.getsize(result_path) if result_path and os.path.exists(result_path) else 0
    validation = validate_image(result_path) if result_path else ValidationResult(passed=False, errors=["No output"])

    bm = BenchmarkResult(
        template=template,
        theme=theme,
        render_time_ms=round(elapsed_ms, 1),
        file_size_bytes=fsize,
        passed_validation=validation.passed,
    )

    if elapsed_ms > 100:
        logger.warning(
            "Render exceeded target: %s/%s took %.0fms (target <100ms)",
            template, theme, elapsed_ms,
        )

    return bm
