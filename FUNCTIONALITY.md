# Current Functionalities & How to Make Them More Accurate

## 1. Current Functionalities

### Backend API (FastAPI)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health / API info |
| `/upload` | POST | Upload CSV → profile + analysis plan, save to `datasets/{id}.csv` |
| `/dataset/{upload_id}/plan` | GET | Return profile + analysis plan for a dataset |
| `/dataset/{upload_id}/analyze` | POST | Run correlation, group comparison, trend analysis |
| `/dataset/{upload_id}/insights` | POST | Generate AI insights from profile + stats (Ollama/OpenAI) |
| `/dataset/{upload_id}/anomalies` | POST | Run Z-score, IQR, Isolation Forest on numeric columns |
| `/dataset/{upload_id}/ask` | POST | Natural language question → intent → safe pandas → answer |
| `/dataset/{upload_id}/pipeline` | POST | Full run: profile → plan → stats → insights → anomalies |

### Dataset Profiling (`analysis/profiler.py`)

- **Column type detection**: numeric, categorical, datetime (including date-like object columns by name/content).
- **Missing values**: count per column.
- **Output**: `rows`, `columns`, `column_types`, `numeric_columns`, `categorical_columns`, `datetime_columns`, `missing_values`.

### Analysis Planner (`analysis/analysis_engine.py`)

- **Rules**: datetime → trend; categorical + numeric → group comparison; 2+ numeric → correlation; 1 numeric → summary stats.
- **Output**: `steps` (e.g. `trend_analysis`, `group_comparison`, `correlation_analysis`), `descriptions`, `analysis_plan` (numbered list).

### Statistical Layer (`analysis/statistics.py`)

- **Correlation**: `df.corr()` on numeric columns, JSON-serialized.
- **Group comparison**: `groupby(categorical)[numeric].agg(sum)` (first category, first 3 numerics).
- **Trend**: resample by date (default daily), sum numeric columns; date column inferred from profile or parsed.
- **Summary stats**: `describe()` for numeric columns.

### Anomaly Detection (`analysis/anomaly_detector.py`)

- **Z-score**: flag rows where \|z\| > 3 (configurable) per numeric column.
- **IQR**: flag below Q1 − 1.5×IQR or above Q3 + 1.5×IQR.
- **Isolation Forest**: sklearn on numeric columns, contamination 0.05.
- **Caps**: 100 per method, 200 total for response size.

### AI / LLM

- **LLM client** (`ai/llm.py`): Ollama by default (local), optional OpenAI fallback via `OPENAI_API_KEY`.
- **Insight generator** (`ai/insight_generator.py`): Converts profile + statistical results into bullet-point insights.
- **Query agent** (`ai/query_agent.py`): Question → LLM intent (JSON) or heuristic → `execute_intent` (group_compare, aggregate, summary).

### Natural Language QA (`ai/query_agent.py`)

- **Supported intents**: `group_compare`, `aggregate`, `summary`.
- **Execution**: Safe pandas only (groupby + agg, single-column agg, or summary); no arbitrary code.
- **Fallback**: If LLM unavailable or JSON parse fails, keyword heuristic (“highest”, “most”, “top”, “max” + column name).

### Frontend (Next.js)

- **Upload**: CSV upload, step/percentage progress, result with upload_id, rows, columns, analysis plan.
- **Insights**: Generate insights + run analyze; show bullets and optional Plotly group bar chart + raw results.
- **Anomalies**: Run detection, show total count and list of anomalies by method.
- **Ask**: Text input for question, display answer and optional data.
- **State**: Current `upload_id` in `localStorage`; all pages use it.

---

## 2. How to Make It More Accurate

### Profiling

| Current limitation | Improvement |
|--------------------|-------------|
| Date inference only for columns whose name contains date/time/day/month/year | Add inference for any column that parses as datetime (e.g. try `pd.to_datetime` on sample); support more date formats. |
| Categorical vs numeric by dtype + unique count only | Use cardinality threshold (e.g. unique &lt; 5% of rows → categorical); optionally use semantic names (e.g. “id” → skip from correlation). |
| No detection of IDs (e.g. customer_id) | Mark high-cardinality unique columns as “id” and exclude from correlation/group by default. |
| Single profile, no schema versioning | Store profile with schema version; re-profile on request or when dataset changes. |

### Analysis planner

