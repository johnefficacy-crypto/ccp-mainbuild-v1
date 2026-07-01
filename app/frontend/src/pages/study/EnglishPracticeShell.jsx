/**
 * EnglishPracticeShell — the EWP-3 Sentence Builder surface.
 *
 * Route: /app/study/practice/english/:sessionId (a sibling route under the
 * protected DashShell, NOT nested in StudyShell and NOT via AttemptShellRouter —
 * English practice uses writing_sessions, never mock_attempts, §2). Entry is via
 * planner tasks; there is no sidebar destination (no-new-surface rule).
 *
 * One API source of truth: /api/study/practice/english/* through
 * useEnglishPracticeSession. Language issues (EWP-2B, async) are rendered when
 * present in a submit/evaluation response; until the async evaluator + a resume
 * endpoint land, the surface degrades gracefully to deterministic feedback +
 * unit status.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import ErrorState from "../../shared/ui/ErrorState";
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

function unitConstraint(unit, key, fallback) {
  const c = unit?.unit_constraints || {};
  return c[key] ?? fallback;
}

/** Extract language issues from a submit/evaluation payload, if any are present. */
function issuesFromResult(result) {
  const langIssues = result?.evaluation?.language_result?.issues;
  if (Array.isArray(langIssues)) return langIssues;
  return [];
}

export default function EnglishPracticeShell() {
  const { sessionId } = useParams();
  const { fetchSession, submitUnit, reopenUnit, busy } = useEnglishPracticeSession();

  const [status, setStatus] = useState("loading"); // loading | error | ready
  const [error, setError] = useState(null);
  const [session, setSession] = useState(null);
  const [units, setUnits] = useState([]);
  // Per-unit-number local runtime state captured from submit responses (the
  // current API's get_session does not return versions/evaluations — resume of
  // prior evaluations is an EWP-2 deferred item, tracked in the checklist).
  const [results, setResults] = useState({}); // { [unitNumber]: submitResponse }
  const [nextVersion, setNextVersion] = useState({}); // { [unitNumber]: int }
  const [reopened, setReopened] = useState({}); // { [unitId]: bool }

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const data = await fetchSession(sessionId);
      setSession(data.session);
      setUnits(data.units || []);
      setStatus("ready");
    } catch (e) {
      setError(e?.message || "Could not load this practice session.");
      setStatus("error");
    }
  }, [fetchSession, sessionId]);

  useEffect(() => {
    load();
  }, [load]);

  const applyOutcome = useCallback((unit, res) => {
    if (!res?.ok) return;
    const data = res.data || {};
    setResults((prev) => ({ ...prev, [unit.unit_number]: data }));
    setNextVersion((prev) => ({
      ...prev,
      [unit.unit_number]: (data.version_number || 0) + 1,
    }));
    setReopened((prev) => ({ ...prev, [unit.id]: false }));
    // Refresh unit statuses (submit drives the rollup server-side).
    load();
  }, [load]);

  const onSubmitUnit = useCallback(async (unit, text) => {
    const version = nextVersion[unit.unit_number] || 1;
    const res = await submitUnit(sessionId, unit.unit_number, text, version);
    applyOutcome(unit, res);
  }, [nextVersion, submitUnit, sessionId, applyOutcome]);

  const onReopenUnit = useCallback(async (unit) => {
    const latest = results[unit.unit_number]?.version_id
      || results[unit.unit_number]?.evaluation?.unit_version_id;
    if (!latest) return; // cannot reopen without the latest version id (resume gap)
    const res = await reopenUnit(sessionId, unit.id, latest);
    if (res?.ok) setReopened((prev) => ({ ...prev, [unit.id]: true }));
  }, [results, reopenUnit, sessionId]);

  const prompt = useMemo(() => session?.prompt || {}, [session]);

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
        <ErrorState title="Practice session unavailable" message={error} onRetry={load} />
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

      {units.map((unit) => {
        const meta = UNIT_STATUS[unit.status] || UNIT_STATUS.not_started;
        const result = results[unit.unit_number];
        const issues = issuesFromResult(result);
        const minWords = unitConstraint(unit, "min_words", prompt.min_words);
        const maxWords = unitConstraint(unit, "max_words", prompt.max_words);
        const isRewrite = unit.status === "rewrite_required" || reopened[unit.id];

        return (
          <StudyCard key={unit.id} className="mt-4" data-testid={`unit-${unit.unit_number}`}>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium">Sentence {unit.unit_number}</span>
              <span className="flex items-center gap-1.5 text-xs text-slate-500">
                <StatusDot state={meta.dot} label={meta.label} />
                {meta.label}
              </span>
            </div>

            {/* Compose / rewrite / pending / done, driven by unit status. */}
            {["not_started", "draft"].includes(unit.status) && !reopened[unit.id] && (
              <SentenceBuilder
                unitNumber={unit.unit_number}
                promptText={prompt.prompt_text}
                minWords={minWords}
                maxWords={maxWords}
                busy={busy}
                onSubmit={(text) => onSubmitUnit(unit, text)}
              />
            )}

            {unit.status === "evaluation_pending" && (
              <p className="text-sm text-amber-700" data-testid={`unit-${unit.unit_number}-pending`}>
                Your sentence is being evaluated. Language feedback will appear here shortly.
              </p>
            )}

            {isRewrite && result && (
              <RewriteEditor
                previousAnswer={result.evaluation?.answer_text || result.answer_text || ""}
                minWords={minWords}
                maxWords={maxWords}
                busy={busy}
                onSubmit={(text) => onSubmitUnit(unit, text)}
              />
            )}
            {unit.status === "rewrite_required" && result && !reopened[unit.id] && (
              <button
                type="button"
                className="btn btn-ghost mt-2"
                data-testid={`unit-${unit.unit_number}-reopen`}
                disabled={busy}
                onClick={() => onReopenUnit(unit)}
              >
                Start rewrite
              </button>
            )}

            {["ready", "completed"].includes(unit.status) && (
              <p className="text-sm text-emerald-700" data-testid={`unit-${unit.unit_number}-done`}>
                Nicely done — this sentence is complete.
              </p>
            )}

            {/* Deterministic + language feedback (when a submit response is held). */}
            {result?.coverage && result.coverage.passed === false && (
              <p className="mt-2 text-xs text-rose-600">
                Some required words are still missing.
              </p>
            )}
            {issues.length > 0 && (
              <div className="mt-3 space-y-2">
                <SectionHeader eyebrow="Feedback" title="Language issues" />
                {issues.map((issue, i) => (
                  <SentenceIssueCard
                    key={`${unit.unit_number}-${i}`}
                    issue={issue}
                    answerText={result.evaluation?.answer_text || result.answer_text || ""}
                  />
                ))}
              </div>
            )}
          </StudyCard>
        );
      })}
    </div>
  );
}
