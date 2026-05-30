import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, ExternalLink, ShoppingBag } from "lucide-react";
import { api } from "../../lib/api";

const TYPE_LABELS = {
  book: "Standard Book",
  free_pdf: "Free Resource",
  course: "Course",
  notes: "Notes",
  website: "Website",
};

const TYPE_ORDER = ["book", "free_pdf", "course", "notes", "website"];

function ResourceRow({ res }) {
  return (
    <div
      className="flex items-start gap-3 py-3 border-b border-border/50 last:border-0"
      data-testid={`booklist-resource-${res.id}`}
    >
      <BookOpen className="h-4 w-4 text-clay-500 mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-sm">{res.title}</span>
          {res.recommended_for && (
            <span className="text-[10px] uppercase tracking-wide bg-clay-50 border border-clay-200 text-clay-700 px-1.5 py-0.5 rounded-full">
              {res.recommended_for}
            </span>
          )}
          <span className="text-[10px] uppercase tracking-wide bg-dusk-50 border border-dusk-200 text-dusk-700 px-1.5 py-0.5 rounded-full">
            {TYPE_LABELS[res.resource_type] || res.resource_type}
          </span>
        </div>
        {(res.author || res.provider) && (
          <div className="text-xs text-muted-foreground mt-0.5">
            {[res.author, res.provider].filter(Boolean).join(" · ")}
          </div>
        )}
        <div className="flex flex-wrap gap-2 mt-1.5">
          {res.url && (
            <a
              href={res.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-clay-700 hover:underline"
            >
              <ExternalLink className="h-3 w-3" /> Visit
            </a>
          )}
          {res.marketplace_resource_id && (
            <Link
              to={`/app/marketplace/${res.marketplace_resource_id}`}
              className="inline-flex items-center gap-1 text-xs text-clay-700 hover:underline"
            >
              <ShoppingBag className="h-3 w-3" /> Marketplace
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

function SubjectCard({ subject }) {
  const byType = {};
  for (const res of subject.resources) {
    const t = res.resource_type || "other";
    if (!byType[t]) byType[t] = [];
    byType[t].push(res);
  }
  const orderedTypes = [
    ...TYPE_ORDER.filter((t) => byType[t]),
    ...Object.keys(byType).filter((t) => !TYPE_ORDER.includes(t)),
  ];

  return (
    <div
      className="soft-card rounded-2xl p-5"
      data-testid={`booklist-subject-${subject.subject_id}`}
    >
      <div className="font-heading text-base font-semibold mb-3">
        {subject.subject_name}
      </div>
      {orderedTypes.map((type) => (
        <div key={type} className="mb-2 last:mb-0">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold mb-1">
            {TYPE_LABELS[type] || type}
          </div>
          {byType[type].map((res) => (
            <ResourceRow key={res.id} res={res} />
          ))}
        </div>
      ))}
    </div>
  );
}

export default function SubjectBooklistSection({ examSlug }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!examSlug) return;
    setLoading(true);
    setError(null);
    api
      .get(`/api/exam-intelligence/exams/${examSlug}/booklist`)
      .then((d) => setData(d))
      .catch((e) => setError(e?.message || "Failed to load booklist."))
      .finally(() => setLoading(false));
  }, [examSlug]);

  if (!examSlug) return null;

  if (loading) {
    return (
      <div data-testid="booklist-loading" className="text-sm text-muted-foreground">
        Loading booklist…
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="booklist-error" className="text-sm text-destructive">
        {error}
      </div>
    );
  }

  const subjects = data?.subjects ?? [];

  if (subjects.length === 0) {
    return (
      <div
        data-testid="booklist-empty"
        className="soft-card rounded-2xl p-6 text-sm text-muted-foreground"
      >
        No verified booklist yet for this exam. Check back once resources are
        reviewed.
      </div>
    );
  }

  return (
    <div
      data-testid="subject-booklist-section"
      className="grid md:grid-cols-2 gap-4"
    >
      {subjects.map((subj) => (
        <SubjectCard key={subj.subject_id} subject={subj} />
      ))}
    </div>
  );
}
