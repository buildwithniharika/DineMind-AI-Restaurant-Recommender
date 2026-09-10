"""Phase 3: response parser tests."""

from __future__ import annotations

import pytest

from src.llm.response_parser import ParseError, ResponseParser
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
            cuisines=["Chinese"],
            average_cost_for_two=900,
            rating=4.2,
            votes=80,
        ),
    ]


def test_parse_valid_json() -> None:
    raw = """
    {
      "recommendations": [
        {
          "rank": 1,
          "restaurant_id": "r1",
          "name": "WRONG NAME",
          "cuisine": "WRONG",
          "rating": 1.0,
          "estimated_cost": 1,
          "explanation": "Great Italian for a medium budget."
        }
      ],
      "summary": "Solid Italian picks."
    }
    """
    result = ResponseParser().parse(raw, _candidates(), top_n=5)
    assert result.source == "llm"
    assert result.summary == "Solid Italian picks."
    assert len(result.recommendations) == 1
    rec = result.recommendations[0]
    # Grounded fields overwrite hallucinated values
    assert rec.restaurant_id == "r1"
    assert rec.name == "Pasta House"
    assert rec.cuisine == "Italian"
    assert rec.rating == 4.5
    assert rec.estimated_cost == 800
    assert "Italian" in rec.explanation


def test_parse_fenced_json() -> None:
    raw = """```json
{"recommendations":[{"restaurant_id":"r2","explanation":"Fits Chinese craving."}],"summary":null}
```"""
    result = ResponseParser().parse(raw, _candidates(), top_n=5)
    assert result.recommendations[0].restaurant_id == "r2"
    assert result.recommendations[0].name == "Noodle Bar"
    assert result.summary is None


def test_parse_malformed_json_raises() -> None:
    with pytest.raises(ParseError):
        ResponseParser().parse("not json at all", _candidates(), top_n=5)


def test_drops_hallucinated_ids_and_caps_top_n() -> None:
    raw = """
    {
      "recommendations": [
        {"restaurant_id": "fake", "explanation": "nope"},
        {"restaurant_id": "r1", "explanation": "first"},
        {"restaurant_id": "r2", "explanation": "second"},
        {"restaurant_id": "r1", "explanation": "dup"}
      ]
    }
    """
    result = ResponseParser().parse(raw, _candidates(), top_n=1)
    assert len(result.recommendations) == 1
    assert result.recommendations[0].restaurant_id == "r1"
    assert result.recommendations[0].rank == 1


def test_drops_duplicate_brand_names_with_different_ids() -> None:
    candidates = [
        Restaurant(
            id="pg-1",
            name="Punjab Grill",
            location="Malleshwaram",
            cuisines=["North Indian", "Mughlai"],
            average_cost_for_two=2000,
            rating=4.9,
            votes=1985,
        ),
        Restaurant(
            id="pg-2",
            name="Punjab Grill",
            location="Whitefield",
            cuisines=["North Indian"],
            average_cost_for_two=2000,
            rating=4.9,
            votes=518,
        ),
    ]
    raw = """
    {
      "recommendations": [
        {"restaurant_id": "pg-1", "explanation": "Premium North Indian."},
        {"restaurant_id": "pg-2", "explanation": "Another branch."}
      ]
    }
    """
    result = ResponseParser().parse(raw, candidates, top_n=5)
    assert len(result.recommendations) == 1
    assert result.recommendations[0].restaurant_id == "pg-1"
    assert result.recommendations[0].location == "Malleshwaram"


def test_all_hallucinated_raises() -> None:
    raw = '{"recommendations":[{"restaurant_id":"ghost","explanation":"x"}]}'
    with pytest.raises(ParseError, match="No recommendations"):
        ResponseParser().parse(raw, _candidates(), top_n=5)
