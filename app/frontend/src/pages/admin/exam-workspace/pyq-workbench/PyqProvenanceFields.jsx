import React from "react";

// ─── Shared provenance inputs ────────────────────────────────────────────────
// Extracted from PaperProvenanceModal (PR #763) so the source-type selector,
// source-url field, exam-scoped document picker, pyq_source selector, and the
// blocking/advisory formatting exist in ONE place. Consumed by BOTH
// PaperProvenanceModal and AddPyqPaperModal (onboarding). Do NOT re-implement
// these inputs anywhere else (Section E reuse mandate).

export const SOURCE_TYPE_LABELS = {
  official:     "Official",
  memory_based: "Memory-based",
  coaching:     "Coaching",
  community:    "Community",
  aggregator:   "Aggregator",
  unknown:      "Unknown",
};

// Build a human-readable label for a pyq_paper document option.
// Keeps page count + question/extracted count, but truncates the visible
// filename so long names do not clip the <option>. The caller pairs this with
// a `title` attribute carrying the full, untruncated text (tooltip).
const MAX_FILENAME = 48;

function truncateMiddle(text, max = MAX_FILENAME) {
  if (!text || text.length <= max) return text;
  const head = Math.ceil((max - 1) / 2);
  const tail = Math.floor((max - 1) / 2);
  return `${text.slice(0, head)}…${text.slice(text.length - tail)}`;
}

export function documentOptionLabel(doc, qCount) {
  const name = doc.original_filename || doc.id;
  const pages = doc.page_count ? ` (${doc.page_count}pp)` : "";
  const extracted = doc.extracted_count
    ? ` · ${doc.extracted_count} extracted`
    : "";
  const questions = qCount ? ` · ${qCount} question${qCount === 1 ? "" : "s"}` : "";
  return { name, pages, extracted, questions };
}

/**
 * Reusable provenance inputs. Controlled — the parent owns the values and
 * passes setters. Any field can be hidden via the `show` flags so the
 * onboarding "source step" and "evidence step" can render subsets.
 *
 * Props:
 *  - sourceType / onSourceTypeChange
 *  - sourceUrl / onSourceUrlChange
 *  - documentId / onDocumentIdChange
 *  - pyqSourceId / onPyqSourceIdChange
 *  - pyqDocuments: array of {id, original_filename, page_count, extracted_count, status}
 *  - pyqSources: array of {id, title, source_url}
 *  - docCounts: Map<documentId, number> (optional question counts)
 *  - show: { sourceType, sourceUrl, document, pyqSource } — defaults all true
 *  - idPrefix: data-testid prefix (default "provenance")
 */
export default function PyqProvenanceFields({
  sourceType,
  onSourceTypeChange,
  sourceUrl,
  onSourceUrlChange,
  documentId,
  onDocumentIdChange,
  pyqSourceId,
  onPyqSourceIdChange,
  pyqDocuments,
  pyqSources,
  docCounts,
  show = {},
  idPrefix = "provenance",
}) {
  const showSourceType = show.sourceType !== false;
  const showSourceUrl = show.sourceUrl !== false;
  const showDocument = show.document !== false;
  const showPyqSource = show.pyqSource !== false;

  return (
    <>
      {showSourceType && (
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Source type <span className="text-gray-400 font-normal">(required for verification)</span>
          <select
            value={sourceType}
            onChange={(e) => onSourceTypeChange(e.target.value)}
            className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
            data-testid={`${idPrefix}-source-type`}
          >
            <option value="">— not selected —</option>
            {Object.entries(SOURCE_TYPE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </label>
      )}

      {showSourceUrl && (
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Source URL <span className="text-gray-400 font-normal">(public download link)</span>
          <input
            type="url"
            value={sourceUrl}
            onChange={(e) => onSourceUrlChange(e.target.value)}
            className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
            placeholder="https://upsc.gov.in/…"
            data-testid={`${idPrefix}-source-url`}
          />
        </label>
      )}

      {showDocument && (
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Source document <span className="text-gray-400 font-normal">(uploaded PDF)</span>
          <select
            value={documentId}
            onChange={(e) => onDocumentIdChange(e.target.value)}
            className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none font-mono"
            data-testid={`${idPrefix}-document-id`}
          >
            <option value="">— none —</option>
            {(pyqDocuments || []).map((d) => {
              const qCount = docCounts?.get(d.id);
              const { name, pages, extracted, questions } = documentOptionLabel(d, qCount);
              const fullLabel = `${name}${pages}${extracted}${questions}`;
              const visibleLabel = `${truncateMiddle(name)}${pages}${extracted}${questions}`;
              return (
                // title carries the full, untruncated filename + counts as a tooltip
                <option key={d.id} value={d.id} title={fullLabel}>
                  {visibleLabel}
                </option>
              );
            })}
          </select>
        </label>
      )}

      {showPyqSource && (pyqSources || []).length > 0 && (
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Source registry entry <span className="text-gray-400 font-normal">(optional)</span>
          <select
            value={pyqSourceId}
            onChange={(e) => onPyqSourceIdChange(e.target.value)}
            className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
            data-testid={`${idPrefix}-pyq-source-id`}
          >
            <option value="">— none —</option>
            {(pyqSources || []).map((s) => (
              <option key={s.id} value={s.id} title={s.title || s.source_url || s.id}>
                {s.title || s.source_url || s.id}
              </option>
            ))}
          </select>
        </label>
      )}
    </>
  );
}
