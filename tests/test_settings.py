"""Phase 0: settings bootstrap tests."""

from __future__ import annotations

from src.config.settings import Settings, get_settings


def test_settings_defaults():
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        openai_api_key="",
        groq_api_key="",
    )
    assert settings.llm_provider == "groq"
    assert settings.llm_model == "qwen/qwen3.8-27b"
    assert settings.max_candidates == 30
    assert settings.top_n_default == 5
    assert settings.budget_low_max == 500
    assert settings.budget_medium_max == 1500


def test_budget_ranges():
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.budget_range("low") == (None, 500)
    assert settings.budget_range("medium") == (501, 1500)
    assert settings.budget_range("high") == (1501, None)


def test_get_settings_cached():
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b
    get_settings.cache_clear()
