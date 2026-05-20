import React from "react";
import { Link } from "react-router-dom";
import { Info } from "lucide-react";

// A lightweight, single-line guidance hint rather than a heavy banner: a small
// info icon + the next step, with an inline action link. Sits inline at the top
// of a page/section so it guides without dominating the layout.
export default function NextActionCallout({ message, href, actionLabel, tone = "info", title }) {
  if (!message) return null;
  const warn = tone === "warn";
  const cls = warn
    ? "border-amber-200 bg-amber-50 text-amber-900"
    : "border-border bg-white/70 text-foreground/80";
  return (
    <div
      data-testid="next-action-callout"
      role="note"
      className={`flex flex-wrap items-center gap-2 rounded-xl border px-3 py-2 text-xs ${cls}`}
    >
      <Info className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="font-semibold">Next{title ? `: ${title}` : ""}</span>
      <span className="min-w-0 flex-1">{message}</span>
      {href && actionLabel ? (
        <Link className="font-semibold underline underline-offset-2" to={href}>{actionLabel} →</Link>
      ) : null}
    </div>
  );
}
