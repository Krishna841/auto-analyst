"""
Dataset profiling: column types, missing values, cardinality, identifiers, normalized names.
Improvement roadmap: datetime by parsing, 5% categorical rule, identifier detection, name normalization.
"""

from __future__ import annotations

import re
import pandas as pd
from typing import Any

# Cardinality threshold: unique_values / rows < this → categorical
CATEGORICAL_CARDINALITY_RATIO = 0.05
# unique_values / rows >= this → identifier (exclude from correlation/grouping)
IDENTIFIER_RATIO_MIN = 0.95


def normalize_column_name(name: str) -> str:
    """Lowercase, replace spaces with '_', remove special characters for matching."""
    s = str(name).strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^\w]", "", s)
    return s or "column"


def get_normalized_column_names(columns: list[str]) -> dict[str, str]:
    """Map original column name -> normalized name. Handles collisions by appending _1, _2."""
    out: dict[str, str] = {}
    seen: dict[str, int] = {}
    for col in columns:
        norm = normalize_column_name(col)
        if norm in seen:
            seen[norm] += 1
            out[col] = f"{norm}_{seen[norm]}"
        else:
            seen[norm] = 0
            out[col] = norm
    return out


def detect_column_types(df: pd.DataFrame) -> dict[str, str]:
    """
    Classify each column as 'numeric', 'categorical', 'datetime', or 'identifier'.
    - Try parsing all object columns as datetime (not just name-based).
    - If unique/rows < 5% → categorical; if unique/rows >= 95% → identifier.
    """
    result: dict[str, str] = {}
    rows = len(df)
    for col in df.columns:
        dtype = df[col].dtype
        n_unique = df[col].nunique()
        unique_ratio = n_unique / rows if rows > 0 else 0

        if unique_ratio >= IDENTIFIER_RATIO_MIN:
            result[col] = "identifier"
            continue

        if pd.api.types.is_numeric_dtype(dtype):
            if unique_ratio < CATEGORICAL_CARDINALITY_RATIO:
                result[col] = "categorical"
            else:
                result[col] = "numeric"
            continue

        if pd.api.types.is_datetime64_any_dtype(dtype):
            result[col] = "datetime"
            continue

        # Object/string: try parsing as datetime (any column)
        try:
            sample = df[col].dropna().head(200)
            if len(sample) > 0:
                pd.to_datetime(sample, errors="raise")
                result[col] = "datetime"
                continue
        except Exception:
            pass

        # Name hint for date-like
        col_lower = col.lower()
        if any(x in col_lower for x in ("date", "time", "day", "month", "year")):
            try:
                sample = df[col].dropna().head(100)
                if len(sample) > 0:
                    pd.to_datetime(sample, errors="raise")
                    result[col] = "datetime"
                    continue
            except Exception:
                pass

        # Categorical vs numeric by cardinality
        if unique_ratio < CATEGORICAL_CARDINALITY_RATIO:
            result[col] = "categorical"
        else:
            result[col] = "categorical"  # default object to categorical
    return result


def get_missing_values(df: pd.DataFrame) -> dict[str, int]:
    """Return count of missing values per column."""
    return df.isna().sum().astype(int).to_dict()


def get_unique_counts(df: pd.DataFrame) -> dict[str, int]:
    """Return number of unique values per column (excluding NaNs for stability)."""
    return df.nunique(dropna=True).astype(int).to_dict()


def get_constant_columns(df: pd.DataFrame) -> list[str]:
    """Columns with no variability (0 or 1 unique non-null values)."""
    out: list[str] = []
    for col in df.columns:
        # dropna=True so all-NaN counts as constant (0 unique)
        n_unique = df[col].nunique(dropna=True)
        if n_unique <= 1:
            out.append(col)
    return out


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """
    Full profile: rows, column types, numeric/categorical/datetime/identifier,
    missing values, normalized column names.
    """
    rows = len(df)
    columns = list(df.columns)
    col_types = detect_column_types(df)

    numeric_columns = [c for c, t in col_types.items() if t == "numeric"]
    categorical_columns = [c for c, t in col_types.items() if t == "categorical"]
    datetime_columns = [c for c, t in col_types.items() if t == "datetime"]
    identifier_columns = [c for c, t in col_types.items() if t == "identifier"]

    missing_values = get_missing_values(df)
    unique_counts = get_unique_counts(df)
    constant_columns = get_constant_columns(df)
    normalized_names = get_normalized_column_names(columns)

    return {
        "rows": rows,
        "columns": columns,
        "column_types": col_types,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "datetime_columns": datetime_columns,
        "identifier_columns": identifier_columns,
        # primary missing-values field used by the frontend
        "missing_values": missing_values,
        # compatibility with the requirements doc
        "missing": missing_values,
        "unique_counts": unique_counts,
        "constant_columns": constant_columns,
        "normalized_column_names": normalized_names,
    }
