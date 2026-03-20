from __future__ import annotations

from typing import Any, Dict, Iterable

import pandas as pd

from backend.dataset.pipeline_manager import register_transformation


def _normalize_column_list(cols: Any) -> list[str]:
    if cols is None:
        return []
    if isinstance(cols, str):
        return [cols]
    return [str(c) for c in cols]


def _ensure_column(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns


def drop_null_rows(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if col and _ensure_column(df, str(col)):
        return df.dropna(subset=[str(col)])
    return df.dropna()


def drop_column(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    cols = params.get("columns")
    if cols is None:
        cols = params.get("column")
    col_list = _normalize_column_list(cols)
    if not col_list:
        return df
    existing = [c for c in col_list if c in df.columns]
    if not existing:
        return df
    return df.drop(columns=existing)


def fill_null_mean(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    if not pd.api.types.is_numeric_dtype(df[col]):
        return df
    mean = df[col].mean()
    return df.assign(**{col: df[col].fillna(mean)})


def normalize_column(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    if not pd.api.types.is_numeric_dtype(df[col]):
        return df
    s = df[col]
    mean = s.mean()
    std = s.std()
    if std == 0 or pd.isna(std):
        std = 1.0
    return df.assign(**{col: (s - mean) / std})


def fill_null_median(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    if not pd.api.types.is_numeric_dtype(df[col]):
        return df
    med = df[col].median()
    return df.assign(**{col: df[col].fillna(med)})


def fill_null_mode(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    # mode works for non-numeric too, but we keep it generic
    modes = df[col].mode(dropna=True)
    if modes.empty:
        return df
    fill_val = modes.iloc[0]
    return df.assign(**{col: df[col].fillna(fill_val)})


def fill_null_constant(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    if "value" not in params:
        return df
    value = params.get("value")
    return df.assign(**{col: df[col].fillna(value)})


def forward_fill_nulls(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if col and _ensure_column(df, str(col)):
        col = str(col)
        return df.assign(**{col: df[col].ffill()})
    # If no column specified, forward-fill everything as a safe fallback.
    return df.ffill()


def backward_fill_nulls(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if col and _ensure_column(df, str(col)):
        col = str(col)
        return df.assign(**{col: df[col].bfill()})
    return df.bfill()


def drop_null_columns(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    # Drop columns where all values are null
    return df.dropna(axis=1, how="all")


def rename_column(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    old = params.get("old") or params.get("from")
    new = params.get("new") or params.get("to")
    if not old or not new:
        return df
    old = str(old)
    new = str(new)
    if old not in df.columns:
        return df
    return df.rename(columns={old: new})


def convert_to_numeric(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    return df.assign(**{col: pd.to_numeric(df[col], errors="coerce")})


def convert_to_string(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    # Keep NaN as NaN by converting only non-null values.
    s = df[col]
    return df.assign(**{col: s.where(s.isna(), s.astype(str))})


def convert_to_datetime(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    fmt = params.get("format")  # optional
    if fmt:
        return df.assign(**{col: pd.to_datetime(df[col], format=fmt, errors="coerce")})
    return df.assign(**{col: pd.to_datetime(df[col], errors="coerce")})


def convert_to_categorical(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    return df.assign(**{col: df[col].astype("category")})


def trim_whitespace(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    s = df[col]
    if pd.api.types.is_numeric_dtype(s):
        return df
    return df.assign(**{col: s.where(s.isna(), s.astype(str).str.strip())})


def lowercase_text(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    s = df[col]
    if pd.api.types.is_numeric_dtype(s):
        return df
    return df.assign(**{col: s.where(s.isna(), s.astype(str).str.lower())})


def _zscore_bounds(series: pd.Series, z_threshold: float) -> tuple[float, float]:
    s = pd.to_numeric(series, errors="coerce")
    s = s.dropna()
    if s.empty:
        return (float("nan"), float("nan"))
    mean = float(s.mean())
    std = float(s.std() or 0.0)
    if std == 0.0:
        return (mean, mean)
    return (mean - z_threshold * std, mean + z_threshold * std)


def remove_outliers_zscore(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    z = float(params.get("z_threshold", 3.0))
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    s = pd.to_numeric(df[col], errors="coerce")
    mean = float(s.mean())
    std = float(s.std() or 0.0)
    if std == 0.0:
        return df
    zscores = (s - mean) / std
    mask = zscores.abs() <= z
    return df.loc[mask.fillna(True)]


def cap_outliers_zscore(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    z = float(params.get("z_threshold", 3.0))
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    s = pd.to_numeric(df[col], errors="coerce")
    low, high = _zscore_bounds(s, z)
    if low != low or high != high:
        return df
    return df.assign(**{col: s.clip(lower=low, upper=high)})


def _iqr_bounds(series: pd.Series, iqr_multiplier: float) -> tuple[float, float]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return (float("nan"), float("nan"))
    q1 = float(s.quantile(0.25))
    q3 = float(s.quantile(0.75))
    iqr = q3 - q1
    low = q1 - iqr_multiplier * iqr
    high = q3 + iqr_multiplier * iqr
    return (low, high)


def remove_outliers_iqr(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    mult = float(params.get("iqr_multiplier", 1.5))
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    s = pd.to_numeric(df[col], errors="coerce")
    low, high = _iqr_bounds(s, mult)
    if low != low or high != high:
        return df
    mask = (s >= low) & (s <= high)
    return df.loc[mask.fillna(True)]


def cap_outliers_iqr(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    mult = float(params.get("iqr_multiplier", 1.5))
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    s = pd.to_numeric(df[col], errors="coerce")
    low, high = _iqr_bounds(s, mult)
    if low != low or high != high:
        return df
    return df.assign(**{col: s.clip(lower=low, upper=high)})


def drop_duplicates_subset(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    # Alias for remove_duplicates with subset parameter
    subset = params.get("subset")
    return remove_duplicates(df, {"subset": subset})


def sort_by_column(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    col = params.get("column")
    ascending = params.get("ascending", True)
    if not col or not _ensure_column(df, str(col)):
        return df
    col = str(col)
    # If it's datetime-like it should work; otherwise pandas will raise.
    try:
        return df.sort_values(by=col, ascending=bool(ascending), na_position="last")
    except Exception:
        return df

def remove_duplicates(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    # Optional subset parameter: {"subset": ["col1","col2"]}
    subset = params.get("subset")
    if subset is None:
        return df.drop_duplicates()
    subset_cols = _normalize_column_list(subset)
    existing = [c for c in subset_cols if c in df.columns]
    if not existing:
        return df.drop_duplicates()
    return df.drop_duplicates(subset=existing)


# Register transformations (support multiple action names for robustness)
register_transformation("drop_null_rows", drop_null_rows)
register_transformation("remove_null_rows", drop_null_rows)

register_transformation("drop_column", drop_column)
register_transformation("remove_column", drop_column)

register_transformation("fill_null_mean", fill_null_mean)
register_transformation("fill_null_mean_value", fill_null_mean)

register_transformation("normalize_column", normalize_column)
register_transformation("normalize", normalize_column)

register_transformation("remove_duplicates", remove_duplicates)
register_transformation("drop_duplicates", remove_duplicates)

register_transformation("fill_null_median", fill_null_median)
register_transformation("fill_null_mode", fill_null_mode)
register_transformation("fill_null_constant", fill_null_constant)

register_transformation("forward_fill_nulls", forward_fill_nulls)
register_transformation("forward_fill", forward_fill_nulls)
register_transformation("backward_fill_nulls", backward_fill_nulls)
register_transformation("backward_fill", backward_fill_nulls)

register_transformation("drop_null_columns", drop_null_columns)

register_transformation("rename_column", rename_column)

register_transformation("convert_to_numeric", convert_to_numeric)
register_transformation("convert_to_string", convert_to_string)
register_transformation("convert_to_datetime", convert_to_datetime)
register_transformation("convert_to_categorical", convert_to_categorical)

register_transformation("trim_whitespace", trim_whitespace)
register_transformation("lowercase_text", lowercase_text)
register_transformation("lowercase", lowercase_text)

register_transformation("remove_outliers_zscore", remove_outliers_zscore)
register_transformation("cap_outliers_zscore", cap_outliers_zscore)

register_transformation("remove_outliers_iqr", remove_outliers_iqr)
register_transformation("cap_outliers_iqr", cap_outliers_iqr)

register_transformation("drop_duplicates_subset", drop_duplicates_subset)

register_transformation("sort_by_column", sort_by_column)