| Current limitation | Improvement |
|--------------------|-------------|
| Always first categorical, first numerics | Let user or LLM choose “focus” columns; or run multiple group-bys (e.g. by each categorical) and pick by variance. |
| Trend only daily | Add freq detection (e.g. infer D/W/M from date range) or allow query param (e.g. `freq=W`). |
| No “distribution” or “top N” steps | Add steps: histogram/distribution for numeric; value_counts/top_n for categorical. |

### Statistics

| Current limitation | Improvement |
|--------------------|-------------|
| Group comparison uses only first category and sum | Support mean/median; run for each categorical or let user choose; handle multiple value columns explicitly. |
| Trend always sum | Support mean (e.g. for rates); handle missing dates (reindex with fill_value=0 or forward fill). |
| Correlation on raw columns only | Optionally drop constant columns; support Spearman in addition to Pearson; cap matrix size for huge column sets. |
| Serialization edge cases | Already fixed for nested dicts; add handling for numpy integers/longs and Inf/NaN in JSON. |

### Anomaly detection

| Current limitation | Improvement |
|--------------------|-------------|
| Fixed Z-score threshold (3) and IQR multiplier (1.5) | Make configurable via API (e.g. query params or body); document “strict” vs “relaxed” presets. |
| Per-column Z-score/IQR only | Add multivariate (e.g. Mahalanobis) or use Isolation Forest as primary for multi-column. |
| No explanation for why a point is anomalous | Add “nearest normal” or feature contribution (e.g. which column drove the score); optional short LLM explanation. |
| Caps (100/200) may hide important anomalies | Return summary (counts by method) + paginated or “top N by severity” instead of truncating arbitrarily. |

### Insight generation (LLM)

| Current limitation | Improvement |
|--------------------|-------------|
| Single prompt with raw JSON stats | Structure prompt with clear sections (summary, correlations, groups, trends); pass sample numbers not full matrix. |
| No grounding in actual numbers | Include 2–3 key numbers in the prompt (e.g. “Top region: North, 45% of sales”) so the model doesn’t hallucinate. |
| Placeholder when Ollama down | Keep placeholder but add “Retry” and optional “Use last cached insights” if you add caching. |

### Natural language QA

| Current limitation | Improvement |
|--------------------|-------------|
| Limited intents (group_compare, aggregate, summary) | Add intents: filter (e.g. “sales &gt; 1000”), top_n with sort, comparison between two groups, trend “over time”. |
| Heuristic only for “highest/most/top” + column name | Expand heuristics: “lowest”, “average”, “count”, “total”; fuzzy match column names (e.g. “revenue” → “sales”). |
| LLM intent often returns wrong column names | Pass column list + sample values or types in the prompt; add validation: if intent column not in df.columns, map from synonyms or ask user. |
| No clarification when ambiguous | If confidence low or multiple interpretations, return “Did you mean: …?” with options. |

### General accuracy

| Area | Improvement |
|------|-------------|
| **Column name handling** | Normalize (strip, lower) for matching; maintain a column alias map (e.g. “revenue” → “sales”) from schema or first run. |
| **Date handling** | Parse dates at upload; store inferred freq; use same parsing in trend and in QA (“in 2024”, “last month”). |
| **Errors and edge cases** | Validate profile (e.g. no empty numeric_columns when dtype is numeric); return 4xx with clear message for “no data”, “single row”, “all null column”. |
| **Caching** | Cache profile and analysis results per upload_id (and invalidation key) to avoid re-running when user only asks again or refreshes insights. |
| **Evaluation** | Add a small test suite: fixed CSV + expected profile and analysis outputs; regression tests for serialization and intent parsing. |

---

## 3. Quick Wins (High Impact, Lower Effort)

1. **Profiler**: Try parsing every object column as datetime; if it parses, mark as datetime.
2. **Query agent**: Add “lowest”, “average”, “count” to heuristic; validate intent columns against `df.columns` and substitute first categorical/numeric if missing.
3. **Insight generator**: Include 3–5 key numbers in the prompt (e.g. top group value, correlation range).
4. **Anomalies**: Expose `threshold` and `multiplier` as optional query/body params.
5. **Statistics**: Use first valid date column when profile has no datetime (e.g. try columns with “date” in name).

Implementing these will improve robustness and perceived accuracy without large architectural changes.
