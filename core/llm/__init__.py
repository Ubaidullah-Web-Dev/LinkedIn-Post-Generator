"""core/llm — LLM provider gateway with strategy-pattern failover."""

from core.llm.base import LLMProvider, LLMResult
from core.llm.gateway import LLMGateway

__all__ = ["LLMProvider", "LLMResult", "LLMGateway"]
