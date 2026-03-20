"""
AI Autonomous Data Analyst — FastAPI backend.
"""

import io
import sys
import uuid
from pathlib import Path
from typing import Any, Dict

# Allow running as python main.py from backend/ or as uvicorn backend.main:app from project root
_BACKEND_DIR = Path(__file__).resolve().parent
_ROOT = _BACKEND_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env from project root so OLLAMA_* and OPENAI_* are available
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from backend.analysis.profiler import profile_dataframe
    from backend.analysis.analysis_engine import build_analysis_plan
    from backend.analysis.statistics import run_all_analyses
    from backend.analysis.anomaly_detector import run_anomaly_detection
    from backend.analysis.charts import generate_charts
    from backend.ai.insight_generator import generate_insights
    from backend.ai.query_agent import answer_question
    from backend.dataset.pipeline_manager import (
        add_transformation,
        get_pipeline as get_transform_pipeline,
        get_profile as get_transform_profile,
        materialize_dataframe,
        redo_last as redo_transform,
        register_dataset as register_transform_dataset,
        reset_pipeline as reset_transform_pipeline,
        set_profile as set_transform_profile,
        undo_last as undo_transform,
    )
    from backend.chat.intent_parser import parse_transform_intent
    from backend.chat.command_executor import execute_control, execute_transform
    # Import for side-effects: registers cleaning transformations in the pipeline registry.
    import backend.analysis.cleaning  # noqa: F401
except ImportError:
    from analysis.profiler import profile_dataframe
    from analysis.analysis_engine import build_analysis_plan
    from analysis.statistics import run_all_analyses
    from analysis.anomaly_detector import run_anomaly_detection
    from analysis.charts import generate_charts
    from ai.insight_generator import generate_insights
    from ai.query_agent import answer_question
    from dataset.pipeline_manager import (
        add_transformation,
        get_pipeline as get_transform_pipeline,
        get_profile as get_transform_profile,
        materialize_dataframe,
        redo_last as redo_transform,
        register_dataset as register_transform_dataset,
        reset_pipeline as reset_transform_pipeline,
        set_profile as set_transform_profile,
        undo_last as undo_transform,
    )
    from chat.intent_parser import parse_transform_intent
    from chat.command_executor import execute_control, execute_transform
    import analysis.cleaning  # noqa: F401

app = FastAPI(title="Autonomous AI Data Analyst API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persist uploaded CSVs under datasets/ for reuse in later phases
DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)

# In-memory cache of loaded dataframes keyed by upload_id (optional for same-session use)
_datasets: dict[str, pd.DataFrame] = {}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Autonomous AI Data Analyst API", "docs": "/docs"}


@app.get("/datasets")
def list_datasets() -> dict:
    """List available datasets by scanning datasets/ CSV files."""
    out: list[dict[str, Any]] = []
    for csv_path in DATASETS_DIR.glob("*.csv"):
        dataset_id = csv_path.stem
        try:
            df = pd.read_csv(csv_path)
            profile = profile_dataframe(df)
            cols = profile.get("columns") or []
            out.append(
                {
                    "upload_id": dataset_id,
                    "filename": csv_path.name,
                    "rows": profile.get("rows"),
                    "columns_count": len(cols),
                    "columns": cols[:30],
                }
            )
        except Exception:
            # If one dataset can't be profiled, still list its id.
            out.append({"upload_id": dataset_id, "filename": csv_path.name, "rows": None, "columns_count": None, "columns": []})
    return {"datasets": out}


def _get_dataframe(upload_id: str) -> pd.DataFrame:
    """
    Return the current dataframe version by materializing the transformation pipeline.
    If the dataset_id was not registered yet, register it from disk.
    """
    try:
        return materialize_dataframe(upload_id)
    except KeyError:
        csv_path = DATASETS_DIR / f"{upload_id}.csv"
        if not csv_path.exists():
            raise HTTPException(status_code=404, detail="Dataset not found")
        df = pd.read_csv(csv_path)
        profile = profile_dataframe(df)
        register_transform_dataset(upload_id, str(csv_path), profile)
        return df


