"""
Autonomous analysis planner: decide what analyses to run.
Improvement: multi-group comparisons, trend frequency hint.
"""

from __future__ import annotations

from typing import Any


def build_analysis_plan(
    profile: dict[str, Any],
    agg: str = "sum",
    trend_freq: str | None = None,
) -> dict[str, Any]:
    """
    Build analysis plan. Excludes identifier columns from correlation/grouping.
    Multi-group: one comparison per categorical column.
    """
    steps: list[str] = []
    descriptions: list[str] = []

    numeric = profile.get("numeric_columns") or []
    categorical = profile.get("categorical_columns") or []
    datetime_cols = profile.get("datetime_columns") or []
    # Identifiers excluded from numeric/categorical for analysis

    # Trend analysis
    if datetime_cols and numeric:
        steps.append("trend_analysis")
        freq = trend_freq or "D"
        descriptions.append(f"Trend over time (freq={freq})")

    # Multi-group comparison: one per categorical
    if categorical and numeric:
        steps.append("group_comparison")
        for cat_col in categorical[:10]:  # cap for response size
            num_col = numeric[0]
            descriptions.append(f"{cat_col} by {num_col} ({agg})")

    # Correlation: numeric only (identifiers already excluded in profile)
    if len(numeric) >= 2:
        steps.append("correlation_analysis")
        extra = f" (and {len(numeric) - 2} more)" if len(numeric) > 2 else ""
        descriptions.append(f"Correlation: {numeric[0]}, {numeric[1]}{extra}")
    elif len(numeric) == 1:
        steps.append("summary_stats")
        descriptions.append(f"Summary statistics for {numeric[0]}")

    if not steps:
        steps.append("summary_only")
        descriptions.append("Dataset summary only")

    return {
        "steps": steps,
        "descriptions": descriptions,
        "analysis_plan": [f"{i + 1}. {d}" for i, d in enumerate(descriptions)],
        "params": {"agg": agg, "trend_freq": trend_freq},
    }
