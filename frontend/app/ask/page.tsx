"use client";

import { useState, useEffect } from "react";
import {
  ask,
  getPlan,
  getPipeline,
  redoTransform,
  resetTransform,
  transformDataset,
  undoTransform,
  getCharts,
  getInsights,
  exportPipeline,
  columnAnalysis,
  rowAnalysis,
  filteredAnalysis,
} from "@/lib/api";
import Link from "next/link";
import PlotFigure from "@/components/PlotFigure";

export default function AskPage() {
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [mode, setMode] = useState<"qa" | "eda">("qa");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<{ answer?: string; data?: unknown } | null>(null);

  const [profile, setProfile] = useState<any | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);

  const [pipeline, setPipeline] = useState<any[]>([]);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  const [charts, setCharts] = useState<any | null>(null);
  const [chartsLoading, setChartsLoading] = useState(false);
  const [chartsError, setChartsError] = useState<string | null>(null);

  const [columnChoice, setColumnChoice] = useState<string>("");
  const [columnAnalysisResult, setColumnAnalysisResult] = useState<any | null>(null);
  const [columnAnalysisLoading, setColumnAnalysisLoading] = useState(false);

  const [rowIndex, setRowIndex] = useState<number>(0);
  const [rowAnalysisResult, setRowAnalysisResult] = useState<any | null>(null);
  const [rowAnalysisLoading, setRowAnalysisLoading] = useState(false);

  const [filterColumn, setFilterColumn] = useState<string>("");
  const [filterOperator, setFilterOperator] = useState<string>("=");
  const [filterValue, setFilterValue] = useState<string>("");
  const [filteredAnalysisResult, setFilteredAnalysisResult] = useState<any | null>(null);
  const [filteredAnalysisLoading, setFilteredAnalysisLoading] = useState(false);

  const [edaBusy, setEdaBusy] = useState(false);
  const [ignoredSuggestionKeys, setIgnoredSuggestionKeys] = useState<string[]>([]);
  const [constantValue, setConstantValue] = useState<string>("0");

  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState<string | null>(null);
  const [insights, setInsights] = useState<{ insights?: string[] } | null>(null);

  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportCode, setExportCode] = useState<string | null>(null);

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

  useEffect(() => {
    setIgnoredSuggestionKeys([]);
  }, [uploadId]);

  useEffect(() => {
    async function loadProfile() {
      if (!uploadId || mode !== "eda") return;
      setProfileLoading(true);
      setProfileError(null);
      try {
        const res = await getPlan(uploadId);
        setProfile(res?.profile ?? null);
      } catch (e) {
        setProfileError(e instanceof Error ? e.message : "Failed to load profile");
      } finally {
        setProfileLoading(false);
      }
    }

    loadProfile();
  }, [uploadId, mode]);

  useEffect(() => {
    if (!profile?.columns || !Array.isArray(profile.columns) || profile.columns.length === 0) return;
    if (!columnChoice) setColumnChoice(profile.columns[0]);
    if (!filterColumn) setFilterColumn(profile.columns[0]);
  }, [profile]);

  useEffect(() => {
    async function loadPipe() {
      if (!uploadId || mode !== "eda") return;
      setPipelineLoading(true);
      setPipelineError(null);
      try {
        const res = await getPipeline(uploadId);
        setPipeline(res?.pipeline ?? []);
      } catch (e) {
        setPipelineError(e instanceof Error ? e.message : "Failed to load pipeline");
      } finally {
        setPipelineLoading(false);
      }
    }

    loadPipe();
  }, [uploadId, mode]);

  useEffect(() => {
    async function loadCharts() {
      if (!uploadId || mode !== "eda") return;
      setChartsLoading(true);
      setChartsError(null);
      try {
        const res = await getCharts(uploadId);
        setCharts(res?.charts ?? null);
      } catch (e) {
        setChartsError(e instanceof Error ? e.message : "Failed to load charts");
      } finally {
        setChartsLoading(false);
      }
    }

    loadCharts();
  }, [uploadId, mode]);

  const edaSuggestions = (() => {
    const numericCols: string[] = profile?.numeric_columns ?? [];
    const categoricalCols: string[] = profile?.categorical_columns ?? [];

    const topNum = numericCols[0];
    const topCat = categoricalCols[0];

    const out: string[] = [];
    if (topNum) {
      out.push(`Top 10 rows with highest ${topNum}`);
      out.push(`Top 10 rows with lowest ${topNum}`);
    }
    if (topCat && topNum) {
      out.push(`Which ${topCat} has the highest ${topNum}?`);
      out.push(`Which ${topCat} has the lowest ${topNum}?`);
    }
    return out.slice(0, 8);
  })();

  const missingHighlights = (() => {
    const missingValues: Record<string, number> = profile?.missing_values ?? {};
    const entries = Object.entries(missingValues)
      .filter(([, v]) => (typeof v === "number" ? v : Number(v)) > 0)
      .sort((a, b) => Number(b[1]) - Number(a[1]));
    return entries.slice(0, 6).map(([col, count]) => ({ col, count: Number(count) }));
  })();

  const topMissingColumn = missingHighlights[0]?.col ?? null;
  const topNumericColumn = (profile?.numeric_columns ?? [])[0] ?? null;

  const dropNullKey = topMissingColumn ? `drop_null_rows:${topMissingColumn}` : null;
  const fillNullKey = topNumericColumn ? `fill_null_mean:${topNumericColumn}` : null;
  const normalizeKey = topNumericColumn ? `normalize_column:${topNumericColumn}` : null;

  const isDropNullIgnored = dropNullKey ? ignoredSuggestionKeys.includes(dropNullKey) : false;
  const isFillIgnored = fillNullKey ? ignoredSuggestionKeys.includes(fillNullKey) : false;
  const isNormalizeIgnored = normalizeKey ? ignoredSuggestionKeys.includes(normalizeKey) : false;

  async function refreshEDA() {
    if (!uploadId) return;
    const [planRes, pipeRes, chartsRes] = await Promise.all([
      getPlan(uploadId),
      getPipeline(uploadId),
      getCharts(uploadId),
    ]);
    setProfile(planRes?.profile ?? null);
    setPipeline(pipeRes?.pipeline ?? []);
    setCharts(chartsRes?.charts ?? null);
  }

  async function applyTransform(action: string, parameters: Record<string, unknown> = {}) {
    if (!uploadId) return;
    setEdaBusy(true);
    setError(null);
    try {
      await transformDataset(uploadId, action, parameters);
      await refreshEDA();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to apply transformation");
    } finally {
      setEdaBusy(false);
    }
  }

  async function applyControl(action: "undo" | "redo" | "reset") {
    if (!uploadId) return;
    setEdaBusy(true);
    setError(null);
    try {
      if (action === "undo") await undoTransform(uploadId);
      if (action === "redo") await redoTransform(uploadId);
      if (action === "reset") await resetTransform(uploadId);
      await refreshEDA();
    } catch (e) {
      setError(e instanceof Error ? e.message : `Failed to ${action}`);
    } finally {
      setEdaBusy(false);
    }
  }

  async function generateKeyInsights() {
    if (!uploadId) return;
    setInsightsLoading(true);
    setInsightsError(null);
    setInsights(null);
    try {
      const res = await getInsights(uploadId);
      setInsights(res);
    } catch (e) {
      setInsightsError(e instanceof Error ? e.message : "Failed to generate insights");
    } finally {
      setInsightsLoading(false);
    }
  }

  async function handleExportPipeline() {
    if (!uploadId) return;
    setExportLoading(true);
    setExportError(null);
    setExportCode(null);
    try {
      const res = await exportPipeline(uploadId);
      const code = res?.export?.code ?? null;
      setExportCode(code);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Failed to export pipeline");
    } finally {
      setExportLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!uploadId || !question.trim()) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const res = await ask(uploadId, question.trim());
      setAnswer(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  if (!uploadId) {
    return (
      <div>
        <h1>Ask a question</h1>
        <p>No dataset selected. <Link href="/upload">Upload a CSV</Link> first and return here.</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Ask a question</h1>
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem", alignItems: "center" }}>
        <button
          type="button"
          onClick={() => setMode("qa")}
          style={{
            padding: "0.5rem 0.75rem",
            borderRadius: 8,
            border: mode === "qa" ? "1px solid #818cf8" : "1px solid #2d2d3d",
            background: mode === "qa" ? "#2a245e" : "#141423",
            color: mode === "qa" ? "#e4e4e7" : "#a1a1aa",
            cursor: "pointer",
          }}
        >
          QA
        </button>
        <button
          type="button"
          onClick={() => setMode("eda")}
          style={{
            padding: "0.5rem 0.75rem",
            borderRadius: 8,
            border: mode === "eda" ? "1px solid #818cf8" : "1px solid #2d2d3d",
            background: mode === "eda" ? "#2a245e" : "#141423",
            color: mode === "eda" ? "#e4e4e7" : "#a1a1aa",
            cursor: "pointer",
          }}
        >
          EDA Assistant
        </button>
      </div>

      {mode === "eda" && (
        <div style={{ background: "#1e1e2e", padding: "1.25rem", borderRadius: 8, marginBottom: "1.25rem" }}>
          <p style={{ margin: 0, fontWeight: 700, marginBottom: "0.5rem" }}>EDA Assistant</p>
          <p style={{ margin: 0, color: "#a1a1aa", marginBottom: "0.75rem" }}>
            Uses your dataset profile to suggest exploration prompts (top-N and group comparisons).
          </p>

          {profileLoading && <p style={{ color: "#a1a1aa" }}>Loading dataset profile…</p>}
          {profileError && <p style={{ color: "#f87171" }}>{profileError}</p>}

          {profile && (
            <div>
              <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
                <div style={{ background: "#141423", padding: "0.75rem 0.9rem", borderRadius: 8 }}>
                  <div style={{ color: "#a1a1aa", fontSize: "0.85rem" }}>Rows</div>
                  <div style={{ fontWeight: 700 }}>{profile?.rows ?? "—"}</div>
                </div>
                <div style={{ background: "#141423", padding: "0.75rem 0.9rem", borderRadius: 8 }}>
                  <div style={{ color: "#a1a1aa", fontSize: "0.85rem" }}>Columns</div>
                  <div style={{ fontWeight: 700 }}>{(profile?.columns ?? []).length}</div>
                </div>
              </div>

              {missingHighlights.length > 0 && (
                <div style={{ marginBottom: "0.75rem" }}>
                  <div style={{ fontWeight: 700, marginBottom: "0.35rem" }}>Missing values</div>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                    {missingHighlights.map((m) => (
                      <li key={m.col} style={{ padding: "0.25rem 0", color: "#a1a1aa" }}>
                        <span style={{ color: "#e4e4e7", fontWeight: 600 }}>{m.col}</span>: {m.count} missing
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ fontWeight: 700, marginBottom: "0.35rem" }}>Actions</div>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
                  <button
                    type="button"
                    disabled={!topMissingColumn || edaBusy || isDropNullIgnored}
                    onClick={() => applyTransform("drop_null_rows", { column: topMissingColumn })}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: !topMissingColumn || edaBusy || isDropNullIgnored ? "not-allowed" : "pointer",
                      opacity: !topMissingColumn || edaBusy || isDropNullIgnored ? 0.6 : 1,
                    }}
                  >
                    Remove null rows ({topMissingColumn ?? "—"})
                  </button>

                  <button
                    type="button"
                    disabled={!topMissingColumn || edaBusy}
                    onClick={() =>
                      setIgnoredSuggestionKeys((prev) =>
                        dropNullKey ? [...prev, dropNullKey] : prev
                      )
                    }
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#a1a1aa",
                      cursor: !topMissingColumn || edaBusy ? "not-allowed" : "pointer",
                      opacity: !topMissingColumn || edaBusy ? 0.6 : 1,
                    }}
                  >
                    Ignore
                  </button>

                  <button
                    type="button"
                    disabled={!topNumericColumn || edaBusy || isFillIgnored}
                    onClick={() => applyTransform("fill_null_mean", { column: topNumericColumn })}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: !topNumericColumn || edaBusy || isFillIgnored ? "not-allowed" : "pointer",
                      opacity: !topNumericColumn || edaBusy || isFillIgnored ? 0.6 : 1,
                    }}
                  >
                    Fill nulls (mean) ({topNumericColumn ?? "—"})
                  </button>

                  <button
                    type="button"
                    disabled={!topNumericColumn || edaBusy}
                    onClick={() => applyTransform("fill_null_median", { column: topNumericColumn })}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: !topNumericColumn || edaBusy ? "not-allowed" : "pointer",
                      opacity: !topNumericColumn || edaBusy ? 0.6 : 1,
                    }}
                  >
                    Fill nulls (median) ({topNumericColumn ?? "—"})
                  </button>

                  <button
                    type="button"
                    disabled={!topNumericColumn || edaBusy}
                    onClick={() => applyTransform("fill_null_mode", { column: topNumericColumn })}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: !topNumericColumn || edaBusy ? "not-allowed" : "pointer",
                      opacity: !topNumericColumn || edaBusy ? 0.6 : 1,
                    }}
                  >
                    Fill nulls (mode) ({topNumericColumn ?? "—"})
                  </button>

                  <button
                    type="button"
                    disabled={!topNumericColumn || edaBusy}
                    onClick={() =>
                      setIgnoredSuggestionKeys((prev) =>
                        fillNullKey ? [...prev, fillNullKey] : prev
                      )
                    }
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#a1a1aa",
                      cursor: !topNumericColumn || edaBusy ? "not-allowed" : "pointer",
                      opacity: !topNumericColumn || edaBusy ? 0.6 : 1,
                    }}
                  >
                    Ignore
                  </button>

                  <button
                    type="button"
                    disabled={!topNumericColumn || edaBusy || isNormalizeIgnored}
                    onClick={() => applyTransform("normalize_column", { column: topNumericColumn })}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: !topNumericColumn || edaBusy || isNormalizeIgnored ? "not-allowed" : "pointer",
                      opacity: !topNumericColumn || edaBusy || isNormalizeIgnored ? 0.6 : 1,
                    }}
                  >
                    Normalize ({topNumericColumn ?? "—"})
                  </button>

                  <button
                    type="button"
                    disabled={!topNumericColumn || edaBusy}
                    onClick={() =>
                      setIgnoredSuggestionKeys((prev) =>
                        normalizeKey ? [...prev, normalizeKey] : prev
                      )
                    }
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#a1a1aa",
                      cursor: !topNumericColumn || edaBusy ? "not-allowed" : "pointer",
                      opacity: !topNumericColumn || edaBusy ? 0.6 : 1,
                    }}
                  >
                    Ignore
                  </button>
                </div>

                <div style={{ marginTop: "0.6rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <input
                    type="text"
                    value={constantValue}
                    onChange={(e) => setConstantValue(e.target.value)}
                    style={{
                      width: 180,
                      padding: "0.4rem 0.6rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                    }}
                    placeholder="constant value"
                  />
                  <button
                    type="button"
                    disabled={!topMissingColumn || edaBusy}
                    onClick={() => {
                      const parsed = Number(constantValue);
                      const val = Number.isNaN(parsed) ? constantValue : parsed;
                      applyTransform("fill_null_constant", { column: topMissingColumn, value: val });
                    }}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: !topMissingColumn || edaBusy ? "not-allowed" : "pointer",
                      opacity: !topMissingColumn || edaBusy ? 0.6 : 1,
                    }}
                  >
                    Fill nulls (constant) ({topMissingColumn ?? "—"})
                  </button>

                  <button
                    type="button"
                    disabled={!topMissingColumn || edaBusy}
                    onClick={() => applyTransform("forward_fill_nulls", { column: topMissingColumn })}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: !topMissingColumn || edaBusy ? "not-allowed" : "pointer",
                      opacity: !topMissingColumn || edaBusy ? 0.6 : 1,
                    }}
                  >
                    Forward fill ({topMissingColumn ?? "—"})
                  </button>

                  <button
                    type="button"
                    disabled={!topMissingColumn || edaBusy}
                    onClick={() => applyTransform("backward_fill_nulls", { column: topMissingColumn })}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: !topMissingColumn || edaBusy ? "not-allowed" : "pointer",
                      opacity: !topMissingColumn || edaBusy ? 0.6 : 1,
                    }}
                  >
                    Backward fill ({topMissingColumn ?? "—"})
                  </button>
                </div>

                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    disabled={edaBusy}
                    onClick={() => applyControl("undo")}
                    style={{
                      padding: "0.4rem 0.6rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: edaBusy ? "not-allowed" : "pointer",
                      opacity: edaBusy ? 0.6 : 1,
                    }}
                  >
                    Undo
                  </button>
                  <button
                    type="button"
                    disabled={edaBusy}
                    onClick={() => applyControl("redo")}
                    style={{
                      padding: "0.4rem 0.6rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: edaBusy ? "not-allowed" : "pointer",
                      opacity: edaBusy ? 0.6 : 1,
                    }}
                  >
                    Redo
                  </button>
                  <button
                    type="button"
                    disabled={edaBusy}
                    onClick={() => applyControl("reset")}
                    style={{
                      padding: "0.4rem 0.6rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: edaBusy ? "not-allowed" : "pointer",
                      opacity: edaBusy ? 0.6 : 1,
                    }}
                  >
                    Reset
                  </button>
                </div>

                {(pipelineLoading || pipelineError) && (
                  <p style={{ color: pipelineError ? "#f87171" : "#a1a1aa", marginTop: "0.65rem" }}>
                    {pipelineLoading ? "Loading pipeline…" : pipelineError}
                  </p>
                )}
              </div>

              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ fontWeight: 700, marginBottom: "0.35rem" }}>Pipeline</div>
                {pipeline.length === 0 ? (
                  <p style={{ margin: 0, color: "#a1a1aa" }}>No transformations yet.</p>
                ) : (
                  <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                    {pipeline.map((step) => (
                      <li key={step.id} style={{ padding: "0.35rem 0", borderBottom: "1px solid #2d2d3d" }}>
                        <span style={{ color: "#a78bfa", fontWeight: 700 }}>#{step.id}</span>{" "}
                        <span style={{ color: "#e4e4e7" }}>{step.action}</span>
                        {step.parameters && Object.keys(step.parameters).length > 0 ? (
                          <span style={{ color: "#a1a1aa" }}>
                            {" "}
                            • {JSON.stringify(step.parameters)}
                          </span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}

                <div style={{ marginTop: "0.65rem" }}>
                  <button
                    type="button"
                    disabled={exportLoading || pipeline.length === 0}
                    onClick={handleExportPipeline}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: exportLoading || pipeline.length === 0 ? "not-allowed" : "pointer",
                      opacity: exportLoading || pipeline.length === 0 ? 0.6 : 1,
                    }}
                  >
                    {exportLoading ? "Exporting…" : "Export pipeline"}
                  </button>
                  {exportError && <p style={{ color: "#f87171", marginTop: "0.5rem" }}>{exportError}</p>}
                  {exportCode && (
                    <details style={{ marginTop: "0.65rem" }}>
                      <summary>Exported Python</summary>
                      <pre style={{ background: "#0f0f1a", padding: "1rem", overflow: "auto", fontSize: "0.8rem" }}>
                        {exportCode}
                      </pre>
                    </details>
                  )}
                </div>
              </div>

              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ fontWeight: 700, marginBottom: "0.35rem" }}>EDA Charts</div>
                {chartsLoading && <p style={{ color: "#a1a1aa", marginTop: "0.25rem" }}>Loading charts…</p>}
                {chartsError && <p style={{ color: "#f87171" }}>{chartsError}</p>}
                {charts && (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1rem" }}>
                    {charts.distribution && (
                      <div style={{ background: "#141423", padding: "0.75rem", borderRadius: 8 }}>
                        <PlotFigure figure={charts.distribution} />
                      </div>
                    )}
                    {charts.correlation_heatmap && (
                      <div style={{ background: "#141423", padding: "0.75rem", borderRadius: 8 }}>
                        <PlotFigure figure={charts.correlation_heatmap} />
                      </div>
                    )}
                    {charts.trend && (
                      <div style={{ background: "#141423", padding: "0.75rem", borderRadius: 8 }}>
                        <PlotFigure figure={charts.trend} />
                      </div>
                    )}
                    {charts.top_categories && (
                      <div style={{ background: "#141423", padding: "0.75rem", borderRadius: 8 }}>
                        <PlotFigure figure={charts.top_categories} />
                      </div>
                    )}
                    {!charts.distribution && !charts.correlation_heatmap && !charts.trend && !charts.top_categories && (
                      <p style={{ margin: 0, color: "#a1a1aa" }}>No charts available for this dataset yet.</p>
                    )}
                  </div>
                )}
              </div>

              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", marginBottom: "0.35rem" }}>
                  <div style={{ fontWeight: 700 }}>Key Insights</div>
                  <button
                    type="button"
                    disabled={insightsLoading || !uploadId}
                    onClick={generateKeyInsights}
                    style={{
                      padding: "0.4rem 0.6rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: insightsLoading ? "not-allowed" : "pointer",
                      opacity: insightsLoading ? 0.6 : 1,
                    }}
                  >
                    {insightsLoading ? "Generating…" : "Generate insights"}
                  </button>
                </div>
                {insightsError && <p style={{ color: "#f87171", margin: 0 }}>{insightsError}</p>}
                {insights?.insights && (
                  <div style={{ background: "#141423", padding: "0.75rem", borderRadius: 8 }}>
                    <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
                      {insights.insights.slice(0, 10).map((item, i) => (
                        <li key={i} style={{ marginBottom: "0.35rem", color: "#e4e4e7" }}>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ fontWeight: 700, marginBottom: "0.35rem" }}>Column Analysis</div>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.5rem" }}>
                  <select
                    value={columnChoice}
                    onChange={(e) => setColumnChoice(e.target.value)}
                    style={{ padding: "0.4rem 0.6rem", borderRadius: 8, border: "1px solid #2d2d3d", background: "#141423", color: "#e4e4e7" }}
                  >
                    {(profile?.columns ?? []).map((c: string) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={!columnChoice || columnAnalysisLoading}
                    onClick={async () => {
                      setColumnAnalysisLoading(true);
                      setColumnAnalysisResult(null);
                      try {
                        if (!columnChoice) return;
                        const res = await columnAnalysis(uploadId!, columnChoice);
                        setColumnAnalysisResult(res);
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Failed to analyze column");
                      } finally {
                        setColumnAnalysisLoading(false);
                      }
                    }}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: !columnChoice || columnAnalysisLoading ? "not-allowed" : "pointer",
                      opacity: !columnChoice || columnAnalysisLoading ? 0.6 : 1,
                    }}
                  >
                    {columnAnalysisLoading ? "Analyzing…" : "Analyze column"}
                  </button>
                </div>
                {columnAnalysisResult && (
                  <details>
                    <summary>Column result</summary>
                    <pre style={{ background: "#0f0f1a", padding: "1rem", overflow: "auto", fontSize: "0.85rem" }}>
                      {JSON.stringify(columnAnalysisResult, null, 2)}
                    </pre>
                  </details>
                )}
              </div>

              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ fontWeight: 700, marginBottom: "0.35rem" }}>Row Analysis</div>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.5rem" }}>
                  <input
                    type="number"
                    value={rowIndex}
                    onChange={(e) => setRowIndex(Number(e.target.value))}
                    style={{ width: 140, padding: "0.4rem 0.6rem", borderRadius: 8, border: "1px solid #2d2d3d", background: "#141423", color: "#e4e4e7" }}
                  />
                  <button
                    type="button"
                    disabled={rowAnalysisLoading}
                    onClick={async () => {
                      setRowAnalysisLoading(true);
                      setRowAnalysisResult(null);
                      setError(null);
                      try {
                        const res = await rowAnalysis(uploadId!, rowIndex);
                        setRowAnalysisResult(res);
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Failed to analyze row");
                      } finally {
                        setRowAnalysisLoading(false);
                      }
                    }}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: rowAnalysisLoading ? "not-allowed" : "pointer",
                      opacity: rowAnalysisLoading ? 0.6 : 1,
                    }}
                  >
                    {rowAnalysisLoading ? "Analyzing…" : "Analyze row"}
                  </button>
                </div>
                {rowAnalysisResult && (
                  <details>
                    <summary>Row result</summary>
                    <pre style={{ background: "#0f0f1a", padding: "1rem", overflow: "auto", fontSize: "0.85rem" }}>
                      {JSON.stringify(rowAnalysisResult, null, 2)}
                    </pre>
                  </details>
                )}
              </div>

              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ fontWeight: 700, marginBottom: "0.35rem" }}>Filtered Analysis</div>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.5rem" }}>
                  <select
                    value={filterColumn}
                    onChange={(e) => setFilterColumn(e.target.value)}
                    style={{ padding: "0.4rem 0.6rem", borderRadius: 8, border: "1px solid #2d2d3d", background: "#141423", color: "#e4e4e7" }}
                  >
                    {(profile?.columns ?? []).map((c: string) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  <select
                    value={filterOperator}
                    onChange={(e) => setFilterOperator(e.target.value)}
                    style={{ padding: "0.4rem 0.6rem", borderRadius: 8, border: "1px solid #2d2d3d", background: "#141423", color: "#e4e4e7" }}
                  >
                    {["=", "!=", ">", ">=", "<", "<=", "contains"].map((op) => (
                      <option key={op} value={op}>{op}</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    value={filterValue}
                    onChange={(e) => setFilterValue(e.target.value)}
                    placeholder="value"
                    style={{ width: 220, padding: "0.4rem 0.6rem", borderRadius: 8, border: "1px solid #2d2d3d", background: "#141423", color: "#e4e4e7" }}
                  />
                  <button
                    type="button"
                    disabled={!filterColumn || !filterOperator || filteredAnalysisLoading}
                    onClick={async () => {
                      setFilteredAnalysisLoading(true);
                      setFilteredAnalysisResult(null);
                      setError(null);
                      try {
                        const res = await filteredAnalysis(uploadId!, filterColumn, filterOperator, filterValue);
                        setFilteredAnalysisResult(res);
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Failed to run filtered analysis");
                      } finally {
                        setFilteredAnalysisLoading(false);
                      }
                    }}
                    style={{
                      padding: "0.45rem 0.7rem",
                      borderRadius: 8,
                      border: "1px solid #2d2d3d",
                      background: "#141423",
                      color: "#e4e4e7",
                      cursor: !filterColumn || filteredAnalysisLoading ? "not-allowed" : "pointer",
                      opacity: !filterColumn || filteredAnalysisLoading ? 0.6 : 1,
                    }}
                  >
                    {filteredAnalysisLoading ? "Running…" : "Run"}
                  </button>
                </div>
                {filteredAnalysisResult && (
                  <details>
                    <summary>Filtered analysis result</summary>
                    <pre style={{ background: "#0f0f1a", padding: "1rem", overflow: "auto", fontSize: "0.85rem" }}>
                      {JSON.stringify(filteredAnalysisResult, null, 2)}
                    </pre>
                  </details>
                )}
              </div>

              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ fontWeight: 700, marginBottom: "0.35rem" }}>Suggested prompts</div>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  {edaSuggestions.map((s, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setQuestion(s)}
                      style={{
                        padding: "0.4rem 0.6rem",
                        borderRadius: 999,
                        border: "1px solid #2d2d3d",
                        background: "#141423",
                        color: "#e4e4e7",
                        cursor: "pointer",
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
                {edaSuggestions.length === 0 && (
                  <p style={{ color: "#a1a1aa", marginTop: "0.5rem" }}>
                    No numeric/categorical columns detected yet.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ marginBottom: "1.5rem" }}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={
            mode === "eda"
              ? "Click a prompt above or type an EDA question (e.g. 'Top 10 rows with highest loudness')"
              : "e.g. Which region has the highest sales?"
          }
          style={{ width: "100%", maxWidth: 400, padding: "0.5rem", marginRight: "0.5rem", marginBottom: "0.5rem" }}
        />
        <br />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? "Asking…" : "Ask"}
        </button>
      </form>
      {error && <p style={{ color: "#f87171" }}>{error}</p>}
      {answer && (
        <div style={{ background: "#1e1e2e", padding: "1.5rem", borderRadius: 8 }}>
          <p><strong>Answer:</strong> {answer.answer ?? ""}</p>
          {answer.data != null && typeof answer.data === "object" && Object.keys(answer.data).length > 0 ? (
            <details style={{ marginTop: "0.75rem" }}>
              <summary>Data</summary>
              <pre style={{ background: "#0f0f1a", padding: "1rem", overflow: "auto", fontSize: "0.85rem" }}>
                {JSON.stringify(answer.data, null, 2)}
              </pre>
            </details>
          ) : null}
        </div>
      )}
    </div>
  );
}
