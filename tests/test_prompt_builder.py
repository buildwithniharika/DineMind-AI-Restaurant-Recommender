"""Phase 3: prompt builder tests."""

from __future__ import annotations

import json

from src.config.settings import Settings
from src.llm.prompt_builder import FORMAT_REMINDER, PromptBuilder
from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant


def _candidates() -> list[Restaurant]:
    return [
        Restaurant(
            id="r1",
            name="Pasta House",
            location="Koramangala",
            cuisines=["Italian"],
            average_cost_for_two=800,
            rating=4.5,
            votes=100,
        ),
        Restaurant(
            id="r2",
            name="Noodle Bar",
            location="Indiranagar",
            cuisines=["Chinese", "Thai"],
            average_cost_for_two=900,
            rating=4.2,
            votes=80,
        ),
    ]


def test_prompt_contains_preferences_and_candidates() -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        additional_preferences="family-friendly",
        top_n=3,
    )
    built = PromptBuilder(Settings()).build(prefs, _candidates())

    assert "restaurant recommendation assistant" in built.system.casefold()
    assert "Bangalore" in built.user
    assert "medium" in built.user
    assert "Italian" in built.user
    assert "4.0" in built.user
    assert "family-friendly" in built.user
    assert "top 3" in built.user.casefold() or "top 3" in built.user
    assert "Pasta House" in built.user
    assert "Noodle Bar" in built.user
    assert '"id":"r1"' in built.user or '"id": "r1"' in built.user
    # Compact payload: cost key, not average_cost_for_two
    assert "average_cost_for_two" not in built.user
    assert "votes" not in built.user


def test_prompt_budget_range_and_any_cuisine() -> None:
    prefs = UserPreferences(location="Koramangala", budget="low", cuisine=None, top_n=5)
    built = PromptBuilder(Settings()).build(prefs, _candidates())
    assert "≤ ₹500" in built.user
    assert "Cuisine: Any" in built.user
    assert "Additional Preferences: None" in built.user


def test_compact_candidate_json_is_valid() -> None:
    prefs = UserPreferences(location="HSR", budget="high", cuisine="Chinese", top_n=2)
    built = PromptBuilder(Settings()).build(prefs, _candidates())
    # Extract the candidate JSON array line after the header
    marker = "Candidate Restaurants:\n"
    assert marker in built.user
    after = built.user.split(marker, 1)[1]
    json_line = after.split("\n", 1)[0]
    payload = json.loads(json_line)
    assert payload[0]["id"] == "r1"
    assert set(payload[0].keys()) == {"id", "name", "cuisine", "rating", "cost"}


def test_format_reminder_appended_on_retry() -> None:
    prefs = UserPreferences(location="BTM", budget="medium", top_n=1)
    builder = PromptBuilder(Settings())
    original = builder.build(prefs, _candidates())
    retry = builder.with_format_reminder(original)
    assert retry.system == original.system
    assert original.user in retry.user
    assert FORMAT_REMINDER in retry.user
