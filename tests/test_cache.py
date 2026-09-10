"""Phase 1: cache save/load round-trip tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data.cache import CacheError, CacheManager
from src.data.preprocessor import preprocess_restaurants

RAW = pd.DataFrame(
    {
        "name": ["Jalsa", "Truffles"],
        "location": ["Banashankari", "Koramangala"],
        "cuisines": ["North Indian, Mughlai", "Italian, Continental"],
        "approx_cost(for two people)": ["800", "1,200"],
        "rate": ["4.1/5", "4.5/5"],
        "votes": [775, 1500],
        "address": ["942, 21st Main", "Koramangala 5th Block"],
        "rest_type": ["Casual Dining", "Cafe"],
    }
)


def test_cache_round_trip(tmp_path: Path):
    processed = preprocess_restaurants(RAW)
    cache = CacheManager(tmp_path / "restaurants.parquet")
    cache.save(processed)

    assert cache.exists()
    loaded = cache.load()

    assert len(loaded) == len(processed)
    assert list(loaded["id"]) == list(processed["id"])
    assert set(loaded["name"]) == {"Jalsa", "Truffles"}
    jalsa = loaded[loaded["name"] == "Jalsa"].iloc[0]
    assert list(jalsa["cuisines"]) == ["North Indian", "Mughlai"]
    assert int(jalsa["average_cost_for_two"]) == 800
    assert float(jalsa["rating"]) == pytest.approx(4.1)


def test_cache_missing_file_raises(tmp_path: Path):
    cache = CacheManager(tmp_path / "missing.parquet")
    with pytest.raises(CacheError, match="not found"):
        cache.load()


def test_cache_rejects_incomplete_schema(tmp_path: Path):
    cache = CacheManager(tmp_path / "bad.parquet")
    with pytest.raises(CacheError, match="missing columns"):
        cache.save(pd.DataFrame({"name": ["x"]}))
