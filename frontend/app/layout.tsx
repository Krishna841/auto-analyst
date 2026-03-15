import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Autonomous AI Data Analyst",
  description: "Upload data, get insights, detect anomalies, ask questions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav style={navStyle}>
          <a href="/">Home</a>
          <a href="/upload">Upload</a>
          <a href="/insights">Insights</a>
          <a href="/anomalies">Anomalies</a>
          <a href="/ask">Ask</a>
        </nav>
        <main style={mainStyle}>{children}</main>
      </body>
    </html>
  );
}

const navStyle: React.CSSProperties = {
  padding: "1rem 2rem",
  background: "#1a1a2e",
  display: "flex",
  gap: "1.5rem",
  alignItems: "center",
};

const mainStyle: React.CSSProperties = {
  maxWidth: 900,
  margin: "0 auto",
  padding: "2rem",
};
