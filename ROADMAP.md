# Autonomous AI Data Analyst — Project Roadmap

## Goal

Build an AI system that automatically analyzes datasets and behaves like a junior data analyst.

## Core Capabilities

1. Autonomous analysis
2. Insight generation
3. Anomaly detection
4. Natural language question answering

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js, Plotly |
| Backend | FastAPI |
| Data processing | Pandas, NumPy, Scikit-learn |
| AI | OpenAI / Llama |
| Optional | LangChain, ChromaDB |

## Project Architecture

```
Frontend (Next.js)
        ↓
Backend API (FastAPI)
        ↓
Analysis Engine (Pandas + Python)
        ↓
AI Reasoning Layer (LLM)

Later: Vector DB (Chroma), AI Agent Pipeline
```

## Phases

### Phase 1 — Project setup ✅

- Repository structure with `backend/`, `frontend/`, `datasets/`
- Backend: `main.py`, `analysis/` (profiler, analysis_engine, statistics, anomaly_detector), `ai/` (insight_generator, query_agent)
- Dependencies: `pip install fastapi uvicorn pandas numpy scikit-learn openai plotly`
- Optional later: `langchain`, `chromadb`

### Phase 2 — Dataset upload ✅

- **POST /upload** — accept CSV, load with pandas, return dataset summary + profile + analysis plan.
- Response: `{ "rows", "columns", "profile", "analysis_plan" }`

### Phase 3 — Dataset profiling engine ✅

- **analysis/profiler.py** — detect column types, missing values, numeric vs categorical, dataset summary.
- Output: `{ "rows", "numeric_columns", "categorical_columns", "datetime_columns", "missing_values", ... }`

### Phase 4 — Autonomous analysis engine ✅

- **analysis/analysis_engine.py** — decide what analyses to run automatically (steps + descriptions).
- Rules: numeric → correlation; categorical → group comparison; datetime → trend analysis.

### Phase 5 — Statistical analysis layer ✅

- **analysis/statistics.py** — correlation, group comparison, trend analysis. JSON: `correlations`, `group_analysis`, `trend_analysis`.
- **POST /dataset/{id}/analyze** runs all applicable analyses.

### Phase 6 — Insight generation (AI) ✅

- **ai/insight_generator.py** — OpenAI turns summary + stats into bullet insights. Placeholder when no API key.

### Phase 7 — Anomaly detection ✅

- **analysis/anomaly_detector.py** — Z-score, IQR, Isolation Forest. **POST /dataset/{id}/anomalies**.

### Phase 8 — Natural language QA ✅

- **ai/query_agent.py** — intent from LLM or heuristic → safe pandas → answer. **POST /dataset/{id}/ask**.

### Phase 9 — Frontend dashboard ✅

- Next.js: Upload, Insights (with Plotly bar chart), Anomalies, Ask. Uses `localStorage` for current upload_id.

### Phase 10 — AI agent pipeline ✅

- **POST /dataset/{id}/pipeline** — profile → plan → statistics → insights → anomalies in one request.

### Phase 11 — Deployment

- Frontend: Vercel. Backend: Render / AWS. Optional DB: Supabase / PostgreSQL.

### Phase 12 — GitHub presentation

- README: problem, solution, architecture diagram, feature list, screenshots, demo video.

---

## Estimated build time (MVP)

| Phase | Time |
|-------|------|
| Setup | 1 day |
| Upload + profiling | 2 days |
| Analysis engine | 2 days |
| Insights | 1 day |
| Anomaly detection | 1 day |
| Question answering | 2 days |
| Frontend | 2 days |
| **Total** | **~10 days** |

## Resume bullet

> Built an autonomous AI data analyst that performs automated dataset profiling, anomaly detection, insight generation, and natural language querying using LLM-driven reasoning pipelines.
