"""
Anomaly detection: Z-score, IQR, Isolation Forest.
Improvements: configurable thresholds, per-method counts, top-N by severity, optional explanation.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _to_serializable(obj: Any) -> Any:
    if hasattr(obj, "item"):
        return obj.item()
    if pd.isna(obj):
        return None
    return obj


def _explain_anomaly(record: dict[str, Any], method: str) -> str:
    """Generate short explanation for an anomaly."""
    if method == "z_score":
        val = record.get("value")
        z = record.get("z_score")
        th = record.get("threshold", 3)
        return f"Value {val} is {abs(z):.1f} standard deviations from the mean (threshold {th}). Possible outlier or data error."
    if method == "iqr":
        val = record.get("value")
        b = record.get("bounds", {})
        return f"Value {val} lies outside IQR bounds [{b.get('low')}, {b.get('high')}]. Possible extreme value or data error."
    if method == "isolation_forest":
        return "Flagged as anomalous by Isolation Forest (multivariate). Could indicate unusual combination of values."
    return "Anomaly detected."


def detect_anomalies_zscore(
    df: pd.DataFrame, column: str, threshold: float = 3.0
) -> list[dict[str, Any]]:
    """Flag rows where |z-score| > threshold. Include severity (abs z-score) for ranking."""
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return []
    s = df[column].dropna()
    if len(s) < 3:
        return []
    mean, std = s.mean(), s.std()
    if std == 0:
        return []
    z = (s - mean) / std
    anomalies = []
    for idx in z[z.abs() > threshold].index:
        rec = {
            "index": _to_serializable(idx),
            "column": column,
            "value": _to_serializable(df.loc[idx, column]),
            "z_score": _to_serializable(round(z.loc[idx], 4)),
            "method": "z_score",
            "threshold": threshold,
            "severity": abs(z.loc[idx]),
        }
        rec["explanation"] = _explain_anomaly(rec, "z_score")
        anomalies.append(rec)
    return anomalies


def detect_anomalies_iqr(
    df: pd.DataFrame, column: str, multiplier: float = 1.5
) -> list[dict[str, Any]]:
    """Flag rows outside IQR bounds. Severity = distance from nearest bound (normalized)."""
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return []
    s = df[column].dropna()
    if len(s) < 4:
        return []
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return []
    low, high = q1 - multiplier * iqr, q3 + multiplier * iqr
    anomalies = []
    for idx in s[(s < low) | (s > high)].index:
        val = df.loc[idx, column]
        dist = (low - val) if val < low else (val - high)
        severity = dist / iqr if iqr else 0
        rec = {
            "index": _to_serializable(idx),
            "column": column,
            "value": _to_serializable(val),
            "method": "iqr",
            "bounds": {"low": _to_serializable(low), "high": _to_serializable(high)},
            "severity": _to_serializable(round(severity, 4)),
        }
        rec["explanation"] = _explain_anomaly(rec, "iqr")
        anomalies.append(rec)
    return anomalies


def detect_anomalies_isolation_forest(
    df: pd.DataFrame, numeric_columns: list[str], contamination: float = 0.05
) -> list[dict[str, Any]]:
    """Isolation Forest; severity = negative of decision function (higher = more anomalous)."""
    if not numeric_columns or len(df) < 10:
        return []
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return []
    subset = df[numeric_columns].dropna(how="all")
    if len(subset) < 10:
        return []
    clf = IsolationForest(contamination=contamination, random_state=42)
    clf.fit(subset)
    scores = -clf.decision_function(subset)  # higher = more anomalous
    pred = clf.predict(subset)
    anomalies = []
    for i, idx in enumerate(subset.index):
        if pred[i] == -1:
            row = df.loc[idx, numeric_columns].to_dict()
            rec = {
                "index": _to_serializable(idx),
                "columns": numeric_columns,
                "values": {k: _to_serializable(v) for k, v in row.items()},
                "method": "isolation_forest",
                "severity": _to_serializable(round(float(scores[i]), 4)),
            }
            rec["explanation"] = _explain_anomaly(rec, "isolation_forest")
            anomalies.append(rec)
    return anomalies


def run_anomaly_detection(
    df: pd.DataFrame,
    numeric_columns: list[str],
    methods: list[str] | None = None,
    z_threshold: float = 3.0,
    iqr_multiplier: float = 1.5,
    top_n: int | None = 50,
) -> dict[str, Any]:
    """
    Run anomaly detection. Returns per-method counts and top-N by severity.
    Configurable: z_threshold, iqr_multiplier; top_n caps returned list (by severity).
    """
    methods = methods or ["z_score", "iqr", "isolation_forest"]
    all_anomalies: list[dict[str, Any]] = []
    by_method: dict[str, list] = {"z_score": [], "iqr": [], "isolation_forest": []}

    for col in numeric_columns[:10]:
        if "z_score" in methods:
            z_anomalies = detect_anomalies_zscore(df, col, threshold=z_threshold)
            by_method["z_score"].extend(z_anomalies)
            all_anomalies.extend(z_anomalies)
        if "iqr" in methods:
            iqr_anomalies = detect_anomalies_iqr(df, col, multiplier=iqr_multiplier)
            by_method["iqr"].extend(iqr_anomalies)
            all_anomalies.extend(iqr_anomalies)

    if "isolation_forest" in methods and numeric_columns:
        if_anomalies = detect_anomalies_isolation_forest(df, numeric_columns[:20])
        by_method["isolation_forest"] = if_anomalies
        all_anomalies.extend(if_anomalies)

    # Sort by severity (desc) and take top_n
    def get_severity(a: dict[str, Any]) -> float:
        return float(a.get("severity", 0))

    all_anomalies.sort(key=get_severity, reverse=True)
    if top_n is not None:
        all_anomalies = all_anomalies[:top_n]

    counts = {
        "z_score": len(by_method["z_score"]),
        "iqr": len(by_method["iqr"]),
        "isolation_forest": len(by_method["isolation_forest"]),
    }
    return {
        "anomalies": all_anomalies,
        "by_method": {k: v[:50] for k, v in by_method.items()},
        "counts": counts,
        "total_count": sum(counts.values()),
    }
