const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function handleFetchError(err: unknown, fallback: string): never {
  if (err instanceof TypeError && err.message === "Failed to fetch") {
    throw new Error(
      `Cannot reach the backend at ${API_BASE}. Make sure the API is running (e.g. \`python -m uvicorn backend.main:app --reload\` from project root).`
    );
  }
  throw err instanceof Error ? err : new Error(fallback);
}

export async function uploadCsv(file: File) {
  try {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Upload failed");
  }
}

export async function getPlan(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/plan`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to load plan");
  }
}

export async function runAnalyze(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/analyze`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to run analysis");
  }
}

export async function getInsights(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/insights`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to load insights");
  }
}

export async function getAnomalies(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/anomalies`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to load anomalies");
  }
}

export async function ask(uploadId: string, question: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to ask");
  }
}
