"""Ollama local provider (OpenAI-compatible API)."""

from __future__ import annotations

from openai import APIError, OpenAI

from src.config.settings import Settings
from src.llm.client import LLMClient, LLMError


class OllamaProvider(LLMClient):
    """Call a local Ollama server via its OpenAI-compatible endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.ollama_api_key or "ollama",
            base_url=settings.ollama_base_url.rstrip("/"),
            timeout=settings.llm_timeout_seconds,
        )

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Ollama's OpenAI shim may not support response_format on all models;
        # rely on prompt instructions for JSON.
        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=self._settings.llm_temperature,
                max_tokens=self._settings.llm_max_tokens,
            )
        except APIError as exc:
            raise LLMError(f"Ollama API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMError("Ollama returned an empty response")
        return content
