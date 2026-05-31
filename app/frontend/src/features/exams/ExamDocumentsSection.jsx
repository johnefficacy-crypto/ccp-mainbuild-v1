import React, { useEffect, useState } from "react";
import { ExternalLink, FileText } from "lucide-react";
import { api } from "../../lib/api";

const DOC_TYPE_LABELS = {
  notification:  "Notification",
  syllabus:      "Syllabus",
  corrigendum:   "Corrigendum",
  pyq_pdf:       "PYQ PDFs",
  answer_key:    "Answer Keys",
  cutoff_pdf:    "Cutoff PDFs",
  admit_card:    "Admit Card",
};

// Preferred display order
const DOC_TYPE_ORDER = [
  "notification",
  "syllabus",
  "corrigendum",
  "pyq_pdf",
  "answer_key",
  "cutoff_pdf",
  "admit_card",
];

function DocRow({ doc }) {
  return (
    <a
      href={doc.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-2 rounded-lg border border-border bg-white/60 p-3 hover:bg-clay-50 transition-colors text-sm"
      data-testid={`doc-row-${doc.id}`}
    >
      <FileText className="h-4 w-4 text-clay-600 mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="font-medium truncate">{doc.title}</div>
        {doc.cycle_year && (
          <div className="text-xs text-muted-foreground">Year {doc.cycle_year}</div>
        )}
      </div>
      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />
    </a>
  );
}

function DocGroup({ label, docs }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground font-semibold mb-2">
        {label}
      </div>
      <div className="space-y-2">
        {docs.map((d) => (
          <DocRow key={d.id} doc={d} />
        ))}
      </div>
    </div>
  );
}

export default function ExamDocumentsSection({ examSlug }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!examSlug) return;
    setLoading(true);
    api
      .get(`/api/exam-intelligence/exams/${examSlug}/documents`)
      .then(setData)
      .catch(() => setData({ groups: {}, total: 0 }))
      .finally(() => setLoading(false));
  }, [examSlug]);

  if (!examSlug) return null;

  if (loading) {
    return (
      <div className="soft-card rounded-2xl p-6" data-testid="exam-docs-loading">
        <p className="text-sm text-muted-foreground">Loading documents…</p>
      </div>
    );
  }

  const groups = data?.groups || {};
  const orderedKeys = DOC_TYPE_ORDER.filter((k) => groups[k]?.length > 0);
  const extraKeys = Object.keys(groups).filter(
    (k) => !DOC_TYPE_ORDER.includes(k) && groups[k]?.length > 0,
  );
  const allKeys = [...orderedKeys, ...extraKeys];

  if (allKeys.length === 0) {
    return (
      <div
        className="rounded-2xl border border-dashed border-clay-200 bg-clay-50/50 p-6 text-center"
        data-testid="exam-docs-empty"
      >
        <FileText className="h-5 w-5 mx-auto text-clay-500" />
        <div className="mt-2 font-heading text-base font-semibold">No documents yet</div>
        <p className="mt-1 text-xs text-muted-foreground">
          Verified notifications, syllabi, and PYQs will appear here once curated.
        </p>
      </div>
    );
  }

  return (
    <div className="soft-card rounded-2xl p-6 space-y-6" data-testid="exam-docs-section">
      {allKeys.map((k) => (
        <DocGroup
          key={k}
          label={DOC_TYPE_LABELS[k] || k}
          docs={groups[k]}
        />
      ))}
    </div>
  );
}
