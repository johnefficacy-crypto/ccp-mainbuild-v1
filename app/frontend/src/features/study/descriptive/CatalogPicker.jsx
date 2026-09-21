import React from "react";
import PropTypes from "prop-types";

/**
 * Subject → paper / theme / year.
 *
 * The corpus has two halves and they are navigated differently, so the picker
 * says so rather than flattening them. A real paper has a sitting and a question
 * order worth honouring; a thematic compilation is topic-wise with no order at
 * all, and offering it a "year" filter would promise a sitting that never
 * happened.
 */
export default function CatalogPicker({ catalog, selection, onSelect, loading, error }) {
  if (loading) {
    return (
      <p role="status" className="py-6 text-sm text-muted-foreground">
        Loading the question catalogue…
      </p>
    );
  }
  if (error) {
    return (
      <p role="status" className="py-6 text-sm text-rose-700">
        {error}
      </p>
    );
  }

  const subjects = catalog?.subjects || [];
  const papers = catalog?.papers || [];
  const themes = catalog?.themes || [];

  if (subjects.length === 0) {
    return (
      <p className="py-6 text-sm text-muted-foreground" data-testid="descriptive-catalog-empty">
        No verified descriptive questions for this exam yet.
      </p>
    );
  }

  const chip = (active) =>
    `rounded-full border px-3 py-1 text-sm ${
      active
        ? "border-[#2E2218] bg-[#F3EADB] font-semibold"
        : "border-clay-300 hover:bg-[#F3EADB]"
    }`;

  return (
    <div className="flex flex-col gap-5" data-testid="descriptive-catalog">
      <section>
        <h3 className="font-heading text-sm font-semibold">Subject</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          {subjects.map((s) => (
            <button
              key={s.subject}
              type="button"
              className={chip(selection.subject === s.subject)}
              aria-pressed={selection.subject === s.subject}
              onClick={() =>
                onSelect({
                  subject: selection.subject === s.subject ? null : s.subject,
                  paper_id: null,
                  theme: null,
                  year: null,
                })
              }
              data-testid="descriptive-subject"
            >
              {s.subject}
              <span className="num-mono ml-2 text-xs text-muted-foreground">
                {s.question_count}
              </span>
            </button>
          ))}
        </div>
      </section>

      <section>
        <h3 className="font-heading text-sm font-semibold">Papers</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Sat papers, in question order.
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {papers.length === 0 && (
            <span className="text-sm text-muted-foreground">No papers yet.</span>
          )}
          {papers.map((p) => (
            <button
              key={p.id}
              type="button"
              className={chip(selection.paper_id === p.id)}
              aria-pressed={selection.paper_id === p.id}
              onClick={() =>
                onSelect({
                  ...selection,
                  paper_id: selection.paper_id === p.id ? null : p.id,
                  theme: null,
                })
              }
              data-testid="descriptive-paper"
            >
              {p.label}
              <span className="num-mono ml-2 text-xs text-muted-foreground">
                {p.question_count}
              </span>
            </button>
          ))}
        </div>
      </section>

      <section>
        <h3 className="font-heading text-sm font-semibold">Themes</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Topic-wise compilations. No paper order, no year.
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {themes.length === 0 && (
            <span className="text-sm text-muted-foreground">No themes yet.</span>
          )}
          {themes.map((t) => (
            <button
              key={t.theme}
              type="button"
              className={chip(selection.theme === t.theme)}
              aria-pressed={selection.theme === t.theme}
              onClick={() =>
                onSelect({
                  ...selection,
                  theme: selection.theme === t.theme ? null : t.theme,
                  paper_id: null,
                  year: null,
                })
              }
              data-testid="descriptive-theme"
            >
              {t.theme}
              <span className="num-mono ml-2 text-xs text-muted-foreground">
                {t.question_count}
              </span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

CatalogPicker.propTypes = {
  catalog: PropTypes.object,
  selection: PropTypes.object.isRequired,
  onSelect: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  error: PropTypes.string,
};