def _apply_filter(df: pd.DataFrame, column: str, operator: str, value: Any) -> pd.DataFrame:
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Unknown column: {column}")
    s = df[column]
    op = (operator or "").strip()

    # String normalization for equality/contains
    if op in {"=", "==", "eq"}:
        # compare case-insensitive string-wise to handle mixed dtypes safely
        left = s.astype(str).str.strip().str.lower()
        right = str(value).strip().lower()
        return df[left == right]
    if op in {"!=", "<>","ne"}:
        left = s.astype(str).str.strip().str.lower()
        right = str(value).strip().lower()
        return df[left != right]
    if op in {"contains", "ct"}:
        left = s.astype(str).str.lower()
        right = str(value).lower()
        return df[left.str.contains(right, na=False)]

    # Numeric comparisons when possible
    try:
        num = pd.to_numeric(s, errors="coerce")
        v = pd.to_numeric(value, errors="coerce")
    except Exception:
        raise HTTPException(status_code=400, detail="Operator requires numeric column/value")

    if pd.isna(v):
        raise HTTPException(status_code=400, detail="Filter value is not numeric")

    if op in {">", "gt"}:
        return df[num > v]
    if op in {">=", "ge"}:
        return df[num >= v]
    if op in {"<", "lt"}:
        return df[num < v]
    if op in {"<=", "le"}:
        return df[num <= v]

    raise HTTPException(status_code=400, detail=f"Unsupported operator: {operator}")


@app.get("/dataset/{upload_id}/plan")
def get_analysis_plan(upload_id: str) -> dict:
    """
    Return profile and analysis plan for an uploaded dataset (by upload_id).
    Loads from disk if not in memory.
    """
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    analysis_plan = build_analysis_plan(profile)
    return {
        "upload_id": upload_id,
        "profile": profile,
        "analysis_plan": analysis_plan,
    }


@app.post("/dataset/{upload_id}/analyze")
def run_analysis(
    upload_id: str,
    freq: str | None = None,
    agg: str = "sum",
    correlation_method: str = "pearson",
) -> dict:
    """
    Run full statistical analysis. Optional: freq (D|W|M), agg (sum|mean|median|count), correlation_method (pearson|spearman).
    """
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    plan = build_analysis_plan(profile, agg=agg, trend_freq=freq)
    results = run_all_analyses(
        df, profile, steps=plan.get("steps"), freq=freq, agg=agg, correlation_method=correlation_method
    )
    return {
        "upload_id": upload_id,
        "analysis_plan": plan,
        "results": results,
    }


class AskRequest(BaseModel):
    question: str


class ChatRequest(BaseModel):
    message: str


class TransformRequest(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}


class ColumnAnalysisRequest(BaseModel):
    column: str
    z_threshold: float = 3.0
    top_n: int = 10


class RowAnalysisRequest(BaseModel):
    row_index: int
    z_threshold: float = 3.0


class FilteredAnalysisFilter(BaseModel):
    column: str
    operator: str
    value: Any


class FilteredAnalysisRequest(BaseModel):
    filter: FilteredAnalysisFilter


def _suggested_questions(profile: dict) -> list[str]:
    """Generate suggested questions from profile."""
    num = profile.get("numeric_columns") or []
    cat = profile.get("categorical_columns") or []
    dt = profile.get("datetime_columns") or []
    qs = []
    if cat and num:
        qs.append(f"Which {cat[0]} has the highest {num[0]}?")
        qs.append(f"Which {cat[0]} drives the most {num[0]}?")
    if dt and num:
        qs.append("Are values increasing over time?")
    qs.append("What anomalies exist in the data?")
    if num:
        qs.append(f"What is the distribution of {num[0]}?")
    return qs[:8]


@app.get("/dataset/{upload_id}/suggested_questions")
def get_suggested_questions(upload_id: str) -> dict:
    """Return suggested natural-language questions for the dataset."""
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    return {"questions": _suggested_questions(profile)}


