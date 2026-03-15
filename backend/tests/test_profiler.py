"""
Regression tests for profiler and analysis (Section 11).
Use: pytest backend/tests/ -v  (from project root)
"""
import pandas as pd

from backend.analysis.profiler import profile_dataframe, normalize_column_name
from backend.analysis.analysis_engine import build_analysis_plan
from backend.analysis.statistics import run_correlation_analysis, run_all_analyses, _drop_constant_columns


def test_normalize_column_name():
    assert normalize_column_name("Total Sales ($)") == "totalsales"
    assert normalize_column_name("  Region  ") == "region"


def test_profile_small_csv():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
        "region": ["North", "South", "North", "South", "East"],
        "sales": [100, 200, 150, 220, 180],
    })
    profile = profile_dataframe(df)
    assert profile["rows"] == 5
    assert "sales" in profile["numeric_columns"]
    assert "region" in profile["categorical_columns"]
    assert "date" in profile["datetime_columns"]
    assert "normalized_column_names" in profile


def test_analysis_plan():
    profile = {
        "numeric_columns": ["sales", "quantity"],
        "categorical_columns": ["region"],
        "datetime_columns": ["date"],
    }
    plan = build_analysis_plan(profile)
    assert "trend_analysis" in plan["steps"]
    assert "group_comparison" in plan["steps"]
    assert "correlation_analysis" in plan["steps"]


def test_correlation_drops_constant():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [1, 1, 1], "c": [4, 5, 6]})
    dropped = _drop_constant_columns(df, ["a", "b", "c"])
    assert "b" not in dropped
    assert "a" in dropped and "c" in dropped


def test_correlation_analysis():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6]})
    out = run_correlation_analysis(df, ["x", "y"], method="pearson")
    assert "correlations" in out
    assert out["numeric_columns"] == ["x", "y"]
