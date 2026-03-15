# Autonomous AI Data Analyst

An AI system that automatically analyzes datasets and behaves like a junior data analyst.

## Problem

Manual data analysis is time-consuming. Exploring data, spotting anomalies, and writing up insights require repeated, manual steps.

## Solution

An autonomous AI data analyst that:

- **Profiles** uploaded datasets (column types, missing values, numeric vs categorical).
- **Plans and runs** analyses based on the data (correlation, group comparison, trends).
- **Generates insights** from statistical results using an LLM.
- **Detects anomalies** (Z-score, IQR, Isolation Forest) and flags them.
- **Answers questions** in natural language by turning questions into safe pandas and returning answers.

## Architecture

```
Frontend (Next.js + Plotly)
        ↓
Backend API (FastAPI)
        ↓
Analysis Engine (Pandas + Python)
        ↓
AI Reasoning Layer (LLM — OpenAI)
```

**Repository structure:**

```
auto-analyst/
├── backend/
│   ├── main.py                 # FastAPI + /chat, /suggested_questions, /charts
│   ├── analysis/
│   │   ├── profiler.py         # Profiling (cardinality, identifiers, normalized names)
│   │   ├── analysis_engine.py  # Multi-group plan, trend freq
│   │   ├── statistics.py      # Correlation (drop constant, Pearson/Spearman), trend reindex
│   │   ├── anomaly_detector.py # Z/IQR/IF, configurable, explanations
│   │   └── charts.py           # Auto chart specs (distribution, heatmap, trend, bar)
│   ├── ai/                      # Insights (grounded), QA (fuzzy match, more intents)
│   └── tests/                   # pytest regression tests
├── frontend/                    # Next.js: Upload, Insights, Anomalies, Ask
├── datasets/
├── README.md
├── ROADMAP.md
└── FUNCTIONALITY.md             # Feature list + accuracy notes
```

## Feature list

| Feature | Status |
|--------|--------|
| CSV upload & summary | ✅ |
| Dataset profiling (types, missing, cardinality, identifiers, normalized names) | ✅ |
| Autonomous analysis planner (multi-group, trend freq) | ✅ |
| Statistical layer (correlation Pearson/Spearman, group sum/mean/median, trend with reindex) | ✅ |
| LLM insight generation (grounded with key numbers) | ✅ |
| Anomaly detection (configurable z/iqr, top-N by severity, explanations) | ✅ |
| Natural language QA (fuzzy column match, lowest/count/average) | ✅ |
| **Suggested questions** | ✅ `GET /dataset/{id}/suggested_questions` |
| **Automatic charts** (distribution, heatmap, trend, bar) | ✅ `GET /dataset/{id}/charts` |
| **AI chat** | ✅ `POST /dataset/{id}/chat` |
| Frontend dashboard (Upload, Insights, Anomalies, Ask) | ✅ |
| Full pipeline | ✅ |
| Tests | ✅ `pytest backend/tests/` |

## Example queries (Ask / Chat)

- "Which region has the highest sales?"
- "Which category has the lowest revenue?"
- "What is the average sales by region?"
- "How many orders per region?"

## Quick start

### Backend

1. From project root:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. **Ollama (free LLM):** Install [Ollama](https://ollama.com), then in a terminal run: `ollama run llama3.2` (or another model). The backend uses it by default; optional: set `OLLAMA_MODEL` in `.env` to match.
3. Run API:
   ```bash
   cd backend && python -m uvicorn main:app --reload
   ```
   Or from project root: `python -m uvicorn backend.main:app --reload`  
   (On Windows use `python -m uvicorn` if `uvicorn` is not recognized.)

### Frontend

1. From project root:
   ```bash
   cd frontend && npm install && npm run dev
   ```
2. Open http://localhost:3000. Upload a CSV, then use Insights, Anomalies, and Ask.

### Try the API

- **POST /upload** — upload CSV; returns profile and analysis plan.
- **GET /dataset/{id}/plan** — profile + analysis plan.
- **POST /dataset/{id}/analyze** — run statistics. Optional query: `?freq=M&agg=mean&correlation_method=spearman`.
- **POST /dataset/{id}/insights** — AI insights (grounded with key stats).
- **POST /dataset/{id}/anomalies** — anomaly detection. Optional: `?z=2.5&iqr=1.8&top_n=30`.
- **POST /dataset/{id}/ask** — body: `{"question": "Which region has highest sales?"}`.
- **POST /dataset/{id}/chat** — body: `{"message": "..."}` (AI data assistant).
- **GET /dataset/{id}/suggested_questions** — suggested questions for the dataset.
- **GET /dataset/{id}/charts** — Plotly chart specs (distribution, heatmap, trend, bar).
- **POST /dataset/{id}/pipeline** — full pipeline in one call.

Docs: http://127.0.0.1:8000/docs

## Deployment (Phase 11)

- **Frontend:** Vercel — connect repo, build command `cd frontend && npm run build`, output `frontend`. Set `NEXT_PUBLIC_API_URL` to your backend URL.
- **Backend:** Render / Railway / AWS — run `uvicorn backend.main:app --host 0.0.0.0`. Use Ollama (self-hosted) or set `OPENAI_API_KEY` for cloud LLM. Allow CORS for your frontend origin.
- **Optional DB:** Supabase/PostgreSQL for storing upload metadata or user sessions (not required for MVP).

## Screenshots / demo

- Add a screenshot of the **Upload** page after a successful upload.
- Add a screenshot of **Insights** with AI bullets and the group bar chart.
- Optionally link a short **demo video** (e.g. Loom/YouTube) showing upload → insights → ask.

## Roadmap

See **[ROADMAP.md](ROADMAP.md)** for the full phase-by-phase plan (Phases 1–12).

## Resume bullet

> Built an autonomous AI data analyst that performs automated dataset profiling, anomaly detection, insight generation, and natural language querying using LLM-driven reasoning pipelines.
