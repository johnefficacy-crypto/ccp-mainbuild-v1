import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import useCalculationGym from "../../features/study/calculation-gym/useCalculationGym";
import { ErrorState } from "../../shared/ui/core";
import { PageHeader, StudyCard } from "../../shared/ui/studyos";

function secondsRemaining(expiresAt) {
  if (!expiresAt) return 0;
  return Math.max(0, Math.ceil((new Date(expiresAt).getTime() - Date.now()) / 1000));
}

function formatClock(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, "0")}`;
}

export default function CalculationGymShell() {
  const { sessionId } = useParams();
  const { fetchSession, submitSession, busy } = useCalculationGym();
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [session, setSession] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [remaining, setRemaining] = useState(0);
  const answersRef = useRef({});
  const answerRef = useRef("");
  const enteredAtRef = useRef(Date.now());
  const submittingRef = useRef(false);

  const load = useCallback(async () => {
    setStatus("loading");
    setError("");
    try {
      const data = await fetchSession(sessionId);
      setSession(data);
      setRemaining(secondsRemaining(data.expires_at));
      enteredAtRef.current = Date.now();
      setStatus("ready");
    } catch (e) {
      setError(e?.message || "Could not load this Calculation Gym session.");
      setStatus("error");
    }
  }, [fetchSession, sessionId]);

  useEffect(() => { load(); }, [load]);

  const snapshotCurrent = useCallback(() => {
    const item = session?.items?.[currentIndex];
    if (!item) return;
    const prior = answersRef.current[item.item_index] || { time_spent_sec: 0 };
    const elapsed = Math.max(0, Math.round((Date.now() - enteredAtRef.current) / 1000));
    answersRef.current[item.item_index] = {
      item_index: item.item_index,
      user_answer: answerRef.current.trim() || null,
      time_spent_sec: prior.time_spent_sec + elapsed,
    };
    enteredAtRef.current = Date.now();
  }, [currentIndex, session]);

  const finish = useCallback(async () => {
    if (submittingRef.current || session?.status !== "in_progress") return;
    submittingRef.current = true;
    snapshotCurrent();
    const answers = Object.values(answersRef.current).sort(
      (a, b) => a.item_index - b.item_index,
    );
    const result = await submitSession(sessionId, answers);
    if (result?.ok) await load();
    submittingRef.current = false;
  }, [load, session?.status, sessionId, snapshotCurrent, submitSession]);

  useEffect(() => {
    if (status !== "ready" || session?.status !== "in_progress") return undefined;
    const tick = window.setInterval(() => {
      const next = secondsRemaining(session.expires_at);
      setRemaining(next);
      if (next === 0) {
        // The database rejects late submission by contract. Withdraw the form at
        // the authoritative deadline instead of repeatedly posting a doomed submit.
        setSession((prev) => ({ ...prev, status: "expired" }));
      }
    }, 1000);
    return () => window.clearInterval(tick);
  }, [session?.expires_at, session?.status, status]);

  const moveNext = () => {
    snapshotCurrent();
    if (currentIndex >= (session?.items?.length || 1) - 1) {
      finish();
      return;
    }
    const nextIndex = currentIndex + 1;
    const nextItem = session.items[nextIndex];
    const nextAnswer = answersRef.current[nextItem.item_index]?.user_answer || "";
    answerRef.current = nextAnswer;
    setAnswer(nextAnswer);
    setCurrentIndex(nextIndex);
    enteredAtRef.current = Date.now();
  };

  const onAnswer = (value) => {
    answerRef.current = value;
    setAnswer(value);
  };

  if (status === "loading") {
    return <div className="p-6" role="status">Loading Calculation Gym…</div>;
  }
  if (status === "error") {
    return <div className="p-6"><ErrorState message={error} onRetry={load} /></div>;
  }

  const submitted = session?.status === "submitted";
  const expired = session?.status === "expired";
  const items = session?.items || [];
  const current = items[currentIndex];

  return (
    <div className="mx-auto max-w-2xl p-4" data-testid="calculation-gym-shell">
      <PageHeader
        eyebrow="Quantitative Aptitude"
        title="Calculation Gym"
        sub={submitted
          ? `Score ${session.score_correct ?? 0}/${session.score_total ?? items.length}`
          : expired
            ? "This timed session has expired"
            : `${currentIndex + 1}/${items.length} · ${formatClock(remaining)} remaining`}
      />

      <Link className="text-sm text-emerald-700 underline" to="/app/study/subjects">
        Back to Subject practice hub
      </Link>

      {submitted ? (
        <div className="mt-4 space-y-3" aria-live="polite" data-testid="calc-gym-result">
          <StudyCard>
            <p className="font-medium">Session complete</p>
            <p className="text-sm text-slate-600">
              {session.score_correct ?? 0} correct out of {session.score_total ?? items.length}
            </p>
          </StudyCard>
          {items.map((item, index) => (
            <StudyCard key={item.item_index}>
              <p className="text-sm font-medium">{index + 1}. {item.prompt}</p>
              <p className="mt-1 text-sm">
                {item.is_correct ? "Correct" : "Incorrect"} · Your answer: {item.user_answer || "Not answered"}
              </p>
              {!item.is_correct ? (
                <p className="text-sm text-emerald-800">Correct answer: {item.expected_answer}</p>
              ) : null}
            </StudyCard>
          ))}
        </div>
      ) : expired ? (
        <StudyCard className="mt-4">
          <p role="status">Time is up. Start a new session from the Subject practice hub.</p>
        </StudyCard>
      ) : current ? (
        <StudyCard className="mt-4">
          <div className="flex items-center justify-between text-sm text-slate-500">
            <span>Question {currentIndex + 1} of {items.length}</span>
            <span aria-label={`${remaining} seconds remaining`}>{formatClock(remaining)}</span>
          </div>
          <p className="my-8 text-center text-4xl font-semibold" data-testid="calc-gym-prompt">
            {current.prompt}
          </p>
          <form
            onSubmit={(event) => { event.preventDefault(); moveNext(); }}
            className="space-y-3"
          >
            <label htmlFor="calc-gym-answer" className="block text-sm font-medium">
              Your answer
            </label>
            <input
              id="calc-gym-answer"
              autoFocus
              autoComplete="off"
              inputMode="decimal"
              value={answer}
              onChange={(event) => onAnswer(event.target.value)}
              disabled={busy}
              className="w-full rounded border border-slate-300 px-3 py-2 text-lg"
            />
            <button type="submit" className="btn btn-primary w-full" disabled={busy}>
              {currentIndex === items.length - 1 ? "Submit session" : "Next"}
            </button>
          </form>
        </StudyCard>
      ) : null}
    </div>
  );
}
