import Link from "next/link";

export default function Home() {
  return (
    <div>
      <h1 style={{ marginBottom: "0.5rem" }}>Autonomous AI Data Analyst</h1>
      <p style={{ color: "#a1a1aa", marginBottom: "2rem" }}>
        Upload a CSV, get profiling, analysis, insights, anomalies, and ask questions in natural language.
      </p>
      <ul style={{ listStyle: "none", padding: 0 }}>
        <li style={{ marginBottom: "0.75rem" }}>
          <Link href="/upload">📤 Upload dataset</Link> — Upload a CSV to get started
        </li>
        <li style={{ marginBottom: "0.75rem" }}>
          <Link href="/insights">💡 Insights</Link> — View AI-generated insights (after upload)
        </li>
        <li style={{ marginBottom: "0.75rem" }}>
          <Link href="/anomalies">⚠️ Anomalies</Link> — See detected anomalies (after upload)
        </li>
        <li style={{ marginBottom: "0.75rem" }}>
          <Link href="/ask">❓ Ask</Link> — Ask questions about your data in natural language
        </li>
      </ul>
      <p style={{ marginTop: "2rem", fontSize: "0.9rem", color: "#71717a" }}>
        Ensure the backend is running at <code>http://localhost:8000</code> (or set <code>NEXT_PUBLIC_API_URL</code>).
      </p>
    </div>
  );
}
