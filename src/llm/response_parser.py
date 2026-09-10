"""Parse and validate LLM recommendation JSON."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from src.models.recommendation import Recommendation, RecommendationResponse
from src.models.restaurant import Restaurant

_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*(.*?)\s*```\s*$",
    re.DOTALL | re.IGNORECASE,
)


class ParseError(Exception):
    """Raised when LLM output cannot be turned into a valid RecommendationResponse."""


class ResponseParser:
    """Extract JSON from LLM text and validate against the recommendation schema."""

    def parse(
        self,
        raw: str,
        candidates: list[Restaurant],
        *,
        top_n: int,
        source: str = "llm",
    ) -> RecommendationResponse:
        """Parse raw LLM text into a RecommendationResponse grounded in candidates."""
        if not raw or not raw.strip():
            raise ParseError("Empty LLM response")

        data = self._load_json(raw)
        if not isinstance(data, dict):
            raise ParseError("LLM JSON root must be an object")

        by_id = {r.id: r for r in candidates}
        raw_recs = data.get("recommendations")
        if not isinstance(raw_recs, list) or not raw_recs:
            raise ParseError("Missing or empty recommendations array")

        recommendations: list[Recommendation] = []
        seen_ids: set[str] = set()
        seen_names: set[str] = set()

        for item in raw_recs:
            if len(recommendations) >= top_n:
                break
            if not isinstance(item, dict):
                continue
            restaurant_id = str(item.get("restaurant_id") or item.get("id") or "").strip()
            if not restaurant_id or restaurant_id in seen_ids:
                continue
            restaurant = by_id.get(restaurant_id)
            if restaurant is None:
                continue  # drop hallucinations

            name_key = restaurant.name.casefold()
            if name_key in seen_names:
                continue  # drop same brand at another branch

            cuisine = ", ".join(restaurant.cuisines) if restaurant.cuisines else "Unknown"
            explanation = str(item.get("explanation") or "").strip()
            if not explanation:
                explanation = (
                    f"Rated {restaurant.rating}/5 and matches your filters "
                    f"in {restaurant.location}."
                )

            recommendations.append(
                Recommendation(
                    rank=len(recommendations) + 1,
                    restaurant_id=restaurant.id,
                    name=restaurant.name,
                    cuisine=cuisine,
                    rating=restaurant.rating,
                    estimated_cost=restaurant.average_cost_for_two,
                    explanation=explanation,
                    location=restaurant.location,
                )
            )
            seen_ids.add(restaurant_id)
            seen_names.add(name_key)

        if not recommendations:
            raise ParseError("No recommendations mapped to candidate restaurant IDs")

        summary = data.get("summary")
        summary_text = str(summary).strip() if summary is not None else None
        if summary_text == "":
            summary_text = None

        try:
            return RecommendationResponse(
                recommendations=recommendations,
                summary=summary_text,
                source=source,  # type: ignore[arg-type]
            )
        except ValidationError as exc:
            raise ParseError(f"Schema validation failed: {exc}") from exc

    def _load_json(self, raw: str) -> Any:
        text = raw.strip()
        fence = _FENCE_RE.match(text)
        if fence:
            text = fence.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Best-effort: extract first {...} block
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ParseError("Response is not valid JSON") from None
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as exc:
                raise ParseError(f"Response is not valid JSON: {exc}") from exc
