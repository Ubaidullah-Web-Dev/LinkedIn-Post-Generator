"""
core/llm/base.py — Abstract base class for LLM providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    """Structured result from an LLM call."""
    success: bool
    content: str
    provider_name: str = ""
    model: str = ""


class LLMProvider(ABC):
    """
    Abstract LLM provider. Each concrete provider implements `complete()`.
    """

    name: str = "base"

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        token_limit: int = 150,
        temp: float = 1.0,
        retry_limit: int = 3,
    ) -> tuple[bool, str]:
        """
        Send messages to the LLM and return (success, content_or_error).
        """
        ...

    @property
    def is_configured(self) -> bool:
        """Return True if this provider has a valid API key."""
        return False
