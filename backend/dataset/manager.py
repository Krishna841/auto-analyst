from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import pandas as pd


@dataclass
class DatasetState:
    """In-memory state for an uploaded dataset."""

    df: pd.DataFrame
    profile: Dict[str, Any] | None = None
    cache: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    original_df: pd.DataFrame | None = None

    def __post_init__(self) -> None:
        if self.original_df is None:
            # Keep a pristine copy for reset/undo-all.
            self.original_df = self.df.copy(deep=True)


DATASETS: Dict[str, DatasetState] = {}


def register_dataset(dataset_id: str, df: pd.DataFrame, profile: Dict[str, Any] | None = None) -> None:
    """Register a new dataset with optional profile."""
    DATASETS[dataset_id] = DatasetState(df=df.copy(deep=True), profile=profile)


def get_state(dataset_id: str) -> DatasetState:
    if dataset_id not in DATASETS:
        raise KeyError(f"Unknown dataset_id: {dataset_id}")
    return DATASETS[dataset_id]


def get_dataframe(dataset_id: str) -> pd.DataFrame:
    return get_state(dataset_id).df


def get_profile(dataset_id: str) -> Dict[str, Any] | None:
    return get_state(dataset_id).profile


def set_profile(dataset_id: str, profile: Dict[str, Any]) -> None:
    state = get_state(dataset_id)
    state.profile = profile


def update_dataframe(dataset_id: str, df: pd.DataFrame, operation: str | None = None) -> None:
    """Replace dataframe and record operation in history."""
    state = get_state(dataset_id)
    state.df = df.copy(deep=True)
    if operation:
        state.history.append(operation)
    # Invalidate cached derived results; they will be recomputed lazily.
    state.cache.clear()


def get_history(dataset_id: str) -> List[str]:
    return list(get_state(dataset_id).history)


def undo_last(dataset_id: str) -> None:
    """Very simple undo: revert one step by reloading from original_df for now."""
    state = get_state(dataset_id)
    if not state.history:
        return
    # For v1 we support coarse undo: go back to original and drop history.
    state.df = state.original_df.copy(deep=True)
    state.history.clear()
    state.cache.clear()


def reset(dataset_id: str) -> None:
    """Reset dataset to initial uploaded dataframe."""
    state = get_state(dataset_id)
    state.df = state.original_df.copy(deep=True)
    state.history.clear()
    state.cache.clear()

