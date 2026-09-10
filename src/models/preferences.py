"""User preference domain model."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

BudgetTier = Literal["low", "medium", "high"]

_CUISINE_ANY = frozenset({"", "any", "all", "none", "n/a", "na", "-"})


class UserPreferences(BaseModel):
    """Validated dining preferences used by the filter and LLM stages."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    location: str = Field(min_length=1, description="City or locality to search")
    budget: BudgetTier
    cuisine: str | None = Field(default=None, description="Optional cuisine preference")
    min_rating: float = Field(default=3.0, ge=0.0, le=5.0)
    additional_preferences: str | None = Field(
        default=None,
        max_length=500,
        description="Free-text dining preferences for the LLM",
    )
    top_n: int = Field(default=5, ge=1, le=10)

    @field_validator("budget", mode="before")
    @classmethod
    def normalize_budget(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().casefold()
        return value

    @field_validator("cuisine", mode="before")
    @classmethod
    def normalize_cuisine(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if text.casefold() in _CUISINE_ANY:
            return None
        return text

    @field_validator("additional_preferences", mode="before")
    @classmethod
    def normalize_additional(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = " ".join(str(value).split())
        return text or None

    @model_validator(mode="after")
    def location_not_blank(self) -> UserPreferences:
        if not self.location.strip():
            raise ValueError("location must not be blank")
        return self
