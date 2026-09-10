"""Phase 1: preprocessor unit tests."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data.preprocessor import (
    normalize_location,
    parse_cost,
    parse_cuisines,
    parse_rating,
    parse_votes,
    preprocess_restaurants,
    restaurant_id,
)
from src.data.schema import SchemaMapper, SchemaMismatchError

RAW_COLUMNS = {
    "name": ["Jalsa", "Spice", "Cafe A", "NEW Place", "Dup A", "Dup A", None, "Zero Cost"],
    "location": ["banashankari", "Koramangala", "  HSR Layout ", "Indiranagar", "Whitefield", "Whitefield", "BTM", "BTM"],
    "cuisines": [
        "North Indian, Mughlai",
        "Italian, Chinese",
        "NA",
        "Cafe",
        "South Indian",
        "South Indian, Chinese",
        "Biryani",
        "Fast Food",
    ],
    "approx_cost(for two people)": ["800", "1,200", "500", "400", "600", "650", "300", "0"],
    "rate": ["4.1/5", "4.5/5", "3.8/5", "NEW", "4.0/5", "3.2/5", "4.0/5", "3.5/5"],
    "votes": [775, 1200, 10, 0, 50, 999, 20, 5],
    "address": ["942, 21st Main", "Koramangala", None, "Indiranagar", "WF", "WF", "BTM", "BTM"],
    "rest_type": ["Casual Dining", "Casual Dining", "Cafe", "Cafe", "Quick Bites", "Quick Bites", "Quick Bites", "Quick Bites"],
}


def test_schema_mapper_renames_raw_columns():
    raw = pd.DataFrame(RAW_COLUMNS)
    mapped = SchemaMapper().to_internal(raw)
    assert "average_cost_for_two" in mapped.columns
    assert "rating" in mapped.columns
    assert "name" in mapped.columns


def test_schema_mismatch_fails_fast():
    raw = pd.DataFrame({"foo": [1], "bar": [2]})
    with pytest.raises(SchemaMismatchError, match="Missing"):
        SchemaMapper().resolve(raw.columns)


def test_parse_cuisines_splits_and_trims():
    assert parse_cuisines("Italian, Chinese") == ["Italian", "Chinese"]
    assert parse_cuisines("  North Indian ,  Mughlai ") == ["North Indian", "Mughlai"]


def test_parse_cuisines_sentinels_are_empty():
    assert parse_cuisines(None) == []
    assert parse_cuisines("NA") == []
    assert parse_cuisines("-") == []
    assert parse_cuisines("None") == []


def test_parse_cost_handles_commas_and_currency():
    assert parse_cost("1,200") == 1200
    assert parse_cost("Rs. 800") == 800
    assert parse_cost("₹1,500") == 1500
    assert parse_cost(900) == 900


def test_parse_cost_drops_invalid():
    assert parse_cost("0") is None
    assert parse_cost(-10) is None
    assert parse_cost("999999") is None
    assert parse_cost("") is None


def test_parse_rating_from_zomato_string():
    assert parse_rating("4.1/5") == 4.1
    assert parse_rating(4.5) == 4.5


def test_parse_rating_drops_new_and_clamps():
    assert parse_rating("NEW") is None
    assert parse_rating("-") is None
    assert parse_rating(5.5) == 5.0
    assert parse_rating(-1) == 0.0


def test_parse_votes_defaults_to_zero():
    assert parse_votes(None) == 0
    assert parse_votes("1,234") == 1234


def test_preprocessor_drops_missing_name_location_rating():
    raw = pd.DataFrame(RAW_COLUMNS)
    result = preprocess_restaurants(raw)
    names = set(result["name"])
    assert "NEW Place" not in names  # NEW rating dropped
    assert None not in names
    assert result["name"].notna().all()
    assert result["location"].notna().all()
    assert result["rating"].notna().all()


def test_preprocessor_deduplicates_keeping_highest_rating():
    raw = pd.DataFrame(RAW_COLUMNS)
    result = preprocess_restaurants(raw)
    dup = result[result["name"] == "Dup A"]
    assert len(dup) == 1
    assert float(dup.iloc[0]["rating"]) == 4.0  # 4.0/5 beats 3.2/5


def test_preprocessor_normalizes_location_case():
    raw = pd.DataFrame(RAW_COLUMNS)
    result = preprocess_restaurants(raw)
    locations = set(result["location"])
    assert "Banashankari" in locations
    assert "HSR Layout" in locations  # mixed-case preserved


def test_normalize_location_preserves_short_acronyms():
    assert normalize_location("BTM") == "BTM"
    assert normalize_location("HSR") == "HSR"
    assert normalize_location("banashankari") == "Banashankari"
    assert normalize_location("KORAMANGALA") == "Koramangala"


def test_preprocessor_parses_cuisines_and_cost():
    raw = pd.DataFrame(RAW_COLUMNS)
    result = preprocess_restaurants(raw)
    jalsa = result[result["name"] == "Jalsa"].iloc[0]
    assert jalsa["cuisines"] == ["North Indian", "Mughlai"]
    assert int(jalsa["average_cost_for_two"]) == 800
    cafe = result[result["name"] == "Cafe A"].iloc[0]
    assert cafe["cuisines"] == []


def test_preprocessor_assigns_stable_unique_ids():
    raw = pd.DataFrame(RAW_COLUMNS)
    a = preprocess_restaurants(raw)
    b = preprocess_restaurants(raw)
    assert a["id"].is_unique
    assert list(a["id"]) == list(b["id"])
    row = a[a["name"] == "Jalsa"].iloc[0]
    assert row["id"] == restaurant_id("Jalsa", "Banashankari")


def test_preprocessor_required_columns_present():
    result = preprocess_restaurants(pd.DataFrame(RAW_COLUMNS))
    for column in ("id", "name", "location", "cuisines", "average_cost_for_two", "rating"):
        assert column in result.columns


def test_preprocessor_drops_zero_cost():
    result = preprocess_restaurants(pd.DataFrame(RAW_COLUMNS))
    assert "Zero Cost" not in set(result["name"])
