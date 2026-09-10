#!/usr/bin/env python3
"""Phase 2 demo: run RestaurantFilter on sample preference sets against the cache."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import get_settings
from src.data.cache import CacheManager
from src.filters.restaurant_filter import RestaurantFilter, extract_metadata
from src.models.preferences import UserPreferences

SAMPLES = [
    UserPreferences(location="Bangalore", budget="medium", cuisine="Italian", min_rating=4.0),
    UserPreferences(location="Koramangala", budget="low", cuisine=None, min_rating=3.5),
    UserPreferences(location="InvalidCity", budget="medium", cuisine="Any", min_rating=3.0),
]


def main() -> int:
    settings = get_settings()
    cache = CacheManager(settings.processed_data_path)
    if not cache.exists():
        print(f"Cache missing at {cache.path}. Run: python scripts/prepare_data.py")
        return 1

    data = cache.load()
    meta = extract_metadata(data)
    print(f"Loaded {len(data):,} restaurants")
    print(
        f"Metadata: {len(meta['locations'])} locations, "
        f"{len(meta['cities'])} cities, {len(meta['cuisines'])} cuisines\n"
    )

    engine = RestaurantFilter(settings)
    for prefs in SAMPLES:
        candidates = engine.filter(data, prefs)
        cuisine = prefs.cuisine or "Any"
        print(
            f"Query: location={prefs.location!r}, budget={prefs.budget}, "
            f"cuisine={cuisine!r}, min_rating={prefs.min_rating}"
        )
        print(f"  Candidates: {len(candidates)}")
        for restaurant in candidates[:5]:
            print(
                f"    - {restaurant.name} | {restaurant.location} | "
                f"{', '.join(restaurant.cuisines[:3])} | "
                f"₹{restaurant.average_cost_for_two} | {restaurant.rating}/5"
            )
        if not candidates:
            print("    (empty — no matches)")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