@app.get("/dataset/{upload_id}")
def get_dataset(upload_id: str) -> dict:
    """Return current dataset state (profile + transformation pipeline)."""
    df = _get_dataframe(upload_id)
    profile = get_transform_profile(upload_id) or profile_dataframe(df)
    if get_transform_profile(upload_id) is None:
        set_transform_profile(upload_id, profile)
    return {
        "upload_id": upload_id,
        "rows": len(df),
        "columns": list(df.columns),
        "profile": profile,
        "pipeline": get_transform_pipeline(upload_id),
    }


@app.post("/dataset/{upload_id}/column-analysis")
def column_analysis(upload_id: str, body: ColumnAnalysisRequest) -> dict:
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    col = body.column
    if col not in df.columns:
        raise HTTPException(status_code=400, detail=f"Unknown column: {col}")

    missing_values = profile.get("missing_values") or {}
    missing_count = int(missing_values.get(col, 0) or 0)
    unique_counts = profile.get("unique_counts") or {}
    unique_count = int(unique_counts.get(col, df[col].nunique(dropna=True)) or 0)
    col_type = (profile.get("column_types") or {}).get(col)

    if pd.api.types.is_numeric_dtype(df[col]):
        s = pd.to_numeric(df[col], errors="coerce")
        desc = s.describe()
        mean = float(desc.get("mean", 0.0))
        std = float(desc.get("std", 0.0) or 0.0)
        if std == 0:
            std = 1.0
        z = (s - mean) / std
        outlier_mask = z.abs() > body.z_threshold
        outlier_count = int(outlier_mask.sum())
        outlier_values = (
            df.loc[outlier_mask, col]
            .dropna()
            .astype(float)
            .sort_values(key=lambda x: x.abs(), ascending=False)
            .head(body.top_n)
            .tolist()
        )
        return {
            "column": col,
            "column_type": col_type,
            "missing_count": missing_count,
            "unique_count": unique_count,
            "numeric_stats": {
                "mean": mean,
                "median": float(s.median()),
                "std": float(std),
                "min": float(s.min()),
                "max": float(s.max()),
            },
            "outliers": {
                "z_threshold": body.z_threshold,
                "outlier_count": outlier_count,
                "top_outlier_values": outlier_values,
            },
        }

    if pd.api.types.is_datetime64_any_dtype(df[col]) or col_type == "datetime":
        d = pd.to_datetime(df[col], errors="coerce")
        if d.dropna().empty:
            return {
                "column": col,
                "column_type": "datetime",
                "missing_count": missing_count,
                "unique_count": unique_count,
                "datetime_stats": {"min": None, "max": None},
            }
        # Aggregate by month for a quick trend view.
        month = d.dt.to_period("M").astype(str)
        month_counts = month.value_counts().sort_values(ascending=False).head(body.top_n)
        return {
            "column": col,
            "column_type": "datetime",
            "missing_count": missing_count,
            "unique_count": unique_count,
            "datetime_stats": {"min": str(d.min()), "max": str(d.max())},
            "month_distribution": month_counts.to_dict(),
        }

    # categorical / fallback
    v = df[col].astype(str).fillna("NaN")
    value_counts = v.value_counts(dropna=False).head(body.top_n)
    total = len(v)
    return {
        "column": col,
        "column_type": col_type or "categorical",
        "missing_count": missing_count,
        "unique_count": unique_count,
        "value_counts": value_counts.to_dict(),
        "value_distribution_pct": (value_counts / total * 100).round(2).to_dict(),
    }


