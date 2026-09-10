#!/usr/bin/env python3
"""Phase 3 demo: filter → LLM (or fallback) → ranked recommendations with explanations."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import get_settings
from src.data.cache import CacheManager
from src.filters.restaurant_filter import RestaurantFilter
from src.models.preferences import UserPreferences
from src.services.recommendation_service import RecommendationService

SAMPLES = [
    UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        additional_preferences="romantic ambience",
        top_n=3,
    ),
    UserPreferences(
        location="Koramangala",
        budget="low",
        cuisine=None,
        min_rating=3.5,
        additional_preferences="quick lunch",
        top_n=3,
    ),
    UserPreferences(
        location="Indiranagar",
        budget="high",
        cuisine="North Indian",
        min_rating=4.0,
        additional_preferences="family-friendly",
        top_n=3,
    ),
    UserPreferences(
        location="HSR",
        budget="medium",
        cuisine="Chinese",
        min_rating=4.2,
        top_n=2,
    ),
    UserPreferences(
        location="InvalidCity",
        budget="medium",
        cuisine="Any",
        min_rating=3.0,
        top_n=3,
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo Phase 3 LLM / fallback recommendations")
    parser.add_argument(
        "--fallback-only",
        action="store_true",
        help="Skip LLM and always use rule-based ranking",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    settings = get_settings()
    cache = CacheManager(settings.processed_data_path)
    if not cache.exists():
        print(f"Cache missing at {cache.path}. Run: python scripts/prepare_data.py")
        return 1

    data = cache.load()
    print(f"Loaded {len(data):,} restaurants")
    print(f"Provider: {settings.llm_provider} | model: {settings.llm_model}")
    if args.fallback_only:
        print("Mode: fallback-only\n")
    else:
        print("Mode: LLM with fallback\n")

    filter_engine = RestaurantFilter(settings)
    if args.fallback_only:
        service = RecommendationService(settings=settings, llm_client=None)
    else:
        service = RecommendationService(settings=settings, allow_missing_llm=True)

    for prefs in SAMPLES:
        cuisine = prefs.cuisine or "Any"
        print(
            f"Query: location={prefs.location!r}, budget={prefs.budget}, "
            f"cuisine={cuisine!r}, min_rating={prefs.min_rating}, top_n={prefs.top_n}"
        )
        if prefs.additional_preferences:
            print(f"  additional: {prefs.additional_preferences!r}")

        candidates = filter_engine.filter(data, prefs)
        print(f"  Candidates after filter: {len(candidates)}")
        if not candidates:
            print("  (empty — no matches)\n")
            continue

        response = service.recommend_from_candidates(prefs, candidates)
        print(f"  Source: {response.source}")
        if response.summary:
            print(f"  Summary: {response.summary}")
        for rec in response.recommendations:
            print(
                f"    #{rec.rank} {rec.name} | {rec.cuisine} | "
                f"{rec.rating}/5 | ₹{rec.estimated_cost}"
            )
            print(f"       {rec.explanation}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
