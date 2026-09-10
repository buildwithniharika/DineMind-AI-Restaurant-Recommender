"""Phase 2: restaurant filter and preference validation tests."""

from __future__ import annotations

import pandas as pd
import pytest
from pydantic import ValidationError

from src.config.settings import Settings
from src.filters.restaurant_filter import RestaurantFilter, extract_metadata
from src.models.preferences import UserPreferences


def _sample_frame() -> pd.DataFrame:
    """Synthetic restaurants covering localities, city, budgets, and cuisines."""
    rows = []
    # Bangalore city-wide matches via city field; Italian medium-budget options
    for i in range(5):
        rows.append(
            {
                "id": f"it-{i}",
                "name": f"Italian Spot {i}",
                "location": "Koramangala 5th Block" if i % 2 == 0 else "Indiranagar",
                "city": "Bangalore",
                "cuisines": ["Italian", "Continental"],
                "average_cost_for_two": 800 + i * 50,  # medium: 501–1500
                "rating": 4.5 - i * 0.1,
                "votes": 1000 - i * 10,
            }
        )
    # Low budget
    rows.append(
        {
            "id": "low-1",
            "name": "Cheap Eats",
            "location": "BTM",
            "city": "Bangalore",
            "cuisines": ["South Indian"],
            "average_cost_for_two": 300,
            "rating": 4.0,
            "votes": 200,
        }
    )
    # Budget boundary: exactly 500 → low; 501 → medium; 1500 → medium; 1501 → high
    rows.extend(
        [
            {
                "id": "bound-500",
                "name": "Exactly 500",
                "location": "HSR",
                "city": "Bangalore",
                "cuisines": ["Cafe"],
                "average_cost_for_two": 500,
                "rating": 4.2,
                "votes": 50,
            },
            {
                "id": "bound-501",
                "name": "Exactly 501",
                "location": "HSR",
                "city": "Bangalore",
                "cuisines": ["Cafe"],
                "average_cost_for_two": 501,
                "rating": 4.2,
                "votes": 40,
            },
            {
                "id": "bound-1500",
                "name": "Exactly 1500",
                "location": "HSR",
                "city": "Bangalore",
                "cuisines": ["Cafe"],
                "average_cost_for_two": 1500,
                "rating": 4.2,
                "votes": 30,
            },
            {
                "id": "bound-1501",
                "name": "Exactly 1501",
                "location": "HSR",
                "city": "Bangalore",
                "cuisines": ["Cafe"],
                "average_cost_for_two": 1501,
                "rating": 4.2,
                "votes": 20,
            },
        ]
    )
    # High budget Chinese
    rows.append(
        {
            "id": "high-cn",
            "name": "Premium Chinese",
            "location": "MG Road",
            "city": "Bangalore",
            "cuisines": ["Chinese", "Asian"],
            "average_cost_for_two": 2000,
            "rating": 4.6,
            "votes": 800,
        }
    )
    # Low rating (should be excluded when min_rating=4.0)
    rows.append(
        {
            "id": "low-rate",
            "name": "Meh Italian",
            "location": "Koramangala",
            "city": "Bangalore",
            "cuisines": ["Italian"],
            "average_cost_for_two": 700,
            "rating": 3.2,
            "votes": 10,
        }
    )
    # Many high-rated North Indian for candidate-cap test
    for i in range(40):
        rows.append(
            {
                "id": f"ni-{i}",
                "name": f"North Indian {i}",
                "location": "Whitefield",
                "city": "Bangalore",
                "cuisines": ["North Indian"],
                "average_cost_for_two": 600,
                "rating": 4.8 - (i * 0.01),
                "votes": 500 - i,
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def restaurants() -> pd.DataFrame:
    return _sample_frame()


@pytest.fixture
def filter_engine() -> RestaurantFilter:
    return RestaurantFilter(Settings(_env_file=None))  # type: ignore[call-arg]


def test_preferences_require_location():
    with pytest.raises(ValidationError):
        UserPreferences(location="", budget="medium")  # type: ignore[arg-type]


def test_preferences_reject_invalid_budget():
    with pytest.raises(ValidationError):
        UserPreferences(location="Bangalore", budget="cheap")  # type: ignore[arg-type]


def test_preferences_normalize_budget_case():
    prefs = UserPreferences(location="Bangalore", budget="MEDIUM")  # type: ignore[arg-type]
    assert prefs.budget == "medium"


def test_preferences_rating_and_top_n_bounds():
    with pytest.raises(ValidationError):
        UserPreferences(location="Bangalore", budget="low", min_rating=5.5)
    with pytest.raises(ValidationError):
        UserPreferences(location="Bangalore", budget="low", top_n=0)
    with pytest.raises(ValidationError):
        UserPreferences(location="Bangalore", budget="low", top_n=11)


def test_preferences_cuisine_any_becomes_none():
    prefs = UserPreferences(location="Bangalore", budget="low", cuisine="Any")
    assert prefs.cuisine is None


def test_location_exact_and_partial(restaurants: pd.DataFrame, filter_engine: RestaurantFilter):
    exact = filter_engine.filter(
        restaurants,
        UserPreferences(location="BTM", budget="low", cuisine=None, min_rating=3.0),
    )
    assert any(r.name == "Cheap Eats" for r in exact)

    partial = filter_engine.filter(
        restaurants,
        UserPreferences(location="Koramangala", budget="medium", cuisine="Italian", min_rating=4.0),
    )
    assert len(partial) >= 1
    assert all("Koramangala" in r.location for r in partial)


def test_location_matches_city(restaurants: pd.DataFrame, filter_engine: RestaurantFilter):
    """'Bangalore' matches via city even though location is a locality."""
    results = filter_engine.filter(
        restaurants,
        UserPreferences(location="Bangalore", budget="medium", cuisine="Italian", min_rating=4.0),
    )
    assert len(results) >= 1
    assert all("Italian" in r.cuisines for r in results)
    assert all(501 <= r.average_cost_for_two <= 1500 for r in results)
    assert all(r.rating >= 4.0 for r in results)


def test_budget_tier_boundaries(restaurants: pd.DataFrame, filter_engine: RestaurantFilter):
    low = filter_engine.filter(
        restaurants,
        UserPreferences(location="HSR", budget="low", min_rating=0.0),
    )
    low_costs = {r.average_cost_for_two for r in low}
    assert 500 in low_costs
    assert 501 not in low_costs

    medium = filter_engine.filter(
        restaurants,
        UserPreferences(location="HSR", budget="medium", min_rating=0.0),
    )
    medium_costs = {r.average_cost_for_two for r in medium}
    assert 501 in medium_costs
    assert 1500 in medium_costs
    assert 500 not in medium_costs
    assert 1501 not in medium_costs

    high = filter_engine.filter(
        restaurants,
        UserPreferences(location="HSR", budget="high", min_rating=0.0),
    )
    high_costs = {r.average_cost_for_two for r in high}
    assert 1501 in high_costs
    assert 1500 not in high_costs


def test_cuisine_case_insensitive_exact_token(
    restaurants: pd.DataFrame, filter_engine: RestaurantFilter
):
    results = filter_engine.filter(
        restaurants,
        UserPreferences(location="Bangalore", budget="high", cuisine="chinese", min_rating=4.0),
    )
    assert len(results) == 1
    assert results[0].name == "Premium Chinese"


def test_cuisine_does_not_match_substring_of_token(
    restaurants: pd.DataFrame, filter_engine: RestaurantFilter
):
    """'Indian' must not match 'North Indian' (token membership, not naive substring)."""
    results = filter_engine.filter(
        restaurants,
        UserPreferences(location="Whitefield", budget="medium", cuisine="Indian", min_rating=0.0),
    )
    assert results == []


def test_min_rating_threshold(restaurants: pd.DataFrame, filter_engine: RestaurantFilter):
    results = filter_engine.filter(
        restaurants,
        UserPreferences(location="Koramangala", budget="medium", cuisine="Italian", min_rating=4.0),
    )
    assert all(r.rating >= 4.0 for r in results)
    assert all(r.name != "Meh Italian" for r in results)


def test_candidate_cap_at_30(restaurants: pd.DataFrame, filter_engine: RestaurantFilter):
    results = filter_engine.filter(
        restaurants,
        UserPreferences(location="Whitefield", budget="medium", cuisine="North Indian", min_rating=0.0),
    )
    assert len(results) == 30
    ratings = [r.rating for r in results]
    assert ratings == sorted(ratings, reverse=True)


def test_filter_dedupes_same_name_across_locations(
    restaurants: pd.DataFrame, filter_engine: RestaurantFilter
):
    """City-wide search must not return the same chain twice from different localities."""
    extra = pd.DataFrame(
        [
            {
                "id": "pg-1",
                "name": "Punjab Grill",
                "location": "Malleshwaram",
                "city": "Bangalore",
                "cuisines": ["North Indian", "Mughlai"],
                "average_cost_for_two": 2000,
                "rating": 4.9,
                "votes": 1985,
            },
            {
                "id": "pg-2",
                "name": "Punjab Grill",
                "location": "Whitefield",
                "city": "Bangalore",
                "cuisines": ["North Indian"],
                "average_cost_for_two": 2000,
                "rating": 4.9,
                "votes": 518,
            },
        ]
    )
    frame = pd.concat([restaurants, extra], ignore_index=True)
    results = filter_engine.filter(
        frame,
        UserPreferences(location="Bangalore", budget="high", min_rating=4.0),
    )
    names = [r.name.casefold() for r in results]
    assert names.count("punjab grill") == 1
    kept = next(r for r in results if r.name == "Punjab Grill")
    assert kept.location == "Malleshwaram"  # higher votes wins the rating tie
    assert kept.id == "pg-1"


def test_empty_result_when_no_match(restaurants: pd.DataFrame, filter_engine: RestaurantFilter):
    results = filter_engine.filter(
        restaurants,
        UserPreferences(location="InvalidCity", budget="medium", min_rating=3.0),
    )
    assert results == []

    mumbai = filter_engine.filter(
        restaurants,
        UserPreferences(location="Mumbai", budget="high", cuisine="Chinese", min_rating=4.5),
    )
    assert mumbai == []


def test_extract_metadata_sorted_unique(restaurants: pd.DataFrame):
    meta = extract_metadata(restaurants)
    assert meta["budgets"] == ["low", "medium", "high"]
    assert meta["locations"] == sorted(meta["locations"], key=str.casefold)
    assert meta["cuisines"] == sorted(meta["cuisines"], key=str.casefold)
    assert "Italian" in meta["cuisines"]
    assert "Bangalore" in meta["cities"]
    assert len(meta["locations"]) == len(set(meta["locations"]))
