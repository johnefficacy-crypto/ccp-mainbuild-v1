import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api";
import { supabase } from "../../../lib/supabase";
import { BACKEND_URL } from "../../../shared/config/env";
import { eventBus } from "./attemptEventBus";
import useAnswerSync, { SYNC } from "./useAnswerSync";
import AnswerSyncIndicator from "./AnswerSyncIndicator";
import QuestionStem from "./components/questions/shared/QuestionStem";
import QuestionStimuli from "./components/questions/shared/QuestionStimuli";
import { getAttemptReturnContext } from "./attemptReturnContext";
import { resolveOptionLabel } from "./optionLabels";

const DEBOUNCE_MS = 600;
const MOCK_ATTEMPT_API_BASE = `${BACKEND_URL.replace(/\/+$/, "")}/api/study/mocks/attempts`;

function formatTime(sec) {
  if (sec <= 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function MockAttemptShell() {
  const { attemptId } = useParams();
  const navigate = useNavigate();

  const [attempt, setAttempt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [currentSection, setCurrentSection] = useState(0);
  const [responses, setResponses] = useState({});
  const [timeRemaining, setTimeRemaining] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [failedModalOpen, setFailedModalOpen] = useState(false);
  // Right-side question navigator is always visible on desktop; on small screens
  // it collapses to a bottom sheet toggled by this flag.
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Source-aware back link (e.g. "Back to UPSC CSE PYQs") when the attempt was
  // launched from an exam's PYQ Explorer. Null for attempts with no stored source.
  const returnCtx = useMemo(() => getAttemptReturnContext(attemptId), [attemptId]);

  // ── per-question dwell tracking ────────────────────────────────────────────
  // Accumulated seconds spent on each question (survives revisits) + the wall
  // clock at which the current question became visible. Flushed into the answer
  // payload's `time_spent_sec` on every question change / select / mark / submit
  // so the result's time analytics are real instead of a constant 0.
  const dwellRef = useRef({});
  const enteredAtRef = useRef(Date.now());

  const timerRef = useRef(null);
  const autoSubmitFired = useRef(false);
  const timeRemainingRef = useRef(null);

  // ── answer sync (data-loss prevention) ─────────────────────────────────────
  const postAnswer = useCallback(
    (payload) => api.post(`/api/study/mocks/attempts/${attemptId}/answer`, payload),
    [attemptId],
  );
  const emitSyncEvent = useCallback((type, payload) => {
    try {
      eventBus.enqueue(type, payload);
    } catch (e) {
      console.warn("[Shell] sync event enqueue error:", e);
    }
  }, []);
  const answerSync = useAnswerSync({ postAnswer, onEvent: emitSyncEvent, debounceMs: DEBOUNCE_MS });

  // ── event bus init/teardown ────────────────────────────────────────────────
  useEffect(() => {
    if (!attemptId) return;
    try {
      eventBus.init({
        attemptId,
        apiBase: MOCK_ATTEMPT_API_BASE,
        getAuthToken: async () => {
          try {
            const { data } = await supabase.auth.getSession();
            return data?.session?.access_token || null;
          } catch {
            return null;
          }
        },
        getClientRemaining: () => timeRemainingRef.current,
        getServerRemaining: () => null,  // PR3 will supply server-side value
      });
    } catch (e) {
      console.warn("[Shell] eventBus.init error:", e);
    }
    return () => {
      try { eventBus.destroy(); } catch (e) { console.warn("[Shell] eventBus.destroy error:", e); }
    };
  }, [attemptId]);

  // ── load attempt on mount ──────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api.get(`/api/study/mocks/attempts/${attemptId}`);
        if (cancelled) return;
        setAttempt(data);
        setTimeRemaining(data.time_remaining_sec ?? null);
        setCurrentSection(Number(data.current_section_index || 0));

        const initial = {};
        for (const q of data.questions || []) {
          initial[q.question_id] = {
            selected_option_id: q.selected_option_id || null,
            is_marked_for_review: q.is_marked_for_review || false,
          };
        }
        setResponses(initial);
        // Start the dwell clock for question 1 once the attempt is on screen.
        enteredAtRef.current = Date.now();
      } catch (e) {
        if (!cancelled) setError(e?.message || "Could not load attempt.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [attemptId]);

  // Keep ref in sync so eventBus heartbeat can read without a closure over stale state.
  useEffect(() => { timeRemainingRef.current = timeRemaining; }, [timeRemaining]);

  // ── countdown ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (timeRemaining === null) return;
    if (timerRef.current) clearInterval(timerRef.current);

    timerRef.current = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev === null) return null;
        const next = prev - 1;
        if (next <= 0 && !autoSubmitFired.current) {
          autoSubmitFired.current = true;
          clearInterval(timerRef.current);
          doSubmit(true);
        }
        return Math.max(0, next);
      });
    }, 1000);

    return () => clearInterval(timerRef.current);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeRemaining === null ? "null" : "ready"]);

  // ── track current question in event bus ──────────────────────────────────
  // IMPORTANT: these two concerns are merged into one effect so that when the
  // attempt first loads (currentIdx=0, attempt goes from null→object) we both
  // populate questions_ref AND emit question.visited for index 0.  With two
  // separate effects the visit effect fired on mount when questions_ref was
  // still empty, and never re-fired once the attempt loaded because currentIdx
  // hadn't changed.
  const questions_ref = useRef([]);
  useEffect(() => {
    if (attempt) questions_ref.current = attempt.questions || [];
    try {
      const qid = questions_ref.current[currentIdx]?.question_id || null;
      eventBus.setCurrentQuestionId(qid);
      if (qid) eventBus.enqueue("question.visited", { question_id: qid });
    } catch (e) {
      console.warn("[Shell] question visit enqueue error:", e);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIdx, attempt]);

  // ── warn (don't block) on leave while answers are not yet saved ───────────
  useEffect(() => {
    if (!answerSync.hasUnsynced) return undefined;
    const handler = (e) => {
      e.preventDefault();
      e.returnValue = "";
      return "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [answerSync.hasUnsynced]);

  // Once every failed answer recovers, drop the blocking modal automatically.
  useEffect(() => {
    if (answerSync.failedCount === 0) setFailedModalOpen(false);
  }, [answerSync.failedCount]);

  // ── send answer to server (debounced, with visible sync state) ────────────
  const sendAnswer = useCallback(
    (questionId, selected_option_id, is_marked_for_review, time_spent_sec = 0) => {
      answerSync.queueSave(questionId, {
        question_id: questionId,
        selected_option_id: selected_option_id || null,
        is_marked_for_review,
        time_spent_sec,
      });
    },
    [answerSync],
  );

  // Accrue the time spent on the currently-visible question into dwellRef and
  // reset the clock. Returns the running dwell total (seconds) for that question
  // so the caller can send it on the answer payload.
  const accrueDwell = useCallback(
    (questionId) => {
      if (!questionId) return 0;
      const now = Date.now();
      const elapsed = Math.max(0, Math.round((now - enteredAtRef.current) / 1000));
      enteredAtRef.current = now;
      dwellRef.current[questionId] = (dwellRef.current[questionId] || 0) + elapsed;
      return dwellRef.current[questionId];
    },
    [],
  );

  // Persist the current question's accrued dwell (used on navigation / submit so
  // read-time on a question is captured even when the answer itself is unchanged).
  const flushDwellForCurrent = useCallback(() => {
    const qs = attempt?.questions || [];
    const cq = qs[currentIdx];
    if (!cq) return;
    const qid = cq.question_id;
    const total = accrueDwell(qid);
    const r = responses[qid] || {};
    sendAnswer(qid, r.selected_option_id || null, r.is_marked_for_review || false, total);
  }, [attempt, currentIdx, responses, accrueDwell, sendAnswer]);

  // ── handle option select ──────────────────────────────────────────────────
  function selectOption(questionId, optionId) {
    const dwell = accrueDwell(questionId);
    setResponses((prev) => {
      const cur = prev[questionId] || {};
      const updated = { ...cur, selected_option_id: optionId };
      sendAnswer(questionId, optionId, updated.is_marked_for_review || false, dwell);
      try {
        eventBus.enqueue("question.answered", {
          question_id: questionId,
          selected_option_id: optionId,
          time_spent_sec: dwell,
        });
      } catch (e) { console.warn("[Shell] enqueue error:", e); }
      return { ...prev, [questionId]: updated };
    });
  }

  function toggleReview(questionId) {
    const dwell = accrueDwell(questionId);
    setResponses((prev) => {
      const cur = prev[questionId] || {};
      const flipped = !cur.is_marked_for_review;
      const updated = { ...cur, is_marked_for_review: flipped };
      sendAnswer(questionId, cur.selected_option_id || null, flipped, dwell);
      try {
        const evType = flipped ? "question.marked" : "question.unmarked";
        eventBus.enqueue(evType, { question_id: questionId });
      } catch (e) { console.warn("[Shell] enqueue error:", e); }
      return { ...prev, [questionId]: updated };
    });
  }

  // Central "go to question index" — flushes the leaving question's dwell first,
  // then moves. Every navigation path (palette, prev, keyboard) routes through
  // this so dwell is captured on every question change.
  const goToIdx = useCallback(
    (i) => {
      const qs = attempt?.questions || [];
      if (i < 0 || i >= qs.length || i === currentIdx) return;
      flushDwellForCurrent();
      setCurrentIdx(i);
      setPaletteOpen(false);
    },
    [attempt, currentIdx, flushDwellForCurrent],
  );

  // ── keyboard shortcuts ─────────────────────────────────────────────────────
  // Bound once; reads the latest handlers/state through a ref so there are no
  // stale closures and no per-render re-binding. Ignores keys while typing in a
  // form field. See the shortcut map in the PR body.
  const kbdRef = useRef({});
  kbdRef.current = {
    attempt, currentIdx, currentSection,
    confirmOpen, failedModalOpen, paletteOpen,
    failedCount: answerSync.failedCount,
    saveAndNext, goToIdx, toggleReview, selectOption,
  };
  useEffect(() => {
    function onKey(e) {
      const h = kbdRef.current;
      const t = e.target;
      const tag = (t?.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select" || t?.isContentEditable) return;
      const a = h.attempt;
      if (!a || a.status === "submitted") return;

      if (e.key === "Escape") {
        if (h.confirmOpen) setConfirmOpen(false);
        else if (h.failedModalOpen) setFailedModalOpen(false);
        else if (h.paletteOpen) setPaletteOpen(false);
        return;
      }
      // Don't hijack shortcuts while a blocking dialog is open.
      if (h.confirmOpen || h.failedModalOpen) return;

      const qs = a.questions || [];
      const cq = qs[h.currentIdx];
      const locked = Boolean(a.section_locks_enabled) || a.template_config?.allow_switching === false;

      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (h.failedCount > 0) setFailedModalOpen(true);
        else setConfirmOpen(true);
        return;
      }
      if (e.key === "ArrowRight" || e.key === "j" || e.key === "J") {
        e.preventDefault();
        if (h.currentIdx < qs.length - 1) h.saveAndNext();
        return;
      }
      if (e.key === "ArrowLeft" || e.key === "k" || e.key === "K") {
        e.preventDefault();
        const prevOk =
          h.currentIdx > 0 &&
          !(locked && Number(qs[h.currentIdx - 1]?.section_index || 0) !== h.currentSection);
        if (prevOk) h.goToIdx(h.currentIdx - 1);
        return;
      }
      if ((e.key === "m" || e.key === "M") && cq) {
        e.preventDefault();
        h.toggleReview(cq.question_id);
        return;
      }
      if (/^[1-6]$/.test(e.key) && cq) {
        const opt = (cq.options || [])[Number(e.key) - 1];
        if (opt) {
          e.preventDefault();
          h.selectOption(cq.question_id, opt.id);
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // ── section-aware advance ────────────────────────────────────────────────
  // "Save & Next" moves to the next question. When the next question lives in
  // a later section we tell the server we are entering it (POST /enter-section)
  // before moving; with locks on, the server then refuses backward moves and
  // we mirror that in the palette below.
  async function saveAndNext() {
    const all = attempt?.questions || [];
    const nextIdx = currentIdx + 1;
    if (nextIdx >= all.length) return;
    // Capture dwell on the leaving question before any section flush/advance.
    flushDwellForCurrent();
    const nextSection = Number(all[nextIdx]?.section_index || 0);
    if (nextSection !== currentSection) {
      // Drain every pending debounce in the current section before moving the
      // section pointer. A save for section N that fires after enter-section(N+1)
      // is rejected by the server as out-of-section (422 → non-retryable failed),
      // which would wrongly block submit. Flushing all section-N questions while
      // current_section_index is still N ensures they land cleanly.
      const currentSectionQids = all
        .filter((q) => Number(q.section_index || 0) === currentSection)
        .map((q) => q.question_id);
      await answerSync.flushMany(currentSectionQids);
      // Advance both section and question index before awaiting enter-section so
      // the UI shows the first question of the new section immediately. If the
      // index update happened after the await, the old (section-N) question would
      // remain visible until enter-section responded; the test (and a fast user)
      // could re-answer that question with the wrong section_index on the server,
      // causing a 422 → SYNC.FAILED that blocks submit.
      setCurrentSection(nextSection);
      setCurrentIdx(nextIdx);
      try {
        await api.post(`/api/study/mocks/attempts/${attemptId}/enter-section`, {
          section_index: nextSection,
        });
      } catch {
        // server stays authoritative; a failed enter-section just means the
        // next answer in that section may be rejected — surfaced on save.
      }
      return;
    }
    setCurrentIdx(nextIdx);
  }

  // ── submit ────────────────────────────────────────────────────────────────
  async function doSubmit(isAuto = false) {
    if (submitting) return;
    setSubmitting(true);
    clearInterval(timerRef.current);
    try {
      // Capture the final question's dwell and let its save reach a terminal
      // state before /submit computes analytics from the persisted responses.
      const currentQid = (attempt?.questions || [])[currentIdx]?.question_id;
      flushDwellForCurrent();
      if (currentQid) {
        try { await answerSync.flush(currentQid); } catch { /* best-effort */ }
      }
      const { syncStates } = answerSync;
      const answeredCount = Object.entries(syncStates).filter(
        ([, e]) => e?.state === "saved" && responses[e?.question_id]?.selected_option_id != null
      ).length;
      // Deliver buffered telemetry (the final question.visited / answered events)
      // and wait for the server ACK BEFORE /submit triggers compute_and_persist(),
      // so the persisted classifications/dwell reflect them. Time-bounded
      // best-effort — telemetry must never block the user's submit; if the flush
      // does not fully drain, the durable queue replays and the server recomputes
      // analytics on the late /events, so the snapshot still converges.
      try {
        eventBus.markSubmitFlush();  // final-sequence marker for trailing-loss detection
        const flushed = await eventBus.flushAndWait({ timeoutMs: 4000 });
        if (!flushed) {
          console.warn("[Shell] pre-submit flush incomplete; relying on durable replay + server recompute");
        }
      } catch (e) {
        console.warn("[Shell] pre-submit event flush error:", e);
      }
      await api.post(`/api/study/mocks/attempts/${attemptId}/submit`, {
        claimed_answered_count: answeredCount || null,
      });
      navigate(`/app/study/mocks/attempts/${attemptId}/result`, { replace: true });
    } catch (e) {
      if (e?.status === 409) {
        alert("Some answers didn't save. Refreshing to show current state.");
        window.location.reload();
        return;
      }
      if (!isAuto) alert(e?.message || "Submission failed. Please try again.");
      setSubmitting(false);
    }
  }

  // ── render ────────────────────────────────────────────────────────────────
  if (loading) {
    return <div style={styles.center}>Loading attempt…</div>;
  }
  if (error) {
    return <div style={styles.center}>Error: {error}</div>;
  }
  if (!attempt || attempt.status === "submitted") {
    navigate(`/app/study/mocks/attempts/${attemptId}/result`, { replace: true });
    return null;
  }

  const questions = attempt.questions || [];
  const q = questions[currentIdx];
  const resp = responses[q?.question_id] || {};
  const answered = Object.values(responses).filter((r) => r.selected_option_id).length;
  const total = questions.length;

  const sectionLocked =
    Boolean(attempt.section_locks_enabled) || attempt.template_config?.allow_switching === false;
  const sectionIndices = [...new Set(questions.map((qq) => Number(qq.section_index || 0)))].sort(
    (a, b) => a - b,
  );
  const sectionCount = sectionIndices.length || 1;
  const isLastQuestion = currentIdx === total - 1;

  const { pendingCount, failedCount } = answerSync;
  const submitDisabled = submitting || pendingCount > 0;
  const submitTooltip = pendingCount > 0 ? `Waiting for ${pendingCount} answer${pendingCount === 1 ? "" : "s"} to save` : undefined;
  const onSubmitClick = () => {
    if (failedCount > 0) {
      setFailedModalOpen(true);
      return;
    }
    setConfirmOpen(true);
  };

  const paletteButtons = questions.map((qq, i) => {
    const r = responses[qq.question_id] || {};
    const isAnswered = Boolean(r.selected_option_id);
    const isMarked = r.is_marked_for_review;
    const isCurrent = i === currentIdx;
    // With locks on, the palette only lets you move within the section you're
    // currently in — earlier sections are sealed, later ones not yet entered.
    const outOfSection = Number(qq.section_index || 0) !== currentSection;
    const disabled = sectionLocked && outOfSection;
    const syncState = answerSync.syncStates[qq.question_id]?.state;
    const isFailed = syncState === SYNC.FAILED;
    const isSyncing = syncState === SYNC.SAVING || syncState === SYNC.RETRYING;
    let border = isMarked ? "2px solid #f59e0b" : "2px solid transparent";
    if (isFailed) border = "2px solid #ef4444";
    return (
      <button
        key={qq.question_id}
        data-testid={`attempt-nav-${i}`}
        data-section={Number(qq.section_index || 0)}
        data-sync={syncState || "none"}
        className={isSyncing ? "attempt-sync-pulse" : undefined}
        disabled={disabled}
        aria-disabled={disabled}
        aria-label={`Question ${i + 1}`}
        onClick={() => {
          if (disabled) return;
          goToIdx(i);
        }}
        style={{
          ...styles.navBtn,
          position: "relative",
          background: isCurrent ? "#1a56db" : isAnswered ? "#16a34a" : "#374151",
          border,
          opacity: disabled ? 0.4 : 1,
          cursor: disabled ? "not-allowed" : "pointer",
        }}
      >
        {i + 1}
        {isFailed && <span style={styles.navWarn} aria-hidden="true">!</span>}
      </button>
    );
  });

  return (
    <div style={styles.shell}>
      <style>{ATTEMPT_STYLES}</style>
      {/* Header */}
      <div style={styles.header} data-testid="attempt-shell">
        <span style={styles.title}>{attempt.template_name || "Mock Test"}</span>
        {sectionCount > 1 && (
          <span style={styles.sectionLabel} data-testid="attempt-section-label">
            Section {currentSection + 1} of {sectionCount}
            {sectionLocked ? " · locked" : ""}
          </span>
        )}
        <span style={timeRemaining !== null && timeRemaining < 60 ? styles.timerWarn : styles.timer}>
          {timeRemaining !== null ? formatTime(timeRemaining) : "--"}
        </span>
        <button
          style={{ ...styles.submitBtn, opacity: submitDisabled ? 0.5 : 1, cursor: submitDisabled ? "not-allowed" : "pointer" }}
          data-testid="attempt-submit"
          onClick={onSubmitClick}
          disabled={submitDisabled}
          title={submitTooltip}
          aria-disabled={submitDisabled}
        >
          {submitting ? "Submitting…" : "Submit"}
        </button>
      </div>

      {/* Two-pane body: question on the left, sticky question navigator on the right */}
      <div className="attempt-body">
        <div className="attempt-main">
          {/* Scrollable question canvas — the stem/options scroll here so the
              footer action bar below stays fixed regardless of stem length. */}
          <div className="attempt-scroll">
          {returnCtx ? (
            <Link to={returnCtx.return_to} data-testid="attempt-back-source" style={styles.backLink}>
              ← {returnCtx.source_label}
            </Link>
          ) : null}

          {/* Question body */}
          {q && (
            <div style={styles.questionCard}>
              <div style={styles.qMetaRow}>
                <div style={styles.qMeta}>
                  Q {currentIdx + 1} of {total} &nbsp;|&nbsp; {q.marks} mark
                  {q.negative_marks > 0 && ` | −${q.negative_marks} wrong`}
                </div>
                <AnswerSyncIndicator
                  entry={answerSync.syncStates[q.question_id]}
                  onRetry={() => answerSync.retryNow(q.question_id)}
                />
              </div>
              {/* Structured stem + shared passage/table stimuli so statement,
                  match-the-following, and list questions render legibly instead
                  of collapsing into one flat paragraph. */}
              <QuestionStimuli stimuli={q.stimuli} />
              <div style={styles.qText} data-testid="attempt-question-body">
                <QuestionStem text={q.question_text} images={q.images} />
              </div>
              <div style={styles.options}>
                {(q.options || []).map((opt, optIdx) => {
                  const selected = resp.selected_option_id === opt.id;
                  return (
                    <button
                      key={opt.id}
                      data-testid={`attempt-option-${optIdx}`}
                      aria-pressed={selected}
                      onClick={() => selectOption(q.question_id, opt.id)}
                      style={{
                        ...styles.optBtn,
                        background: selected ? "#1e40af" : "#1f2937",
                        border: selected ? "2px solid #60a5fa" : "2px solid #374151",
                      }}
                    >
                      <span style={styles.optIndex}>{resolveOptionLabel(opt, optIdx)}.</span>
                      {opt.option_text}
                    </button>
                  );
                })}
              </div>
              <label style={styles.reviewLabel}>
                <input
                  type="checkbox"
                  data-testid="attempt-mark-review"
                  checked={Boolean(resp.is_marked_for_review)}
                  onChange={() => toggleReview(q.question_id)}
                />
                &nbsp; Mark for review
              </label>
            </div>
          )}
          </div>

          {/* Sticky footer action bar — fixed at the bottom of the question pane
              so Prev / Save & Next never move with stem length. */}
          <div style={styles.navRow} className="attempt-footer" data-testid="attempt-footer">
            <button
              style={styles.navArrow}
              data-testid="attempt-prev"
              disabled={
                currentIdx === 0 ||
                (sectionLocked &&
                  Number(questions[currentIdx - 1]?.section_index || 0) !== currentSection)
              }
              onClick={() => goToIdx(currentIdx - 1)}
            >
              ← Prev
            </button>
            <span style={styles.progress}>
              {answered}/{total} answered
            </span>
            <button
              style={styles.navArrow}
              data-testid="attempt-save-next"
              disabled={isLastQuestion}
              onClick={saveAndNext}
            >
              Save &amp; Next →
            </button>
          </div>
        </div>

        {/* Right-side sticky question navigator (bottom sheet on mobile). */}
        <aside
          className={`attempt-aside${paletteOpen ? " open" : ""}`}
          data-testid="attempt-palette"
          aria-label="Question navigator"
        >
          <div style={styles.asideHead}>
            <span style={styles.asideTitle}>Questions · {answered}/{total}</span>
            <button
              type="button"
              className="attempt-aside-close"
              data-testid="attempt-palette-close"
              onClick={() => setPaletteOpen(false)}
              aria-label="Close question navigator"
              style={styles.asideClose}
            >
              ✕
            </button>
          </div>
          <div style={styles.paletteGrid}>{paletteButtons}</div>
        </aside>
      </div>

      {/* Mobile-only floating toggle for the question navigator. */}
      <button
        type="button"
        className="attempt-mobile-toggle"
        data-testid="attempt-palette-toggle"
        onClick={() => setPaletteOpen((v) => !v)}
        style={styles.mobileToggle}
      >
        Questions {answered}/{total}
      </button>

      {/* Confirm dialog */}
      {confirmOpen && (
        <div style={styles.overlay}>
          <div style={styles.dialog} role="dialog" aria-modal="true" data-testid="attempt-confirm-dialog">
            <h3 style={{ marginTop: 0 }}>Submit test?</h3>
            <p>
              {answered} of {total} questions answered.
              {total - answered > 0 && ` ${total - answered} unattempted.`}
            </p>
            <div style={styles.dialogActions}>
              <button
                style={styles.cancelBtn}
                data-testid="attempt-confirm-cancel"
                onClick={() => setConfirmOpen(false)}
              >
                Cancel
              </button>
              <button
                style={styles.confirmBtn}
                data-testid="attempt-confirm-submit"
                onClick={() => { setConfirmOpen(false); doSubmit(); }}
                disabled={submitting}
              >
                {submitting ? "Submitting…" : "Yes, submit"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Hard block: answers failed to save — cannot submit until resolved */}
      {failedModalOpen && (
        <div style={styles.overlay}>
          <div style={styles.dialog} role="dialog" aria-modal="true" data-testid="attempt-failed-modal">
            <h3 style={{ marginTop: 0, color: "#fecaca" }}>Cannot submit yet</h3>
            <p>
              {failedCount} answer{failedCount === 1 ? "" : "s"} failed to save. Retry or remove
              before submitting — submitting now would discard {failedCount === 1 ? "it" : "them"}.
            </p>
            <div style={styles.dialogActions}>
              <button
                style={styles.cancelBtn}
                data-testid="attempt-failed-modal-close"
                onClick={() => setFailedModalOpen(false)}
              >
                Back
              </button>
              <button
                style={styles.confirmBtn}
                data-testid="attempt-failed-modal-retry"
                onClick={() => answerSync.retryAllFailed()}
              >
                Retry {failedCount === 1 ? "answer" : "all"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const ATTEMPT_STYLES = `
@keyframes attempt-pulse { 0% { opacity: 1; } 50% { opacity: 0.35; } 100% { opacity: 1; } }
.attempt-sync-pulse { animation: attempt-pulse 1s ease-in-out infinite; }
.attempt-body { display: flex; flex: 1; align-items: stretch; min-height: 0; }
.attempt-main { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; }
.attempt-scroll { flex: 1; min-height: 0; overflow-y: auto; }
.attempt-aside { width: 236px; flex-shrink: 0; background: #1f2937; border-left: 1px solid #374151; padding: 14px; position: sticky; top: 0; align-self: flex-start; max-height: 100vh; overflow-y: auto; }
.attempt-aside-close { display: none; }
.attempt-mobile-toggle { display: none; }
@media (max-width: 768px) {
  .attempt-aside { position: fixed; left: 0; right: 0; bottom: 0; top: auto; width: 100%; max-height: 60vh; border-left: none; border-top: 1px solid #374151; z-index: 90; transform: translateY(105%); transition: transform 0.22s ease; }
  .attempt-aside.open { transform: translateY(0); }
  .attempt-aside-close { display: inline-flex; }
  .attempt-mobile-toggle { display: inline-flex; position: fixed; right: 16px; bottom: 16px; z-index: 80; }
}`;

const styles = {
  shell: { height: "100vh", overflow: "hidden", background: "#111827", color: "#f9fafb", display: "flex", flexDirection: "column" },
  center: { textAlign: "center", marginTop: 80, color: "#9ca3af" },
  header: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 20px", background: "#1f2937", borderBottom: "1px solid #374151" },
  title: { fontWeight: 600, fontSize: 16, color: "#f9fafb" },
  sectionLabel: { fontSize: 13, fontWeight: 600, color: "#fbbf24", letterSpacing: "0.02em" },
  timer: { fontVariantNumeric: "tabular-nums", fontSize: 18, fontWeight: 700, color: "#60a5fa" },
  timerWarn: { fontVariantNumeric: "tabular-nums", fontSize: 18, fontWeight: 700, color: "#ef4444" },
  submitBtn: { padding: "6px 18px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 },
  backLink: { display: "inline-flex", alignItems: "center", gap: 6, padding: "12px 24px 0", fontSize: 13, color: "#93c5fd", textDecoration: "none" },
  asideHead: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 },
  asideTitle: { fontSize: 12, fontWeight: 600, color: "#9ca3af", letterSpacing: "0.02em" },
  asideClose: { background: "transparent", border: "none", color: "#9ca3af", fontSize: 16, cursor: "pointer" },
  paletteGrid: { display: "flex", flexWrap: "wrap", gap: 6 },
  mobileToggle: { padding: "10px 16px", background: "#1a56db", color: "#fff", border: "none", borderRadius: 999, cursor: "pointer", fontWeight: 600, fontSize: 13, boxShadow: "0 4px 12px rgba(0,0,0,0.4)" },
  navBtn: { width: 34, height: 34, borderRadius: 4, color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600 },
  navWarn: { position: "absolute", top: -6, right: -6, width: 14, height: 14, lineHeight: "14px", textAlign: "center", borderRadius: "50%", background: "#ef4444", color: "#fff", fontSize: 10, fontWeight: 800 },
  // Exam canvas: stem top-left, comfortable measure, not floated in a narrow
  // centered column (item 4).
  questionCard: { padding: "20px 28px 12px", maxWidth: 900, margin: 0, width: "100%", textAlign: "left" },
  qMetaRow: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 10 },
  qMeta: { fontSize: 13, color: "#6b7280" },
  qText: { fontSize: 17, lineHeight: 1.6, marginBottom: 20, color: "#f3f4f6" },
  options: { display: "flex", flexDirection: "column", gap: 10 },
  optBtn: { padding: "12px 16px", borderRadius: 8, color: "#f9fafb", cursor: "pointer", textAlign: "left", fontSize: 15, display: "flex", gap: 10, alignItems: "flex-start" },
  optIndex: { fontWeight: 700, minWidth: 20, color: "#9ca3af" },
  reviewLabel: { marginTop: 16, fontSize: 14, color: "#9ca3af", cursor: "pointer", display: "flex", alignItems: "center" },
  navRow: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 24px", borderTop: "1px solid #374151", background: "#1f2937" },
  navArrow: { padding: "8px 18px", background: "#374151", color: "#f9fafb", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 14 },
  progress: { fontSize: 14, color: "#9ca3af" },
  overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 },
  dialog: { background: "#1f2937", padding: 28, borderRadius: 12, maxWidth: 400, width: "90%", color: "#f9fafb" },
  dialogActions: { display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 20 },
  cancelBtn: { padding: "8px 18px", background: "#374151", color: "#f9fafb", border: "none", borderRadius: 6, cursor: "pointer" },
  confirmBtn: { padding: "8px 18px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 },
};
