"""
core/linkedin.py — LinkedIn API client.

v2 rewrite:
- post() and post_file() return tuple[bool, str] (no silent failures)
- File handle leak fixed (context manager for uploads)
- Unused fbinary removed, dead code removed
- Proper logging instead of custom_print()
- Full type hints
"""

from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
from re import sub

import requests

from core.constants import LINKEDIN_CHAR_LIMIT, MediaCategory
from core.logger import get_logger

logger = get_logger(__name__)


class ContentTooLong(requests.RequestException):
    """LinkedIn post character limit exceeded."""
    pass


class LinkedIn:
    """LinkedIn API client for posting text and images."""

    BASE_URL = "https://www.linkedin.com"
    POST_ENDPOINT = BASE_URL + "/voyager/api/contentcreation/normShares"
    UPLOAD_ENDPOINT = BASE_URL + "/voyager/api/voyagerVideoDashMediaUploadMetadata?action=upload"

    def __init__(self, cookies: dict[str, str]) -> None:
        self.cookies: dict[str, str] = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in cookies.items()
        }

        # Clean JSESSIONID quotes
        jsid = self.cookies.get("JSESSIONID", "")
        if '\\"' in jsid:
            self.cookies["JSESSIONID"] = sub(r'\\"+', "", jsid)

        self.headers: dict[str, str] = {
            "accept": "application/vnd.linkedin.normalized+json+2.1",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json; charset=UTF-8",
            "csrf-token": self.cookies.get("JSESSIONID", ""),
            "origin": self.BASE_URL,
            "cookie": self._build_cookie_header(),
            "Referer": self.BASE_URL + "/feed/",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
            ),
        }

    def _build_cookie_header(self) -> str:
        """Build the Cookie header string from the cookies dict."""
        parts = []
        for key, value in self.cookies.items():
            if key == "JSESSIONID":
                parts.append(f'{key}="{value}"')
            else:
                parts.append(f"{key}={value}")
        return "; ".join(parts)

    # ── Posting ──────────────────────────────────────────────────────────

    def post(
        self, text: str, media: list[dict] | None = None
    ) -> tuple[bool, str]:
        """
        Post text (with optional media) to LinkedIn.

        Returns (success, message).
        """
        if media is None:
            media = []

        if len(text) > LINKEDIN_CHAR_LIMIT:
            return False, f"Post too long ({len(text)} chars, limit {LINKEDIN_CHAR_LIMIT})."

        payload = {
            "visibleToConnectionsOnly": False,
            "externalAudienceProviders": [],
            "commentaryV2": {"text": text, "attributes": []},
            "origin": "FEED",
            "allowedCommentersScope": "ALL",
            "postState": "PUBLISHED",
            "media": media,
        }

        try:
            response = requests.post(
                self.POST_ENDPOINT, headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()
            self._check_session(response.headers)
            logger.info("Successfully posted to LinkedIn")
            return True, "Posted to LinkedIn successfully."

        except requests.exceptions.RequestException as e:
            msg = f"Error posting to LinkedIn: {e}"
            logger.error(msg)
            return False, msg

    def post_file(
        self, text: str, file_path: str | list[str]
    ) -> tuple[bool, str]:
        """
        Upload an image and post it with text to LinkedIn.

        Returns (success, message).
        """
        # Resolve file path
        if isinstance(file_path, list):
            resolved_path = os.path.join(*file_path)
            fname = file_path[-1]
        else:
            resolved_path = file_path
            fname = os.path.basename(file_path)

        if not os.path.exists(resolved_path):
            return False, f"File not found: {resolved_path}"

        content_type = mimetypes.guess_type(resolved_path)[0]
        if not content_type:
            return False, f"Cannot determine content type for: {resolved_path}"

        fsize = os.path.getsize(resolved_path)

        payload = {
            "mediaUploadType": "IMAGE_SHARING",
            "fileSize": fsize,
            "filename": fname,
        }

        try:
            # Step 1: Request upload URL
            response = requests.post(
                self.UPLOAD_ENDPOINT,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()
            self._check_session(response.headers)

            data = response.json()["data"]["value"]
            upload_endpoint = data["singleUploadUrl"]

            # Step 2: Upload the file (fixed: use context manager — no leak)
            upload_headers = dict(self.headers)
            upload_headers["media-type-family"] = data["singleUploadHeaders"]["media-type-family"]
            upload_headers["content-type"] = content_type

            with open(resolved_path, "rb") as f:
                response = requests.put(
                    upload_endpoint, headers=upload_headers, data=f, timeout=60
                )
                response.raise_for_status()

            # Step 3: Create post with the uploaded media
            return self.post(
                text,
                [
                    {
                        "category": MediaCategory.IMAGE.value,
                        "mediaUrn": data["urn"],
                        "tapTargets": [],
                    }
                ],
            )

        except requests.exceptions.RequestException as e:
            msg = f"Error uploading/posting to LinkedIn: {e}"
            logger.error(msg)
            return False, msg

    # ── Session Management ───────────────────────────────────────────────

    def _check_session(self, resp_headers: dict | None = None) -> None:
        """Check if LinkedIn returned new session cookies and update them."""
        try:
            if not resp_headers:
                response = requests.get(self.BASE_URL, headers=self.headers, timeout=10)
                response.raise_for_status()
                resp_headers = dict(response.headers)

            set_cookie = resp_headers.get("Set-Cookie", "")
            if not set_cookie or "li_at=" not in set_cookie:
                return

            cookie_parts = set_cookie.split(";")
            has_updates = False

            for cookie_key in ("JSESSIONID", "li_at"):
                if f"{cookie_key}=" not in set_cookie:
                    continue

                found = next(
                    (part for part in cookie_parts if f"{cookie_key}=" in part),
                    None,
                )
                if not found:
                    continue

                new_val = (
                    found.split(f"{cookie_key}=")[1]
                    .split(";")[0]
                    .strip()
                    .replace('\\"', "")
                )
                if new_val and self.cookies.get(cookie_key) != new_val:
                    self.cookies[cookie_key] = new_val
                    has_updates = True

            if has_updates:
                logger.info("LinkedIn session cookies refreshed")
                self.headers["cookie"] = self._build_cookie_header()
                self.headers["csrf-token"] = self.cookies.get("JSESSIONID", "")

        except requests.exceptions.RequestException as e:
            logger.warning("Error checking LinkedIn session: %s", e)
