"""Local Parquet cache for the processed restaurant dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.schema import INTERNAL_REQUIRED_COLUMNS

_LIST_COLUMNS = ("cuisines",)


class CacheError(ValueError):
    """Raised when the processed cache is missing, corrupt, or incomplete."""


class CacheManager:
    """Save and load processed restaurants as Parquet."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def exists(self) -> bool:
        return self.path.is_file() and self.path.stat().st_size > 0

    def save(self, data: pd.DataFrame) -> Path:
        """Write processed restaurants to Parquet, creating parent dirs as needed."""
        self._validate_schema(data, context="save")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = data.copy()
        for column in _LIST_COLUMNS:
            if column in payload.columns:
                payload[column] = payload[column].map(lambda value: list(value) if value is not None else [])
        payload.to_parquet(self.path, index=False, engine="pyarrow")
        return self.path

    def load(self) -> pd.DataFrame:
        """Load cached Parquet. Converts cuisine arrays back to Python lists."""
        if not self.exists():
            raise CacheError(
                f"Processed dataset not found at {self.path}. "
                "Run `python scripts/prepare_data.py` locally, or include "
                "data/processed/restaurants.parquet in the git repo for Streamlit Cloud."
            )
        try:
            data = pd.read_parquet(self.path, engine="pyarrow")
        except Exception as exc:
            raise CacheError(
                f"Processed dataset at {self.path} is corrupt or unreadable ({exc}). "
                "Delete it and re-run `python scripts/prepare_data.py`."
            ) from exc

        self._validate_schema(data, context="load")
        if "cuisines" in data.columns:
            data["cuisines"] = data["cuisines"].map(
                lambda value: list(value) if value is not None else []
            )
        return data

    @staticmethod
    def _validate_schema(data: pd.DataFrame, *, context: str) -> None:
        missing = [col for col in INTERNAL_REQUIRED_COLUMNS if col not in data.columns]
        if missing:
            raise CacheError(
                f"Cannot {context} processed data; missing columns: {missing}"
            )
        if data.empty:
            raise CacheError("Processed restaurant dataset is empty.")
