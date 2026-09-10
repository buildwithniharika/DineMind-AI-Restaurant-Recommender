"""Rule-based ranking when the LLM is unavailable or returns invalid output."""

from __future__ import annotations

from src.models.preferences import UserPreferences
from src.models.recommendation import Recommendation, RecommendationResponse
from src.models.restaurant import Restaurant

FALLBACK_EXPLANATION = (
    "Rated {rating}/5 and fits your {budget} budget in {location}."
)


def build_fallback_response(
    preferences: UserPreferences,
    candidates: list[Restaurant],
) -> RecommendationResponse:
    """Sort candidates by rating (then votes) and return top N with template explanations."""
    ranked = sorted(
        candidates,
        key=lambda r: (r.rating, r.votes),
        reverse=True,
    )
    recommendations: list[Recommendation] = []
    seen_names: set[str] = set()
    for restaurant in ranked:
        if len(recommendations) >= preferences.top_n:
            break
        name_key = restaurant.name.casefold()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        cuisine = ", ".join(restaurant.cuisines) if restaurant.cuisines else "Unknown"
        recommendations.append(
            Recommendation(
                rank=len(recommendations) + 1,
                restaurant_id=restaurant.id,
                name=restaurant.name,
                cuisine=cuisine,
                rating=restaurant.rating,
                estimated_cost=restaurant.average_cost_for_two,
                explanation=FALLBACK_EXPLANATION.format(
                    rating=restaurant.rating,
                    budget=preferences.budget,
                    location=preferences.location,
                ),
                location=restaurant.location,
            )
        )

    summary = None
    if recommendations:
        summary = (
            f"Top {len(recommendations)} options in {preferences.location} "
            f"for a {preferences.budget} budget (rule-based ranking)."
        )

    return RecommendationResponse(
        recommendations=recommendations,
        summary=summary,
        source="fallback",
    )
