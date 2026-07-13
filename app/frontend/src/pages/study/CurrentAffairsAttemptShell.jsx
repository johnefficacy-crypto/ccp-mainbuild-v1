/**
 * CurrentAffairsAttemptShell — the GA weekly current-affairs learner attempt surface
 * (GQR-G5).
 *
 * Route: /app/study/current-affairs/attempts/:attemptId — mounted UNDER StudyShell and
 * inside RouteErrorBoundary, like the EWP-3 English practice route. Entry is the Subject
 * Practice Hub `weekly_current_affairs` launch (server-owned bundle freeze); there is no
 * sidebar destination (no-new-surface rule).
 *
 * One API source of truth: /api/study/current-affairs/* through useCurrentAffairsAttempt.
 * The bundle + question set were frozen server-side at launch — the browser only reads the
 * frozen attempt, persists answers (owner + in-progress + frozen-option + monotonic
 * client_seq enforced server-side), and submits for inline scoring. GA never touches
 * mastery/SRS. The correct answer, explanation, and §10 provenance envelope are hidden
 * until submit, then revealed post-submit.
 *
 * Resume: the GET returns each question's stored selected option, client_seq, and
 * time-spent, so a reloaded client seeds its per-question monotonic counter ABOVE the
 * stored value — a legitimate later edit is never swallowed as an idempotent no-op.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Link, useParams } from "react-router-dom";

import { EmptyState, ErrorState } from "../../shared/ui/core";
import { PageHeader, StudyCard, SectionHeader, StatusDot } from "../../shared/ui/studyos";
import useCurrentAffairsAttempt from "../../features/study/current-affairs/useCurrentAffairsAttempt";

function ProvenanceEnvelope({ question }) {
  // §10 envelope, revealed only post-submit: event date, source publication date,
  // source link, and a supersession warning where a more recent claim may exist.
  const hasProvenance =
    question.event_date || question.source_published_at || question.source_url || question.superseded;
  if (!hasProvenance) return null;
  return (
    <div className="mt-3 rounded border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
      <SectionHeader eyebrow="Source" title="Where this comes from" />
      <dl className="mt-1 space-y-1">
        {question.event_date ? (
          <div className="flex gap-2">
            <dt className="font-medium text-slate-500">Event date</dt>
            <dd>{question.event_date}</dd>
          </div>
        ) : null}
        {question.source_published_at ? (
          <div className="flex gap-2">
            <dt className="font-medium text-slate-500">Published</dt>
            <dd>{question.source_published_at}</dd>
          </div>
        ) : null}
        {question.source_url ? (
          <div className="flex gap-2">
            <dt className="font-medium text-slate-500">Source</dt>
            <dd>
              <a
                href={question.source_url}
                target="_blank"
                rel="noreferrer noopener"
                className="text-emerald-700 underline"
              >
                View source
              </a>
            </dd>
          </div>
        ) : null}
      </dl>
      {question.superseded ? (
        <p
          className="mt-2 rounded bg-amber-50 p-2 text-amber-800"
          role="note"
          data-testid={`ca-superseded-${question.question_id}`}
        >
          {question.supersession_note ||
            "A more recent development may have superseded this item."}
        </p>
      ) : null}
    </div>
  );
}

ProvenanceEnvelope.propTypes = {
  question: PropTypes.shape({
    question_id: PropTypes.string,
    event_date: PropTypes.string,
    source_published_at: PropTypes.string,
    source_url: PropTypes.string,
    superseded: PropTypes.bool,
    supersession_note: PropTypes.string,
  }).isRequired,
};

export default function CurrentAffairsAttemptShell() {
  const { attemptId } = useParams();
  const { fetchAttempt, saveAnswer, submitAttempt, busy } = useCurrentAffairsAttempt();

  const [status, setStatus] = useState("loading"); // loading | error | ready
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(null);
  // Local optimistic selection per question id (mirrors the server-persisted answer).
  const [selections, setSelections] = useState({});
  // Per-question monotonic client_seq, seeded ABOVE the stored value on load so a
  // resumed edit is never swallowed as an idempotent no-op (F4).
  const seqRef = useRef({});
  // Per-question cumulative dwell (seconds), seeded from the resumed attempt so the
  // stored time-spent authority is never reset to zero, plus the wall clock of the
  // last interaction. Elapsed since the last save is attributed to the question just
  // answered — mirrors the mock shell's dwell accounting for a list interface.
  const dwellRef = useRef({});
  const lastTickRef = useRef(Date.now());

  const submitted = attempt?.status === "submitted";

  const load = useCallback(
    async ({ showLoading = false } = {}) => {
      if (showLoading) {
        setStatus("loading");
        setError(null);
      }
      try {
        const data = await fetchAttempt(attemptId);
        setAttempt(data);
        const seeded = {};
        const seqs = {};
        const dwell = {};
        (data.questions || []).forEach((q) => {
          seeded[q.question_id] = q.selected_option_id || null;
          // Seed the counter one above the stored value — the next save wins the guard.
          seqs[q.question_id] = Number(q.client_seq || 0);
          // Resume the stored per-question time so the authority is never reset to 0.
          dwell[q.question_id] = Number(q.time_spent_sec || 0);
        });
        setSelections(seeded);
        seqRef.current = seqs;
        dwellRef.current = dwell;
        lastTickRef.current = Date.now();
        setStatus("ready");
        return data;
      } catch (e) {
        setError(e?.message || "Could not load this current-affairs attempt.");
        setStatus("error");
        return null;
      }
    },
    [fetchAttempt, attemptId],
  );

  useEffect(() => {
    load({ showLoading: true });
  }, [load]);

  const onSelect = useCallback(
    async (question, optionId) => {
      if (submitted || busy) return;
      const qid = question.question_id;
      const previous = selections[qid] ?? null;
      setSelections((prev) => ({ ...prev, [qid]: optionId })); // optimistic
      const nextSeq = (seqRef.current[qid] || 0) + 1;
      seqRef.current[qid] = nextSeq;
      // Attribute the seconds elapsed since the last save to this question, and send
      // the cumulative (monotonic) total so the server-side time authority is real.
      const now = Date.now();
      const elapsed = Math.max(0, Math.round((now - lastTickRef.current) / 1000));
      lastTickRef.current = now;
      const cumulative = (dwellRef.current[qid] || 0) + elapsed;
      dwellRef.current[qid] = cumulative;
      const res = await saveAnswer(attemptId, {
        questionId: qid,
        selectedOptionId: optionId,
        isMarkedForReview: Boolean(question.is_marked_for_review),
        timeSpentSec: cumulative,
        clientSeq: nextSeq,
      });
      if (!res?.ok) {
        setSelections((prev) => ({ ...prev, [qid]: previous })); // rollback
        return;
      }
      // A stale/duplicate sequence is an idempotent server no-op: the server did NOT
      // store our selection (a newer sequence from another tab/device already won).
      // Keeping the optimistic answer would show a value that was never recorded — so
      // reconcile against the authoritative stored state instead of trusting the UI.
      if (res.data?.status === "already_recorded" || res.data?.idempotent === true) {
        await load({ showLoading: false });
      }
    },
    [attemptId, saveAnswer, selections, submitted, busy, load],
  );

  const onSubmit = useCallback(async () => {
    const res = await submitAttempt(attemptId);
    if (res?.ok) {
      // Re-read so the frozen §10 provenance envelope + correct answers are revealed.
      await load({ showLoading: false });
    }
  }, [attemptId, submitAttempt, load]);

  const answeredCount = useMemo(
    () => Object.values(selections).filter(Boolean).length,
    [selections],
  );

  if (status === "loading") {
    return (
      <div className="mx-auto max-w-3xl p-4" data-testid="ca-loading">
        <div role="status" aria-live="polite" className="space-y-3">
          <div className="h-6 w-1/2 animate-pulse rounded bg-slate-100" />
          <div className="h-24 w-full animate-pulse rounded bg-slate-100" />
          <span className="sr-only">Loading current-affairs attempt</span>
        </div>
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="mx-auto max-w-3xl p-4">
        <ErrorState
          title="Current-affairs attempt unavailable"
          message={error}
          onRetry={() => load({ showLoading: true })}
        />
      </div>
    );
  }

  const questions = attempt?.questions || [];

  return (
    <div className="mx-auto max-w-3xl p-4" data-testid="current-affairs-attempt-shell">
      <PageHeader
        eyebrow="Weekly current affairs"
        title="Current-affairs practice"
        sub={
          submitted
            ? `Scored ${attempt.total_correct ?? 0}/${attempt.total_questions ?? questions.length}`
            : `${answeredCount}/${attempt?.total_questions ?? questions.length} answered`
        }
      />

      <div className="mt-2">
        <Link
          to="/app/study/subjects"
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          Back to Subject practice hub
        </Link>
      </div>

      {questions.length === 0 && (
        <div className="mt-4" data-testid="ca-empty">
          <EmptyState
            title="No questions in this attempt"
            description="This current-affairs set has no questions. Try again from the Subject practice hub."
          />
        </div>
      )}

      {questions.map((question, index) => {
        const qid = question.question_id;
        const selected = selections[qid] ?? null;
        const isCorrectAnswered = submitted && question.is_correct === true;
        const isWrongAnswered = submitted && selected && question.is_correct === false;
        return (
          <StudyCard key={qid} className="mt-4" data-testid={`ca-question-${index + 1}`}>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium">Question {index + 1}</span>
              {submitted ? (
                <span className="flex items-center gap-1.5 text-xs">
                  <StatusDot
                    state={
                      question.is_correct === true
                        ? "verified"
                        : selected
                          ? "error"
                          : "preview"
                    }
                    label={
                      question.is_correct === true
                        ? "Correct"
                        : selected
                          ? "Incorrect"
                          : "Not answered"
                    }
                  />
                  {question.is_correct === true
                    ? "Correct"
                    : selected
                      ? "Incorrect"
                      : "Not answered"}
                </span>
              ) : null}
            </div>

            <p className="text-sm text-slate-800">{question.question_text}</p>

            <fieldset className="mt-3 space-y-2" disabled={submitted || busy}>
              <legend className="sr-only">Answer options for question {index + 1}</legend>
              {(question.options || []).map((opt) => {
                const chosen = selected === opt.id;
                const isKey = submitted && question.correct_option_id === opt.id;
                return (
                  <label
                    key={opt.id}
                    data-testid={`ca-option-${index + 1}-${opt.option_index}`}
                    className={[
                      "flex cursor-pointer items-start gap-2 rounded border p-2 text-sm",
                      isKey ? "border-emerald-400 bg-emerald-50" : "border-slate-200",
                      chosen && !submitted ? "border-slate-400 bg-slate-50" : "",
                      chosen && isWrongAnswered ? "border-rose-300 bg-rose-50" : "",
                    ].join(" ")}
                  >
                    <input
                      type="radio"
                      name={`ca-q-${qid}`}
                      className="mt-0.5"
                      checked={chosen}
                      onChange={() => onSelect(question, opt.id)}
                    />
                    <span>{opt.option_text}</span>
                  </label>
                );
              })}
            </fieldset>

            {submitted && question.explanation ? (
              <div className="mt-3" data-testid={`ca-explanation-${index + 1}`}>
                <SectionHeader eyebrow="Explanation" title="Why" />
                <p className="text-sm text-slate-700">{question.explanation}</p>
              </div>
            ) : null}

            {submitted ? <ProvenanceEnvelope question={question} /> : null}

            {/* Presence marker so the correct/incorrect classes above are observable. */}
            {isCorrectAnswered ? <span className="sr-only">Answered correctly</span> : null}
          </StudyCard>
        );
      })}

      {!submitted && questions.length > 0 ? (
        <div className="mt-6 flex items-center justify-between">
          <p className="text-xs text-slate-500" role="status">
            {answeredCount} of {attempt?.total_questions ?? questions.length} answered
          </p>
          <button
            type="button"
            data-testid="ca-submit"
            onClick={onSubmit}
            disabled={busy}
            aria-busy={busy}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-40"
          >
            {busy ? "Submitting…" : "Submit attempt"}
          </button>
        </div>
      ) : null}

      {submitted ? (
        <div
          className="mt-6 rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800"
          data-testid="ca-result-summary"
          role="status"
        >
          You scored {attempt.total_correct ?? 0} out of{" "}
          {attempt.total_questions ?? questions.length}. Review the source provenance under
          each question above.
        </div>
      ) : null}
    </div>
  );
}
