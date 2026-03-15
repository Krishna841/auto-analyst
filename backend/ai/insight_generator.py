"""
LLM-based insight generation. Improvement: ground prompts with extracted key numbers.
"""

from __future__ import annotations

import json
from typing import Any

try:
    from backend.ai.llm import chat, get_default_model
except ImportError:
    from ai.llm import chat, get_default_model


def _extract_key_numbers(statistical_results: dict[str, Any]) -> list[str]:
    """Extract 3–5 key statistics to ground the LLM and reduce hallucination."""
    lines: list[str] = []
    # Group analysis: top group and share if available
    ga = statistical_results.get("group_analysis")
    if isinstance(ga, dict) and "by_column" in ga:
        for item in (ga["by_column"] or [])[:2]:
            if not isinstance(item, dict):
                continue
            g = item.get("group_analysis") or {}
            if not g:
                continue
            group_col = item.get("group_column", "")
            val_col = (item.get("value_columns") or [""])[0]
            if isinstance(g, dict):
                try:
                    sorted_items = sorted(g.items(), key=lambda x: (x[1] or {}).get(val_col, 0) if isinstance(x[1], dict) else 0, reverse=True)
                    if sorted_items:
                        top_name, top_vals = sorted_items[0]
                        top_val = top_vals.get(val_col, top_vals) if isinstance(top_vals, dict) else top_vals
                        total = sum((v.get(val_col, v) if isinstance(v, dict) else v) for _, v in sorted_items)
                        pct = round(100 * float(top_val) / total, 1) if total else 0
                        lines.append(f"Top {group_col}: {top_name} ({pct}% of {val_col})")
                except (TypeError, ZeroDivisionError):
                    pass
    elif isinstance(ga, dict) and "group_analysis" in ga:
        g = ga.get("group_analysis") or {}
        group_col = ga.get("group_column", "")
        val_col = (ga.get("value_columns") or [""])[0]
        if isinstance(g, dict) and g:
            try:
                sorted_items = sorted(g.items(), key=lambda x: (x[1] or {}).get(val_col, 0) if isinstance(x[1], dict) else 0, reverse=True)
                if sorted_items:
                    top_name, top_vals = sorted_items[0]
                    top_val = top_vals.get(val_col, top_vals) if isinstance(top_vals, dict) else top_vals
                    lines.append(f"Top {group_col}: {top_name} with {val_col}={top_val}")
            except TypeError:
                pass
    # Correlation: strongest pair
    corr = statistical_results.get("correlations") or {}
    if isinstance(corr, dict):
        c = corr.get("correlations") or corr
        if isinstance(c, dict) and c:
            best_pair, best_val = None, -2
            for col1, row in c.items():
                if not isinstance(row, dict):
                    continue
                for col2, val in row.items():
                    if col1 != col2 and isinstance(val, (int, float)) and -1 <= val <= 1:
                        if abs(val) > abs(best_val):
                            best_val = val
                            best_pair = (col1, col2)
            if best_pair:
                lines.append(f"Strongest correlation: {best_pair[0]} vs {best_pair[1]} = {round(best_val, 2)}")
    # Trend: mention if present
    trend = statistical_results.get("trend_analysis") or {}
    if isinstance(trend, dict) and trend.get("trend_analysis"):
        lines.append("Trend over time computed for numeric columns.")
    return lines[:5]


def generate_insights(
    dataset_summary: str,
    statistical_results: dict[str, Any],
    max_bullets: int = 5,
) -> dict[str, Any]:
    """Generate insights; prompt includes extracted key numbers to ground the LLM."""
    key_numbers = _extract_key_numbers(statistical_results)
    prompt = _build_prompt(dataset_summary, statistical_results, max_bullets, key_numbers)
    model = get_default_model()
    text = chat(
        messages=[
            {
                "role": "system",
                "content": "You are a concise data analyst. Use ONLY the statistics provided. Output only key insights as bullet points. No preamble.",
            },
            {"role": "user", "content": prompt},
        ],
        model=model,
    )
    if text:
        bullets = [line.strip().lstrip("-•* ").strip() for line in text.splitlines() if line.strip()]
        return {
            "insights": bullets[:max_bullets],
            "raw_response": text,
            "model": model,
        }
    return {
        **_placeholder_insights(dataset_summary, statistical_results),
        "model": None,
        "placeholder": True,
    }


def _build_prompt(
    dataset_summary: str,
    statistical_results: dict[str, Any],
    max_bullets: int,
    key_numbers: list[str],
) -> str:
    parts = [f"Dataset summary:\n{dataset_summary}"]
    if key_numbers:
        parts.append("\nKey statistics (use these):")
        parts.append("\n".join(f"- {k}" for k in key_numbers))
    if statistical_results:
        parts.append("\nFull statistical results (reference):")
        parts.append(json.dumps(statistical_results, default=str)[:1500])
    parts.append(f"\nGenerate exactly {max_bullets} key insights as bullet points. One line per bullet. Base insights on the key statistics above.")
    return "\n".join(parts)


def _placeholder_insights(dataset_summary: str, statistical_results: dict[str, Any]) -> dict[str, Any]:
    insights = ["Start Ollama (e.g. ollama run llama3.2) for AI-generated insights."]
    if statistical_results:
        if "correlations" in statistical_results:
            insights.append("Correlation analysis was run on numeric columns.")
        if "group_analysis" in statistical_results:
            insights.append("Group comparison by category is available.")
        if "trend_analysis" in statistical_results:
            insights.append("Trend over time was computed.")
    return {"insights": insights[:5], "raw_response": ""}
