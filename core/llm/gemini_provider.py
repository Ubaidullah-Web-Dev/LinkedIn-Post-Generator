"""
core/llm/gemini_provider.py — Google Gemini provider with exponential backoff
and safe response parsing.
"""

from __future__ import annotations

from time import sleep

import requests

from core.llm.base import LLMProvider
from core.logger import get_logger

logger = get_logger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    name = "gemini"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def complete(
        self,
        messages: list[dict[str, str]],
        token_limit: int = 150,
        temp: float = 1.0,
        retry_limit: int = 3,
        model: str = "gemini-2.0-flash",
    ) -> tuple[bool, str]:
        if not self._api_key:
            return False, "Gemini API key not configured."

        # Convert OpenAI-style messages to Gemini format
        system_instruction: str | None = None
        contents: list[dict] = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": token_limit,
                "temperature": temp,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"{GEMINI_API_BASE}/{model}:generateContent?key={self._api_key}"
        headers = {"Content-Type": "application/json"}

        for attempt in range(retry_limit + 1):
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=30
                )

                if response.status_code != 200:
                    resp_text = response.text.lower()
                    if response.status_code == 429:
                        if any(kw in resp_text for kw in ("quota", "limit: 0", "resource_exhausted")):
                            return False, "Quota exhausted or billing required."
                        wait = min(2 ** attempt * 3, 30)
                        logger.warning("Gemini rate limit, retrying in %ds...", wait)
                        sleep(wait)
                        continue

                    # Try to extract error message
                    try:
                        err = response.json().get("error", {}).get("message", response.text)
                        return False, str(err)
                    except (ValueError, KeyError):
                        return False, response.text

                # Safe response parsing (fixes IndexError/KeyError on empty candidates)
                res_data = response.json()
                candidates = res_data.get("candidates", [])
                if not candidates:
                    return False, "Gemini returned no candidates (possibly safety-filtered)."

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts or "text" not in parts[0]:
                    return False, "Gemini returned empty content."

                text = parts[0]["text"]
                logger.debug("Gemini success (model=%s)", model)
                return True, text.strip()

            except requests.Timeout:
                wait = min(2 ** attempt * 2, 20)
                logger.warning("Gemini timeout, retrying in %ds...", wait)
                sleep(wait)

            except Exception as e:
                logger.error("Gemini error: %s", e)
                if attempt >= retry_limit:
                    return False, str(e)
                sleep(2)

        return False, "Max retries exceeded."
