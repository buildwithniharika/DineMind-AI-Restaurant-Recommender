"""Clean, normalize, and type-cast restaurant records."""

from __future__ import annotations

import hashlib
import re
from typing import Any

import pandas as pd

from src.data.schema import (
    DEFAULT_CITY,
    INTERNAL_REQUIRED_COLUMNS,
    SchemaMapper,
)

_COST_NOISE = re.compile(r"(rs\.?|inr|₹|\$)", re.IGNORECASE)
_NON_NUMERIC = re.compile(r"[^0-9.]")
_RATING_NUMBER = re.compile(r"(\d+(?:\.\d+)?)")
_CUISINE_SENTINELS = frozenset({"", "na", "n/a", "none", "-", "nan", "null", "nil"})
_MAX_REASONABLE_COST = 100_000


def parse_cuisines(value: Any) -> list[str]:
    """Split a cuisine string into a trimmed list. Empty / sentinel values → []."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, (list, tuple)):
        parts = [str(item) for item in value]
    else:
        parts = str(value).split(",")

    cuisines: list[str] = []
    seen: set[str] = set()
    for part in parts:
        item = " ".join(part.strip().split())
        if item.casefold() in _CUISINE_SENTINELS:
            continue
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            cuisines.append(item)
    return cuisines


def parse_cost(value: Any) -> int | None:
    """Normalize cost-for-two to a positive integer. Invalid / zero / huge → None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        cost = value
    elif isinstance(value, float):
        if pd.isna(value):
            return None
        cost = round(value)
    else:
        text = _COST_NOISE.sub("", str(value))
        text = text.replace(",", "").strip()
        text = _NON_NUMERIC.sub("", text)
        if not text:
            return None
        try:
            cost = round(float(text))
        except ValueError:
            return None
    if cost <= 0 or cost > _MAX_REASONABLE_COST:
        return None
    return cost


def parse_rating(value: Any) -> float | None:
    """Parse Zomato ratings ('4.1/5', 4.1). Drop NEW / '-' / missing. Clamp to 0–5."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        rating = float(value)
    else:
        text = str(value).strip()
        if text.casefold() in _CUISINE_SENTINELS | {"new"}:
            return None
        match = _RATING_NUMBER.search(text)
        if not match:
            return None
        rating = float(match.group(1))
        # "4.1/5" — if the first number is the scale (5) skip; the first is always the score.
        if rating > 5 and "/" in text:
            return None
    if rating < 0:
        return 0.0
    if rating > 5:
        return 5.0
    return round(rating, 2)


def parse_votes(value: Any) -> int:
    """Coerce votes to a non-negative int; missing → 0."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(int(value), 0)
    text = str(value).replace(",", "").strip()
    try:
        return max(int(float(text)), 0)
    except ValueError:
        return 0


def normalize_location(value: Any) -> str | None:
    """Trim whitespace; title-case all-lower (and long all-upper) values.

    Short all-caps tokens such as BTM / HSR are preserved.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = " ".join(str(value).strip().split())
    if not text or text.casefold() in _CUISINE_SENTINELS:
        return None
    if text.islower():
        return text.title()
    if text.isupper() and len(text) > 4:
        return text.title()
    return text


def normalize_name(value: Any) -> str | None:
    """Trim restaurant names; preserve original casing and punctuation."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = " ".join(str(value).strip().split())
    return text or None


def normalize_optional_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return " ".join(str(value).strip().split())


def restaurant_id(name: str, location: str) -> str:
    """Stable unique id from name + location (hex prefix of SHA-256)."""
    payload = f"{name.casefold()}|{location.casefold()}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def preprocess_restaurants(raw: pd.DataFrame, *, city: str = DEFAULT_CITY) -> pd.DataFrame:
    """Full preprocess: map schema, parse fields, drop invalid rows, dedupe, assign ids.

    Dedup key is name + location (case-insensitive). When duplicates exist, the
    row with the highest rating, then highest votes, is kept.
    """
    mapped = SchemaMapper().to_internal(raw)

    names = mapped["name"].map(normalize_name)
    locations = mapped["location"].map(normalize_location)
    ratings = mapped["rating"].map(parse_rating)
    costs = mapped["average_cost_for_two"].map(parse_cost)
    cuisines = mapped["cuisines"].map(parse_cuisines)
    votes = mapped["votes"].map(parse_votes)
    addresses = mapped["address"].map(normalize_optional_text)
    rest_types = mapped["rest_type"].map(normalize_optional_text)

    cleaned = pd.DataFrame(
        {
            "name": names,
            "location": locations,
            "cuisines": cuisines,
            "average_cost_for_two": costs,
            "rating": ratings,
            "votes": votes,
            "address": addresses,
            "rest_type": rest_types,
            "city": city,
        }
    )

    cleaned = cleaned.dropna(subset=["name", "location", "rating", "average_cost_for_two"])
    cleaned["average_cost_for_two"] = cleaned["average_cost_for_two"].astype(int)
    cleaned["rating"] = cleaned["rating"].astype(float)
    cleaned["votes"] = cleaned["votes"].astype(int)

    cleaned["_name_key"] = cleaned["name"].str.casefold()
    cleaned["_location_key"] = cleaned["location"].str.casefold()
    cleaned = cleaned.sort_values(["rating", "votes"], ascending=[False, False])
    cleaned = cleaned.drop_duplicates(subset=["_name_key", "_location_key"], keep="first")
    cleaned = cleaned.drop(columns=["_name_key", "_location_key"])

    cleaned["id"] = [
        restaurant_id(name, location)
        for name, location in zip(cleaned["name"], cleaned["location"], strict=True)
    ]

    ordered = list(INTERNAL_REQUIRED_COLUMNS) + [
        col for col in ("city", "votes", "address", "rest_type") if col in cleaned.columns
    ]
    cleaned = cleaned.loc[:, ordered].reset_index(drop=True)
    return cleaned