@app.post("/dataset/{upload_id}/row-analysis")
def row_analysis(upload_id: str, body: RowAnalysisRequest) -> dict:
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    if body.row_index < 0 or body.row_index >= len(df):
        raise HTTPException(status_code=400, detail="row_index out of bounds")

    row = df.iloc[body.row_index]
    row_dict = row.to_dict()

    # Missing columns in that row
    missing_cols = [c for c in df.columns if pd.isna(row_dict.get(c))]
    missing_count = len(missing_cols)

    numeric_cols = profile.get("numeric_columns") or []
    anomalies: list[dict[str, Any]] = []
    for col in numeric_cols:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue
        mean = float(series.mean())
        std = float(series.std() or 0.0)
        if std == 0:
            continue
        val = row_dict.get(col)
        if pd.isna(val):
            continue
        z = (float(val) - mean) / std
        if abs(z) > body.z_threshold:
            anomalies.append({"column": col, "value": val, "z_score": z})

    # delta from dataset numeric means for numeric columns
    deltas: dict[str, float] = {}
    for col in numeric_cols:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        mean = float(series.mean())
        val = row_dict.get(col)
        if pd.isna(val):
            continue
        deltas[col] = float(val) - mean

    return {
        "row_index": body.row_index,
        "row": row_dict,
        "missing_columns": missing_cols,
        "missing_count": missing_count,
        "numeric_anomalies": anomalies[:50],
        "numeric_deltas_from_mean": deltas,
    }


@app.post("/dataset/{upload_id}/filtered-analysis")
def filtered_analysis(upload_id: str, body: FilteredAnalysisRequest) -> dict:
    df = _get_dataframe(upload_id)
    f = body.filter
    subset = _apply_filter(df, f.column, f.operator, f.value)
    subset_profile = profile_dataframe(subset)

    plan = build_analysis_plan(subset_profile)
    results = run_all_analyses(subset, subset_profile, steps=plan.get("steps"))

    return {
        "filter": {"column": f.column, "operator": f.operator, "value": f.value},
        "filtered_rows": len(subset),
        "profile": subset_profile,
        "results": results,
        "analysis_plan": plan,
    }


@app.get("/dataset/{upload_id}/profile")
def get_dataset_profile(upload_id: str) -> dict:
    """Return current dataset profile."""
    df = _get_dataframe(upload_id)
    profile = get_transform_profile(upload_id) or profile_dataframe(df)
    if get_transform_profile(upload_id) is None:
        set_transform_profile(upload_id, profile)
    return {"upload_id": upload_id, "profile": profile}


@app.get("/dataset/{upload_id}/pipeline")
def get_dataset_pipeline(upload_id: str) -> dict:
    """Return transformation pipeline steps (transformation workflow)."""
    # ensure dataset exists and materialize once so unknown IDs fail fast
    _ = _get_dataframe(upload_id)
    return {"upload_id": upload_id, "pipeline": get_transform_pipeline(upload_id)}


@app.get("/dataset/{upload_id}/pipeline/export")
def export_dataset_pipeline(upload_id: str, format: str = "python") -> dict:
    """Export transformation pipeline as runnable code."""
    if format != "python":
        raise HTTPException(status_code=400, detail="Only python export supported")
    from backend.dataset.pipeline_exporter import export_pipeline_python

    code = export_pipeline_python(upload_id)
    return {"upload_id": upload_id, "export": {"language": "python", "code": code}}


@app.post("/dataset/{upload_id}/transform")
def transform_dataset(upload_id: str, body: TransformRequest) -> dict:
    """
    Apply a safe registered dataset transformation and append it to the pipeline.
    Example body:
      { "action": "drop_null_rows", "parameters": { "column": "sales" } }
    """
    result = execute_transform(upload_id, body.action, body.parameters or {})
    return {
        "answer": f"Applied transformation: {body.action}",
        "data": result,
    }


@app.post("/dataset/{upload_id}/undo")
def undo_dataset(upload_id: str) -> dict:
    result = execute_control(upload_id, "undo")
    return {"answer": "Undid last transformation.", "data": result}


@app.post("/dataset/{upload_id}/redo")
def redo_dataset(upload_id: str) -> dict:
    result = execute_control(upload_id, "redo")
    return {"answer": "Redid last transformation.", "data": result}


@app.post("/dataset/{upload_id}/reset")
def reset_dataset(upload_id: str) -> dict:
    result = execute_control(upload_id, "reset")
    return {"answer": "Reset transformation pipeline.", "data": result}


@app.get("/dataset/{upload_id}/charts")
def get_charts(upload_id: str) -> dict:
    """Return automatic chart specs (distribution, heatmap, trend, top categories) as Plotly figure dicts."""
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    return {"charts": generate_charts(df, profile)}


