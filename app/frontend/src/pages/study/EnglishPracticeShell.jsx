/**
 * EnglishPracticeShell — the EWP-3 Sentence Builder surface.
 *
 * Route: /app/study/practice/english/:sessionId — mounted UNDER StudyShell and
 * inside RouteErrorBoundary per the design lock (NOT via AttemptShellRouter —
 * English practice uses writing_sessions, never mock_attempts, §2). Entry is via
 * planner tasks; there is no sidebar destination (no-new-surface rule).
 *
 * One API source of truth: /api/study/practice/english/* through
 * useEnglishPracticeSession. The enriched session read returns, per unit, the
 * latest version (answer text + number → CAS baseline) and the latest evaluation
 * (language issues), gated by feedback release (§13 rule 13). After a submit the
 * unit is `evaluation_pending`; the async EWP-2B evaluator produces issues out of
 * band, so the shell polls the session until no unit is pending, then renders the
 * released issues and the rewrite path.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import ErrorState from "../../shared/ui/ErrorState";
import EmptyState from "../../shared/ui/EmptyState";
import { PageHeader, StudyCard, SectionHeader, StatusDot } from "../../shared/ui/studyos";
import SentenceBuilder from "../../features/study/english-practice/SentenceBuilder";
import RewriteEditor from "../../features/study/english-practice/RewriteEditor";
import SentenceIssueCard from "../../features/study/english-practice/SentenceIssueCard";
import useEnglishPracticeSession from "../../features/study/english-practice/useEnglishPracticeSession";

// Unit status → a human label + a StatusDot state (see shared/ui/studyos).
const UNIT_STATUS = {
  not_started: { label: "Not started", dot: "preview" },
  draft: { label: "Draft", dot: "preview" },
  evaluation_pending: { label: "Evaluating…", dot: "pending" },
  evaluation_failed: { label: "Evaluation failed", dot: "error" },
  rewrite_required: { label: "Needs a rewrite", dot: "error" },
  ready: { label: "Ready", dot: "verified" },
  completed: { label: "Completed", dot: "verified" },
};

// Poll cadence + cap while a unit is being evaluated asynchronously (EWP-2B).
const POLL_INTERVAL_MS = 2500;
const MAX_POLLS = 24;

function unitConstraint(unit, key, fallback) {
  const c = unit?.unit_constraints || {};
  return c[key] ?? fallback;
}

/** Language issues for a unit: server-resumed evaluation first, else in-session. */
function unitIssues(unit, inSessionResult) {
  const resumed = unit?.latest_evaluation?.language_result?.issues;
  if (Array.isArray(resumed)) return resumed;
  const live = inSessionResult?.evaluation?.language_result?.issues;
  if (Array.isArray(live)) return live;
  return [];
}

