"""Phase 0: settings bootstrap tests."""

from __future__ import annotations

import os

from src.config.settings import Settings, apply_external_secrets, get_settings


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


def test_apply_external_secrets_sets_missing_env(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("DINEMIND_TEST_NESTED", raising=False)
    apply_external_secrets(
        {
            "GROQ_API_KEY": "gsk_from_streamlit",
            "nested": {"DINEMIND_TEST_NESTED": "ok"},
        }
    )
    assert os.environ["GROQ_API_KEY"] == "gsk_from_streamlit"
    assert os.environ["DINEMIND_TEST_NESTED"] == "ok"


def test_apply_external_secrets_does_not_override_existing_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "already-set")
    apply_external_secrets({"GROQ_API_KEY": "from-secrets"})
    assert os.environ["GROQ_API_KEY"] == "already-set"


def test_shipped_parquet_loads_for_streamlit_cloud():
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    from src.data.cache import CacheManager

    data = CacheManager(settings.processed_data_path).load()
    assert len(data) >= 1_000
    assert "name" in data.columns
    assert "location" in data.columns
