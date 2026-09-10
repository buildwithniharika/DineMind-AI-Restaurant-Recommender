"""FastAPI route handlers."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.schemas import ErrorResponse, HealthResponse, MetadataResponse
from src.models.preferences import UserPreferences
from src.models.recommendation import RecommendationResponse
from src.services.exceptions import DatasetNotLoadedError
from src.services.recommendation_service import RecommendationService

router = APIRouter()


def _service(request: Request) -> RecommendationService:
    service: RecommendationService | None = getattr(request.app.state, "recommendation_service", None)
    if service is None:
        raise DatasetNotLoadedError("Recommendation service is not initialized")
    return service


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Health check",
)
def health(request: Request) -> HealthResponse:
    service = getattr(request.app.state, "recommendation_service", None)
    loaded = bool(service and service.dataset_loaded)
    count = service.restaurant_count if service else 0
    return HealthResponse(status="ok", dataset_loaded=loaded, restaurant_count=count)


@router.get(
    "/api/metadata",
    response_model=MetadataResponse,
    responses={503: {"model": ErrorResponse}},
    tags=["recommendations"],
    summary="Locations, cuisines, and budget options",
)
def metadata(request: Request) -> MetadataResponse:
    meta = _service(request).metadata()
    return MetadataResponse(
        locations=meta.get("locations", []),
        cuisines=meta.get("cuisines", []),
        budgets=meta.get("budgets", ["low", "medium", "high"]),
        cities=meta.get("cities", []),
    )


@router.post(
    "/api/recommendations",
    response_model=RecommendationResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    tags=["recommendations"],
    summary="Generate personalized restaurant recommendations",
)
def recommendations(preferences: UserPreferences, request: Request) -> RecommendationResponse:
    return _service(request).recommend(preferences)
