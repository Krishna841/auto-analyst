"""
Statistical analysis: correlation, group comparison, trend.
Improvements: drop constant columns, Pearson/Spearman, multi-group, trend freq inference, reindex+fill.
"""

from __future__ import annotations

import pandas as pd
from typing import Any


def _to_serializable(obj: Any) -> Any:
    """Convert numpy/pandas types to native Python for JSON."""
    if hasattr(obj, "item"):
        return obj.item()
    if pd.isna(obj):
        return None
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(x) for x in obj]
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if hasattr(obj, "to_dict"):
        return _to_serializable(obj.to_dict())
    return obj


def _drop_constant_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    """Remove columns with at most one unique value (invalid for correlation)."""
    return [c for c in columns if c in df.columns and df[c].nunique() > 1]


def infer_trend_freq(df: pd.DataFrame, date_column: str) -> str:
    """Infer resample frequency from date range: <90 days → D, <2 years → W, else M."""
    if date_column not in df.columns:
        return "D"
    s = pd.to_datetime(df[date_column], errors="coerce").dropna()
    if len(s) < 2:
        return "D"
    delta = s.max() - s.min()
    days = delta.days
    if days <= 90:
        return "D"
    if days <= 730:
        return "W"
    return "M"


def run_correlation_analysis(
    df: pd.DataFrame,
    numeric_columns: list[str],
    method: str = "pearson",
) -> dict[str, Any]:
    """Compute correlation matrix. Drops constant columns. Supports pearson/spearman."""
    cols = _drop_constant_columns(df, numeric_columns)
    if len(cols) < 2:
        return {"message": "Need at least 2 non-constant numeric columns", "correlations": {}}
    subset = df[cols].copy()
    subset = subset.dropna(how="all", axis=1).dropna(how="all", axis=0)
    if subset.empty or len(subset) < 2:
        return {"message": "Insufficient data", "correlations": {}}
    method = method if method in ("pearson", "spearman", "kendall") else "pearson"
    corr = subset.corr(method=method)
    return {
        "correlations": _to_serializable(corr.round(4).to_dict()),
        "numeric_columns": list(subset.columns),
        "method": method,
    }


def run_group_comparison(
    df: pd.DataFrame,
    group_column: str,
    value_columns: list[str],
    agg: str = "sum",
) -> dict[str, Any]:
    """Group by categorical column; agg one of sum, mean, median, count, min, max."""
    if group_column not in df.columns or not value_columns:
        return {"message": "Invalid columns", "group_analysis": {}}
    valid = [c for c in value_columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if not valid:
        return {"message": "No valid numeric columns", "group_analysis": {}}
    allowed = ("sum", "mean", "median", "count", "min", "max")
    agg_fn = agg if agg in allowed else "sum"
    grouped = df.groupby(group_column, dropna=False)[valid].agg(agg_fn)
    result = grouped.round(4).to_dict(orient="index")
    return {
        "group_column": group_column,
        "value_columns": valid,
        "agg": agg_fn,
        "group_analysis": _to_serializable(result),
    }


def run_trend_analysis(
    df: pd.DataFrame,
    date_column: str,
    value_columns: list[str],
    freq: str = "D",
) -> dict[str, Any]:
    """Trend by date. Infers freq if needed. Reindex + fill missing periods with 0."""
    if date_column not in df.columns or not value_columns:
        return {"message": "Invalid columns", "trend_analysis": {}}
    d = df[[date_column] + [c for c in value_columns if c in df.columns]].copy()
    d = d.dropna(subset=[date_column])
    if d.empty:
        return {"message": "No valid rows", "trend_analysis": {}}
    d[date_column] = pd.to_datetime(d[date_column], errors="coerce")
    d = d.dropna(subset=[date_column])
    if d.empty:
        return {"message": "No valid dates", "trend_analysis": {}}
    if freq is None or freq == "infer":
        freq = infer_trend_freq(df, date_column)
    d = d.set_index(date_column)
    numeric = [c for c in d.columns if pd.api.types.is_numeric_dtype(d[c])]
    if not numeric:
        return {"message": "No numeric value columns", "trend_analysis": {}}
    try:
        resampled = d[numeric].resample(freq).sum()
    except Exception:
        resampled = d[numeric].resample("D").sum()
        freq = "D"
    # Reindex to full range and fill missing with 0
    if len(resampled) > 0:
        full_range = pd.date_range(start=resampled.index.min(), end=resampled.index.max(), freq=freq)
        resampled = resampled.reindex(full_range, fill_value=0)
    resampled = resampled.dropna(how="all")
    if len(resampled) > 500:
        resampled = resampled.iloc[-500:]
    result = resampled.round(4).to_dict(orient="index")
    serialized = {str(k): {col: _to_serializable(v) for col, v in row.items()} for k, row in result.items()}
    return {
        "date_column": date_column,
        "value_columns": numeric,
        "freq": freq,
        "trend_analysis": serialized,
    }


def run_summary_stats(df: pd.DataFrame, numeric_columns: list[str]) -> dict[str, Any]:
    """Summary statistics for numeric columns."""
    if not numeric_columns:
        return {"summary_stats": {}}
    subset = df[numeric_columns].describe()
    return {"summary_stats": _to_serializable(subset.round(4).to_dict())}


MAX_ROWS_FOR_ANALYSIS = 100_000  # Cap for heavy operations (Section 10)


def run_all_analyses(
    df: pd.DataFrame,
    profile: dict[str, Any],
    steps: list[str] | None = None,
    freq: str | None = None,
    agg: str = "sum",
    correlation_method: str = "pearson",
) -> dict[str, Any]:
    """
    Run analyses. Multi-group: one group_comparison per categorical column.
    Drops constant columns for correlation; infers trend freq; supports agg and correlation method.
    Samples to MAX_ROWS_FOR_ANALYSIS if dataset is larger.
    """
    if len(df) > MAX_ROWS_FOR_ANALYSIS:
        df = df.sample(n=MAX_ROWS_FOR_ANALYSIS, random_state=42)
    numeric = profile.get("numeric_columns") or []
    categorical = profile.get("categorical_columns") or []
    datetime_cols = profile.get("datetime_columns") or []

    if steps is None:
        try:
            from backend.analysis.analysis_engine import build_analysis_plan
        except ImportError:
            from analysis.analysis_engine import build_analysis_plan
        plan = build_analysis_plan(profile, agg=agg, trend_freq=freq)
        steps = plan.get("steps") or []

    out: dict[str, Any] = {}

    if "correlation_analysis" in steps and len(numeric) >= 2:
        out["correlations"] = run_correlation_analysis(df, numeric, method=correlation_method)

    if "group_comparison" in steps and categorical and numeric:
        group_results: list[dict[str, Any]] = []
        for cat_col in categorical[:10]:
            group_results.append(
                run_group_comparison(df, cat_col, numeric[:5], agg=agg)
            )
        out["group_analysis"] = {
            "by_column": group_results,
            "aggregation": agg,
        }

    if "trend_analysis" in steps and datetime_cols and numeric:
        trend_freq = freq or infer_trend_freq(df, datetime_cols[0])
        out["trend_analysis"] = run_trend_analysis(
            df, datetime_cols[0], numeric[:3], freq=trend_freq
        )

    if "summary_stats" in steps and numeric:
        out["summary_stats"] = run_summary_stats(df, numeric)

    return out
