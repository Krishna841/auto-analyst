"""
Natural language QA. Improvements: more intents (filter, top_n, lowest, count), column validation with fuzzy match.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd  # type: ignore[reportMissingImports]

try:
    from backend.ai.llm import chat, get_default_model
except ImportError:
    from ai.llm import chat, get_default_model

# Synonyms for column matching (query term -> possible column substrings)
COLUMN_SYNONYMS: dict[str, list[str]] = {
    "revenue": ["revenue", "sales", "amount", "value"],
    "sales": ["sales", "revenue", "amount"],
    "region": ["region", "location", "area", "territory"],
    "category": ["category", "type", "product_type"],
    "date": ["date", "time", "day", "month", "year"],
    "song": ["song", "track", "name", "title", "track_name", "song_name"],
    "mood": ["mood", "genre", "category", "type"],
}


def _fuzzy_match_column(query: str, columns: list[str], threshold: int = 60) -> str | None:
    """Return best matching column name from dataset, or None. Uses rapidfuzz if available."""
    if not columns:
        return None
    q = query.strip().lower()
    if q in columns:
        return q
    for col in columns:
        if col.lower() == q or q in col.lower():
            return col
    try:
        from rapidfuzz import process  # type: ignore[reportMissingImports]
        match = process.extractOne(q, columns, score_cutoff=threshold)
        if match:
            return match[0]
    except ImportError:
        pass
    for syn_key, syns in COLUMN_SYNONYMS.items():
        if syn_key in q:
            for col in columns:
                if any(s in col.lower() for s in syns):
                    return col
    return None


def _resolve_intent_columns(intent: dict[str, Any], columns: list[str], numeric: list[str], categorical: list[str]) -> dict[str, Any]:
    """Ensure group_by, aggregate_column, filter_column, order_by, etc. exist; fuzzy match if missing."""
    out = dict(intent)
    all_cols = columns
    group_by = intent.get("group_by")
    agg_col = intent.get("aggregate_column")
    filter_col = intent.get("filter_column")
    order_by = intent.get("order_by")
    if group_by and group_by not in all_cols:
        out["group_by"] = _fuzzy_match_column(group_by, categorical) or (categorical[0] if categorical else None)
    if agg_col and agg_col not in all_cols:
        out["aggregate_column"] = _fuzzy_match_column(agg_col, numeric) or (numeric[0] if numeric else None)
    if filter_col and filter_col not in all_cols:
        out["filter_column"] = _fuzzy_match_column(filter_col, categorical + numeric + all_cols, threshold=50) or filter_col
    if order_by and order_by not in all_cols and intent.get("intent") == "top_n_rows":
        out["order_by"] = _fuzzy_match_column(order_by, numeric + all_cols, threshold=50) or order_by
    return out


SYSTEM_PROMPT = """You are a data analyst. The user will ask a question about a dataset.
Respond with a single JSON object (no other text) with this shape:
{
  "intent": "group_compare" | "aggregate" | "filter" | "filter_top_n" | "top_n_rows" | "summary",
  "group_by": "<column name or null>",
  "aggregate_column": "<column name or null>",
  "aggregate_func": "sum" | "mean" | "median" | "count" | "min" | "max" | null,
  "order_by": "<column or null>",
  "ascending": true | false,
  "limit": <number or null>,
  "question_column": "<column to answer about>",
  "filter_column": "<column to filter on, e.g. mood>",
  "filter_value": "<value to match, e.g. loudr>",
  "result_column": "<column to list in results, e.g. song name, or null for all>"
}
Use exact column names from the list.
- For "list of top N X where Y = Z" use intent "filter", filter_column=Y, filter_value=Z, limit=N.
- For "N songs with highest X" or "top N X" (list of rows sorted by X) use intent "top_n_rows", order_by=X, limit=N, ascending=false for highest.
- For "which region has the highest sales" (one group winner) use intent "group_compare".
- For "which has lowest" use ascending true. For "how many" use aggregate_func "count". For "average" use "mean"."""


def _parse_filter_heuristic(question: str, columns: list[str]) -> dict[str, Any] | None:
    """Detect 'list of top N X where Y = Z' or 'where Y = Z' pattern."""
    q = question.lower().strip()
    # "where mood = loudr" or "where mood=loudr" or "mood = loudr"
    import re
    where_match = re.search(r"where\s+(\w+)\s*=\s*['\"]?(\w+)['\"]?", q, re.I) or re.search(r"(\w+)\s*=\s*['\"]?(\w+)['\"]?", q)
    filter_col = None
    filter_val = None
    if where_match:
        filter_col_cand, filter_val = where_match.group(1).strip(), where_match.group(2).strip()
        filter_col = _fuzzy_match_column(filter_col_cand, columns, threshold=50) or (filter_col_cand if filter_col_cand in columns else None)
        if not filter_col and filter_col_cand in [c.lower() for c in columns]:
            for c in columns:
                if c.lower() == filter_col_cand:
                    filter_col = c
                    break
    if not filter_col or not filter_val:
        return None
    # "top 10" or "top 5"
    top_match = re.search(r"top\s+(\d+)", q, re.I)
    limit = int(top_match.group(1)) if top_match else 10
    # "songs" or "list of X" -> result_column (column to show in the list)
    result_col = None
    if "song" in q or "track" in q or "list" in q:
        for c in columns:
            if any(s in c.lower() for s in ["song", "track", "name", "title", "track_name", "song_name"]):
                result_col = c
                break
        if result_col is None and columns:
            result_col = columns[0]
    return {
        "intent": "filter",
        "group_by": None,
        "aggregate_column": None,
        "aggregate_func": None,
        "order_by": None,
        "ascending": False,
        "limit": limit,
        "question_column": filter_col,
        "filter_column": filter_col,
        "filter_value": filter_val,
        "result_column": result_col,
    }


def _parse_top_n_rows_heuristic(question: str, columns: list[str], numeric_columns: list[str]) -> dict[str, Any] | None:
    """Detect '10 songs with highest loudness' or 'top N X' -> return top N rows sorted by column X."""
    import re
    q = question.lower().strip()
    # "10 songs with highest loudness" or "top 10 loudness" or "top 10 by loudness"
    limit = None
    for pat in [r"top\s+(\d+)", r"(\d+)\s+songs?", r"(\d+)\s+rows?", r"(\d+)\s+records?"]:
        m = re.search(pat, q, re.I)
        if m:
            limit = int(m.group(1))
            break
    if limit is None:
        return None
    # Find column mentioned for ordering: "highest loudness", "by loudness", "top 10 loudness"
    order_col = None
    ascending = True
    if "highest" in q or "most" in q or "max" in q:
        ascending = False
    elif "lowest" in q or "least" in q or "min" in q:
        ascending = True
    # Prefer numeric/metric columns that appear in the question (for "10 songs with highest loudness")
    candidates = [c for c in columns if c.lower() in q]
    for col in candidates:
        if col in numeric_columns or any(x in col.lower() for x in ["loudness", "danceability", "energy", "sales", "price", "amount", "score", "rating"]):
            order_col = col
            break
    if not order_col and candidates:
        order_col = candidates[0]
    if not order_col:
        return None
    # Use top_n_rows when order column is numeric or looks like a metric
    if order_col in numeric_columns or any(x in order_col.lower() for x in ["loudness", "danceability", "energy", "sales", "price", "amount", "score", "rating"]):
        return {
            "intent": "top_n_rows",
            "group_by": None,
            "aggregate_column": None,
            "aggregate_func": None,
            "order_by": order_col,
            "ascending": ascending,
            "limit": min(limit, 100),
            "question_column": order_col,
            "filter_column": None,
            "filter_value": None,
            "result_column": None,
        }
    return None


def parse_question_to_intent(question: str, columns: list[str], numeric_columns: list[str] | None = None) -> dict[str, Any]:
    """LLM or heuristic intent. Heuristics for filter, top_n_rows, and group_compare."""
    numeric_columns = numeric_columns or []
    # Try "top N rows by X" first (e.g. "10 songs with highest loudness")
    top_n_intent = _parse_top_n_rows_heuristic(question, columns, numeric_columns)
    if top_n_intent:
        return top_n_intent
    # Try filter heuristic (e.g. "top 10 songs where mood = loudr")
    filter_intent = _parse_filter_heuristic(question, columns)
    if filter_intent:
        return filter_intent
    col_list = ", ".join(columns[:30])
    text = chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Columns: [{col_list}]. Question: {question}"},
        ],
        model=get_default_model(),
    )
    if text:
        start = text.find("{")
        if start != -1:
            end = text.rfind("}") + 1
            try:
                parsed = json.loads(text[start:end])
                if parsed.get("intent") in ("filter", "filter_top_n") and parsed.get("filter_column") and parsed.get("filter_value") is not None:
                    return parsed
                if parsed.get("intent") == "top_n_rows" and parsed.get("order_by"):
                    return parsed
                if parsed.get("group_by") or parsed.get("aggregate_column") or parsed.get("intent") == "summary":
                    return parsed
            except json.JSONDecodeError:
                pass
    import re
    q = question.lower()
    for col in columns:
        col_lower = col.lower()
        if col_lower not in q:
            continue
        # Only use group_compare when it's "which category has highest X" (column is categorical-like)
        if "highest" in q or "most" in q or "top" in q or "max" in q:
            if col in numeric_columns and ("songs" in q or "rows" in q or "list" in q or re.search(r"\d+\s+\w+", q)):
                continue  # Let top_n_rows handle "10 songs with highest loudness"
            return {
                "intent": "group_compare",
                "group_by": col,
                "aggregate_column": columns[0] if columns else None,
                "aggregate_func": "sum",
                "order_by": None,
                "ascending": False,
                "limit": 1,
                "question_column": col,
            }
        if "lowest" in q or "least" in q or "min" in q:
            return {
                "intent": "group_compare",
                "group_by": col,
                "aggregate_column": columns[0] if columns else None,
                "aggregate_func": "sum",
                "order_by": None,
                "ascending": True,
                "limit": 1,
                "question_column": col,
            }
        if "average" in q or "mean" in q:
            return {
                "intent": "group_compare",
                "group_by": col,
                "aggregate_column": columns[0] if columns else None,
                "aggregate_func": "mean",
                "order_by": None,
                "ascending": False,
                "limit": 5,
                "question_column": col,
            }
        if "count" in q or "how many" in q:
            return {
                "intent": "group_compare",
                "group_by": col,
                "aggregate_column": col,
                "aggregate_func": "count",
                "order_by": None,
                "ascending": False,
                "limit": 5,
                "question_column": col,
            }
    return {
        "intent": "summary",
        "group_by": None,
        "aggregate_column": None,
        "aggregate_func": None,
        "order_by": None,
        "ascending": True,
        "limit": None,
        "question_column": None,
    }


def _safe_value_compare(df: pd.DataFrame, col: str, val: str):
    """Compare column values to val (string or number). Handles mixed types."""
    s = df[col].astype(str).str.strip().str.lower()
    val_clean = str(val).strip().lower()
    return s == val_clean


def execute_intent(df: pd.DataFrame, intent: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Execute safe pandas from intent. Column names validated/fuzzy-matched."""
    numeric = profile.get("numeric_columns") or []
    categorical = profile.get("categorical_columns") or []
    all_cols = list(df.columns)
    intent = _resolve_intent_columns(intent, all_cols, numeric, categorical)

    intent_type = intent.get("intent") or "summary"
    group_by = intent.get("group_by")
    agg_col = intent.get("aggregate_column")
    agg_func = intent.get("aggregate_func") or "sum"
    ascending = intent.get("ascending", False)
    limit = intent.get("limit")
    filter_column = intent.get("filter_column")
    filter_value = intent.get("filter_value")
    result_column = intent.get("result_column")

    if group_by and group_by not in all_cols:
        group_by = categorical[0] if categorical else None
    if agg_col and agg_col not in all_cols:
        agg_col = numeric[0] if numeric else None

    try:
        # Top N rows: "10 songs with highest loudness" -> sort by column, take first N rows
        order_col = intent.get("order_by")
        if intent_type == "top_n_rows" and order_col:
            if order_col and order_col in all_cols:
                asc = intent.get("ascending", False)
                limit_n = min(int(limit) if limit else 10, 100)
                sorted_df = df.sort_values(by=order_col, ascending=asc, na_position="last")
                rows = sorted_df.head(limit_n)
                if rows.empty:
                    return {
                        "answer": "No data to sort.",
                        "data": [],
                        "query_description": f"Top {limit_n} by {order_col}",
                    }
                data_list = rows.fillna("").to_dict(orient="records")
                for r in data_list:
                    for k, v in list(r.items()):
                        if hasattr(v, "item"):
                            r[k] = v.item()
                        elif pd.isna(v):
                            r[k] = None
                display_col = result_column if result_column and result_column in all_cols else all_cols[0]
                if display_col in rows.columns:
                    items = rows[display_col].astype(str).tolist()
                else:
                    items = rows.iloc[:, 0].astype(str).tolist()
                answer = f"Top {len(rows)} rows by {order_col} ({'highest first' if not asc else 'lowest first'}): " + ", ".join(str(x) for x in items[:15])
                if len(items) > 15:
                    answer += f" ... and {len(items) - 15} more."
                return {
                    "answer": answer,
                    "data": data_list,
                    "query_description": f"Top {limit_n} by {order_col}",
                }
        if intent_type in ("filter", "filter_top_n") and filter_column and filter_column in all_cols and filter_value is not None:
            mask = _safe_value_compare(df, filter_column, filter_value)
            filtered = df.loc[mask]
            n = len(filtered)
            limit_n = min(int(limit) if limit else 10, 100)
            rows = filtered.head(limit_n)
            if result_column and result_column in all_cols:
                display_col = result_column
            else:
                display_col = all_cols[0]
            if rows.empty:
                return {
                    "answer": f"No rows where {filter_column} = '{filter_value}'.",
                    "data": [],
                    "query_description": f"Filter {filter_column}={filter_value}",
                }
            # Build list of records for display
            if display_col in rows.columns:
                items = rows[display_col].astype(str).tolist()
            else:
                items = rows.iloc[:, 0].astype(str).tolist()
            data_list = rows.head(limit_n).fillna("").to_dict(orient="records")
            for r in data_list:
                for k, v in list(r.items()):
                    if hasattr(v, "item"):
                        r[k] = v.item()
                    elif pd.isna(v):
                        r[k] = None
            answer = f"Found {n} row(s) where {filter_column} = '{filter_value}'. Top {min(limit_n, n)}: " + ", ".join(str(x) for x in items[:15])
            if len(items) > 15:
                answer += f" ... and {len(items) - 15} more."
            return {
                "answer": answer,
                "data": data_list,
                "query_description": f"Filter {filter_column}={filter_value}, limit {limit_n}",
            }
        if intent_type == "group_compare" and group_by:
            use_col = agg_col if agg_col and agg_col in numeric else (numeric[0] if numeric else group_by)
            if use_col in df.columns and pd.api.types.is_numeric_dtype(df[use_col]):
                g = df.groupby(group_by, dropna=False)[use_col].agg(agg_func)
            else:
                g = df.groupby(group_by, dropna=False).size()
                use_col = "count"
            g = g.sort_values(ascending=ascending)
            if limit:
                g = g.head(int(limit))
            top = g.index[0] if len(g) else None
            val = g.iloc[0] if len(g) else None
            answer = f"{group_by} '{top}' has {agg_func} {use_col}: {val}" if top is not None else "No data."
            return {
                "answer": answer,
                "data": g.round(4).to_dict() if hasattr(g, "round") else dict(g),
                "query_description": f"Group by {group_by}, {agg_func} of {use_col}",
            }
        if intent_type == "aggregate" and agg_col and agg_col in numeric:
            val = getattr(df[agg_col], agg_func)()
            return {
                "answer": f"{agg_func} of {agg_col}: {val}",
                "data": {agg_func: val},
                "query_description": f"{agg_func}({agg_col})",
            }
        if intent_type == "summary":
            return {
                "answer": f"Dataset has {len(df)} rows and {len(all_cols)} columns: {', '.join(all_cols[:10])}.",
                "data": {"rows": len(df), "columns": all_cols},
                "query_description": "Dataset summary",
            }
    except Exception as e:
        return {
            "answer": f"Could not compute: {e}",
            "data": {},
            "query_description": "Error",
            "error": str(e),
        }
    return {
        "answer": "No matching analysis for this question.",
        "data": {},
        "query_description": "Unhandled intent",
    }


def answer_question(df: pd.DataFrame, question: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Parse question, resolve columns, execute, return answer."""
    columns = profile.get("columns") or list(df.columns)
    numeric = profile.get("numeric_columns") or [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    intent = parse_question_to_intent(question, columns, numeric_columns=numeric)
    result = execute_intent(df, intent, profile)
    result["intent"] = intent
    return result
