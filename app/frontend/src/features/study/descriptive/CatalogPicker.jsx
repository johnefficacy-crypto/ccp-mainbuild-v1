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
  const themePapers = catalog?.theme_papers || [];
  const subjectChosen = Boolean(selection.subject);

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
              // The number is a question count and nothing else. It read as a
              // paper count, a year count or anything the reader guessed,
              // which is how "Anthropology 45 · PolSci 1" looked plausible
              // while measuring the wrong thing entirely.
              title={`${s.question_count} ${
                s.question_count === 1 ? "question" : "questions"
              }`}
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
        {/* The claim is only made when there is something to claim it about.
            Thematic compilations were leaking into this list and inheriting
            "in question order" — a promise the thematic half cannot keep,
            since its question_number is NULL by design. */}
        {papers.length > 0 && (
          <p className="mt-1 text-xs text-muted-foreground" data-testid="descriptive-papers-hint">
            Sat papers, in question order.
          </p>
        )}
        <div className="mt-2 flex flex-wrap gap-2">
          {papers.length === 0 && (
            <span className="text-sm text-muted-foreground">
              {subjectChosen
                ? "No papers for this subject yet."
                : "Pick a subject to see its papers."}
            </span>
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
              title={`${p.question_count} ${
                p.question_count === 1 ? "question" : "questions"
              }`}
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
          Topic-wise compilations, arranged as the syllabus is arranged. No
          paper order, no year.
        </p>

        {/* Paper tabs. Derived from the themes actually present, so a subject
            with one paper's worth gets one tab. Selecting one narrows the
            sittings above as well — a Paper I tab that left Paper II sittings
            on screen would be a filter that only half applies. */}
        {themePapers.length > 1 && (
          <div className="mt-2 flex flex-wrap gap-2" role="tablist" aria-label="Paper">
            {themePapers.map((t) => {
              const active = selection.paper_number === String(t.paper_number ?? "");
              return (
                <button
                  key={t.paper_label}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={chip(active)}
                  disabled={t.paper_number == null}
                  title={`${t.question_count} ${
                    t.question_count === 1 ? "question" : "questions"
                  }`}
                  onClick={() =>
                    onSelect({
                      ...selection,
                      paper_number: active ? null : String(t.paper_number),
                      theme: null,
                      paper_id: null,
                    })
                  }
                  data-testid="descriptive-theme-paper-tab"
                >
                  {t.paper_label}
                  <span className="num-mono ml-2 text-xs text-muted-foreground">
                    {t.question_count}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        <div className="mt-2 flex flex-col gap-3">
          {themes.length === 0 && (
            <span className="text-sm text-muted-foreground">
              {subjectChosen
                ? "No themes for this subject yet."
                : "Pick a subject to see its themes."}
            </span>
          )}
          {themes.map((paper) => (
            <div key={paper.paper_label} data-testid="descriptive-theme-paper">
              {themes.length > 1 && (
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {paper.paper_label}
                </h4>
              )}
              <div className="mt-1 flex flex-col gap-1">
                {paper.sections.map((section) => (
                  <details
                    key={`${paper.paper_label}-${section.section}`}
                    className="rounded-xl border border-clay-200 px-3 py-2"
                    data-testid="descriptive-theme-section"
                  >
                    <summary className="cursor-pointer text-sm">
                      {section.section}
                      {section.part && (
                        // M10-rev3: a syllabus's named parts are metadata, not
                        // a level of their own. Shown beside the unit, never
                        // as a grouping that eight of the twelve papers lack.
                        <span className="ml-2 text-xs text-muted-foreground">
                          {section.part}
                        </span>
                      )}
                      <span className="num-mono ml-2 text-xs text-muted-foreground">
                        {section.question_count}
                      </span>
                    </summary>
                    {section.line && (
                      // The official syllabus line for this unit, as the
                      // syllabus prints it.
                      <p
                        className="mt-1 text-xs text-muted-foreground"
                        data-testid="descriptive-section-line"
                      >
                        {section.line}
                      </p>
                    )}
                    <div className="mt-2 flex flex-wrap gap-2">
                      {section.themes.map((t) => (
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
                          title={`${t.question_count} ${
                            t.question_count === 1 ? "question" : "questions"
                          }`}
                          data-testid="descriptive-theme"
                        >
                          {t.theme}
                          <span className="num-mono ml-2 text-xs text-muted-foreground">
                            {t.question_count}
                          </span>
                        </button>
                      ))}
                    </div>
                  </details>
                ))}
              </div>
            </div>
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
