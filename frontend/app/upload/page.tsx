"use client";

import { useState, useEffect, useRef } from "react";
import { uploadCsv } from "@/lib/api";
import { useRouter } from "next/navigation";

const UPLOAD_STEPS = [
  "Uploading file…",
  "Loading dataset…",
  "Profiling columns…",
  "Building analysis plan…",
  "Finalizing…",
] as const;

const STEP_PERCENT = [15, 35, 55, 75, 90];

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [percent, setPercent] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const router = useRouter();

  // Advance step and percentage while loading (simulated progress)
  useEffect(() => {
    if (!loading) return;
    setStepIndex(0);
    setPercent(STEP_PERCENT[0] ?? 0);
    const interval = setInterval(() => {
      setStepIndex((prev) => {
        const next = Math.min(prev + 1, UPLOAD_STEPS.length - 1);
        setPercent(STEP_PERCENT[next] ?? 90);
        return next;
      });
    }, 1200);
    intervalRef.current = interval;
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
    };
  }, [loading]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setStepIndex(0);
    setPercent(0);
    try {
      const data = await uploadCsv(file);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setStepIndex(UPLOAD_STEPS.length);
      setPercent(100);
      setResult(data);
      if (typeof window !== "undefined" && data.upload_id) {
        localStorage.setItem("upload_id", data.upload_id);
      }
    } catch (err) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setStepIndex(UPLOAD_STEPS.length);
      setPercent(100);
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Upload dataset</h1>
      <p style={{ color: "#a1a1aa", marginBottom: "1.5rem" }}>
        Upload a CSV file. The backend will profile it and prepare an analysis plan.
      </p>
      <form onSubmit={handleSubmit} style={{ marginBottom: "1.5rem" }}>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          style={{ marginRight: "0.5rem" }}
        />
        <button type="submit" disabled={!file || loading}>
          {loading ? "Processing…" : "Upload"}
        </button>
      </form>

      {loading && (
        <div style={{ marginBottom: "1.5rem", background: "#1e1e2e", padding: "1.25rem", borderRadius: 8 }}>
          <p style={{ margin: "0 0 0.75rem 0", fontWeight: 600 }}>
            {percent}%
          </p>
          <div
            style={{
              height: 8,
              background: "#2d2d3d",
              borderRadius: 4,
              overflow: "hidden",
              marginBottom: "1rem",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${percent}%`,
                background: "linear-gradient(90deg, #4f46e5, #818cf8)",
                borderRadius: 4,
                transition: "width 0.3s ease",
              }}
            />
          </div>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "#a1a1aa", fontSize: "0.9rem" }}>
            {UPLOAD_STEPS.map((label, i) => (
              <li
                key={label}
                style={{
                  marginBottom: "0.25rem",
                  color: i < stepIndex ? "#a5b4fc" : i === stepIndex ? "#e4e4e7" : "#71717a",
                  fontWeight: i === stepIndex ? 600 : 400,
                }}
              >
                {i < stepIndex ? "✓ " : i === stepIndex ? "● " : ""}
                {label}
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p style={{ color: "#f87171" }}>{error}</p>}
      {result && !loading && (
        <div style={{ background: "#1e1e2e", padding: "1rem", borderRadius: 8 }}>
          <p style={{ color: "#86efac", marginBottom: "0.5rem", fontWeight: 600 }}>✓ Upload complete</p>
          <p><strong>Upload ID:</strong> {(result as { upload_id?: string }).upload_id}</p>
          <p><strong>Rows:</strong> {(result as { rows?: number }).rows}</p>
          <p><strong>Columns:</strong> {(result as { columns?: string[] }).columns?.join(", ")}</p>
          {(result as { analysis_plan?: { analysis_plan?: string[] } }).analysis_plan?.analysis_plan && (
            <div style={{ marginTop: "0.75rem" }}>
              <strong>Analysis plan:</strong>
              <ul style={{ margin: "0.25rem 0 0 1rem" }}>
                {((result as { analysis_plan?: { analysis_plan?: string[] } }).analysis_plan?.analysis_plan ?? []).map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </div>
          )}
          <p style={{ marginTop: "1rem" }}>
            <button type="button" onClick={() => router.push("/insights")}>
              View insights →
            </button>
          </p>
        </div>
      )}
    </div>
  );
}
