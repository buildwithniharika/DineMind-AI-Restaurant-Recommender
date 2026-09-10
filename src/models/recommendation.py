"""Recommendation response models (Phase 3 stubs; schemas defined for API readiness)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Recommendation(BaseModel):
    """A single ranked restaurant recommendation with explanation."""

    model_config = ConfigDict(extra="ignore")

    rank: int = Field(ge=1)
    restaurant_id: str
    name: str
    cuisine: str
    rating: float = Field(ge=0.0, le=5.0)
    estimated_cost: int = Field(ge=0)
    explanation: str
    location: str = ""


class RecommendationResponse(BaseModel):
    """Full recommendation payload returned by the orchestrator / API."""

    model_config = ConfigDict(extra="ignore")

    recommendations: list[Recommendation] = Field(default_factory=list)
    summary: str | None = None
    source: Literal["llm", "fallback"] = "llm"
