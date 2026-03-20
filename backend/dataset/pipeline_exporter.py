from __future__ import annotations

from typing import Any, Dict, List

import re

from backend.dataset.pipeline_manager import get_pipeline, get_state


def _format_value(v: Any) -> str:
    """Return a safe Python literal representation."""
    if isinstance(v, str):
        return repr(v)
    return repr(v)


def _quote_col(col: Any) -> str:
    return _format_value(str(col))


def _safe_var(name: Any) -> str:
    """
    Convert a column name into a safe Python identifier suffix.
    Export code uses this for local helper variables like `_mean_<col>`.
    """
    s = str(name)
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", s)
    if not s:
        s = "col"
    if re.match(r"^\d", s):
        s = f"_{s}"
    return s


def _render_step(lines: List[str], step: Dict[str, Any]) -> None:
    action = step.get("action")
    params: Dict[str, Any] = step.get("parameters") or {}

    # null handling
    if action in {"drop_null_rows", "remove_null_rows"}:
        col = params.get("column")
        if col:
            lines.append(f"df = df.dropna(subset=[{_quote_col(col)}])")
        else:
            lines.append("df = df.dropna()")
        return

    if action in {"drop_null_columns"}:
        lines.append("df = df.dropna(axis=1, how='all')")
        return

    if action in {"drop_column", "remove_column"}:
        cols = params.get("columns")
        if cols is None:
            cols = params.get("column")
        if isinstance(cols, str):
            cols = [cols]
        if isinstance(cols, list) and cols:
            cols_py = ", ".join(_quote_col(c) for c in cols)
            lines.append(f"df = df.drop(columns=[{cols_py}])")
        return

    if action in {"fill_null_mean", "fill_null_mean_value"}:
        col = params.get("column")
        if col:
            c = _quote_col(col)
            lines.append(f"df[{c}] = df[{c}].fillna(df[{c}].mean())")
        return

    if action == "fill_null_median":
        col = params.get("column")
        if col:
            c = _quote_col(col)
            lines.append(f"df[{c}] = df[{c}].fillna(df[{c}].median())")
        return

    if action == "fill_null_mode":
        col = params.get("column")
        if col:
            c = _quote_col(col)
            v = _safe_var(col)
            lines.append(f"_mode_{v} = df[{c}].mode(dropna=True)")
            lines.append(f"if not _mode_{v}.empty:")
            lines.append(f"    df[{c}] = df[{c}].fillna(_mode_{v}.iloc[0])")
        return

    if action == "fill_null_constant":
        col = params.get("column")
        if col and "value" in params:
            c = _quote_col(col)
            val = _format_value(params.get("value"))
            lines.append(f"df[{c}] = df[{c}].fillna({val})")
        return

    if action in {"forward_fill_nulls", "forward_fill"}:
        col = params.get("column")
        if col:
            c = _quote_col(col)
            lines.append(f"df[{c}] = df[{c}].ffill()")
        else:
            lines.append("df = df.ffill()")
        return

    if action in {"backward_fill_nulls", "backward_fill"}:
        col = params.get("column")
        if col:
            c = _quote_col(col)
            lines.append(f"df[{c}] = df[{c}].bfill()")
        else:
            lines.append("df = df.bfill()")
        return

    # text & dtype
    if action in {"trim_whitespace"}:
        col = params.get("column")
        if col:
            c = _quote_col(col)
            lines.append(f"df[{c}] = df[{c}].where(df[{c}].isna(), df[{c}].astype(str).str.strip())")
        return

    if action in {"lowercase_text", "lowercase"}:
        col = params.get("column")
        if col:
            c = _quote_col(col)
            lines.append(f"df[{c}] = df[{c}].where(df[{c}].isna(), df[{c}].astype(str).str.lower())")
        return

    if action == "convert_to_numeric":
        col = params.get("column")
        if col:
            c = _quote_col(col)
            lines.append(f"df[{c}] = pd.to_numeric(df[{c}], errors='coerce')")
        return

    if action == "convert_to_string":
        col = params.get("column")
        if col:
            c = _quote_col(col)
            lines.append(f"df[{c}] = df[{c}].where(df[{c}].isna(), df[{c}].astype(str))")
        return

    if action == "convert_to_datetime":
        col = params.get("column")
        if col:
            c = _quote_col(col)
            lines.append(f"df[{c}] = pd.to_datetime(df[{c}], errors='coerce')")
        return

    if action == "convert_to_categorical":
        col = params.get("column")
        if col:
            c = _quote_col(col)
            lines.append(f"df[{c}] = df[{c}].astype('category')")
        return

    if action == "rename_column":
        old = params.get("old") or params.get("from")
        new = params.get("new") or params.get("to")
        if old and new:
            lines.append(f"df = df.rename(columns={{ {_format_value(str(old))}: {_format_value(str(new))} }})")
        return

    # duplicates / sort
    if action in {"remove_duplicates", "drop_duplicates"}:
        subset = params.get("subset")
        if subset is None:
            lines.append("df = df.drop_duplicates()")
        else:
            if isinstance(subset, str):
                subset = [subset]
            subset_py = ", ".join(_quote_col(c) for c in subset)
            lines.append(f"df = df.drop_duplicates(subset=[{subset_py}])")
        return

    if action == "sort_by_column":
        col = params.get("column")
        ascending = bool(params.get("ascending", True))
        if col:
            c = _quote_col(col)
            lines.append(f"df = df.sort_values(by={c}, ascending={ascending}, na_position='last')")
        return

    # normalize
    if action in {"normalize_column", "normalize"}:
        col = params.get("column")
        if col:
            c = _quote_col(col)
            v = _safe_var(col)
            lines.append(f"_mean_{v} = df[{c}].mean()")
            lines.append(f"_std_{v} = df[{c}].std()")
            lines.append(f"if _std_{v} == 0 or _std_{v} != _std_{v}:")
            lines.append(f"    _std_{v} = 1.0")
            lines.append(f"df[{c}] = (df[{c}] - _mean_{v}) / _std_{v}")
        return

    # outliers
    if action in {"remove_outliers_zscore"}:
        col = params.get("column")
        z = float(params.get("z_threshold", 3.0))
        if col:
            c = _quote_col(col)
            v = _safe_var(col)
            lines.append(f"_s_{v} = pd.to_numeric(df[{c}], errors='coerce')")
            lines.append(f"_mean_{v} = _s_{v}.mean()")
            lines.append(f"_std_{v} = _s_{v}.std()")
            lines.append(f"if _std_{v} == 0 or _std_{v} != _std_{v}:")
            lines.append(f"    _std_{v} = 1.0")
            lines.append(f"_mask_{v} = ((_s_{v} - _mean_{v}) / _std_{v}).abs() <= {_format_value(z)}")
            lines.append(f"df = df.loc[_mask_{v}.fillna(True)]")
        return

    if action in {"cap_outliers_zscore"}:
        col = params.get("column")
        z = float(params.get("z_threshold", 3.0))
        if col:
            c = _quote_col(col)
            v = _safe_var(col)
            lines.append(f"_s_{v} = pd.to_numeric(df[{c}], errors='coerce')")
            lines.append(f"_mean_{v} = _s_{v}.mean()")
            lines.append(f"_std_{v} = _s_{v}.std()")
            lines.append(f"if _std_{v} == 0 or _std_{v} != _std_{v}:")
            lines.append(f"    _std_{v} = 1.0")
            lines.append(f"_low_{v} = _mean_{v} - {_format_value(z)} * _std_{v}")
            lines.append(f"_high_{v} = _mean_{v} + {_format_value(z)} * _std_{v}")
            lines.append(f"df[{c}] = _s_{v}.clip(lower=_low_{v}, upper=_high_{v})")
        return

    if action in {"remove_outliers_iqr"}:
        col = params.get("column")
        mult = float(params.get("iqr_multiplier", 1.5))
        if col:
            c = _quote_col(col)
            v = _safe_var(col)
            lines.append(f"_s_{v} = pd.to_numeric(df[{c}], errors='coerce')")
            lines.append(f"_q1_{v} = _s_{v}.quantile(0.25)")
            lines.append(f"_q3_{v} = _s_{v}.quantile(0.75)")
            lines.append(f"_iqr_{v} = _q3_{v} - _q1_{v}")
            lines.append(f"_low_{v} = _q1_{v} - {_format_value(mult)} * _iqr_{v}")
            lines.append(f"_high_{v} = _q3_{v} + {_format_value(mult)} * _iqr_{v}")
            lines.append(f"_mask_{v} = (_s_{v} >= _low_{v}) & (_s_{v} <= _high_{v})")
            lines.append(f"df = df.loc[_mask_{v}.fillna(True)]")
        return

    if action in {"cap_outliers_iqr"}:
        col = params.get("column")
        mult = float(params.get("iqr_multiplier", 1.5))
        if col:
            c = _quote_col(col)
            v = _safe_var(col)
            lines.append(f"_s_{v} = pd.to_numeric(df[{c}], errors='coerce')")
            lines.append(f"_q1_{v} = _s_{v}.quantile(0.25)")
            lines.append(f"_q3_{v} = _s_{v}.quantile(0.75)")
            lines.append(f"_iqr_{v} = _q3_{v} - _q1_{v}")
            lines.append(f"_low_{v} = _q1_{v} - {_format_value(mult)} * _iqr_{v}")
            lines.append(f"_high_{v} = _q3_{v} + {_format_value(mult)} * _iqr_{v}")
            lines.append(f"df[{c}] = _s_{v}.clip(lower=_low_{v}, upper=_high_{v})")
        return

    # Unknown/unimplemented step
    lines.append(f"# TODO export for action={action} parameters={params}")


def export_pipeline_python(dataset_id: str) -> str:
    """
    Export the current pipeline as a runnable Python snippet.
    """
    state = get_state(dataset_id)
    steps = get_pipeline(dataset_id)

    lines: List[str] = []
    lines.append("import pandas as pd")
    lines.append("")
    lines.append(f"df = pd.read_csv({_format_value(state.raw_path)})  # replace path if needed")
    lines.append("")
    lines.append(f"# Transformation pipeline for dataset_id={dataset_id} ({len(steps)} steps)")

    for step in steps:
        lines.append(f"# Step {step.get('id')}: {step.get('action')}")
        _render_step(lines, step)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"

