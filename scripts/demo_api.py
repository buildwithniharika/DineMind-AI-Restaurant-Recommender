#!/usr/bin/env python3
"""Phase 4 demo: exercise health, metadata, and recommendations endpoints."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Call Phase 4 API endpoints")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--location", default="Bangalore")
    parser.add_argument("--budget", default="medium")
    parser.add_argument("--cuisine", default="Italian")
    parser.add_argument("--min-rating", type=float, default=4.0)
    parser.add_argument("--top-n", type=int, default=3)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    with httpx.Client(base_url=base, timeout=60.0) as client:
        print("=== GET /health ===")
        health = client.get("/health")
        print(health.status_code, json.dumps(health.json(), indent=2))
        if health.status_code != 200:
            return 1

        print("\n=== GET /api/metadata ===")
        meta = client.get("/api/metadata")
        print(meta.status_code)
        body = meta.json()
        print(
            f"locations={len(body.get('locations', []))} "
            f"cuisines={len(body.get('cuisines', []))} "
            f"budgets={body.get('budgets')}"
        )
        if meta.status_code != 200:
            return 1

        payload = {
            "location": args.location,
            "budget": args.budget,
            "cuisine": args.cuisine,
            "min_rating": args.min_rating,
            "additional_preferences": "family-friendly",
            "top_n": args.top_n,
        }
        print("\n=== POST /api/recommendations ===")
        print("request:", json.dumps(payload))
        rec = client.post("/api/recommendations", json=payload)
        print(rec.status_code)
        print(json.dumps(rec.json(), indent=2))
        return 0 if rec.status_code in {200, 404} else 1


if __name__ == "__main__":
    raise SystemExit(main())
