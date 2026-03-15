"use client";

import { useState, useEffect } from "react";
import { ask } from "@/lib/api";
import Link from "next/link";

export default function AskPage() {
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<{ answer?: string; data?: unknown } | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setUploadId(localStorage.getItem("upload_id"));
    }
  }, []);

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
      <p style={{ color: "#a1a1aa", marginBottom: "1rem" }}>
        Ask in natural language (e.g. &quot;Which region has the highest sales?&quot;). Uses Ollama by default; ensure <code>ollama run llama3.2</code> is running.
      </p>
      <form onSubmit={handleSubmit} style={{ marginBottom: "1.5rem" }}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Which region has the highest sales?"
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
