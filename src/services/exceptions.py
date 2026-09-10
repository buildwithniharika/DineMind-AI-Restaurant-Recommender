"""Domain/service exceptions mapped to HTTP status codes in the API layer."""

from __future__ import annotations


class DatasetNotLoadedError(RuntimeError):
    """Raised when the restaurant dataset is not available in memory."""


class NoMatchesError(LookupError):
    """Raised when filtering yields no candidate restaurants."""

    def __init__(self, message: str = "No restaurants match your criteria.") -> None:
        super().__init__(message)
        self.message = message


class RecommendationEngineError(RuntimeError):
    """Raised when recommendation generation fails after LLM and fallback attempts."""
