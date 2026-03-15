"use client";

import { useState, useEffect } from "react";
import { getAnomalies } from "@/lib/api";
import Link from "next/link";

type Anomaly = {
  index?: number;
  column?: string;
  columns?: string[];
  value?: number;
  values?: Record<string, unknown>;
  method?: string;
  z_score?: number;
  bounds?: { low?: number; high?: number };
};

export default function AnomaliesPage() {
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<{ anomalies?: Anomaly[]; total_count?: number } | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setUploadId(localStorage.getItem("upload_id"));
    }
  }, []);

  async function loadAnomalies() {
    if (!uploadId) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await getAnomalies(uploadId);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  if (!uploadId) {
    return (
      <div>
        <h1>Anomalies</h1>
        <p>No dataset selected. <Link href="/upload">Upload a CSV</Link> first and return here.</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Anomaly detection</h1>
      <p style={{ color: "#a1a1aa", marginBottom: "1rem" }}>
        Z-score, IQR, and Isolation Forest are run on numeric columns. Review flagged rows below.
      </p>
      <button onClick={loadAnomalies} disabled={loading} style={{ marginBottom: "1.5rem" }}>
        {loading ? "Detecting…" : "Run anomaly detection"}
      </button>
      {error && <p style={{ color: "#f87171" }}>{error}</p>}
      {data && (
        <div style={{ background: "#1e1e2e", padding: "1.5rem", borderRadius: 8 }}>
          <p><strong>Total anomalies:</strong> {data.total_count ?? 0}</p>
          {data.anomalies && data.anomalies.length > 0 ? (
            <ul style={{ listStyle: "none", padding: 0, marginTop: "1rem" }}>
              {data.anomalies.slice(0, 30).map((a, i) => (
                <li key={i} style={{ padding: "0.5rem 0", borderBottom: "1px solid #2d2d3d" }}>
                  <span style={{ color: "#a78bfa" }}>{a.method}</span>
                  {a.column && ` • ${a.column}`}
                  {a.value != null && ` = ${a.value}`}
                  {a.z_score != null && ` (z=${a.z_score})`}
                  {a.bounds && ` [${a.bounds.low}–${a.bounds.high}]`}
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ color: "#a1a1aa" }}>No anomalies detected.</p>
          )}
        </div>
      )}
    </div>
  );
}
