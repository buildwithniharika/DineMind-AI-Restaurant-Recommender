"""Fetch the Zomato restaurant dataset from Hugging Face."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from src.config.settings import Settings, get_settings
from src.data.schema import UNUSED_RAW_COLUMNS

_MAX_ATTEMPTS = 3
_RETRY_BASE_SECONDS = 2


class DatasetLoadError(RuntimeError):
    """Raised when the Hugging Face dataset cannot be downloaded."""


class DatasetLoader:
    """Download (or reuse the HF cache of) the Zomato restaurant dataset."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def load(self) -> pd.DataFrame:
        """Return the raw dataset as a DataFrame, dropping unused heavy columns."""
        dataset = self._load_with_retry()
        frame = dataset.to_pandas()
        drop = [col for col in UNUSED_RAW_COLUMNS if col in frame.columns]
        if drop:
            frame = frame.drop(columns=drop)
        return frame

    def _load_with_retry(self) -> Any:
        try:
            from datasets import DatasetDict, load_dataset
        except ImportError as exc:
            raise DatasetLoadError(
                "The `datasets` package is required. Install with: pip install -r requirements.txt"
            ) from exc

        last_error: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                raw = load_dataset(self.settings.hf_dataset_id)
                if isinstance(raw, DatasetDict):
                    split = raw.get("train") or next(iter(raw.values()))
                else:
                    split = raw
                return split
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < _MAX_ATTEMPTS:
                    wait = _RETRY_BASE_SECONDS**attempt
                    print(
                        f"  Dataset download failed (attempt {attempt}/{_MAX_ATTEMPTS}): {exc}. "
                        f"Retrying in {wait}s..."
                    )
                    time.sleep(wait)

        raise DatasetLoadError(
            f"Failed to download '{self.settings.hf_dataset_id}' after {_MAX_ATTEMPTS} attempts. "
            "Check your network, then re-run `python scripts/prepare_data.py`. "
            "If Hugging Face is unreachable, retry later — the library caches a successful download."
        ) from last_error
