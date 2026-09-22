import React, { useEffect, useRef } from "react";
import PropTypes from "prop-types";

import { formatDuration } from "./rubric";

const SAVE_LABEL = {
  saved: "Saved",
  saving: "Saving…",
  dirty: "Unsaved changes",
  error: "Couldn't save — will retry",
};

/**
 * The answer area: chips, an optional timer, a textarea and a live word count.
 *
 * Plain on purpose. A Mains answer is prose on ruled paper; the nearest honest
 * digital equivalent is a large plain textarea, not a rich-text editor whose
 * formatting the real exam has no way to reward.
 *
 * The word count goes amber past the limit and NEVER blocks typing. Real answer
 * booklets do not stop you writing, and an aspirant who has gone over needs to
 * see by how much so they can cut — a hard cap would hide exactly that.
 */
export default function AnswerEditor({
  question,
  answer,
  onChange,
  onBlur,
  wordCount,
  saveState,
  elapsed,
  timerRunning,
  onStartTimer,
  onPauseTimer,
  onPaste,
  readOnly,
}) {
  const areaRef = useRef(null);

  // Focus the answer when the question changes — the aspirant came here to
  // write, and a click into the box is a step that buys nothing.
  useEffect(() => {
    if (!readOnly && areaRef.current) areaRef.current.focus();
  }, [question?.id, readOnly]);

  const limit = question?.word_limit;
  const overLimit = typeof limit === "number" && wordCount > limit;
  const target = question?.timer_target_seconds;

  return (
    <section className="soft-card rounded-2xl p-4" data-testid="descriptive-editor">
      <div className="flex flex-wrap items-center gap-2">
        {typeof question?.marks === "number" && (
          <span className="rounded-full border border-clay-300 px-2 py-0.5 text-xs">
            {question.marks} marks
          </span>
        )}
        {typeof limit === "number" ? (
          <span className="rounded-full border border-clay-300 px-2 py-0.5 text-xs">
            {limit} words
          </span>
        ) : (
          <span className="rounded-full border border-dashed border-clay-300 px-2 py-0.5 text-xs text-muted-foreground">
            No word limit given
          </span>
        )}
        {question?.verified_against_official === false && (
          // Provenance, stated rather than implied. Most of the corpus is
          // memory-based or coaching-sourced; an aspirant deciding how much to
          // trust the wording needs to know which.
          <span
            className="rounded-full border border-amber-400 bg-amber-50 px-2 py-0.5 text-xs text-amber-900"
            data-testid="descriptive-provenance"
          >
            Not checked against the official paper
          </span>
        )}
      </div>

      {/* The timer is only offered when the question carries marks — without
          them there is no target to write against, and a bare stopwatch would
          imply one exists. */}
      {typeof target === "number" && (
        <div className="mt-3 flex flex-wrap items-center gap-3" data-testid="descriptive-timer">
          <span className="num-mono text-sm">
            {formatDuration(elapsed)}
            <span className="text-muted-foreground"> / {formatDuration(target)}</span>
          </span>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={timerRunning ? onPauseTimer : onStartTimer}
            disabled={readOnly}
            data-testid="descriptive-timer-toggle"
          >
            {timerRunning ? "Pause" : "Start timer"}
          </button>
          <span className="text-xs text-muted-foreground">
            Guidance, not a limit — nothing stops when it runs out.
          </span>
        </div>
      )}

      <label className="sr-only" htmlFor="descriptive-answer">
        Your answer
      </label>
      <textarea
        id="descriptive-answer"
        ref={areaRef}
        className="mt-3 w-full rounded-xl border border-clay-300 p-3 text-sm leading-relaxed"
        rows={18}
        value={answer}
        onChange={(e) => onChange(e.target.value)}
        // Recorded, never blocked. Pasting is allowed — an aspirant drafting in
        // another editor is doing nothing wrong — but the history says so, and
        // saying so is what keeps "I wrote this" meaningful six months later.
        onPaste={(e) => {
          if (readOnly || !onPaste) return;
          const text = e.clipboardData?.getData?.("text") ?? "";
          onPaste(text);
        }}
        onBlur={onBlur}
        readOnly={readOnly}
        placeholder="Write your answer here."
        data-testid="descriptive-answer-input"
      />

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <span
          className={`num-mono text-xs ${overLimit ? "font-semibold text-amber-700" : "text-muted-foreground"}`}
          data-testid="descriptive-word-count"
        >
          {wordCount} {wordCount === 1 ? "word" : "words"}
          {typeof limit === "number" && ` of ${limit}`}
          {overLimit && ` · ${wordCount - limit} over`}
        </span>
        <span className="text-xs text-muted-foreground" data-testid="descriptive-save-state">
          {readOnly ? "Submitted" : SAVE_LABEL[saveState] || ""}
        </span>
      </div>
    </section>
  );
}

AnswerEditor.propTypes = {
  question: PropTypes.shape({
    id: PropTypes.string,
    marks: PropTypes.number,
    word_limit: PropTypes.number,
    timer_target_seconds: PropTypes.number,
    verified_against_official: PropTypes.bool,
  }),
  answer: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  onBlur: PropTypes.func,
  wordCount: PropTypes.number.isRequired,
  saveState: PropTypes.string,
  elapsed: PropTypes.number,
  timerRunning: PropTypes.bool,
  onStartTimer: PropTypes.func,
  onPauseTimer: PropTypes.func,
  onPaste: PropTypes.func,
  readOnly: PropTypes.bool,
};
