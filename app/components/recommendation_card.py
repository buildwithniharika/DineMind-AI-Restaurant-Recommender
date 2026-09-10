"""Recommendation card + result-state canvases (DineMind / Stitch)."""

from __future__ import annotations

from html import escape

from src.models.preferences import UserPreferences
from src.models.recommendation import Recommendation, RecommendationResponse


def _stars(rating: float) -> str:
    full = int(rating)
    return "★" * full + ("½" if rating - full >= 0.5 else "")


def render_recommendation_card(rec: Recommendation, *, source: str) -> str:
    """Return HTML for a single ranked dossier card."""
    cuisine = escape(rec.cuisine or "Various")
    name = escape(rec.name)
    explanation = escape(rec.explanation)
    location = escape(rec.location) if rec.location else ""
    cost = f"₹{rec.estimated_cost:,} for two"
    rating = f"{rec.rating:.1f}"
    source_label = "AI ranked" if source == "llm" else "Filter ranked"
    location_bit = f"&nbsp;·&nbsp;{location}" if location else ""
    return f"""
    <article class="dm-card">
      <div class="dm-card-top">
        <span class="dm-rank">{rec.rank}</span>
        <div>
          <h2 class="dm-card-title">{name}</h2>
          <div class="dm-meta">
            <strong>{cuisine}</strong>
            &nbsp;·&nbsp;
            <strong>{_stars(rec.rating)} {rating}</strong>
            &nbsp;·&nbsp;
            {escape(cost)}{location_bit}
          </div>
        </div>
      </div>
      <div class="dm-explain">
        <span class="dm-explain-label">{escape(source_label)} rationale</span>
        “{explanation}”
      </div>
    </article>
    """


def render_initial_canvas() -> str:
    return """
    <div class="dm-canvas">
      <div class="dm-canvas-icon">🍽</div>
      <h2>Your recommendations will appear here.</h2>
      <p>
        Set your cravings and mood on the left to receive ranked dining
        recommendations with tailored rationales.
      </p>
    </div>
    """


def render_empty_canvas(prefs: UserPreferences) -> str:
    cuisine = prefs.cuisine or "any cuisine"
    return f"""
    <div class="dm-canvas">
      <div class="dm-canvas-icon">🔎</div>
      <h2>No restaurants match your criteria.</h2>
      <p>
        Nothing in <strong>{escape(prefs.location)}</strong> matched
        {escape(cuisine)}, {escape(prefs.budget)} budget, and ★{prefs.min_rating}+.
        Try broadening location, lowering the rating floor, or choosing Any cuisine.
      </p>
    </div>
    """


def render_error_canvas(message: str) -> str:
    return f"""
    <div class="dm-canvas dm-error-canvas">
      <div class="dm-canvas-icon">!</div>
      <h2>Something went wrong</h2>
      <p>{escape(message)}</p>
    </div>
    """


def render_loading_canvas(location: str) -> str:
    return f"""
    <div class="dm-canvas">
      <div class="dm-canvas-icon">✨</div>
      <h2>Finding restaurants for you…</h2>
      <p>
        Matching cuisine &amp; budget, then ranking options for
        <strong>{escape(location)}</strong>.
      </p>
    </div>
    """


def render_results(response: RecommendationResponse, prefs: UserPreferences) -> str:
    chips = f"""
    <div class="dm-chip-row">
      <span class="dm-chip">📍 {escape(prefs.location)}</span>
      <span class="dm-chip">₹ {escape(prefs.budget.title())}</span>
      <span class="dm-chip">🍽 {escape(prefs.cuisine or "Any")}</span>
      <span class="dm-chip">★ {prefs.min_rating}+</span>
    </div>
    """
    summary = ""
    if response.summary:
        summary = f'<div class="dm-summary">{escape(response.summary)}</div>'

    cards = "".join(
        render_recommendation_card(rec, source=response.source)
        for rec in response.recommendations
    )
    return chips + summary + cards
