"use client";

import { useEffect, useState } from "react";
import { getDatasets } from "@/lib/api";

export default function DatasetSelect() {
  const [datasets, setDatasets] = useState<Array<any>>([]);
  const [uploadId, setUploadId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const current = localStorage.getItem("upload_id") || "";
    setUploadId(current);
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await getDatasets();
        setDatasets(res?.datasets ?? []);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load datasets");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function onChange(nextId: string) {
    localStorage.setItem("upload_id", nextId);
    setUploadId(nextId);
    window.dispatchEvent(new Event("datasetChanged"));
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <span style={{ color: "#a1a1aa", fontSize: "0.9rem" }}>Dataset:</span>
      {error && <span style={{ color: "#f87171", fontSize: "0.9rem" }}>{error}</span>}
      <select
        value={uploadId}
        onChange={(e) => onChange(e.target.value)}
        style={{ padding: "0.35rem 0.5rem", borderRadius: 8, border: "1px solid #2d2d3d", background: "#141423", color: "#e4e4e7" }}
        disabled={loading || datasets.length === 0}
      >
        {datasets.length === 0 ? (
          <option value="">No datasets</option>
        ) : (
          datasets.map((d) => (
            <option key={d.upload_id} value={d.upload_id}>
              {d.upload_id} {typeof d.rows === "number" ? `(${d.rows} rows)` : ""}
            </option>
          ))
        )}
      </select>
    </div>
  );
}

