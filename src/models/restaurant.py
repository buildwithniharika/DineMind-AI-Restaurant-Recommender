"""Restaurant domain model."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Restaurant(BaseModel):
    """A single restaurant from the processed Zomato dataset."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    location: str
    cuisines: list[str] = Field(default_factory=list)
    average_cost_for_two: int = Field(ge=0)
    rating: float = Field(ge=0.0, le=5.0)
    votes: int = Field(default=0, ge=0)
    city: str = ""
    address: str = ""
    rest_type: str = ""

    @field_validator("cuisines", mode="before")
    @classmethod
    def coerce_cuisines(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return list(value)

    @classmethod
    def from_row(cls, row: pd.Series | dict[str, Any]) -> Restaurant:
        """Build a Restaurant from a DataFrame row or mapping."""
        data = row.to_dict() if isinstance(row, pd.Series) else dict(row)
        return cls.model_validate(data)
