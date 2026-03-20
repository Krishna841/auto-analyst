from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from backend.analysis.profiler import profile_dataframe
from backend.dataset.pipeline_manager import (
    add_transformation,
    get_pipeline,
    get_profile,
    materialize_dataframe,
    redo_last,
    reset_pipeline,
    set_profile,
    undo_last,
)


def _infer_parameter_column(action: str, params: Dict[str, Any], df: pd.DataFrame, profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fill missing parameters using dataset profile.
    """
    out = dict(params or {})

    if action in {"drop_null_rows"}:
        if not out.get("column"):
            missing_values = profile.get("missing_values") or {}
            # choose max missing column
            if missing_values:
                best_col = max(missing_values.items(), key=lambda kv: int(kv[1] or 0))[0]
                out["column"] = best_col

    if action in {"fill_null_mean"}:
        if not out.get("column"):
            num_cols = profile.get("numeric_columns") or []
            if num_cols:
                out["column"] = num_cols[0]

    if action in {"normalize_column", "normalize"}:
        if not out.get("column"):
            num_cols = profile.get("numeric_columns") or []
            if num_cols:
                out["column"] = num_cols[0]

    if action in {"fill_null_median", "fill_null_mode"}:
        if not out.get("column"):
            num_cols = profile.get("numeric_columns") or []
            if num_cols:
                out["column"] = num_cols[0]

    if action in {"fill_null_constant"}:
        if not out.get("column"):
            missing_values = profile.get("missing_values") or {}
            if missing_values:
                best_col = max(missing_values.items(), key=lambda kv: int(kv[1] or 0))[0]
                out["column"] = best_col

    if action in {"forward_fill_nulls", "forward_fill", "backward_fill_nulls", "backward_fill"}:
        if not out.get("column"):
            missing_values = profile.get("missing_values") or {}
            if missing_values:
                best_col = max(missing_values.items(), key=lambda kv: int(kv[1] or 0))[0]
                out["column"] = best_col

    if action in {
        "trim_whitespace",
        "lowercase_text",
        "lowercase",
        "convert_to_numeric",
        "convert_to_string",
        "convert_to_datetime",
        "convert_to_categorical",
    }:
        if not out.get("column"):
            missing_values = profile.get("missing_values") or {}
            if missing_values:
                best_col = max(missing_values.items(), key=lambda kv: int(kv[1] or 0))[0]
                out["column"] = best_col
            elif df.columns:
                out["column"] = df.columns[0]

    if action in {
        "remove_outliers_zscore",
        "cap_outliers_zscore",
        "remove_outliers_iqr",
        "cap_outliers_iqr",
    }:
        if not out.get("column"):
            num_cols = profile.get("numeric_columns") or []
            if num_cols:
                out["column"] = num_cols[0]

    if action in {"sort_by_column"}:
        if not out.get("column"):
            dt_cols = profile.get("datetime_columns") or []
            if dt_cols:
                out["column"] = dt_cols[0]
            elif df.columns:
                out["column"] = df.columns[0]

    if action in {"drop_column", "remove_column"}:
        if not out.get("column"):
            # Prefer most-missing column
            missing_values = profile.get("missing_values") or {}
            if missing_values:
                best_col = max(missing_values.items(), key=lambda kv: int(kv[1] or 0))[0]
                out["column"] = best_col

    return out


def execute_transform(dataset_id: str, action: str, parameters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    df = materialize_dataframe(dataset_id)
    profile = profile_dataframe(df)

    params = _infer_parameter_column(action, parameters or {}, df, profile)
    step = add_transformation(dataset_id, action, params)

    new_df = materialize_dataframe(dataset_id)
    new_profile = profile_dataframe(new_df)
    set_profile(dataset_id, new_profile)

    return {
        "mode": "transform",
        "step": step.__dict__,
        "rows": len(new_df),
        "columns": list(new_df.columns),
        "profile": new_profile,
        "pipeline": get_pipeline(dataset_id),
    }


def execute_control(dataset_id: str, control_action: str) -> Dict[str, Any]:
    # control_action: undo | redo | reset
    if control_action == "undo":
        undo_last(dataset_id)
    elif control_action == "redo":
        redo_last(dataset_id)
    elif control_action == "reset":
        reset_pipeline(dataset_id)
    else:
        raise ValueError(f"Unsupported control action: {control_action}")

    df = materialize_dataframe(dataset_id)
    profile = profile_dataframe(df)
    set_profile(dataset_id, profile)

    return {
        "mode": "control",
        "control_action": control_action,
        "rows": len(df),
        "columns": list(df.columns),
        "profile": profile,
        "pipeline": get_pipeline(dataset_id),
    }

