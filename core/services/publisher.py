"""
core/services/publisher.py — LinkedIn post publishing service.

Returns structured results (no silent failures).
"""

from __future__ import annotations

import os

from core.linkedin import LinkedIn
from core.logger import get_logger

logger = get_logger(__name__)


class Publisher:
    """Publishes posts to LinkedIn with proper error propagation."""

    def __init__(self, cookies: dict[str, str]) -> None:
        self._cookies = cookies

    def publish(
        self, text: str, image_path: str | None = None
    ) -> tuple[bool, str]:
        """
        Publish a post to LinkedIn.

        Returns (success, message).
        """
        if not self._cookies.get("li_at"):
            return False, "LinkedIn cookies not configured."

        try:
            linkedin = LinkedIn(self._cookies)
            if image_path and os.path.exists(image_path):
                success, msg = linkedin.post_file(text, image_path)
            else:
                success, msg = linkedin.post(text)
            return success, msg
        except Exception as e:
            logger.error("Publishing failed: %s", e)
            return False, str(e)
