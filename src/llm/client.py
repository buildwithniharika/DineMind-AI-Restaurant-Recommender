"""Abstract LLM client and provider factory.

Phase 3 default provider is Groq (`LLM_PROVIDER=groq` + `GROQ_API_KEY`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from src.config.settings import Settings, get_settings

ProviderName = Literal["groq", "openai", "ollama"]


class LLMError(Exception):
    """Raised when an LLM provider call fails."""


class LLMClient(ABC):
    """Common interface for LLM text generation."""

    @abstractmethod
    def generate(self, prompt: str, *, system: str | None = None) -> str:
        """Return raw model text for the given user prompt (optional system message)."""


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    """Instantiate the provider selected by ``LLM_PROVIDER`` (default: groq)."""
    cfg = settings or get_settings()
    provider = cfg.llm_provider

    if provider == "groq":
        from src.llm.providers.groq_provider import GroqProvider

        return GroqProvider(cfg)
    if provider == "openai":
        from src.llm.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(cfg)
    if provider == "ollama":
        from src.llm.providers.ollama_provider import OllamaProvider

        return OllamaProvider(cfg)

    raise ValueError(f"Unsupported LLM provider: {provider!r}")
