import React from "react";
import PropTypes from "prop-types";

import useAnswerStructure from "./useAnswerStructure";

/**
 * "Compare with answer structure" — shown beside a SUBMITTED answer, typed or
 * handwritten. What the question demanded and the points a good answer
 * carried, with a checklist the aspirant ticks against their own answer.
 *
 * Not a model answer, and not a grade. The ticks are the aspirant's judgement
 * of their own answer, the same way the rubric is.
 */
function Section({ title, items, testId }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mt-4" data-testid={testId}>
      <h4 className="text-[11px] font-semibold uppercase tracking-wide text-clay-700">{title}</h4>
      <ul className="mt-1 list-disc space-y-1 pl-5 text-[13px] leading-snug">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

Section.propTypes = {
  title: PropTypes.string.isRequired,
  items: PropTypes.arrayOf(PropTypes.string),
  testId: PropTypes.string,
};

function budgetLine(budget) {
  if (!budget || !budget.total) return null;
  const parts = [`about ${budget.total} words`];
  if (budget.intro && budget.body && budget.conclusion) {
    parts.push(`${budget.intro} intro · ${budget.body} body · ${budget.conclusion} conclusion`);
  }
  return parts.join(" — ");
}

export default function AnswerStructurePanel({ attemptId }) {
  const {
    state,
    structure,
    ticksFromOlderVersion,
    covered,
    toggle,
    saving,
    saveError,
    pointsCoveredPct,
  } = useAnswerStructure(attemptId);

  if (state === "loading") {
    return (
      <p role="status" className="text-[12px] text-clay-700" data-testid="answer-structure-loading">
        Opening the answer structure…
      </p>
    );
  }
  if (state === "error") {
    return (
      <p role="status" className="text-[12px] text-rose-700" data-testid="answer-structure-error">
        Couldn&apos;t load the answer structure. Try again shortly.
      </p>
    );
  }
  if (!structure) {
    return (
      <section className="soft-card rounded-2xl p-4" data-testid="answer-structure-none">
        <p className="text-[13px]">
          This question doesn&apos;t have a reviewed answer structure yet.
        </p>
      </section>
    );
  }

  const points = structure.body_points || [];
  const budget = budgetLine(structure.word_budget);

  return (
    <section
      className="soft-card rounded-2xl p-4"
      aria-labelledby="answer-structure-heading"
      data-testid="answer-structure-panel"
    >
      <h3 id="answer-structure-heading" className="font-heading text-base font-semibold">
        Answer structure
      </h3>
      <p className="mt-2 text-[13px]" data-testid="answer-structure-directive">
        <span className="font-semibold">{structure.directive}</span>
        {" — "}
        {structure.demand}
      </p>
      {budget && (
        <p className="num-mono mt-1 text-[11px] text-clay-700" data-testid="answer-structure-budget">
          {budget}
        </p>
      )}

      <Section title="Ways to open" items={structure.intro_angles} testId="answer-structure-intro" />

      <fieldset className="mt-4" data-testid="answer-structure-points">
        <legend className="text-[11px] font-semibold uppercase tracking-wide text-clay-700">
          Points a good answer covers — tick the ones yours did
        </legend>
        <ol className="mt-2 space-y-3">
          {points.map((p, i) => {
            const id = `structure-point-${attemptId}-${p.id}`;
            return (
              <li key={p.id} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  id={id}
                  className="mt-1"
                  checked={covered.includes(p.id)}
                  onChange={() => toggle(p.id)}
                  data-testid={`answer-structure-tick-${p.id}`}
                />
                <label htmlFor={id} className="text-[13px] leading-snug">
                  <span className="num-mono mr-1 text-clay-700">{i + 1}.</span>
                  <span className="font-semibold">{p.point}</span>
                  {p.why && <span className="block text-clay-700">{p.why}</span>}
                  {p.evidence_type && (
                    <span className="block text-[12px]">Support with: {p.evidence_type}</span>
                  )}
                  {(p.example || p.thinker) && (
                    <span className="block text-[12px] text-clay-700">
                      {[p.example, p.thinker].filter(Boolean).join(" · ")}
                    </span>
                  )}
                  {p.sub_points?.length > 0 && (
                    <span className="mt-1 block text-[12px]">
                      {p.sub_points.map((s) => (
                        <span key={s} className="block">– {s}</span>
                      ))}
                    </span>
                  )}
                </label>
              </li>
            );
          })}
        </ol>
      </fieldset>
      <p className="mt-3 text-[12px]" aria-live="polite" data-testid="answer-structure-covered">
        {covered.length} of {points.length} points covered
        {pointsCoveredPct !== null ? ` (${pointsCoveredPct}%)` : ""}
        {saving ? " · saving…" : ""}
      </p>
      {ticksFromOlderVersion && (
        <p className="mt-1 text-[11px] text-clay-700" data-testid="answer-structure-older-ticks">
          This structure was updated since you last ticked it.
        </p>
      )}
      {saveError && (
        <p role="alert" className="mt-1 text-[12px] text-rose-700" data-testid="answer-structure-save-error">
          {saveError}
        </p>
      )}

      <Section title="Dimensions to span" items={structure.dimensions} testId="answer-structure-dimensions" />
      <Section title="Illustrations that help" items={structure.examples} testId="answer-structure-examples" />
      <Section title="Ways to close" items={structure.conclusion_angles} testId="answer-structure-conclusion" />
      <Section title="Common pitfalls" items={structure.pitfalls} testId="answer-structure-pitfalls" />
      {structure.sources_note && (
        <p className="mt-4 text-[12px] text-clay-700" data-testid="answer-structure-sources">
          Where to read: {structure.sources_note}
        </p>
      )}
    </section>
  );
}

AnswerStructurePanel.propTypes = {
  attemptId: PropTypes.string.isRequired,
};
