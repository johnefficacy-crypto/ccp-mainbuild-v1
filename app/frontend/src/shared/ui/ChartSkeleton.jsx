import React from "react";

export default function ChartSkeleton({ height = 192 }) {
  return (
    <div className="lg:col-span-2 soft-card rounded-2xl p-5" aria-hidden="true">
      <div className="h-3 w-24 rounded bg-muted/60" />
      <div className="mt-3 h-6 w-40 rounded bg-muted/50" />
      <div
        className="mt-5 w-full rounded-xl border border-border/60 bg-muted/35"
        style={{ height }}
      />
    </div>
  );
}
