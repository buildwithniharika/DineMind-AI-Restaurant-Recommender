"""Phase 3: rule-based fallback and recommendation service tests."""

from __future__ import annotations

from src.llm.client import LLMClient, LLMError
from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant
from src.services.fallback import build_fallback_response
from src.services.recommendation_service import RecommendationService


def _candidates() -> list[Restaurant]:
    return [
        Restaurant(
            id="low-rated",
            name="Okay Place",
            location="BTM",
            cuisines=["Cafe"],
            average_cost_for_two=400,
            rating=3.8,
            votes=50,
        ),
        Restaurant(
            id="top",
            name="Best Spot",
            location="BTM",
            cuisines=["Cafe"],
            average_cost_for_two=450,
            rating=4.7,
            votes=200,
        ),
        Restaurant(
            id="mid",
            name="Mid Spot",
            location="BTM",
            cuisines=["Cafe"],
            average_cost_for_two=420,
            rating=4.1,
            votes=90,
        ),
    ]


class _FakeLLM(LLMClient):
    def __init__(self, responses: list[str] | Exception) -> None:
        self._responses = responses
        self.calls = 0

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.calls += 1
        if isinstance(self._responses, Exception):
            raise self._responses
        if not self._responses:
            raise LLMError("no more responses")
        return self._responses.pop(0)


def test_fallback_returns_valid_structure_without_llm() -> None:
    prefs = UserPreferences(location="BTM", budget="low", top_n=2)
    result = build_fallback_response(prefs, _candidates())

    assert result.source == "fallback"
    assert len(result.recommendations) == 2
    assert result.recommendations[0].restaurant_id == "top"
    assert result.recommendations[0].rank == 1
    assert result.recommendations[1].restaurant_id == "mid"
    assert "Rated 4.7/5" in result.recommendations[0].explanation
    assert "low" in result.recommendations[0].explanation
    assert "BTM" in result.recommendations[0].explanation
    assert result.summary is not None
    for rec in result.recommendations:
        assert rec.name
        assert rec.cuisine
        assert rec.explanation
        assert 0 <= rec.rating <= 5
        assert rec.estimated_cost >= 0


def test_fallback_dedupes_same_brand_name() -> None:
    prefs = UserPreferences(location="Bangalore", budget="high", top_n=5)
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
        Restaurant(
            id="other",
            name="Other Place",
            location="Indiranagar",
            cuisines=["Continental"],
            average_cost_for_two=1800,
            rating=4.6,
            votes=100,
        ),
    ]
    result = build_fallback_response(prefs, candidates)
    names = [r.name for r in result.recommendations]
    assert names.count("Punjab Grill") == 1
    assert result.recommendations[0].restaurant_id == "pg-1"
    assert result.recommendations[0].location == "Malleshwaram"


def test_fallback_empty_candidates() -> None:
    prefs = UserPreferences(location="Nowhere", budget="medium", top_n=5)
    result = build_fallback_response(prefs, [])
    assert result.source == "fallback"
    assert result.recommendations == []


def test_service_uses_fallback_when_llm_unavailable() -> None:
    prefs = UserPreferences(location="BTM", budget="low", top_n=1)
    service = RecommendationService(llm_client=None)
    result = service.recommend_from_candidates(prefs, _candidates())
    assert result.source == "fallback"
    assert len(result.recommendations) == 1


def test_service_uses_llm_when_valid() -> None:
    prefs = UserPreferences(location="BTM", budget="low", top_n=1)
    payload = (
        '{"recommendations":[{"restaurant_id":"mid","explanation":"Nice cafe for low budget."}],'
        '"summary":"One solid pick."}'
    )
    fake = _FakeLLM([payload])
    service = RecommendationService(llm_client=fake)
    result = service.recommend_from_candidates(prefs, _candidates())
    assert result.source == "llm"
    assert result.recommendations[0].restaurant_id == "mid"
    assert result.summary == "One solid pick."
    assert fake.calls == 1


def test_service_retries_then_falls_back_on_parse_failure() -> None:
    prefs = UserPreferences(location="BTM", budget="low", top_n=2)
    fake = _FakeLLM(["not-json", "still-broken"])
    service = RecommendationService(llm_client=fake)
    result = service.recommend_from_candidates(prefs, _candidates())
    assert result.source == "fallback"
    assert fake.calls == 2
    assert len(result.recommendations) == 2


def test_service_succeeds_on_retry() -> None:
    prefs = UserPreferences(location="BTM", budget="low", top_n=1)
    good = '{"recommendations":[{"restaurant_id":"top","explanation":"Highest rated."}]}'
    fake = _FakeLLM(["<<<bad>>>", good])
    service = RecommendationService(llm_client=fake)
    result = service.recommend_from_candidates(prefs, _candidates())
    assert result.source == "llm"
    assert result.recommendations[0].restaurant_id == "top"
    assert fake.calls == 2


def test_service_falls_back_on_llm_error() -> None:
    prefs = UserPreferences(location="BTM", budget="low", top_n=1)
    fake = _FakeLLM(LLMError("timeout"))
    service = RecommendationService(llm_client=fake)
    result = service.recommend_from_candidates(prefs, _candidates())
    assert result.source == "fallback"
    assert result.recommendations[0].restaurant_id == "top"
