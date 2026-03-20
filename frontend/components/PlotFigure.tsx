"use client";

import dynamic from "next/dynamic";

const Plot = dynamic<any>(() => import("react-plotly.js"), { ssr: false });

export default function PlotFigure({ figure }: { figure: any }) {
  if (!figure || !figure.data) return null;
  return (
    <Plot
      data={figure.data}
      layout={figure.layout ?? {}}
      style={{ width: "100%", minHeight: 320 }}
      useResizeHandler
    />
  );
}

