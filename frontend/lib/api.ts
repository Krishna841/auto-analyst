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

export async function getPipeline(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/pipeline`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to load pipeline");
  }
}

export async function getDatasets() {
  try {
    const res = await fetch(`${API_BASE}/datasets`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to load datasets");
  }
}

export async function getDatasetProfile(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/profile`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to load dataset profile");
  }
}

export async function getCharts(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/charts`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to load charts");
  }
}

export async function exportPipeline(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/pipeline/export?format=python`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to export pipeline");
  }
}

export async function columnAnalysis(uploadId: string, column: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/column-analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ column }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to analyze column");
  }
}

export async function rowAnalysis(uploadId: string, row_index: number) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/row-analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ row_index }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to analyze row");
  }
}

export async function filteredAnalysis(
  uploadId: string,
  column: string,
  operator: string,
  value: string
) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/filtered-analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filter: { column, operator, value } }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to run filtered analysis");
  }
}

export async function transformDataset(
  uploadId: string,
  action: string,
  parameters: Record<string, unknown> = {}
) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/transform`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, parameters }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to apply transformation");
  }
}

export async function undoTransform(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/undo`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to undo transformation");
  }
}

export async function redoTransform(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/redo`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to redo transformation");
  }
}

export async function resetTransform(uploadId: string) {
  try {
    const res = await fetch(`${API_BASE}/dataset/${uploadId}/reset`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof Error && e.message !== "Failed to fetch") throw e;
    handleFetchError(e, "Failed to reset pipeline");
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
