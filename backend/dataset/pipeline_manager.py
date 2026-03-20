from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

import pandas as pd


@dataclass(frozen=True)
class TransformationStep:
    id: int
    action: str
    parameters: Dict[str, Any]
    created_at: str


@dataclass
class DatasetState:
    dataset_id: str
    raw_path: str
    profile: Dict[str, Any] | None = None
    pipeline: List[TransformationStep] = field(default_factory=list)
    # steps removed by undo() that can be re-applied by redo()
    redo_stack: List[TransformationStep] = field(default_factory=list)
    # simple cache: step_id -> dataframe after applying up to that step
    cache: Dict[int, pd.DataFrame] = field(default_factory=dict)


DATASETS: Dict[str, DatasetState] = {}
TRANSFORMATIONS: Dict[str, Callable[[pd.DataFrame, Dict[str, Any]], pd.DataFrame]] = {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_transformation(name: str, fn: Callable[[pd.DataFrame, Dict[str, Any]], pd.DataFrame]) -> None:
    TRANSFORMATIONS[name] = fn


def register_dataset(dataset_id: str, raw_path: str, profile: Dict[str, Any] | None = None) -> None:
    DATASETS[dataset_id] = DatasetState(dataset_id=dataset_id, raw_path=raw_path, profile=profile)


def get_state(dataset_id: str) -> DatasetState:
    if dataset_id not in DATASETS:
        raise KeyError(f"Unknown dataset_id: {dataset_id}")
    return DATASETS[dataset_id]


def set_profile(dataset_id: str, profile: Dict[str, Any]) -> None:
    get_state(dataset_id).profile = profile


def get_profile(dataset_id: str) -> Dict[str, Any] | None:
    return get_state(dataset_id).profile


def get_pipeline(dataset_id: str) -> List[Dict[str, Any]]:
    return [s.__dict__ for s in get_state(dataset_id).pipeline]


def _load_raw_dataframe(state: DatasetState) -> pd.DataFrame:
    return pd.read_csv(state.raw_path)


def materialize_dataframe(dataset_id: str) -> pd.DataFrame:
    """
    Rebuild dataframe by replaying transformation steps on the raw CSV.
    Uses a simple cache keyed by step_id.
    """
    state = get_state(dataset_id)
    df = _load_raw_dataframe(state)

    for step in state.pipeline:
        cached = state.cache.get(step.id)
        if cached is not None:
            df = cached
            continue
        fn = TRANSFORMATIONS.get(step.action)
        if fn is None:
            raise ValueError(f"Unknown transformation action: {step.action}")
        df = fn(df, step.parameters or {})
        state.cache[step.id] = df
    return df


def add_transformation(dataset_id: str, action: str, parameters: Dict[str, Any] | None = None) -> TransformationStep:
    if action not in TRANSFORMATIONS:
        raise ValueError(f"Unsupported transformation action: {action}")
    state = get_state(dataset_id)
    step_id = (state.pipeline[-1].id + 1) if state.pipeline else 1
    step = TransformationStep(
        id=step_id,
        action=action,
        parameters=parameters or {},
        created_at=_utc_now_iso(),
    )
    state.pipeline.append(step)
    # new transformations invalidate redo cache
    state.redo_stack.clear()
    state.cache.clear()
    return step


def undo_last(dataset_id: str) -> None:
    state = get_state(dataset_id)
    if not state.pipeline:
        return
    step = state.pipeline.pop()
    state.redo_stack.append(step)
    state.cache.clear()


def redo_last(dataset_id: str) -> None:
    state = get_state(dataset_id)
    if not state.redo_stack:
        return
    step = state.redo_stack.pop()
    state.pipeline.append(step)
    state.cache.clear()


def reset_pipeline(dataset_id: str) -> None:
    state = get_state(dataset_id)
    state.pipeline.clear()
    state.redo_stack.clear()
    state.cache.clear()

