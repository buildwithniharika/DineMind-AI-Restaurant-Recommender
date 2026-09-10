"""Groq chat completions provider (OpenAI-compatible API)."""

from __future__ import annotations

from openai import APIError, OpenAI

from src.config.settings import Settings
from src.llm.client import LLMClient, LLMError

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(LLMClient):
    """Call Groq's OpenAI-compatible Chat Completions API."""

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            raise LLMError("GROQ_API_KEY is not configured")
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=GROQ_BASE_URL,
            timeout=settings.llm_timeout_seconds,
        )

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=self._settings.llm_temperature,
                max_tokens=self._settings.llm_max_tokens,
                response_format={"type": "json_object"},
            )
        except APIError as exc:
            raise LLMError(f"Groq API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Groq request failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMError("Groq returned an empty response")
        return content
