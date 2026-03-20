from __future__ import annotations

from typing import Any, Dict

import re


def _extract_column_after_keywords(q: str, keywords: list[str]) -> str | None:
    """
    Try to extract the first token after any keyword.
    Example: "drop column country_code" -> country_code
    """
    for kw in keywords:
        if kw in q:
            after = q.split(kw, 1)[1].strip()
            if not after:
                return None
            return after.split()[0].strip(" ,.")
    return None


def parse_transform_intent(message: str) -> Dict[str, Any] | None:
    """
    Map user message to a safe transformation intent:
    { "action": "...", "parameters": { ... } }

    This is a heuristic parser (no LLM) to keep transformations safe.
    """
    q = message.lower().strip()

    # undo/redo/reset
    if q in {"undo", "undo last", "revert"}:
        return {"action": "undo", "parameters": {}}
    if q in {"redo", "redo last"}:
        return {"action": "redo", "parameters": {}}
    if q in {"reset", "reset dataset", "clear pipeline"}:
        return {"action": "reset", "parameters": {}}

    # drop column
    if q.startswith("drop column") or " drop column " in f" {q} ":
        col = _extract_column_after_keywords(q, ["drop column", "drop"])
        if col:
            return {"action": "drop_column", "parameters": {"column": col}}

    if q.startswith("remove column") or " remove column " in f" {q} ":
        col = _extract_column_after_keywords(q, ["remove column"])
        if col:
            return {"action": "drop_column", "parameters": {"column": col}}

    # remove null rows / drop nulls
    if "remove null" in q or "drop null" in q or "drop na" in q:
        col = _extract_column_after_keywords(q, ["in ", "on "])
        return {"action": "drop_null_rows", "parameters": {"column": col}}

    # fill null mean
    if ("fill" in q and "null" in q and "mean" in q) or ("fill null mean" in q):
        col = _extract_column_after_keywords(q, ["fill", "null", "mean"])
        # better: try to find "fill null <col> with mean"
        m = re.search(r"fill\s+nulls?\s+([a-zA-Z_]\w*)", q)
        if m:
            col = m.group(1)
        return {"action": "fill_null_mean", "parameters": {"column": col}}

    # fill null median
    if ("fill" in q and "null" in q and "median" in q) or ("fill null median" in q):
        m = re.search(r"median\s*([a-zA-Z_]\w*)", q)
        if m:
            col = m.group(1)
        else:
            col = _extract_column_after_keywords(q, ["fill", "null", "median"])
        return {"action": "fill_null_median", "parameters": {"column": col}}

    # fill null mode
    if ("fill" in q and "null" in q and "mode" in q) or ("fill null mode" in q):
        m = re.search(r"mode\s*([a-zA-Z_]\w*)", q)
        if m:
            col = m.group(1)
        else:
            col = _extract_column_after_keywords(q, ["fill", "null", "mode"])
        return {"action": "fill_null_mode", "parameters": {"column": col}}

    # fill null constant: "fill null sales with constant 0" or "fill nulls in sales with 0"
    if "fill" in q and "null" in q and ("constant" in q or "with" in q):
        # try parse: "... with constant <value>"
        m_val = re.search(r"constant\s+(-?\d+(?:\.\d+)?)", q)
        m_col = re.search(r"fill\s+null\w*\s+([a-zA-Z_]\w*)", q)
        if m_val and m_col:
            raw_val = m_val.group(1)
            val: int | float = float(raw_val) if "." in raw_val else int(raw_val)
            return {
                "action": "fill_null_constant",
                "parameters": {"column": m_col.group(1), "value": val},
            }
        # try "fill nulls <col> with <value>"
        m_val2 = re.search(r"with\s+(-?\d+(?:\.\d+)?)", q)
        # get first token after "null" if possible
        m_col2 = re.search(r"null\w*\s+([a-zA-Z_]\w*)", q)
        if m_val2 and m_col2:
            raw_val2 = m_val2.group(1)
            val2: int | float = float(raw_val2) if "." in raw_val2 else int(raw_val2)
            return {
                "action": "fill_null_constant",
                "parameters": {"column": m_col2.group(1), "value": val2},
            }

    # normalize
    if q.startswith("normalize ") or " normalize " in f" {q} ":
        col = q.split("normalize", 1)[1].strip().split()[0].strip(" ,.")
        return {"action": "normalize_column", "parameters": {"column": col}}

    # forward fill / backward fill
    if "forward fill" in q or "ffill" in q:
        m = re.search(r"forward fill\w*\s*([a-zA-Z_]\w*)", q)
        col = m.group(1) if m else _extract_column_after_keywords(q, ["fill", "forward"])
        return {"action": "forward_fill_nulls", "parameters": {"column": col}}
    if "backward fill" in q or "bfill" in q:
        m = re.search(r"backward fill\w*\s*([a-zA-Z_]\w*)", q)
        col = m.group(1) if m else _extract_column_after_keywords(q, ["fill", "backward"])
        return {"action": "backward_fill_nulls", "parameters": {"column": col}}

    # trim whitespace / lowercase
    if "trim" in q and ("whitespace" in q or "spaces" in q):
        col = _extract_column_after_keywords(q, ["trim", "column", "on "])
        return {"action": "trim_whitespace", "parameters": {"column": col}}
    if "lowercase" in q:
        col = _extract_column_after_keywords(q, ["lowercase", "column", "on "])
        return {"action": "lowercase_text", "parameters": {"column": col}}

    # convert dtype
    if ("convert" in q or "change type" in q) and "to numeric" in q:
        col = _extract_column_after_keywords(q, ["convert", "to numeric", "column"])
        return {"action": "convert_to_numeric", "parameters": {"column": col}}
    if ("convert" in q or "change type" in q) and "to string" in q:
        col = _extract_column_after_keywords(q, ["convert", "to string", "column"])
        return {"action": "convert_to_string", "parameters": {"column": col}}
    if ("convert" in q or "change type" in q) and "to datetime" in q:
        col = _extract_column_after_keywords(q, ["convert", "to datetime", "column"])
        return {"action": "convert_to_datetime", "parameters": {"column": col}}

    # remove duplicates
    if "remove duplicate" in q or "drop duplicate" in q:
        return {"action": "remove_duplicates", "parameters": {}}

    # outliers: remove/cap with z-score or iqr
    if "remove outliers" in q and "z" in q:
        col = _extract_column_after_keywords(q, ["remove outliers", "zscore", "z-score"])
        return {"action": "remove_outliers_zscore", "parameters": {"column": col, "z_threshold": 3.0}}
    if "cap outliers" in q and "z" in q:
        col = _extract_column_after_keywords(q, ["cap outliers", "zscore", "z-score"])
        return {"action": "cap_outliers_zscore", "parameters": {"column": col, "z_threshold": 3.0}}
    if "remove outliers" in q and "iqr" in q:
        col = _extract_column_after_keywords(q, ["remove outliers", "iqr"])
        return {"action": "remove_outliers_iqr", "parameters": {"column": col, "iqr_multiplier": 1.5}}
    if "cap outliers" in q and "iqr" in q:
        col = _extract_column_after_keywords(q, ["cap outliers", "iqr"])
        return {"action": "cap_outliers_iqr", "parameters": {"column": col, "iqr_multiplier": 1.5}}

    # sorting
    if "sort" in q and "by" in q:
        # naive parse: "sort by sales desc/asc"
        col = q.split("by", 1)[1].strip().split()[0].strip(" ,.")
        ascending = not ("desc" in q or "descending" in q)
        return {"action": "sort_by_column", "parameters": {"column": col, "ascending": ascending}}

    return None

