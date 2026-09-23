import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import { api } from "../../../lib/api";
import AnswerEditor from "./AnswerEditor";
import AnswerStructurePanel from "./AnswerStructurePanel";
import HandwrittenPages from "./HandwrittenPages";
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

  // Type or Upload. The mode lives on the attempt, so it survives a reload and
  // the history can say which of two attempts at one question was handwritten.
  const [mode, setMode] = useState("typed");
  const [modeError, setModeError] = useState("");
  const [reviewing, setReviewing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState([]);
  // How many pages the handwritten attempt has. `null` until the uploader has
  // said — an unknown count must not read as zero and disable Submit on a
  // slow connection.
  const [pageCount, setPageCount] = useState(null);
  // The answer structure opens only after submit, and only when asked for:
  // it sits beside the answer, never over it while it is being written.
  const [comparing, setComparing] = useState(false);

  const loadHistory = React.useCallback(() => {
    if (!question?.id) return;
    api
      .get(`/api/study/descriptive/attempts?pyq_question_id=${encodeURIComponent(question.id)}`)
      .then((res) => setHistory(Array.isArray(res?.items) ? res.items : []))
      .catch(() => setHistory([]));
  }, [question?.id]);

  useEffect(() => {
    setReviewing(false);
    setComparing(false);
    setModeError("");
    loadHistory();
  }, [question?.id, loadHistory]);

  useEffect(() => {
    if (attempt?.answer_mode) setMode(attempt.answer_mode);
  }, [attempt?.answer_mode]);

  const switchMode = React.useCallback(
    async (next) => {
      if (!attempt?.id || next === mode) return;
      setModeError("");
      try {
        await api.put(`/api/study/descriptive/attempts/${attempt.id}/answer-mode`, {
          answer_mode: next,
        });
        setMode(next);
      } catch (err) {
        // Switching back to typing with pages still attached is refused by the
        // server rather than silently deleting them. Say which, not "failed".
        setModeError(
          "Remove the uploaded pages first, then switch back to typing.",
        );
      }
    },
    [attempt?.id, mode],
  );

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

  // `pageCount === 0`, not `!pageCount`: null means the uploader has not
  // reported yet, and disabling on an unknown count would block a typed
  // attempt's own button for as long as a request takes.
  const needsPages = mode === "handwritten" && pageCount === 0;

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
        {/* Subject · Paper · Section · Topic, then where it came from. Each
            level is omitted when unknown rather than blanked. */}
        {question.breadcrumb?.trail?.length > 0 && (
          <p className="mt-2 text-xs text-muted-foreground" data-testid="descriptive-breadcrumb">
            {question.breadcrumb.trail.join(" · ")}
          </p>
        )}
        {question.breadcrumb?.source && (
          <p className="num-mono mt-1 text-xs text-muted-foreground" data-testid="descriptive-source">
            {question.breadcrumb.source}
          </p>
        )}
      </section>

      {!submitted && (
        <div
          className="flex flex-wrap items-center gap-2"
          role="radiogroup"
          aria-label="How do you want to answer?"
        >
          {[
            { value: "typed", label: "Type" },
            { value: "handwritten", label: "Upload" },
          ].map((o) => (
            <button
              key={o.value}
              type="button"
              role="radio"
              aria-checked={mode === o.value}
              className={`rounded-full border px-3 py-1 text-[12px] ${
                mode === o.value
                  ? "border-[#D9C7A7] bg-[#FFFDF9] font-semibold"
                  : "border-clay-300 text-clay-700"
              }`}
              onClick={() => switchMode(o.value)}
              data-testid={`descriptive-mode-${o.value}`}
            >
              {o.label}
            </button>
          ))}
          <span className="text-[11px] text-clay-700">
            {mode === "handwritten"
              ? "Write on paper and photograph each side."
              : "Type your answer here."}
          </span>
        </div>
      )}

      {modeError && (
        <p role="status" className="text-[12px] text-rose-700" data-testid="descriptive-mode-error">
          {modeError}
        </p>
      )}

      {/* After submit, "Compare with answer structure" puts the checklist BESIDE
          the answer — typed text or photographed pages alike. Before submit
          there is no affordance at all, and the server refuses the read. */}
      <div
        className={submitted && comparing ? "grid gap-4 lg:grid-cols-2" : ""}
        data-testid="descriptive-answer-area"
      >
      {mode === "handwritten" ? (
        <HandwrittenPages
          attemptId={attempt?.id}
          readOnly={submitted}
          onModeChange={setMode}
          onCountChange={setPageCount}
        />
      ) : (
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
      )}
      {submitted && comparing && attempt?.id && (
        <AnswerStructurePanel attemptId={attempt.id} />
      )}
      </div>

      {!submitted && !reviewing && (
        <div>
          <button
            type="button"
            className="btn btn-primary"
            // THE SAME RULE THE SERVER ENFORCES (409 no_pages). A handwritten
            // attempt with nothing uploaded has no answer to review: its word
            // count is NULL by design, so submitting would record a self-score
            // over nothing at all.
            disabled={needsPages}
            onClick={async () => {
              await save();
              setReviewing(true);
            }}
            data-testid="descriptive-finish"
          >
            Finish and review
          </button>
          {needsPages && (
            <p
              className="mt-2 text-[12px] text-clay-700"
              data-testid="descriptive-needs-pages"
            >
              Upload at least one page before reviewing this answer.
            </p>
          )}
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
            <button
              type="button"
              className="btn"
              aria-expanded={comparing}
              onClick={() => setComparing((v) => !v)}
              data-testid="descriptive-compare-structure"
            >
              {comparing ? "Hide answer structure" : "Compare with answer structure"}
            </button>
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
    label: PropTypes.string,
    breadcrumb: PropTypes.shape({
      trail: PropTypes.arrayOf(PropTypes.string),
      source: PropTypes.string,
    }),
  }).isRequired,
  onNext: PropTypes.func,
  hasNext: PropTypes.bool,
};
