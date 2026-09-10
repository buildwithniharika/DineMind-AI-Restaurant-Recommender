"""Recommendation orchestration: filter → LLM (or fallback) → response.

Phase 4 adds dataset binding and preference-to-response orchestration
around the Phase 3 reason/fallback path.
"""

from __future__ import annotations

import logging
import time

import pandas as pd

from src.config.settings import Settings, get_settings
from src.filters.restaurant_filter import RestaurantFilter, extract_metadata
from src.llm.client import LLMClient, LLMError, get_llm_client
from src.llm.prompt_builder import PromptBuilder
from src.llm.response_parser import ParseError, ResponseParser
from src.models.preferences import UserPreferences
from src.models.recommendation import RecommendationResponse
from src.models.restaurant import Restaurant
from src.services.exceptions import (
    DatasetNotLoadedError,
    NoMatchesError,
    RecommendationEngineError,
)
from src.services.fallback import build_fallback_response

logger = logging.getLogger(__name__)

_UNSET: object = object()


class RecommendationService:
    """Full Retrieve → Filter → Reason pipeline with rule-based fallback."""

    def __init__(
        self,
        settings: Settings | None = None,
        llm_client: LLMClient | None | object = _UNSET,
        *,
        data: pd.DataFrame | None = None,
        restaurant_filter: RestaurantFilter | None = None,
        prompt_builder: PromptBuilder | None = None,
        parser: ResponseParser | None = None,
        allow_missing_llm: bool = True,
    ) -> None:
        self.settings = settings or get_settings()
        self.prompt_builder = prompt_builder or PromptBuilder(self.settings)
        self.parser = parser or ResponseParser()
        self.filter_engine = restaurant_filter or RestaurantFilter(self.settings)
        self._data: pd.DataFrame | None = None
        if data is not None:
            self.bind_data(data)

        self._llm: LLMClient | None
        if llm_client is _UNSET:
            try:
                self._llm = get_llm_client(self.settings)
            except (LLMError, ValueError) as exc:
                if not allow_missing_llm:
                    raise
                logger.warning("LLM client unavailable (%s); fallback-only mode", exc)
                self._llm = None
        else:
            # Explicit None disables the LLM (fallback-only); otherwise use the injected client.
            self._llm = llm_client  # type: ignore[assignment]

    @property
    def dataset_loaded(self) -> bool:
        return self._data is not None and not self._data.empty

    @property
    def restaurant_count(self) -> int:
        return 0 if self._data is None else len(self._data)

    def bind_data(self, data: pd.DataFrame) -> None:
        """Attach the in-memory restaurant dataset (loaded once at app startup)."""
        if data is None or data.empty:
            raise DatasetNotLoadedError("Restaurant dataset is empty or missing")
        self._data = data
        logger.info("Bound restaurant dataset (%s rows)", f"{len(data):,}")

    def metadata(self) -> dict[str, list[str]]:
        """Return sorted locations, cuisines, and budget options for UI dropdowns."""
        if not self.dataset_loaded:
            raise DatasetNotLoadedError("Restaurant dataset is not loaded")
        assert self._data is not None
        return extract_metadata(self._data)

    def recommend(
        self,
        preferences: UserPreferences,
        *,
        include_summary: bool = True,
    ) -> RecommendationResponse:
        """Filter the dataset and rank matches via LLM (with fallback)."""
        if not self.dataset_loaded:
            raise DatasetNotLoadedError("Restaurant dataset is not loaded")
        assert self._data is not None

        logger.info(
            "Recommend request: location=%r budget=%s cuisine=%r min_rating=%s top_n=%s",
            preferences.location,
            preferences.budget,
            preferences.cuisine,
            preferences.min_rating,
            preferences.top_n,
        )

        candidates = self.filter_engine.filter(self._data, preferences)
        logger.info("Filter produced %d candidates (cap=%d)", len(candidates), self.settings.max_candidates)

        if not candidates:
            raise NoMatchesError(
                "No restaurants match your criteria. Try broadening location, "
                "budget, cuisine, or minimum rating."
            )

        try:
            return self.recommend_from_candidates(
                preferences,
                candidates,
                include_summary=include_summary,
            )
        except RecommendationEngineError:
            raise
        except Exception as exc:
            logger.exception("Recommendation engine failed unexpectedly")
            raise RecommendationEngineError(
                "Recommendation generation failed after LLM and fallback attempts."
            ) from exc

    def recommend_from_candidates(
        self,
        preferences: UserPreferences,
        candidates: list[Restaurant],
        *,
        include_summary: bool = True,
    ) -> RecommendationResponse:
        """Produce ranked recommendations from an already-filtered candidate list."""
        if not candidates:
            return RecommendationResponse(
                recommendations=[],
                summary="No restaurants match your criteria.",
                source="fallback",
            )

        if self._llm is None:
            logger.info("Using fallback ranking (no LLM client)")
            return build_fallback_response(preferences, candidates)

        prompt = self.prompt_builder.build(
            preferences,
            candidates,
            include_summary=include_summary,
        )

        try:
            raw = self._generate(prompt.system, prompt.user)
            response = self.parser.parse(
                raw,
                candidates,
                top_n=preferences.top_n,
                source="llm",
            )
            logger.info(
                "LLM recommendations ready (count=%d source=llm)",
                len(response.recommendations),
            )
            return response
        except ParseError as first_err:
            logger.warning("LLM parse failed (%s); retrying once with format reminder", first_err)
            try:
                retry_prompt = self.prompt_builder.with_format_reminder(prompt)
                raw = self._generate(retry_prompt.system, retry_prompt.user)
                response = self.parser.parse(
                    raw,
                    candidates,
                    top_n=preferences.top_n,
                    source="llm",
                )
                logger.info(
                    "LLM recommendations ready after retry (count=%d source=llm)",
                    len(response.recommendations),
                )
                return response
            except (ParseError, LLMError) as retry_err:
                logger.warning("LLM retry failed (%s); using fallback", retry_err)
                return build_fallback_response(preferences, candidates)
        except LLMError as exc:
            logger.warning("LLM call failed (%s); using fallback", exc)
            return build_fallback_response(preferences, candidates)

    def _generate(self, system: str, user: str) -> str:
        assert self._llm is not None
        started = time.perf_counter()
        text = self._llm.generate(user, system=system)
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info("LLM generate completed in %.0f ms (chars=%d)", elapsed_ms, len(text))
        return text
