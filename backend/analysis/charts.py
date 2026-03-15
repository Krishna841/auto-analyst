"""
Automatic chart generation: distribution, correlation heatmap, trend line, top categories bar.
Returns Plotly-compatible figure dicts for frontend rendering.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _to_serializable(obj: Any) -> Any:
    if hasattr(obj, "item"):
        return obj.item()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    return obj


def chart_distribution(df: pd.DataFrame, column: str, nbins: int = 30) -> dict[str, Any]:
    """Histogram for a numeric column. Returns Plotly figure dict."""
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return {}
    s = df[column].dropna()
    return {
        "data": [{"x": s.tolist(), "type": "histogram", "nbinsx": nbins, "marker": {"color": "#6366f1"}}],
        "layout": {"title": f"Distribution of {column}", "xaxis": {"title": column}, "yaxis": {"title": "Count"}},
    }


def chart_correlation_heatmap(df: pd.DataFrame, numeric_columns: list[str]) -> dict[str, Any]:
    """Correlation matrix as heatmap. Returns Plotly figure dict."""
    if len(numeric_columns) < 2:
        return {}
    subset = df[numeric_columns].dropna(how="all", axis=1).dropna(how="all", axis=0)
    if len(subset) < 2:
        return {}
    corr = subset.corr()
    return {
        "data": [{
            "z": corr.values.tolist(),
            "x": list(corr.columns),
            "y": list(corr.index),
            "type": "heatmap",
            "colorscale": "Blues",
        }],
        "layout": {"title": "Correlation heatmap", "height": 400},
    }


def chart_trend(df: pd.DataFrame, date_column: str, value_column: str, freq: str = "D") -> dict[str, Any]:
    """Line chart: date vs aggregated value. Returns Plotly figure dict."""
    if date_column not in df.columns or value_column not in df.columns:
        return {}
    d = df[[date_column, value_column]].copy()
    d[date_column] = pd.to_datetime(d[date_column], errors="coerce")
    d = d.dropna()
    if d.empty:
        return {}
    d = d.set_index(date_column)
    if not pd.api.types.is_numeric_dtype(d[value_column]):
        return {}
    s = d[value_column].resample(freq).sum()
    return {
        "data": [{"x": [str(i) for i in s.index], "y": s.tolist(), "type": "scatter", "mode": "lines+markers", "line": {"color": "#6366f1"}}],
        "layout": {"title": f"{value_column} over time", "xaxis": {"title": date_column}, "yaxis": {"title": value_column}},
    }


def chart_top_categories(df: pd.DataFrame, group_column: str, value_column: str, agg: str = "sum", top_n: int = 15) -> dict[str, Any]:
    """Bar chart: top N categories by aggregate. Returns Plotly figure dict."""
    if group_column not in df.columns or value_column not in df.columns:
        return {}
    g = df.groupby(group_column, dropna=False)[value_column].agg(agg)
    g = g.sort_values(ascending=False).head(top_n)
    return {
        "data": [{"x": g.index.tolist(), "y": g.tolist(), "type": "bar", "marker": {"color": "#6366f1"}}],
        "layout": {"title": f"{value_column} by {group_column}", "xaxis": {"title": group_column, "tickangle": -45}, "yaxis": {"title": agg}},
    }


def generate_charts(df: pd.DataFrame, profile: dict[str, Any]) -> dict[str, Any]:
    """Generate standard charts from profile. Returns dict of chart_name -> Plotly figure."""
    numeric = profile.get("numeric_columns") or []
    categorical = profile.get("categorical_columns") or []
    datetime_cols = profile.get("datetime_columns") or []
    out: dict[str, Any] = {}
    if numeric:
        out["distribution"] = chart_distribution(df, numeric[0])
    if len(numeric) >= 2:
        out["correlation_heatmap"] = chart_correlation_heatmap(df, numeric[:15])
    if datetime_cols and numeric:
        out["trend"] = chart_trend(df, datetime_cols[0], numeric[0])
    if categorical and numeric:
        out["top_categories"] = chart_top_categories(df, categorical[0], numeric[0])
    return {k: v for k, v in out.items() if v}
