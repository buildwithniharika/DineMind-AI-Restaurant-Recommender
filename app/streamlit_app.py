"""DineMind Streamlit app — Stitch white-light UI + recommendation orchestrator."""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.components.preference_form import render_preference_form
from app.components.recommendation_card import (
    render_empty_canvas,
    render_error_canvas,
    render_initial_canvas,
    render_loading_canvas,
    render_results,
)
from src.config.settings import apply_external_secrets, get_settings
from src.data.cache import CacheError, CacheManager
from src.models.preferences import UserPreferences
from src.models.recommendation import RecommendationResponse
from src.services.exceptions import (
    DatasetNotLoadedError,
    NoMatchesError,
    RecommendationEngineError,
)
from src.services.recommendation_service import RecommendationService

APP_DIR = Path(__file__).resolve().parent
CSS_PATH = APP_DIR / "styles" / "dinemind.css"


def _inject_css() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _apply_streamlit_secrets() -> None:
    """Load Streamlit Cloud secrets into the environment before Settings()."""
    try:
        secrets = st.secrets
        mapping = secrets.to_dict() if hasattr(secrets, "to_dict") else dict(secrets)
    except Exception:
        return
    if not mapping:
        return
    apply_external_secrets(mapping)
    get_settings.cache_clear()


@st.cache_resource(show_spinner=False)
def _get_service() -> RecommendationService:
    settings = get_settings()
    data = CacheManager(settings.processed_data_path).load()
    return RecommendationService(settings=settings, data=data, allow_missing_llm=True)


def _render_header() -> None:
    st.markdown(
        """
        <div class="dm-header">
          <div class="dm-brand">
            <span class="dm-brand-mark" aria-hidden="true">✦</span>
            <div class="dm-brand-text">
              <div class="dm-brand-name">DineMind</div>
              <div class="dm-brand-tag">AI restaurant picks, explained</div>
            </div>
          </div>
          <span class="dm-live-pill">
            <span class="dm-live-dot"></span>
            Bangalore live
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="DineMind — AI Restaurant Recommender",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _apply_streamlit_secrets()
    _inject_css()
    _render_header()

    settings = get_settings()
    try:
        service = _get_service()
        metadata = service.metadata()
    except (CacheError, DatasetNotLoadedError, FileNotFoundError) as exc:
        st.markdown(render_error_canvas(str(exc)), unsafe_allow_html=True)
        st.info(
            "Local: run `python scripts/prepare_data.py` and refresh. "
            "Streamlit Cloud: confirm `data/processed/restaurants.parquet` is in the repo."
        )
        return

    if not settings.api_key_for_provider() and settings.llm_provider != "ollama":
        st.caption(
            "No LLM API key found — recommendations still work with rule-based explanations. "
            "Add `GROQ_API_KEY` in Streamlit secrets (or `.env` locally) for AI rationales."
        )

    left, right = st.columns([5, 7], gap="large")

    with left:
        prefs, submitted = render_preference_form(metadata, settings)

    if submitted and prefs is not None:
        st.session_state["dm_error"] = None
        st.session_state["dm_prefs"] = prefs
        st.session_state["dm_empty"] = False
        with right:
            st.markdown(render_loading_canvas(prefs.location), unsafe_allow_html=True)
        time.sleep(0.35)
        try:
            response = service.recommend(prefs, include_summary=True)
            st.session_state["dm_results"] = response
            st.session_state["dm_empty"] = False
        except NoMatchesError:
            st.session_state["dm_results"] = None
            st.session_state["dm_empty"] = True
        except RecommendationEngineError as exc:
            st.session_state["dm_error"] = str(exc)
            st.session_state["dm_results"] = None
        except Exception as exc:  # noqa: BLE001
            st.session_state["dm_error"] = f"Unexpected error: {exc}"
            st.session_state["dm_results"] = None
        st.rerun()

    with right:
        error = st.session_state.get("dm_error")
        if error:
            st.markdown(render_error_canvas(str(error)), unsafe_allow_html=True)
            return

        results: RecommendationResponse | None = st.session_state.get("dm_results")
        prefs_saved: UserPreferences | None = st.session_state.get("dm_prefs")
        if st.session_state.get("dm_empty") and prefs_saved is not None:
            st.markdown(render_empty_canvas(prefs_saved), unsafe_allow_html=True)
            return
        if results and prefs_saved:
            st.markdown(render_results(results, prefs_saved), unsafe_allow_html=True)
            return
        st.markdown(render_initial_canvas(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
