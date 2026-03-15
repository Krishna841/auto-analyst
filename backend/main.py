"""
AI Autonomous Data Analyst — FastAPI backend.
"""

import io
import sys
import uuid
from pathlib import Path

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
except ImportError:
    from analysis.profiler import profile_dataframe
    from analysis.analysis_engine import build_analysis_plan
    from analysis.statistics import run_all_analyses
    from analysis.anomaly_detector import run_anomaly_detection
    from analysis.charts import generate_charts
    from ai.insight_generator import generate_insights
    from ai.query_agent import answer_question

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


def _get_dataframe(upload_id: str) -> pd.DataFrame:
    """Load dataset by upload_id from memory or disk."""
    df = _datasets.get(upload_id)
    if df is None:
        csv_path = DATASETS_DIR / f"{upload_id}.csv"
        if not csv_path.exists():
            raise HTTPException(status_code=404, detail="Dataset not found")
        df = pd.read_csv(csv_path)
        _datasets[upload_id] = df
    return df


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


@app.get("/dataset/{upload_id}/charts")
def get_charts(upload_id: str) -> dict:
    """Return automatic chart specs (distribution, heatmap, trend, top categories) as Plotly figure dicts."""
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    return {"charts": generate_charts(df, profile)}


@app.post("/dataset/{upload_id}/chat")
def chat_dataset(upload_id: str, body: ChatRequest) -> dict:
    """AI data assistant: answer question or fulfill request (e.g. suggest chart). Same as /ask for now."""
    df = _get_dataframe(upload_id)
    profile = profile_dataframe(df)
    return answer_question(df, body.message, profile)


@app.post("/dataset/{upload_id}/ask")
def ask_dataset(upload_id: str, body: AskRequest) -> dict:
    """Natural language question about the dataset. Returns answer and optional data."""
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

    _datasets[upload_id] = df
    profile = profile_dataframe(df)
    analysis_plan = build_analysis_plan(profile)

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
