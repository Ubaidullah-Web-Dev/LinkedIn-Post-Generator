"""
core/llm/openai_provider.py — OpenAI provider with exponential backoff.
"""

from __future__ import annotations

from time import sleep

from openai import OpenAI, RateLimitError

from core.llm.base import LLMProvider
from core.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (GPT-4o-mini, etc.)."""

    name = "openai"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = OpenAI(api_key=api_key) if api_key else None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    @property
    def client(self) -> OpenAI | None:
        return self._client

    def complete(
        self,
        messages: list[dict[str, str]],
        token_limit: int = 150,
        temp: float = 1.0,
        retry_limit: int = 3,
        model: str = "gpt-4o-mini",
    ) -> tuple[bool, str]:
        if not self._client:
            return False, "OpenAI API key not configured."

        for attempt in range(retry_limit + 1):
            try:
                completion = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=token_limit,
                    temperature=temp,
                )
                if completion and completion.choices:
                    content = completion.choices[0].message.content
                    if content:
                        logger.debug("OpenAI success (model=%s)", model)
                        return True, content.strip()
                return False, "Empty response from OpenAI."

            except RateLimitError as e:
                err_msg = str(e).lower()
                if "quota" in err_msg or "insufficient" in err_msg:
                    return False, "Quota exceeded or billing required."
                wait = min(2 ** attempt * 2, 30)
                logger.warning("OpenAI rate limit, retrying in %ds...", wait)
                sleep(wait)

            except Exception as e:
                logger.error("OpenAI error: %s", e)
                return False, str(e)

        return False, "Max retries exceeded."
