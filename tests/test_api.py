"""Phase 4: FastAPI integration tests."""

from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.config.settings import Settings
from src.llm.client import LLMClient
from src.main import create_app
from src.services.recommendation_service import RecommendationService


def _sample_frame() -> pd.DataFrame:
    rows = []
    for i in range(5):
        rows.append(
            {
                "id": f"it-{i}",
                "name": f"Italian Spot {i}",
                "location": "Koramangala 5th Block" if i % 2 == 0 else "Indiranagar",
                "city": "Bangalore",
                "cuisines": ["Italian", "Continental"],
                "average_cost_for_two": 800 + i * 50,
                "rating": 4.5 - i * 0.1,
                "votes": 1000 - i * 10,
            }
        )
    rows.append(
        {
            "id": "cn-1",
            "name": "Dragon Wok",
            "location": "HSR",
            "city": "Bangalore",
            "cuisines": ["Chinese"],
            "average_cost_for_two": 700,
            "rating": 4.3,
            "votes": 300,
        }
    )
    return pd.DataFrame(rows)


class _FakeLLM(LLMClient):
    def generate(self, prompt: str, *, system: str | None = None) -> str:
        return (
            '{"recommendations":['
            '{"restaurant_id":"it-0","explanation":"Top Italian match for your medium budget."}'
            '],"summary":"Great Italian options in Bangalore."}'
        )


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.fixture
def client(settings: Settings) -> TestClient:
    service = RecommendationService(
        settings=settings,
        data=_sample_frame(),
        llm_client=_FakeLLM(),
    )
    app = create_app(recommendation_service=service)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fallback_client(settings: Settings) -> TestClient:
    service = RecommendationService(
        settings=settings,
        data=_sample_frame(),
        llm_client=None,
    )
    app = create_app(recommendation_service=service)
    with TestClient(app) as test_client:
        yield test_client


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["dataset_loaded"] is True
    assert body["restaurant_count"] == 6


def test_metadata_returns_non_empty_locations(client: TestClient) -> None:
    response = client.get("/api/metadata")
    assert response.status_code == 200
    body = response.json()
    assert "Koramangala 5th Block" in body["locations"] or "Indiranagar" in body["locations"]
    assert "Italian" in body["cuisines"]
    assert body["budgets"] == ["low", "medium", "high"]
    assert "Bangalore" in body["cities"]


def test_recommendations_valid_input(client: TestClient) -> None:
    payload = {
        "location": "Bangalore",
        "budget": "medium",
        "cuisine": "Italian",
        "min_rating": 4.0,
        "additional_preferences": "romantic",
        "top_n": 3,
    }
    response = client.post("/api/recommendations", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "llm"
    assert 1 <= len(body["recommendations"]) <= 3
    rec = body["recommendations"][0]
    assert rec["name"]
    assert rec["cuisine"]
    assert "explanation" in rec
    assert rec["restaurant_id"] == "it-0"
    assert body["summary"]


def test_recommendations_fallback_without_llm(fallback_client: TestClient) -> None:
    payload = {
        "location": "Bangalore",
        "budget": "medium",
        "cuisine": "Italian",
        "min_rating": 4.0,
        "top_n": 2,
    }
    response = fallback_client.post("/api/recommendations", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert len(body["recommendations"]) == 2
    assert "Rated" in body["recommendations"][0]["explanation"]


def test_invalid_input_returns_400(client: TestClient) -> None:
    response = client.post(
        "/api/recommendations",
        json={"budget": "medium", "min_rating": 4.0},  # missing location
    )
    assert response.status_code == 400
    assert "detail" in response.json()


def test_invalid_budget_returns_400(client: TestClient) -> None:
    response = client.post(
        "/api/recommendations",
        json={"location": "Bangalore", "budget": "luxury"},
    )
    assert response.status_code == 400


def test_no_match_query_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/recommendations",
        json={
            "location": "InvalidCityXYZ",
            "budget": "medium",
            "cuisine": "Italian",
            "min_rating": 4.0,
            "top_n": 3,
        },
    )
    assert response.status_code == 404
    assert "No restaurants match" in response.json()["detail"]


def test_openapi_docs_available(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
