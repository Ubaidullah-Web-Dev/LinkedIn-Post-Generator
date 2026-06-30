"""
core/llm/gateway.py — LLM Gateway with configurable provider failover chain,
prompt caching, and structured logging.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import Any

from core.llm.base import LLMProvider, LLMResult
from core.llm.gemini_provider import GeminiProvider
from core.llm.openai_provider import OpenAIProvider
from core.llm.openrouter_provider import OpenRouterProvider
from core.config import AppConfig
from core.logger import get_logger

logger = get_logger(__name__)

# ── Prompt Cache (LRU, in-memory) ────────────────────────────────────────────

class _PromptCache:
    """Simple LRU cache for prompt→response pairs."""

    def __init__(self, max_size: int = 50) -> None:
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._max_size = max_size
        self.hits = 0
        self.misses = 0

    def _key(self, messages: list[dict[str, str]], token_limit: int) -> str:
        raw = json.dumps(messages, sort_keys=True) + str(token_limit)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, messages: list[dict[str, str]], token_limit: int) -> str | None:
        k = self._key(messages, token_limit)
        if k in self._cache:
            self.hits += 1
            self._cache.move_to_end(k)
            return self._cache[k]
        self.misses += 1
        return None

    def put(self, messages: list[dict[str, str]], token_limit: int, result: str) -> None:
        k = self._key(messages, token_limit)
        self._cache[k] = result
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)


# ── LLM Gateway ──────────────────────────────────────────────────────────────

class LLMGateway:
    """
    Multi-provider LLM gateway with automatic failover.

    Default chain: Gemini → OpenRouter → OpenAI (configurable).
    Includes prompt caching to reduce redundant API calls.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._cache = _PromptCache()

        # Build providers
        self._openai = OpenAIProvider(config.open_ai_api_key)
        self._gemini = GeminiProvider(config.gemini_api_key)
        self._openrouter = OpenRouterProvider(config.openrouter_api_key)

        self._providers: dict[str, LLMProvider] = {
            "gemini": self._gemini,
            "openrouter": self._openrouter,
            "openai": self._openai,
        }

    @property
    def openai_client(self) -> Any:
        """Access raw OpenAI client (for DALL-E image generation)."""
        return self._openai.client

    @property
    def gemini_key(self) -> str:
        return self._config.gemini_api_key

    def get_provider_status(self) -> dict[str, bool]:
        """Return which providers are configured."""
        return {name: p.is_configured for name, p in self._providers.items()}

    def ask(
        self,
        messages: list[dict[str, str]],
        token_limit: int = 150,
        model: str = "gpt-4o-mini",
        temp: float = 1.0,
        retry_limit: int = 3,
        provider: str = "auto",
        use_cache: bool = False,
    ) -> tuple[bool, str]:
        """
        Send messages through the provider chain.

        Returns (success: bool, content_or_error: str).
        """
        # Check cache first
        if use_cache:
            cached = self._cache.get(messages, token_limit)
            if cached is not None:
                logger.debug("Cache hit for prompt")
                return True, cached

        p = provider.lower()
        errors: list[str] = []

        chain = self._get_chain(p)
        if not chain:
            return False, f"Provider '{provider}' not configured. Please add API keys."

        for prov in chain:
            # Pick the right model name for this provider
            effective_model = model
            if prov.name == "gemini" and model == "gpt-4o-mini":
                effective_model = "gemini-2.0-flash"

            success, res = prov.complete(
                messages, token_limit, temp, retry_limit, model=effective_model
            )
            if success:
                logger.info("LLM success via %s", prov.name)
                if use_cache:
                    self._cache.put(messages, token_limit, res)
                return True, res
            errors.append(f"{prov.name}: {res}")

        return False, "\n".join(errors)

    def _get_chain(self, provider: str) -> list[LLMProvider]:
        """Build the provider chain based on the requested provider."""
        if provider == "auto":
            # Return all configured providers in priority order
            return [p for p in self._providers.values() if p.is_configured]
        elif provider in self._providers:
            p = self._providers[provider]
            return [p] if p.is_configured else []
        return []
