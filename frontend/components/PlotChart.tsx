"use client";

import dynamic from "next/dynamic";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

type GroupAnalysisData = Record<string, Record<string, number>>;

interface GroupBarChartProps {
  groupAnalysis: GroupAnalysisData;
  valueKey: string;
}

export function GroupBarChart({ groupAnalysis, valueKey }: GroupBarChartProps) {
  const labels = Object.keys(groupAnalysis);
  const values = labels.map((k) => {
    const v = groupAnalysis[k];
    return typeof v === "object" && v !== null && valueKey in v
      ? Number((v as Record<string, number>)[valueKey])
      : 0;
  });
  return (
    <Plot
      data={[
        {
          type: "bar",
          x: labels,
          y: values,
          marker: { color: "#6366f1" },
        },
      ]}
      layout={{
        title: `By category (${valueKey})`,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(30,30,46,0.5)",
        font: { color: "#e4e4e7" },
        xaxis: { tickangle: -45 },
        margin: { b: 100 },
      }}
      style={{ width: "100%", minHeight: 320 }}
      useResizeHandler
    />
  );
}
