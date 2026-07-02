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
 *
 * Polling is cancellation-safe: reads commit through a monotonic load token that
 * is invalidated on unmount and on session change, and the loop is serialized
 * (each tick is scheduled only after the previous read resolves) so a slow older
 * poll can never overwrite newer terminal state.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import ErrorState from "../../shared/ui/ErrorState";
import EmptyState from "../../shared/ui/EmptyState";
import { PageHeader, StudyCard, SectionHeader, StatusDot } from "../../shared/ui/studyos";
import SentenceBuilder from "../../features/study/english-practice/SentenceBuilder";
import RewriteEditor from "../../features/study/english-practice/RewriteEditor";
import SentenceIssueCard from "../../features/study/english-practice/SentenceIssueCard";
import BeforeAfterDiff from "../../features/study/english-practice/BeforeAfterDiff";
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
  const [feedbackReleased, setFeedbackReleased] = useState(false);
  const [pollTimedOut, setPollTimedOut] = useState(false);
  // Immediate submit responses keyed by unit number: deterministic coverage
  // feedback + the before/after pair of an accepted rewrite (so the diff
  // survives the rewrite_required → ready/completed transition).
  const [results, setResults] = useState({});
  // Ordering guards for ALL session reads (not just the poll loop):
  //  - genRef      → bumped on unmount + session change; a read from an old
  //                  generation never commits (no cross-session clobber).
  //  - seqRef      → monotonic id assigned to every read AND every optimistic
  //                  local commit, in call order.
  //  - committedRef → highest seq that has committed. A read commits only if its
  //                  seq is still the newest, so an older poll that resolves
  //                  after a newer submit-refresh (across independent units)
  //                  can never overwrite fresher state.
  const genRef = useRef(0);
  const seqRef = useRef(0);
  const committedRef = useRef(0);

  // Fetch the session and commit it iff this read is still the newest (by seq)
  // within the current generation.
  const fetchAndCommit = useCallback(
    async (gen, { showLoading = false } = {}) => {
      const seq = (seqRef.current += 1);
      if (showLoading) {
        setStatus("loading");
        setError(null);
      }
      let data = null;
      let err = null;
      try {
        data = await fetchSession(sessionId);
      } catch (e) {
        err = e;
      }
      if (genRef.current !== gen) return null; // superseded session — drop
      if (seq <= committedRef.current) return null; // a newer read already won — drop
      if (err) {
        if (showLoading) {
          setError(err?.message || "Could not load this practice session.");
          setStatus("error");
        }
        return null;
      }
      committedRef.current = seq;
      setSession(data.session);
      setPrompt(data.prompt || {});
      setUnits(data.units || []);
      // Fail CLOSED: show feedback only on an explicit true (never leak issues
      // if the flag is ever absent/malformed) — "no unreleased-data leakage".
      setFeedbackReleased(data.feedback_released === true);
      setStatus("ready");
      return data;
    },
    [fetchSession, sessionId],
  );

  // Apply a local unit mutation as the newest commit, so no older in-flight read
  // can overwrite it (used for the optimistic post-submit pending lock).
  const commitLocalUnits = useCallback((updater) => {
    committedRef.current = seqRef.current += 1;
    setUnits(updater);
  }, []);

  // Initial load / reload on session change. Cleanup invalidates any in-flight
  // read so a late response for a previous session can't clobber the new one.
  useEffect(() => {
    genRef.current += 1;
    const gen = genRef.current;
    setPollTimedOut(false);
    fetchAndCommit(gen, { showLoading: true });
    return () => {
      genRef.current += 1;
    };
  }, [fetchAndCommit]);

  const retry = useCallback(() => {
    setPollTimedOut(false);
    return fetchAndCommit(genRef.current, { showLoading: true });
  }, [fetchAndCommit]);

  const pendingCount = useMemo(
    () => units.filter((u) => u.status === "evaluation_pending").length,
    [units],
  );

  // Serialized, cancellation-safe poll while any unit is being evaluated. Each
  // tick awaits its read before scheduling the next; the token guard inside
  // fetchAndCommit prevents an overlapping/stale commit.
  useEffect(() => {
    if (status !== "ready" || pendingCount === 0) return undefined;
    const gen = genRef.current;
    let active = true;
    let timer = null;
    let polls = 0;

    const tick = async () => {
      if (!active) return;
      polls += 1;
      const data = await fetchAndCommit(gen, { showLoading: false });
      if (!active || genRef.current !== gen) return;
      if (polls >= MAX_POLLS) {
        setPollTimedOut(true);
        return;
      }
      const stillPending = data
        ? (data.units || []).some((u) => u.status === "evaluation_pending")
        : true;
      if (stillPending) timer = setTimeout(tick, POLL_INTERVAL_MS);
    };

    timer = setTimeout(tick, POLL_INTERVAL_MS);
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [status, pendingCount, fetchAndCommit]);

  const onSubmitUnit = useCallback(
    async (unit, text) => {
      const version = (unit.latest_version?.version_number || 0) + 1;
      const before = unit.latest_version?.answer_text || "";
      const res = await submitUnit(sessionId, unit.unit_number, text, version);
      if (!res?.ok) return res; // surface failure so the composer keeps its autosave
      setResults((prev) => ({
        ...prev,
        [unit.unit_number]: {
          ...(res.data || {}),
          submittedText: text,
          // Retain the accepted rewrite pair for a post-success diff.
          rewriteBefore: version > 1 ? before : null,
          rewriteAfter: version > 1 ? text : null,
        },
      }));
      setPollTimedOut(false);
      // Optimistically lock the unit into evaluation_pending with the accepted
      // version as the new CAS baseline. The submit committed durably on the
      // server, so even if the authoritative refresh below fails, the unit's
      // compose/rewrite control is withdrawn (no duplicate ewp_stale_version
      // resubmit) and polling keeps trying. Applied as the newest commit so an
      // older in-flight read can't revert it.
      commitLocalUnits((prev) =>
        prev.map((u) =>
          u.unit_number === unit.unit_number
            ? {
                ...u,
                status: "evaluation_pending",
                latest_version: {
                  ...(u.latest_version || {}),
                  version_number: version,
                  answer_text: text,
                },
              }
            : u,
        ),
      );
      fetchAndCommit(genRef.current, { showLoading: false });
      return res;
    },
    [submitUnit, sessionId, fetchAndCommit, commitLocalUnits],
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
        <ErrorState title="Practice session unavailable" message={error} onRetry={retry} />
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
        const isDone = ["ready", "completed"].includes(unit.status);
        // Post-success diff: prefer the in-session accepted pair; on reload fall
        // back to the resumed prior version → latest version (§EWP-3 resume).
        const diffBefore = result?.rewriteBefore ?? unit.previous_version?.answer_text ?? null;
        const diffAfter =
          result?.rewriteAfter ?? unit.latest_version?.answer_text ?? null;
        const showRewriteDiff =
          isDone && diffBefore != null && diffAfter != null && diffBefore !== diffAfter;

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
              <div role="status" aria-live="polite" data-testid={`unit-${unit.unit_number}-pending`}>
                {pollTimedOut ? (
                  <div className="text-sm text-amber-700">
                    <p data-testid={`unit-${unit.unit_number}-poll-timeout`}>
                      Feedback is taking longer than expected.
                    </p>
                    <button
                      type="button"
                      data-testid={`unit-${unit.unit_number}-poll-retry`}
                      onClick={retry}
                      className="mt-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700"
                    >
                      Check again
                    </button>
                  </div>
                ) : (
                  <p className="text-sm text-amber-700">
                    Your sentence is being evaluated. Language feedback will appear here shortly.
                  </p>
                )}
              </div>
            )}

            {/* Mandatory rewrite: rewrite_required is directly submittable — edit
                the latest answer and submit the next version (CAS derived from
                the server's latest version number). */}
            {unit.status === "rewrite_required" && (
              <RewriteEditor
                previousAnswer={answerText}
                minWords={minWords}
                maxWords={maxWords}
                sessionId={sessionId}
                unitNumber={unit.unit_number}
                busy={busy}
                onSubmit={(text) => onSubmitUnit(unit, text)}
              />
            )}

            {isDone && (
              <p className="text-sm text-emerald-700" data-testid={`unit-${unit.unit_number}-done`}>
                Nicely done — this sentence is complete.
              </p>
            )}

            {/* Retain the accepted before/after diff through the successful rewrite. */}
            {showRewriteDiff && (
              <div className="mt-3" data-testid={`unit-${unit.unit_number}-rewrite-diff`}>
                <SectionHeader eyebrow="Your rewrite" title="What changed" />
                <BeforeAfterDiff before={diffBefore} after={diffAfter} />
              </div>
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
