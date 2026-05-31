import React from "react";

function confidenceColor(score) {
  if (score >= 1.0) return "bg-green-200 hover:bg-green-300";
  if (score >= 0.85) return "bg-yellow-200 hover:bg-yellow-300";
  return "bg-orange-200 hover:bg-orange-300";
}

function highlightText(rawText, pageProposals, selectedKeys, onToggle) {
  if (!rawText || pageProposals.length === 0) {
    return <span>{rawText}</span>;
  }

  // Build sorted, non-overlapping segments to highlight
  const segments = pageProposals
    .filter((p) => p.raw_text && rawText.includes(p.raw_text))
    .map((p) => ({
      start: rawText.indexOf(p.raw_text),
      end: rawText.indexOf(p.raw_text) + p.raw_text.length,
      proposal: p,
    }))
    .sort((a, b) => a.start - b.start);

  const nodes = [];
  let cursor = 0;
  for (const seg of segments) {
    if (seg.start < cursor) continue; // skip overlaps
    if (seg.start > cursor) nodes.push(<span key={cursor}>{rawText.slice(cursor, seg.start)}</span>);
    const p = seg.proposal;
    const key = p.client_proposal_key;
    const selected = selectedKeys.has(key);
    nodes.push(
      <mark
        key={key}
        role="button"
        tabIndex={0}
        aria-pressed={selected}
        data-proposal-key={key}
        data-testid={`highlight-${key}`}
        title={p.matched_alias || p.topic_id}
        onClick={() => onToggle(key)}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onToggle(key)}
        className={[
          "cursor-pointer rounded px-0.5 outline-none",
          confidenceColor(p.confidence_score),
          selected ? "ring-2 ring-indigo-500" : "",
        ].join(" ")}
      >
        {rawText.slice(seg.start, seg.end)}
      </mark>,
    );
    cursor = seg.end;
  }
  if (cursor < rawText.length) nodes.push(<span key={cursor}>{rawText.slice(cursor)}</span>);
  return <>{nodes}</>;
}

export default function PageViewer({ pageText, pageProposals, selectedKeys, onToggle }) {
  return (
    <div
      className="h-full overflow-y-auto p-4 text-sm leading-relaxed text-gray-800 font-mono whitespace-pre-wrap"
      data-testid="page-viewer"
    >
      {pageText
        ? highlightText(pageText, pageProposals, selectedKeys, onToggle)
        : <span className="text-gray-400">No page text available.</span>}
    </div>
  );
}
