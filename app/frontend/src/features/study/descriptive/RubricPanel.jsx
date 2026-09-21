import React, { useState } from "react";
import PropTypes from "prop-types";

import { RUBRIC, RUBRIC_MAX_TOTAL, isRubricComplete, rubricTotal } from "./rubric";

/**
 * Self-review: six criteria, 0/1/2 each, with the descriptor for every score.
 *
 * The descriptors are the point. "Structure: 1" means nothing in six months;
 * "parts are there but run together" still does, and it is what makes a score
 * you gave yourself in March comparable to one you give in September.
 *
 * Submit is gated on a COMPLETE rubric. A partial one would produce a total out
 * of 12 that measured four criteria — a number that looks like a score and is
 * not one. The server enforces the same rule; this just says so first.
 */
export default function RubricPanel({ onSubmit, busy, initialScores, initialNotes, readOnly }) {
  const [scores, setScores] = useState(initialScores || {});
  const [notes, setNotes] = useState(initialNotes || "");

  const total = rubricTotal(scores);
  const complete = isRubricComplete(scores);

  return (
    <section className="soft-card rounded-2xl p-4" data-testid="descriptive-rubric">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-heading text-base font-semibold">Review your own answer</h3>
        <span className="num-mono text-sm" data-testid="descriptive-rubric-total">
          {total === null ? "—" : total} / {RUBRIC_MAX_TOTAL}
        </span>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        You score this, not the app. Pick the descriptor that matches what you
        actually wrote.
      </p>

      <ul className="mt-4 space-y-4">
        {RUBRIC.map((criterion) => (
          <li key={criterion.key} data-testid={`rubric-${criterion.key}`}>
            <fieldset disabled={readOnly || busy}>
              <legend className="text-sm font-semibold">{criterion.label}</legend>
              <div className="mt-2 space-y-1">
                {criterion.descriptors.map((descriptor, score) => {
                  const id = `rubric-${criterion.key}-${score}`;
                  return (
                    <div key={id} className="flex items-start gap-2">
                      <input
                        type="radio"
                        id={id}
                        name={`rubric-${criterion.key}`}
                        className="mt-1"
                        checked={scores[criterion.key] === score}
                        onChange={() =>
                          setScores((prev) => ({ ...prev, [criterion.key]: score }))
                        }
                        data-testid={id}
                      />
                      <label htmlFor={id} className="text-sm leading-snug">
                        <span className="num-mono mr-2 font-semibold">{score}</span>
                        {descriptor}
                      </label>
                    </div>
                  );
                })}
              </div>
            </fieldset>
          </li>
        ))}
      </ul>

      <label className="mt-4 block text-sm font-semibold" htmlFor="descriptive-notes">
        Notes for next time
      </label>
      <textarea
        id="descriptive-notes"
        className="mt-1 w-full rounded-xl border border-clay-300 p-2 text-sm"
        rows={3}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        readOnly={readOnly}
        placeholder="What would you do differently?"
        data-testid="descriptive-notes"
      />

      {!readOnly && (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="btn btn-primary"
            disabled={!complete || busy}
            onClick={() => onSubmit(scores, notes)}
            data-testid="descriptive-submit"
          >
            {busy ? "Saving…" : "Save review"}
          </button>
          {!complete && (
            <span className="text-xs text-muted-foreground">
              Score all six criteria to save.
            </span>
          )}
        </div>
      )}
    </section>
  );
}

RubricPanel.propTypes = {
  onSubmit: PropTypes.func,
  busy: PropTypes.bool,
  initialScores: PropTypes.object,
  initialNotes: PropTypes.string,
  readOnly: PropTypes.bool,
};
