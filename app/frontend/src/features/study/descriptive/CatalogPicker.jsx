import React from "react";
import PropTypes from "prop-types";

/**
 * Subject → paper → questions. Subject first, and nothing before it.
 *
 * WHAT THIS REPLACES. With no subject chosen the picker rendered every paper
 * in the corpus as a chip — 140 of them — labelled "2025 · P1", a label six
 * different subjects share. The wall was unreadable, and every chip in it was
 * ambiguous. Both problems have the same cause: a paper only means something
 * inside a subject.
 *
 * So the subject is REQUIRED CONTEXT. Until one is chosen this renders the
 * subject picker and nothing else — not a shortened paper list, not a preview.
 * A picker is a question the aspirant can answer; a wall of papers is not.
 *
 * Once chosen, the papers are TABS, not chips: Paper I / Paper II for an
 * optional, GS1..GS4 / Essay for General Studies. The tabs come from the
 * subject's canonical structure rather than from the papers that happen to
 * exist, so a paper with nothing loaded yet is still a tab that says so —
 * a missing tab reads as "this paper does not exist", which is a different
 * and false claim.
 */

function chipClass(active) {
  return `rounded-full border px-3 py-1 text-sm ${
    active
      ? "border-[#2E2218] bg-[#F3EADB] font-semibold"
      : "border-clay-300 hover:bg-[#F3EADB]"
  }`;
}

/** "3 of 28 done", or the plain count when nothing is done yet. */
export function countLabel(total, done) {
  const n = Number(total) || 0;
  const d = Number(done) || 0;
  if (!d) return `${n} ${n === 1 ? "question" : "questions"}`;
  return `${n} ${n === 1 ? "question" : "questions"} · ${d} done`;
}

