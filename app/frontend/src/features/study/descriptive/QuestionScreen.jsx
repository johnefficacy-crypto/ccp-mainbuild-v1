import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import { api } from "../../../lib/api";
import AnswerEditor from "./AnswerEditor";
import RubricPanel from "./RubricPanel";
import useDescriptiveAttempt from "./useDescriptiveAttempt";
import { formatDuration } from "./rubric";

/**
 * One question, start to finish: stem → write → self-review → history.
 *
 * The flow is deliberately linear. Writing and judging are different acts, and
 * showing the rubric while the answer is still open would invite scoring the
 * plan rather than the answer.
 */
export default function QuestionScreen({ question, onNext, hasNext }) {
  const {
    attempt,
    answer,
    setAnswerText,
    status,
    saveState,
    error,
    wordCount,
    elapsed,
    timerRunning,
    startTimer,
    pauseTimer,
    save,
    submit,
    notePaste,
    submitted,
  } = useDescriptiveAttempt(question?.id);

  const [reviewing, setReviewing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState([]);

  const loadHistory = React.useCallback(() => {
    if (!question?.id) return;
    api
      .get(`/api/study/descriptive/attempts?pyq_question_id=${encodeURIComponent(question.id)}`)
      .then((res) => setHistory(Array.isArray(res?.items) ? res.items : []))
      .catch(() => setHistory([]));
  }, [question?.id]);

  useEffect(() => {
    setReviewing(false);
    loadHistory();
  }, [question?.id, loadHistory]);

  useEffect(() => {
    if (submitted) loadHistory();
  }, [submitted, loadHistory]);

  if (status === "loading" || status === "idle") {
    return (
      <p role="status" className="py-8 text-sm text-muted-foreground">
        Opening this question…
      </p>
    );
  }
  if (status === "error") {
    return (
      <p role="status" className="py-8 text-sm text-rose-700" data-testid="descriptive-error">
        {error}
      </p>
    );
  }

  const handleSubmit = async (scores, notes) => {
    setBusy(true);
    const res = await submit(scores, notes);
    setBusy(false);
    if (res.ok) setReviewing(false);
  };

  // Past attempts EXCLUDING the one on screen — the current attempt is the
  // page, not an entry in its own history.
  const past = history.filter((h) => h.id !== attempt?.id && h.status === "submitted");

  return (
    <div className="flex flex-col gap-4" data-testid="descriptive-question-screen">
      <section className="soft-card rounded-2xl p-4">
        {question.parent_text && (
          // A sub-part without its stem is unanswerable: "(b) Examine this"
          // needs the question it is part (b) of.
          <p
            className="mb-2 border-l-2 border-clay-300 pl-3 text-sm text-muted-foreground"
            data-testid="descriptive-parent-stem"
          >
            {question.parent_text}
          </p>
        )}
        <p className="text-base leading-relaxed">{question.text}</p>
        <p className="num-mono mt-2 text-xs text-muted-foreground">
          {[
            question.subject || question.optional_subject,
            question.year ? `${question.year}` : null,
            question.question_number ? `Q${question.question_number}` : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </section>

      <AnswerEditor
        question={question}
        answer={answer}
        onChange={setAnswerText}
        onBlur={save}
        wordCount={wordCount}
        saveState={saveState}
        elapsed={elapsed}
        timerRunning={timerRunning}
        onStartTimer={startTimer}
        onPauseTimer={pauseTimer}
        onPaste={notePaste}
        readOnly={submitted}
      />

      {!submitted && !reviewing && (
        <div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={async () => {
              await save();
              setReviewing(true);
            }}
            data-testid="descriptive-finish"
          >
            Finish and review
          </button>
        </div>
      )}

      {!submitted && reviewing && (
        <RubricPanel onSubmit={handleSubmit} busy={busy} />
      )}

      {submitted && attempt && (
        <section className="soft-card rounded-2xl p-4" data-testid="descriptive-submitted">
          <h3 className="font-heading text-base font-semibold">Saved</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {attempt.word_count} words ·{" "}
            {attempt.self_total !== null && attempt.self_total !== undefined
              ? `you scored it ${attempt.self_total}/12`
              : "not scored"}
            {attempt.time_spent_seconds
              ? ` · ${formatDuration(attempt.time_spent_seconds)} spent`
              : ""}
            {attempt.pasted_chars > 0 ? " · contains pasted text" : ""}
          </p>
          {attempt.notes && <p className="mt-2 text-sm">{attempt.notes}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            {hasNext && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={onNext}
                data-testid="descriptive-next"
              >
                Next question
              </button>
            )}
          </div>
        </section>
      )}

      {past.length > 0 && (
        <section className="soft-card rounded-2xl p-4" data-testid="descriptive-history">
          <h3 className="font-heading text-base font-semibold">
            Earlier attempts at this question
          </h3>
          <ul className="mt-2 space-y-2">
            {past.map((h) => (
              <li key={h.id} className="rounded-xl border border-clay-200 p-3 text-sm">
                <span className="num-mono text-xs text-muted-foreground">
                  {String(h.submitted_at || "").slice(0, 10)}
                </span>
                <span className="ml-2">
                  {h.word_count} words
                  {h.self_total !== null && h.self_total !== undefined
                    ? ` · ${h.self_total}/12`
                    : ""}
                  {h.time_spent_seconds
                    ? ` · ${formatDuration(h.time_spent_seconds)}`
                    : ""}
                  {/* Only for 0-and-above. `null` means the attempt predates
                      paste tracking, which is not the same as "nothing was
                      pasted" and must not be reported as if it were. */}
                  {h.pasted_chars > 0 ? " · contains pasted text" : ""}
                </span>
                {h.notes && <p className="mt-1 text-muted-foreground">{h.notes}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

QuestionScreen.propTypes = {
  question: PropTypes.shape({
    id: PropTypes.string.isRequired,
    text: PropTypes.string,
    parent_text: PropTypes.string,
    optional_subject: PropTypes.string,
    subject: PropTypes.string,
    year: PropTypes.number,
    question_number: PropTypes.number,
  }).isRequired,
  onNext: PropTypes.func,
  hasNext: PropTypes.bool,
};
