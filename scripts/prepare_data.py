#!/usr/bin/env python3
"""Download, preprocess, and cache the Zomato restaurant dataset (Phase 1)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import get_settings
from src.data.cache import CacheManager
from src.data.loader import DatasetLoader
from src.data.preprocessor import preprocess_restaurants

# Plan target after quality filters. Unique name+location rows are typically lower
# because the raw dump repeats restaurants across listing types.
PLAN_RECORD_TARGET = 40_000
MIN_RECORD_FLOOR = 1_000


def _unique_cuisines(frame) -> list[str]:
    values: set[str] = set()
    for items in frame["cuisines"]:
        values.update(items)
    return sorted(values)


def _print_samples(frame, n: int = 5) -> None:
    print(f"\nSample of {n} cleaned records:")
    sample = frame.head(n)
    for _, row in sample.iterrows():
        payload = {
            "id": row["id"],
            "name": row["name"],
            "location": row["location"],
            "city": row.get("city", ""),
            "cuisines": list(row["cuisines"])[:5],
            "average_cost_for_two": int(row["average_cost_for_two"]),
            "rating": float(row["rating"]),
        }
        print(" ", json.dumps(payload, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the Zomato restaurant cache")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild the processed Parquet even if it already exists",
    )
    args = parser.parse_args()

    settings = get_settings()
    cache = CacheManager(settings.processed_data_path)

    if cache.exists() and not args.force:
        print(f"Processed cache already exists at {cache.path}")
        print("Re-run with --force to rebuild from Hugging Face (uses the local HF cache).")
        data = cache.load()
        print(f"Cached records: {len(data):,}")
        _print_samples(data)
        print(f"\nUnique locations: {data['location'].nunique():,}")
        print(f"Unique cities: {data['city'].nunique() if 'city' in data.columns else 0:,}")
        print(f"Unique cuisines: {len(_unique_cuisines(data)):,}")
        return 0

    print(f"Loading dataset: {settings.hf_dataset_id}")
    print("First run downloads ~574 MB; later runs reuse the Hugging Face cache.")
    started = time.perf_counter()
    raw = DatasetLoader(settings).load()
    download_s = time.perf_counter() - started
    print(f"Raw rows: {len(raw):,}  ({download_s:.1f}s)")

    print("Preprocessing (clean, parse, dedupe)...")
    started = time.perf_counter()
    processed = preprocess_restaurants(raw)
    preprocess_s = time.perf_counter() - started
    print(f"Processed rows: {len(processed):,}  ({preprocess_s:.1f}s)")

    if len(processed) < MIN_RECORD_FLOOR:
        print(
            f"ERROR: only {len(processed):,} restaurants after cleaning "
            f"(minimum {MIN_RECORD_FLOOR:,}). Aborting."
        )
        return 1

    if len(processed) < PLAN_RECORD_TARGET:
        print(
            f"NOTE: {len(processed):,} unique restaurants after name+location dedupe "
            f"(plan target was ≥ {PLAN_RECORD_TARGET:,} raw-quality rows). "
            "The HF dump lists the same venue under multiple types, so unique count is lower."
        )

    cache.save(processed)
    print(f"Wrote cache: {cache.path}")

    reload_started = time.perf_counter()
    reloaded = cache.load()
    reload_s = time.perf_counter() - reload_started
    print(f"Cache reload: {len(reloaded):,} rows in {reload_s:.3f}s")

    _print_samples(processed)
    print(f"\nUnique locations (localities): {processed['location'].nunique():,}")
    print(f"Unique cities: {processed['city'].nunique():,}")
    print(f"Unique cuisines: {len(_unique_cuisines(processed)):,}")
    print("\nPhase 1 data preparation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