export function SubjectPicker({ subjects, onPick }) {
  return (
    <section data-testid="descriptive-subject-picker">
      <h3 className="font-heading text-sm font-semibold">Which subject?</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Papers and questions are shown once you pick one — a paper label like
        &ldquo;2025 · P1&rdquo; means a different paper in each subject.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {subjects.map((s) => (
          <button
            key={s.subject}
            type="button"
            className={chipClass(false)}
            onClick={() => onPick(s.subject)}
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
  );
}

SubjectPicker.propTypes = {
  subjects: PropTypes.array.isRequired,
  onPick: PropTypes.func.isRequired,
};

export function PaperTabs({ slots, active, onSelect }) {
  if (!slots.length) return null;
  return (
    <div className="flex flex-wrap gap-2" role="tablist" aria-label="Paper">
      {slots.map((slot) => {
        // THE SLOT CODE, not `paper_number`. Essay's number was 99, which the
        // catalogue endpoint rejected as out of range — so the tab existed,
        // rendered, and answered 422 on every click.
        const value = String(slot.slot);
        const selected = active === value;
        return (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={selected}
            className={chipClass(selected)}
            onClick={() => onSelect(selected ? null : value)}
            data-testid="descriptive-paper-tab"
          >
            {slot.label}
            <span className="num-mono ml-2 text-xs text-muted-foreground">
              {slot.question_count}
            </span>
          </button>
        );
      })}
    </div>
  );
}

PaperTabs.propTypes = {
  slots: PropTypes.array.isRequired,
  active: PropTypes.string,
  onSelect: PropTypes.func.isRequired,
};

export function LensToggle({ lens, onChange }) {
  return (
    <div
      className="flex flex-wrap gap-1 rounded-lg border border-[#E7DECB] bg-[#F3EADB] p-1"
      role="radiogroup"
      aria-label="How to browse"
    >
      {[
        { value: "syllabus", label: "By syllabus" },
        { value: "year", label: "By year" },
      ].map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={lens === o.value}
          className={`rounded-md px-3 py-1 text-[12px] font-semibold ${
            lens === o.value
              ? "border border-[#D9C7A7] bg-[#FFFDF9] text-[#2E2218]"
              : "text-clay-700"
          }`}
          onClick={() => onChange(o.value)}
          data-testid={`descriptive-lens-${o.value}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

LensToggle.propTypes = {
  lens: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
};

/** One row per year for the selected paper. Not a chip wall. */
export function YearLens({ years, selectedYear, onPickYear }) {
  if (!years.length) {
    return (
      <p className="py-4 text-sm text-muted-foreground" data-testid="descriptive-year-empty">
        No sat papers for this selection yet.
      </p>
    );
  }
  return (
    <ul className="flex flex-col" data-testid="descriptive-year-lens">
      {years.map((y) => (
        <li key={y.year} className="border-b border-[#E7DECB] last:border-0">
          <button
            type="button"
            className="w-full py-2.5 text-left"
            aria-pressed={selectedYear === String(y.year)}
            onClick={() => onPickYear(selectedYear === String(y.year) ? null : String(y.year))}
            data-testid="descriptive-year-row"
          >
            <span className="text-[13px] font-semibold">{y.year}</span>
            <span className="num-mono ml-2 text-[11px] text-muted-foreground">
              {countLabel(y.question_count, y.attempted_count)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

YearLens.propTypes = {
  years: PropTypes.array.isRequired,
  selectedYear: PropTypes.string,
  onPickYear: PropTypes.func.isRequired,
};

/** Sections → microtopics, in syllabus order, collapsible. */
export function SyllabusLens({ themes, selectedTheme, onPickTheme, supported }) {
  const sections = themes.flatMap((paper) =>
    (paper.sections || []).map((s) => ({ ...s, paperLabel: paper.paper_label })),
  );
  if (supported === false) {
    // The Essay paper has no syllabus: its questions are prompts, not topics.
    // Saying so is different from "no themes yet", which reads as missing data
    // and invites the aspirant to wait for something that is never coming.
    return (
      <p
        className="py-4 text-sm text-muted-foreground"
        data-testid="descriptive-syllabus-unsupported"
      >
        The Essay paper has no syllabus to browse. Pick a year instead.
      </p>
    );
  }
  if (!sections.length) {
    return (
      <p className="py-4 text-sm text-muted-foreground" data-testid="descriptive-syllabus-empty">
        No syllabus themes for this selection yet.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-1" data-testid="descriptive-syllabus-lens">
      {sections.map((section) => (
        <details
          key={`${section.paperLabel}-${section.section}`}
          className="rounded-xl border border-clay-200 px-3 py-2"
          data-testid="descriptive-theme-section"
        >
          <summary className="cursor-pointer text-sm">
            {section.section}
            {section.part && (
              // M10-rev3: a syllabus's named parts are metadata, not a level of
              // their own. Beside the unit, never as a grouping most papers lack.
              <span className="ml-2 text-xs text-muted-foreground">{section.part}</span>
            )}
            <span className="num-mono ml-2 text-xs text-muted-foreground">
              {countLabel(section.question_count, section.attempted_count)}
            </span>
          </summary>
          {section.line && (
            <p className="mt-1 text-xs text-muted-foreground" data-testid="descriptive-section-line">
              {section.line}
            </p>
          )}
          <div className="mt-2 flex flex-wrap gap-2">
            {section.themes.map((t) => (
              <button
                key={t.theme}
                type="button"
                className={chipClass(selectedTheme === t.theme)}
                aria-pressed={selectedTheme === t.theme}
                onClick={() => onPickTheme(selectedTheme === t.theme ? null : t.theme)}
                title={countLabel(t.question_count, t.attempted_count)}
                data-testid="descriptive-theme"
              >
                {t.theme}
                <span className="num-mono ml-2 text-xs text-muted-foreground">
                  {t.attempted_count ? `${t.attempted_count}/${t.question_count}` : t.question_count}
                </span>
              </button>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}

SyllabusLens.propTypes = {
  themes: PropTypes.array.isRequired,
  selectedTheme: PropTypes.string,
  onPickTheme: PropTypes.func.isRequired,
  supported: PropTypes.bool,
};

export default function CatalogPicker({
  catalog,
  selection,
  onSelect,
  loading,
  error,
  lens,
  onLensChange,
  filters,
  onFilterChange,
}) {
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
  if (subjects.length === 0) {
    return (
      <p className="py-6 text-sm text-muted-foreground" data-testid="descriptive-catalog-empty">
        No verified descriptive questions for this exam yet.
      </p>
    );
  }

  // NOTHING BUT THE PICKER until a subject is chosen.
  if (!selection.subject) {
    return (
      <SubjectPicker
        subjects={subjects}
        onPick={(subject) =>
          onSelect({
            subject, paper: null, paper_id: null, paper_number: null,
            theme: null, year: null,
          })
        }
      />
    );
  }

  const slots = catalog?.paper_slots || [];
  const activeSlot = slots.find((s) => String(s.slot) === selection.paper);
  const slotChosen = Boolean(selection.paper);
  const emptySlot = slotChosen && activeSlot && activeSlot.question_count === 0;

  return (
    <div className="flex flex-col gap-4" data-testid="descriptive-catalog">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h3 className="font-heading text-[18px]" data-testid="descriptive-subject-header">
            {selection.subject}
          </h3>
          <p className="text-xs text-muted-foreground">
            {catalog?.total_questions || 0} questions in this subject
          </p>
        </div>
        <button
          type="button"
          className="link-under text-[12px] text-clay-700"
          onClick={() =>
            onSelect({
              subject: null, paper: null, paper_id: null, paper_number: null,
              theme: null, year: null,
            })
          }
          data-testid="descriptive-change-subject"
        >
          Change subject
        </button>
      </div>

      <PaperTabs
        slots={slots}
        active={selection.paper}
        onSelect={(value) =>
          onSelect({
            ...selection, paper: value, paper_number: null,
            paper_id: null, theme: null, year: null,
          })
        }
      />

      {emptySlot ? (
        // A tab with nothing behind it says which of the two things is true.
        <p className="py-4 text-sm text-muted-foreground" data-testid="descriptive-slot-empty">
          {activeSlot.label} — not available yet.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <LensToggle lens={lens} onChange={onLensChange} />
            <label className="flex items-center gap-1.5 text-[12px] text-clay-700">
              <input
                type="checkbox"
                checked={filters.unattempted}
                onChange={(e) => onFilterChange("unattempted", e.target.checked)}
                data-testid="descriptive-filter-unattempted"
              />
              Unattempted only
            </label>
            <label className="flex items-center gap-1.5 text-[12px] text-clay-700">
              <input
                type="checkbox"
                checked={filters.hasMarks}
                onChange={(e) => onFilterChange("hasMarks", e.target.checked)}
                data-testid="descriptive-filter-has-marks"
              />
              Has marks
            </label>
            {lens === "year" && (
              <span className="flex items-center gap-1.5 text-[12px] text-clay-700">
                Years
                <input
                  type="number"
                  className="w-20 rounded-md border border-[#D9C7A7] bg-[#FFFDF9] px-2 py-1 text-[12px]"
                  placeholder="from"
                  aria-label="Year from"
                  value={filters.yearFrom}
                  onChange={(e) => onFilterChange("yearFrom", e.target.value)}
                  data-testid="descriptive-filter-year-from"
                />
                <input
                  type="number"
                  className="w-20 rounded-md border border-[#D9C7A7] bg-[#FFFDF9] px-2 py-1 text-[12px]"
                  placeholder="to"
                  aria-label="Year to"
                  value={filters.yearTo}
                  onChange={(e) => onFilterChange("yearTo", e.target.value)}
                  data-testid="descriptive-filter-year-to"
                />
              </span>
            )}
          </div>

          {lens === "year" ? (
            <YearLens
              years={catalog?.years || []}
              selectedYear={selection.year}
              onPickYear={(year) =>
                onSelect({ ...selection, year, theme: null, paper_id: null })
              }
            />
          ) : (
            <SyllabusLens
              supported={catalog?.syllabus_supported !== false}
              themes={catalog?.themes || []}
              selectedTheme={selection.theme}
              onPickTheme={(theme) =>
                onSelect({ ...selection, theme, year: null, paper_id: null })
              }
            />
          )}
        </>
      )}
    </div>
  );
}

CatalogPicker.propTypes = {
  catalog: PropTypes.object,
  selection: PropTypes.object.isRequired,
  onSelect: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  error: PropTypes.string,
  lens: PropTypes.string.isRequired,
  onLensChange: PropTypes.func.isRequired,
  filters: PropTypes.object.isRequired,
  onFilterChange: PropTypes.func.isRequired,
};
