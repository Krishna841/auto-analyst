# 🤖 Autonomous AI Data Analyst

An AI-powered system that automatically analyzes datasets, generates insights, detects anomalies, and enables natural language interaction with data.

---

## 🚀 Overview

This system automates the core steps of data analysis:

- Dataset profiling
- Statistical analysis
- Insight generation
- Anomaly detection
- Natural language querying

## Demo Video
[screen-capture (9).webm](https://github.com/user-attachments/assets/e8da53f1-b594-48e4-ac11-626532b1d7a1)

---

## ✨ Features

### 🔍 Dataset Profiling

- Column type detection (numeric, categorical, datetime)
- Missing value analysis
- Cardinality and identifier detection

---

### 📊 Automated Analysis

- Summary statistics (mean, median, etc.)
- Correlation (Pearson / Spearman)
- Group comparisons (sum, mean, count)
- Trend analysis with time-based aggregation

---

### 🧠 AI Insights

- Converts statistical outputs into human-readable insights
- Highlights key patterns and anomalies

---

### 🚨 Anomaly Detection

- Z-score
- IQR
- Isolation Forest
- Configurable thresholds and top-N results

---

### 💬 Natural Language QA

Supports queries like:

- "Which region has highest sales?"
- "What is the average sales by category?"
- "How many orders per region?"

Includes:

- intent parsing
- fuzzy column matching
- safe pandas execution

---

### 📈 Auto Charts

- Distribution plots
- Correlation heatmaps
- Trend charts
- Bar charts for group comparisons

---

### 🤖 AI Chat

- Interactive assistant for dataset exploration
- Context-aware responses

---

### 🔁 Full Analysis Pipeline

- Profile → Analyze → Insights → Anomalies → QA
- Executable in a single API call

---

### 💡 Suggested Questions

- Automatically generates relevant queries for each dataset

---

## 🧱 Architecture

```
Frontend (Next.js + Plotly)
        ↓
Backend API (FastAPI)
        ↓
Analysis Engine (Pandas)
        ↓
AI Layer (Ollama / OpenAI)
```

---

## 📦 API Endpoints

### Dataset

- `POST /upload`
- `GET /dataset/{id}/plan`

### Analysis

- `POST /dataset/{id}/analyze`
- `POST /dataset/{id}/insights`
- `POST /dataset/{id}/anomalies`

### Interaction

- `POST /dataset/{id}/ask`
- `POST /dataset/{id}/chat`

### Utilities

- `GET /dataset/{id}/charts`
- `GET /dataset/{id}/suggested_questions`
- `POST /dataset/{id}/pipeline`

---

## 🖥️ Frontend

- Upload interface
- Insights panel
- Anomaly visualization
- Chat interface

---

## ⚙️ Tech Stack

### Backend

- FastAPI
- Pandas
- Scikit-learn
- Ollama / OpenAI

### Frontend

- Next.js
- Plotly
- Tailwind CSS

---

## 🚀 Quick Start

### Backend

```bash
pip install -r backend/requirements.txt
cd backend && python -m uvicorn main:app --reload
```

### Frontend

```bash
cd frontend && npm install && npm run dev
```
