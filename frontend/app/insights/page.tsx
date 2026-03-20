"use client";

import { useState, useEffect } from "react";
import { getInsights, runAnalyze } from "@/lib/api";
import Link from "next/link";
import { GroupBarChart } from "@/components/PlotChart";

export default function InsightsPage() {
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [insights, setInsights] = useState<{ insights?: string[] } | null>(null);
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setUploadId(localStorage.getItem("upload_id"));
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = () => setUploadId(localStorage.getItem("upload_id"));
    window.addEventListener("datasetChanged", handler);
    return () => window.removeEventListener("datasetChanged", handler);
  }, []);

  async function loadInsights() {
    if (!uploadId) return;
    setLoading(true);
    setError(null);
    setInsights(null);
    setAnalysis(null);
    try {
      const [insightsRes, analyzeRes] = await Promise.all([
        getInsights(uploadId),
        runAnalyze(uploadId),
      ]);
      setInsights(insightsRes);
      setAnalysis(analyzeRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  if (!uploadId) {
    return (
      <div>
        <h1>Insights</h1>
        <p>No dataset selected. <Link href="/upload">Upload a CSV</Link> first and return here.</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Insights</h1>
      <p style={{ color: "#a1a1aa", marginBottom: "1rem" }}>
        AI-generated insights via Ollama (free, local). Run <code>ollama run llama3.2</code> (or set <code>OLLAMA_MODEL</code>) on the backend.
      </p>
      <p style={{ color: "#71717a", fontSize: "0.85rem", marginBottom: "1rem" }}>
        Ensure the API is running: <code>python -m uvicorn backend.main:app --reload</code> from the project root.
      </p>
      <button onClick={loadInsights} disabled={loading} style={{ marginBottom: "1.5rem" }}>
        {loading ? "Loading…" : "Generate insights"}
      </button>
      {error && <p style={{ color: "#f87171" }}>{error}</p>}
      {insights?.insights && (
        <div style={{ background: "#1e1e2e", padding: "1.5rem", borderRadius: 8 }}>
          <h2 style={{ marginTop: 0 }}>Key insights</h2>
          <ul style={{ paddingLeft: "1.25rem" }}>
            {insights.insights.map((item, i) => (
              <li key={i} style={{ marginBottom: "0.5rem" }}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {analysis && (() => {
        const res = (analysis as { results?: { group_analysis?: { by_column?: { group_analysis?: Record<string, Record<string, number>>; value_columns?: string[] }[]; group_analysis?: Record<string, Record<string, number>>; value_columns?: string[] } } }).results;
        const gaBlock = res?.group_analysis;
        const first = gaBlock?.by_column?.[0] ?? gaBlock;
        const ga = first?.group_analysis;
        const valueCols = first?.value_columns;
        const valueKey = valueCols?.[0];
        if (!ga || !valueKey) return null;
        return (
          <div style={{ marginTop: "1rem", background: "#1e1e2e", padding: "1rem", borderRadius: 8 }}>
            <GroupBarChart groupAnalysis={ga} valueKey={valueKey} />
          </div>
        );
      })()}
      {analysis && (analysis as { results?: any }).results != null && (
        <details style={{ marginTop: "1rem" }}>
          <summary>Statistical results (raw)</summary>
          <pre style={{ background: "#0f0f1a", padding: "1rem", overflow: "auto", fontSize: "0.85rem" }}>
            {JSON.stringify((analysis as { results?: unknown }).results, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
