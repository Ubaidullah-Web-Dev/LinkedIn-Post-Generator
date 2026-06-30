"""
core/llm/openrouter_provider.py — OpenRouter provider with free-model rotation
and exponential backoff.
"""

from __future__ import annotations

from time import sleep

from openai import OpenAI, RateLimitError

from core.llm.base import LLMProvider
from core.logger import get_logger

logger = get_logger(__name__)

# Pool of free models for rotation
FREE_MODELS = [
    "openrouter/free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
]


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider with free-model failover rotation."""

    name = "openrouter"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = (
            OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            if api_key
            else None
        )

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def complete(
        self,
        messages: list[dict[str, str]],
        token_limit: int = 150,
        temp: float = 1.0,
        retry_limit: int = 3,
        model: str = "gpt-4o-mini",
    ) -> tuple[bool, str]:
        if not self._client:
            return False, "OpenRouter API key not configured."

        # If using the default model, rotate through free models
        if model == "gpt-4o-mini":
            return self._rotate_free_models(messages, token_limit, temp)

        return self._call(messages, token_limit, model, temp, retry_limit)

    def _rotate_free_models(
        self,
        messages: list[dict[str, str]],
        token_limit: int,
        temp: float,
    ) -> tuple[bool, str]:
        """Try each free model with 1 retry each."""
        errors: list[str] = []
        for free_model in FREE_MODELS:
            success, res = self._call(messages, token_limit, free_model, temp, 1)
            if success:
                return True, res
            errors.append(f"{free_model}: {res}")
        return False, " | ".join(errors)

    def _call(
        self,
        messages: list[dict[str, str]],
        token_limit: int,
        model: str,
        temp: float,
        retry_limit: int,
    ) -> tuple[bool, str]:
        for attempt in range(retry_limit + 1):
            try:
                completion = self._client.chat.completions.create(  # type: ignore[union-attr]
                    model=model,
                    messages=messages,
                    max_tokens=token_limit,
                    temperature=temp,
                )
                if completion and completion.choices:
                    content = completion.choices[0].message.content
                    if content:
                        logger.debug("OpenRouter success (model=%s)", model)
                        return True, content.strip()
                return False, "Empty response."

            except RateLimitError as e:
                err_msg = str(e).lower()
                if "free-models-per-day" in err_msg:
                    return False, "Daily limit reached for free models."
                if "free-models-per-min" in err_msg:
                    wait = min(2 ** attempt * 3, 30)
                    logger.warning("OpenRouter per-min limit, retrying in %ds...", wait)
                    sleep(wait)
                    continue
                return False, "Rate limit exceeded."

            except Exception as e:
                logger.error("OpenRouter error: %s", e)
                return False, str(e)

        return False, "Max retries exceeded."
