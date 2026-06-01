import React from "react";

const STEPS = [
  { id: "upload", label: "Upload" },
  { id: "preview", label: "Preview" },
  { id: "committing", label: "Confirm" },
  { id: "result", label: "Result" },
];

const ORDER = STEPS.map((s) => s.id);

export default function BulkImportSteps({ current }) {
  const currentIdx = ORDER.indexOf(current === "committing" ? "committing" : current);

  return (
    <ol className="flex items-center gap-0" aria-label="Import steps" data-testid="bulk-import-steps">
      {STEPS.map((s, idx) => {
        const done = idx < currentIdx;
        const active = s.id === current || (current === "committing" && s.id === "committing");
        return (
          <li key={s.id} className="flex items-center">
            <span
              aria-current={active ? "step" : undefined}
              className={[
                "flex items-center justify-center w-6 h-6 rounded-full text-[11px] font-bold",
                done ? "bg-indigo-600 text-white" : active ? "bg-indigo-100 text-indigo-700 ring-2 ring-indigo-400" : "bg-gray-100 text-gray-400",
              ].join(" ")}
            >
              {done ? "✓" : idx + 1}
            </span>
            <span className={`ml-1.5 text-[12px] font-medium ${active ? "text-indigo-700" : done ? "text-gray-700" : "text-gray-400"}`}>
              {s.label}
            </span>
            {idx < STEPS.length - 1 && (
              <span className="mx-3 text-gray-300">›</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
