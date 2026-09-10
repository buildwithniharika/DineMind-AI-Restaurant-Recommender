"""FastAPI application entry point — Phase 4 API."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.routes import router
from src.config.settings import get_settings
from src.data.cache import CacheError, CacheManager
from src.services.exceptions import (
    DatasetNotLoadedError,
    NoMatchesError,
    RecommendationEngineError,
)
from src.services.recommendation_service import RecommendationService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(
    *,
    recommendation_service: RecommendationService | None = None,
) -> FastAPI:
    """Build the FastAPI app.

    Pass ``recommendation_service`` to skip cache load (used by unit/integration tests).
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if recommendation_service is not None:
            app.state.recommendation_service = recommendation_service
            app.state.startup_error = None
            logger.info(
                "API ready with injected service (restaurants=%s)",
                f"{recommendation_service.restaurant_count:,}",
            )
            yield
            return

        settings = get_settings()
        cache = CacheManager(settings.processed_data_path)
        try:
            data = cache.load()
        except CacheError as exc:
            logger.error("Failed to load dataset on startup: %s", exc)
            app.state.recommendation_service = None
            app.state.startup_error = str(exc)
            yield
            return

        service = RecommendationService(
            settings=settings,
            data=data,
            allow_missing_llm=True,
        )
        app.state.recommendation_service = service
        app.state.startup_error = None
        logger.info(
            "API ready (restaurants=%s provider=%s model=%s)",
            f"{len(data):,}",
            settings.llm_provider,
            settings.llm_model,
        )
        yield

    app = FastAPI(
        title="Zomato Restaurant Recommendation API",
        description=(
            "Personalized restaurant recommendations using filtered Zomato data "
            "and an LLM ranking/explanation stage."
        ),
        version="0.4.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    _register_exception_handlers(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.info("Validation error on %s: %s", request.url.path, exc.errors())
        return JSONResponse(status_code=400, content={"detail": exc.errors()})

    @app.exception_handler(NoMatchesError)
    async def no_matches_handler(request: Request, exc: NoMatchesError) -> JSONResponse:
        logger.info("No matches for %s: %s", request.url.path, exc.message)
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(DatasetNotLoadedError)
    async def dataset_handler(request: Request, exc: DatasetNotLoadedError) -> JSONResponse:
        logger.error("Dataset unavailable on %s: %s", request.url.path, exc)
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(RecommendationEngineError)
    async def engine_handler(request: Request, exc: RecommendationEngineError) -> JSONResponse:
        logger.error("Engine failure on %s: %s", request.url.path, exc)
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, (HTTPException, StarletteHTTPException, RequestValidationError)):
            raise exc
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


app = create_app()
