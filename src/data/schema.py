"""Raw Hugging Face schema → internal restaurant columns.

The ManikaSaini/zomato-restaurant-recommendation dataset is the classic
Bangalore Zomato listings dump (~51,717 rows). Column names and quirks:

| Raw column                    | Internal field           | Notes                                      |
|-------------------------------|--------------------------|--------------------------------------------|
| name                          | name                     | Restaurant display name                   |
| location                      | location                 | Locality (e.g. Banashankari), not metro    |
| listed_in(city)               | (unused for city)        | Listing *zone*, still a Bangalore area    |
| cuisines                       | cuisines                 | Comma-separated string                       |
| approx_cost(for two people)    | average_cost_for_two     | Often a string with commas ("1,200")      |
| rate                          | rating                   | String like "4.1/5", "NEW", or "-"         |
| votes                         | votes                    | Integer; used later for tie-breaking      |
| address                       | address                  | Optional                                   |
| rest_type                     | rest_type                | Optional (Casual Dining, Cafe, ...)       |

`city` is derived as "Bangalore" because this dataset only covers that metro.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Canonical raw column → first-match wins among aliases (case-insensitive).
RAW_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("name", "restaurant_name", "restaurant name"),
    "location": ("location", "locality"),
    "cuisines": ("cuisines", "cuisine"),
    "cost": (
        "approx_cost(for two people)",
        "approx_cost_for_two",
        "average_cost_for_two",
        "cost",
    ),
    "rating": ("rate", "rating", "aggregate_rating", "aggregate rating"),
    "votes": ("votes",),
    "address": ("address",),
    "rest_type": ("rest_type", "rest type"),
}

INTERNAL_REQUIRED_COLUMNS = (
    "id",
    "name",
    "location",
    "cuisines",
    "average_cost_for_two",
    "rating",
)

INTERNAL_OPTIONAL_COLUMNS = ("city", "votes", "address", "rest_type")

# This HF dataset is Bangalore-only; used when no city column exists.
DEFAULT_CITY = "Bangalore"

# Dropped from the raw dump to keep memory bounded (reviews_list is huge).
UNUSED_RAW_COLUMNS = (
    "url",
    "phone",
    "dish_liked",
    "reviews_list",
    "menu_item",
    "online_order",
    "book_table",
    "listed_in(type)",
)


class SchemaMismatchError(ValueError):
    """Raised when the raw dataset is missing required columns."""


@dataclass(frozen=True)
class ColumnMap:
    """Resolved raw-column names for the fields we ingest."""

    name: str
    location: str
    cuisines: str
    cost: str
    rating: str
    votes: str | None
    address: str | None
    rest_type: str | None


class SchemaMapper:
    """Map raw dataset columns onto the internal restaurant schema."""

    def resolve(self, columns: list[str] | pd.Index) -> ColumnMap:
        """Resolve aliases against actual column names. Fail fast if required fields are missing."""
        lookup = {str(col).strip().casefold(): str(col) for col in columns}
        resolved: dict[str, str | None] = {}
        missing: list[str] = []

        required = ("name", "location", "cuisines", "cost", "rating")
        optional = ("votes", "address", "rest_type")

        for field in (*required, *optional):
            match = next(
                (lookup[alias.casefold()] for alias in RAW_FIELD_ALIASES[field] if alias.casefold() in lookup),
                None,
            )
            if match is None and field in required:
                missing.append(f"{field} (tried {list(RAW_FIELD_ALIASES[field])})")
            resolved[field] = match

        if missing:
            found = ", ".join(sorted(str(c) for c in columns))
            raise SchemaMismatchError(
                "Dataset schema does not match expected Zomato columns. "
                f"Missing: {', '.join(missing)}. Found: {found}"
            )

        return ColumnMap(
            name=resolved["name"] or "",
            location=resolved["location"] or "",
            cuisines=resolved["cuisines"] or "",
            cost=resolved["cost"] or "",
            rating=resolved["rating"] or "",
            votes=resolved["votes"],
            address=resolved["address"],
            rest_type=resolved["rest_type"],
        )

    def to_internal(self, raw: pd.DataFrame) -> pd.DataFrame:
        """Select and rename raw columns to internal names (values still unparsed)."""
        mapping = self.resolve(raw.columns)
        frame = pd.DataFrame(
            {
                "name": raw[mapping.name],
                "location": raw[mapping.location],
                "cuisines": raw[mapping.cuisines],
                "average_cost_for_two": raw[mapping.cost],
                "rating": raw[mapping.rating],
            }
        )
        frame["votes"] = raw[mapping.votes] if mapping.votes else 0
        frame["address"] = raw[mapping.address] if mapping.address else ""
        frame["rest_type"] = raw[mapping.rest_type] if mapping.rest_type else ""
        return frame
