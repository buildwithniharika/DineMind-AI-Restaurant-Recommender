"""Deterministic restaurant preference filtering."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config.settings import Settings, get_settings
from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant


def extract_metadata(data: pd.DataFrame) -> dict[str, list[str]]:
    """Return sorted unique locations, cities, cuisines, and budget labels for UI dropdowns."""
    locations: set[str] = set()
    if "location" in data.columns:
        locations.update(str(v) for v in data["location"].dropna().unique() if str(v).strip())

    cities: set[str] = set()
    if "city" in data.columns:
        cities.update(str(v) for v in data["city"].dropna().unique() if str(v).strip())

    cuisines: set[str] = set()
    if "cuisines" in data.columns:
        for items in data["cuisines"]:
            if items is None:
                continue
            if isinstance(items, str):
                parts = [p.strip() for p in items.split(",") if p.strip()]
            else:
                parts = [str(p).strip() for p in items if str(p).strip()]
            cuisines.update(parts)

    return {
        "locations": sorted(locations, key=str.casefold),
        "cities": sorted(cities, key=str.casefold),
        "cuisines": sorted(cuisines, key=str.casefold),
        "budgets": ["low", "medium", "high"],
    }


class RestaurantFilter:
    """Apply hard preference constraints and return ranked LLM candidates."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def filter(
        self,
        data: pd.DataFrame,
        preferences: UserPreferences,
        *,
        limit: int | None = None,
    ) -> list[Restaurant]:
        """Filter restaurants and return at most `limit` (default: settings.max_candidates)."""
        if data.empty:
            return []

        cap = self.settings.max_candidates if limit is None else limit
        if cap <= 0:
            return []

        frame = data.copy()
        frame = self._filter_location(frame, preferences.location)
        if frame.empty:
            return []

        frame = frame[frame["rating"] >= preferences.min_rating]
        if frame.empty:
            return []

        frame = self._filter_budget(frame, preferences.budget)
        if frame.empty:
            return []

        if preferences.cuisine:
            frame = self._filter_cuisine(frame, preferences.cuisine)
            if frame.empty:
                return []

        sort_cols = ["rating"]
        ascending = [False]
        if "votes" in frame.columns:
            sort_cols.append("votes")
            ascending.append(False)
        frame = frame.sort_values(sort_cols, ascending=ascending)

        # One dossier per brand name — keep the best-rated branch (chains often
        # repeat across localities under city-wide searches like "Bangalore").
        frame = frame.assign(_name_key=frame["name"].astype(str).str.casefold())
        frame = frame.drop_duplicates(subset=["_name_key"], keep="first")
        frame = frame.drop(columns=["_name_key"])

        frame = frame.head(cap)
        return [Restaurant.from_row(row) for _, row in frame.iterrows()]

    def _filter_location(self, frame: pd.DataFrame, location: str) -> pd.DataFrame:
        query = location.strip().casefold()
        if not query:
            return frame.iloc[0:0]

        location_hit = frame["location"].astype(str).str.casefold().str.contains(query, regex=False)
        if "city" in frame.columns:
            city_hit = frame["city"].astype(str).str.casefold().str.contains(query, regex=False)
            return frame[location_hit | city_hit]
        return frame[location_hit]

    def _filter_budget(self, frame: pd.DataFrame, budget: str) -> pd.DataFrame:
        min_cost, max_cost = self.settings.budget_range(budget)  # type: ignore[arg-type]
        costs = frame["average_cost_for_two"]
        mask = pd.Series(True, index=frame.index)
        if min_cost is not None:
            mask &= costs >= min_cost
        if max_cost is not None:
            mask &= costs <= max_cost
        return frame[mask]

    @staticmethod
    def _filter_cuisine(frame: pd.DataFrame, cuisine: str) -> pd.DataFrame:
        """Keep rows where any cuisine token equals the preference (case-insensitive)."""
        target = cuisine.strip().casefold()

        def matches(value: Any) -> bool:
            if value is None:
                return False
            if isinstance(value, str):
                tokens = [part.strip().casefold() for part in value.split(",") if part.strip()]
            else:
                tokens = [str(part).strip().casefold() for part in value if str(part).strip()]
            return target in tokens

        mask = frame["cuisines"].map(matches)
        return frame[mask]
