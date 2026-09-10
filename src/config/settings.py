"""Environment-based application settings."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables / `.env`."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Phase 3 primary provider is Groq; openai/ollama remain optional.
    llm_provider: Literal["groq", "openai", "ollama"] = "groq"
    groq_api_key: str = ""
    openai_api_key: str = ""
    llm_model: str = "qwen/qwen3.8-27b"
    llm_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2000, ge=256, le=8000)
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"

    max_candidates: int = Field(default=30, ge=5, le=50)
    top_n_default: int = Field(default=5, ge=1, le=10)

    budget_low_max: int = Field(default=500, ge=0)
    budget_medium_max: int = Field(default=1500, ge=0)

    hf_dataset_id: str = "ManikaSaini/zomato-restaurant-recommendation"
    processed_data_path: Path = PROJECT_ROOT / "data" / "processed" / "restaurants.parquet"

    @field_validator("processed_data_path", mode="before")
    @classmethod
    def resolve_processed_path(cls, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            return PROJECT_ROOT / path
        return path

    def budget_range(self, budget: Literal["low", "medium", "high"]) -> tuple[int | None, int | None]:
        """Return inclusive (min_cost, max_cost) for a budget tier. None means unbounded."""
        if budget == "low":
            return (None, self.budget_low_max)
        if budget == "medium":
            return (self.budget_low_max + 1, self.budget_medium_max)
        return (self.budget_medium_max + 1, None)

    def api_key_for_provider(self) -> str | None:
        """Return the configured API key for the active LLM provider, if any."""
        if self.llm_provider == "groq":
            return self.groq_api_key or None
        if self.llm_provider == "openai":
            return self.openai_api_key or None
        return None  # ollama typically needs no cloud key


def apply_external_secrets(secrets: Mapping[str, Any]) -> None:
    """Copy Streamlit Cloud (or other) secrets into ``os.environ``.

    Nested TOML tables are flattened. Existing environment variables win so a
    local ``.env`` / shell export is not overwritten. Call
    ``get_settings.cache_clear()`` afterwards if settings were already loaded.
    """
    for key, value in secrets.items():
        if isinstance(value, Mapping) and not isinstance(value, (str, bytes)):
            apply_external_secrets(value)
            continue
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        os.environ.setdefault(str(key), text)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for app and scripts."""
    return Settings()
