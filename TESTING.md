# How to test the Autonomous AI Data Analyst

## 1. Start the backend

From the **project root** (`auto-analyst/`):

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

Or from `backend/`:

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

On Windows, if `uvicorn` is not recognized, always use `python -m uvicorn` instead of `uvicorn`.

- API: **http://127.0.0.1:8000**
- Docs: **http://127.0.0.1:8000/docs**

(Optional) For LLM features (insights, natural-language Ask), start Ollama in another terminal:

```bash
ollama run llama3.2
```

---

## 2. Test via Swagger UI (easiest)

1. Open **http://127.0.0.1:8000/docs**
2. **Upload a CSV**
   - Click **POST /upload** → Try it out
   - Click **Choose File** and pick `datasets/sample_sales.csv` (or any CSV)
   - Execute
   - Copy the `upload_id` from the response
3. **Plan**  
   - **GET /dataset/{upload_id}/plan** → paste `upload_id` → Execute  
   - Check `profile` and `analysis_plan`
4. **Analyze**  
   - **POST /dataset/{upload_id}/analyze** → Execute  
   - Check `results` (correlations, group_analysis, trend_analysis)
5. **Insights** (needs Ollama running)  
   - **POST /dataset/{upload_id}/insights** → Execute  
   - Check `insights`
6. **Anomalies**  
   - **POST /dataset/{upload_id}/anomalies** → Execute  
   - Check `anomalies`
7. **Ask** (needs Ollama for best results)  
   - **POST /dataset/{upload_id}/ask**  
   - Request body: `{"question": "Which region has the highest sales?"}`  
   - Execute and check `answer`
8. **Full pipeline**  
   - **POST /dataset/{upload_id}/pipeline** → Execute  
   - Returns profile, plan, results, insights, and anomalies in one call

---

## 3. Test via frontend

1. Start backend (see above).
2. In another terminal, from project root:

```bash
cd frontend
npm install
npm run dev
```

3. Open **http://localhost:3000**
4. **Upload** → Choose `datasets/sample_sales.csv` → Upload  
   - You should see rows, columns, and analysis plan; `upload_id` is stored in the browser.
5. **Insights** → “Generate insights” (Ollama must be running for LLM insights).
6. **Anomalies** → “Run anomaly detection”.
7. **Ask** → e.g. “Which region has the highest sales?” → Ask.

---

## 4. Test via curl

Replace `YOUR_UPLOAD_ID` with the `upload_id` from step 2.

**Upload (PowerShell):**

```powershell
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/upload" -Method Post -Form @{ file = Get-Item "datasets\sample_sales.csv" }
$response.upload_id
```

**Upload (bash/curl):**

```bash
curl -X POST "http://127.0.0.1:8000/upload" -F "file=@datasets/sample_sales.csv"
```

**Then:**

```bash
# Plan
curl "http://127.0.0.1:8000/dataset/YOUR_UPLOAD_ID/plan"

# Analyze
curl -X POST "http://127.0.0.1:8000/dataset/YOUR_UPLOAD_ID/analyze"

# Ask
curl -X POST "http://127.0.0.1:8000/dataset/YOUR_UPLOAD_ID/ask" -H "Content-Type: application/json" -d "{\"question\": \"Which region has the highest sales?\"}"
```

---

## 5. Quick checklist

| Step | What to do | Expected |
|------|------------|----------|
| Backend | `uvicorn backend.main:app --reload` | Server at :8000, `/docs` loads |
| Upload | POST CSV in Swagger or frontend | 200, `upload_id`, `rows`, `columns`, `profile` |
| Plan | GET `.../plan` with `upload_id` | `profile`, `analysis_plan` with steps |
| Analyze | POST `.../analyze` | `results` with correlations/group/trend |
| Insights | POST `.../insights` | `insights` list (or placeholder if no Ollama) |
| Anomalies | POST `.../anomalies` | `anomalies`, `total_count` |
| Ask | POST `.../ask` with `{"question":"..."}` | `answer` and optional `data` |
| Pipeline | POST `.../pipeline` | All of the above in one response |

---

## Sample data

Use **`datasets/sample_sales.csv`** (date, region, product, sales, quantity) for testing. It has numeric and categorical columns and dates so profiling, analysis plan, and trend/group analyses all run.