export default function EnglishPracticeShell() {
  const { sessionId } = useParams();
  const { fetchSession, submitUnit, busy } = useEnglishPracticeSession();

  const [status, setStatus] = useState("loading"); // loading | error | ready
  const [error, setError] = useState(null);
  const [session, setSession] = useState(null);
  const [prompt, setPrompt] = useState({});
  const [units, setUnits] = useState([]);
  const [feedbackReleased, setFeedbackReleased] = useState(true);
  // Immediate submit responses (deterministic coverage feedback) keyed by unit
  // number. Language issues + the CAS baseline come from the server session read.
  const [results, setResults] = useState({});
  const pollsRef = useRef(0);

  const refresh = useCallback(
    async ({ silent = false } = {}) => {
      if (!silent) {
        setStatus("loading");
        setError(null);
      }
      try {
        const data = await fetchSession(sessionId);
        setSession(data.session);
        setPrompt(data.prompt || {});
        setUnits(data.units || []);
        setFeedbackReleased(data.feedback_released !== false);
        setStatus("ready");
        return data;
      } catch (e) {
        if (!silent) {
          setError(e?.message || "Could not load this practice session.");
          setStatus("error");
        }
        return null;
      }
    },
    [fetchSession, sessionId],
  );

  useEffect(() => {
    pollsRef.current = 0;
    refresh();
  }, [refresh]);

  const pendingCount = useMemo(
    () => units.filter((u) => u.status === "evaluation_pending").length,
    [units],
  );

  // Poll while any unit is being evaluated (EWP-2B produces issues out of band).
  // Stops on unmount, session change, when nothing is pending, or after the cap.
  useEffect(() => {
    if (status !== "ready" || pendingCount === 0) return undefined;
    let cancelled = false;
    const id = setInterval(() => {
      pollsRef.current += 1;
      if (pollsRef.current > MAX_POLLS) {
        clearInterval(id);
        return;
      }
      if (!cancelled) refresh({ silent: true });
    }, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [status, pendingCount, refresh]);

  const onSubmitUnit = useCallback(
    async (unit, text) => {
      const version = (unit.latest_version?.version_number || 0) + 1;
      const res = await submitUnit(sessionId, unit.unit_number, text, version);
      if (!res?.ok) return;
      setResults((prev) => ({ ...prev, [unit.unit_number]: { ...(res.data || {}), submittedText: text } }));
      pollsRef.current = 0;
      refresh({ silent: true }); // pick up the evaluation_pending transition + start polling
    },
    [submitUnit, sessionId, refresh],
  );

  if (status === "loading") {
    return (
      <div className="mx-auto max-w-3xl p-4" data-testid="ewp-loading">
        <div role="status" aria-live="polite" className="space-y-3">
          <div className="h-6 w-1/2 animate-pulse rounded bg-slate-100" />
          <div className="h-24 w-full animate-pulse rounded bg-slate-100" />
          <span className="sr-only">Loading practice session</span>
        </div>
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="mx-auto max-w-3xl p-4">
        <ErrorState title="Practice session unavailable" message={error} onRetry={refresh} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-4" data-testid="english-practice-shell">
      <PageHeader
        eyebrow="English Writing Practice"
        title={prompt.prompt_text || "Sentence practice"}
        sub={session?.mode === "exam" ? "Exam mode" : "Learning mode"}
      />

      {units.length === 0 && (
        <div className="mt-4" data-testid="ewp-empty">
          <EmptyState
            title="No sentences to practise"
            description="This session has no units yet. Launch English practice from a planner task."
          />
        </div>
      )}

      {units.map((unit) => {
        const meta = UNIT_STATUS[unit.status] || UNIT_STATUS.not_started;
        const result = results[unit.unit_number];
        const answerText = unit.latest_version?.answer_text || result?.submittedText || "";
        // Feedback (issues) is gated by the server; the client honours the flag too.
        const issues = feedbackReleased ? unitIssues(unit, result) : [];
        const minWords = unitConstraint(unit, "min_words", prompt.min_words);
        const maxWords = unitConstraint(unit, "max_words", prompt.max_words);
        const requiredWords = prompt.required_words || [];

        return (
          <StudyCard key={unit.id} className="mt-4" data-testid={`unit-${unit.unit_number}`}>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium">Sentence {unit.unit_number}</span>
              <span className="flex items-center gap-1.5 text-xs text-slate-500">
                <StatusDot state={meta.dot} label={meta.label} />
                {meta.label}
              </span>
            </div>

            {/* Compose (not_started/draft): submit version 1+. */}
            {["not_started", "draft"].includes(unit.status) && (
              <SentenceBuilder
                unitNumber={unit.unit_number}
                promptText={prompt.prompt_text}
                minWords={minWords}
                maxWords={maxWords}
                requiredWords={requiredWords}
                sessionId={sessionId}
                busy={busy}
                onSubmit={(text) => onSubmitUnit(unit, text)}
              />
            )}

            {unit.status === "evaluation_pending" && (
              <p
                className="text-sm text-amber-700"
                role="status"
                aria-live="polite"
                data-testid={`unit-${unit.unit_number}-pending`}
              >
                Your sentence is being evaluated. Language feedback will appear here shortly.
              </p>
            )}

            {/* Mandatory rewrite: rewrite_required is directly submittable — edit
                the latest answer and submit the next version (CAS derived from
                the server's latest version number). */}
            {unit.status === "rewrite_required" && (
              <RewriteEditor
                previousAnswer={answerText}
                minWords={minWords}
                maxWords={maxWords}
                busy={busy}
                onSubmit={(text) => onSubmitUnit(unit, text)}
              />
            )}

            {["ready", "completed"].includes(unit.status) && (
              <p className="text-sm text-emerald-700" data-testid={`unit-${unit.unit_number}-done`}>
                Nicely done — this sentence is complete.
              </p>
            )}

            {result?.coverage && result.coverage.passed === false && (
              <p className="mt-2 text-xs text-rose-600">Some required words are still missing.</p>
            )}
            {issues.length > 0 && (
              <div className="mt-3 space-y-2">
                <SectionHeader eyebrow="Feedback" title="Language issues" />
                {issues.map((issue, i) => (
                  <SentenceIssueCard key={`${unit.unit_number}-${i}`} issue={issue} answerText={answerText} />
                ))}
              </div>
            )}
          </StudyCard>
        );
      })}
    </div>
  );
}
