"""Preference form widgets (DineMind / Stitch layout)."""

from __future__ import annotations

import streamlit as st

from src.config.settings import Settings
from src.models.preferences import UserPreferences

BUDGET_HELP = {
    "low": "≤ ₹500 for two",
    "medium": "₹501 – ₹1,500 for two",
    "high": "> ₹1,500 for two",
}


def render_preference_form(
    metadata: dict[str, list[str]],
    settings: Settings,
) -> tuple[UserPreferences | None, bool]:
    """Render the left-column preference panel.

    Returns (preferences, submitted). preferences is None until Submit.
    """
    with st.container(border=True):
        st.markdown(
            """
            <div class="dm-overline">
              <span class="dm-overline-dot"></span>
              <span class="dm-overline-text">Preferences</span>
            </div>
            <h1 class="dm-panel-title">What are you craving?</h1>
            <p class="dm-panel-sub">
              Tell us your preferences. We’ll rank restaurants and explain why they fit.
            </p>
            """,
            unsafe_allow_html=True,
        )

        cities = metadata.get("cities") or []
        locations = metadata.get("locations") or []
        # Prefer metro first, then localities for dropdown
        location_options = list(dict.fromkeys([*cities, *locations]))
        if not location_options:
            location_options = ["Bangalore"]

        cuisines = ["Any", *metadata.get("cuisines", [])]

        location = st.selectbox(
            "Location *",
            options=location_options,
            index=0,
            help="City or Bangalore locality (partial match supported)",
        )

        budget = st.radio(
            "Budget",
            options=["low", "medium", "high"],
            index=1,
            horizontal=True,
            format_func=lambda b: {
                "low": "Low (₹)",
                "medium": "Medium (₹₹)",
                "high": "High (₹₹₹)",
            }[b],
            help=BUDGET_HELP["medium"],
        )
        st.caption(BUDGET_HELP[budget])

        cuisine = st.selectbox(
            "Cuisine (optional)",
            options=cuisines,
            index=0,
        )

        min_rating = st.slider(
            "Minimum rating",
            min_value=0.0,
            max_value=5.0,
            value=3.5,
            step=0.1,
        )

        additional = st.text_area(
            "Additional nuances",
            value="",
            placeholder="Family-friendly, quiet ambiance, outdoor seating…",
            max_chars=500,
            height=90,
        )

        top_n = st.number_input(
            "Curated dossiers (top N)",
            min_value=1,
            max_value=10,
            value=settings.top_n_default,
            step=1,
        )

        col_submit, col_reset = st.columns([2, 1])
        submitted = col_submit.button(
            "Get recommendations", type="primary", use_container_width=True
        )
        reset = col_reset.button("Reset", use_container_width=True)

        if reset:
            st.session_state.pop("dm_results", None)
            st.session_state.pop("dm_error", None)
            st.session_state.pop("dm_prefs", None)
            st.session_state.pop("dm_empty", None)
            st.rerun()

        st.markdown(
            '<p class="dm-footer-note">Contextual LLM rationale · falls back to rating rank if offline</p>',
            unsafe_allow_html=True,
        )

    if not submitted:
        return None, False

    try:
        prefs = UserPreferences(
            location=str(location),
            budget=budget,  # type: ignore[arg-type]
            cuisine=None if cuisine == "Any" else str(cuisine),
            min_rating=float(min_rating),
            additional_preferences=additional or None,
            top_n=int(top_n),
        )
        return prefs, True
    except Exception as exc:  # noqa: BLE001
        st.session_state["dm_error"] = f"Invalid preferences: {exc}"
        return None, True