@app.post("/dataset/{upload_id}/chat")
def chat_dataset(upload_id: str, body: ChatRequest) -> dict:
    """AI data assistant: answer question or fulfill request (e.g. suggest chart). Same as /ask for now."""
    intent = parse_transform_intent(body.message)
    if intent:
        action = intent.get("action")
        params = intent.get("parameters") or {}
        if action in {"undo", "redo", "reset"}:
            result = execute_control(upload_id, action)
        else:
            result = execute_transform(upload_id, action, params)
        if result.get("mode") == "transform":
            return {"answer": f"Applied transformation: {action}", "data": result}
        return {"answer": f"Applied control action: {action}", "data": result}

    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    return answer_question(df, body.message, profile)


@app.post("/dataset/{upload_id}/ask")
def ask_dataset(upload_id: str, body: AskRequest) -> dict:
    """Natural language question about the dataset. Returns answer and optional data."""
    intent = parse_transform_intent(body.question)
    if intent:
        action = intent.get("action")
        params = intent.get("parameters") or {}
        if action in {"undo", "redo", "reset"}:
            result = execute_control(upload_id, action)
        else:
            result = execute_transform(upload_id, action, params)
        if result.get("mode") == "transform":
            return {"answer": f"Applied transformation: {action}", "data": result}
        return {"answer": f"Applied control action: {action}", "data": result}

    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    return answer_question(df, body.question, profile)


@app.post("/dataset/{upload_id}/anomalies")
def get_anomalies(
    upload_id: str,
    z: float = 3.0,
    iqr: float = 1.5,
    top_n: int | None = 50,
) -> dict:
    """Run anomaly detection. Optional: z (z-score threshold), iqr (IQR multiplier), top_n (cap by severity)."""
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    numeric = profile.get("numeric_columns") or []
    return run_anomaly_detection(df, numeric, z_threshold=z, iqr_multiplier=iqr, top_n=top_n)


@app.post("/dataset/{upload_id}/insights")
def get_insights(upload_id: str) -> dict:
    """Generate AI insights from profile + statistical results. Uses Ollama (free) by default."""
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    plan = build_analysis_plan(profile)
    results = run_all_analyses(df, profile, steps=plan.get("steps"))
    summary = f"Rows: {profile['rows']}, Columns: {profile['columns']}. " \
              f"Numeric: {profile.get('numeric_columns', [])}, Categorical: {profile.get('categorical_columns', [])}."
    return generate_insights(summary, results)


@app.post("/dataset/{upload_id}/pipeline")
def run_pipeline(upload_id: str) -> dict:
    """
    Run full pipeline: profile -> plan -> statistics -> insights -> anomalies.
    Phase 10: single request returns combined result for the dataset.
    """
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    plan = build_analysis_plan(profile)
    results = run_all_analyses(df, profile, steps=plan.get("steps"))
    summary = f"Rows: {profile['rows']}, Columns: {profile['columns']}. " \
              f"Numeric: {profile.get('numeric_columns', [])}, Categorical: {profile.get('categorical_columns', [])}."
    insights = generate_insights(summary, results)
    anomalies = run_anomaly_detection(df, profile.get("numeric_columns") or [])
    return {
        "upload_id": upload_id,
        "profile": profile,
        "analysis_plan": plan,
        "results": results,
        "insights": insights,
        "anomalies": anomalies,
    }


@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    """
    Accept a CSV file, load with pandas, run profiling, return summary and profile.
    Saves CSV to datasets/{upload_id}.csv for later use.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}") from e

    upload_id = str(uuid.uuid4())
    csv_path = DATASETS_DIR / f"{upload_id}.csv"
    df.to_csv(csv_path, index=False)

    profile = profile_dataframe(df)
    analysis_plan = build_analysis_plan(profile)
    register_transform_dataset(upload_id, str(csv_path), profile)

    return {
        "upload_id": upload_id,
        "rows": profile["rows"],
        "columns": profile["columns"],
        "profile": profile,
        "analysis_plan": analysis_plan,
    }


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
