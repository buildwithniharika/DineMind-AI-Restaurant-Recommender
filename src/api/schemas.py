"""API request/response schemas beyond core domain models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    dataset_loaded: bool
    restaurant_count: int = Field(ge=0)


class MetadataResponse(BaseModel):
    locations: list[str]
    cuisines: list[str]
    budgets: list[str]
    cities: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
