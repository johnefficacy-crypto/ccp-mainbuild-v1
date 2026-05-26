import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api";

const DEBOUNCE_MS = 600;

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
  const [responses, setResponses] = useState({});
  const [timeRemaining, setTimeRemaining] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const clientSeq = useRef(0);
  const debounceTimer = useRef(null);
  const timerRef = useRef(null);
  const autoSubmitFired = useRef(false);

  // ── load attempt on mount ──────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api.get(`/study/mocks/attempts/${attemptId}`);
        if (cancelled) return;
        setAttempt(data);
        setTimeRemaining(data.time_remaining_sec ?? null);

        const initial = {};
        for (const q of data.questions || []) {
          initial[q.question_id] = {
            selected_option_id: q.selected_option_id || null,
            is_marked_for_review: q.is_marked_for_review || false,
          };
        }
        setResponses(initial);
      } catch (e) {
        if (!cancelled) setError(e?.message || "Could not load attempt.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [attemptId]);

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

  // ── send answer to server (debounced) ────────────────────────────────────
  const sendAnswer = useCallback(
    (questionId, selected_option_id, is_marked_for_review, time_spent_sec = 0) => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(async () => {
        const seq = ++clientSeq.current;
        try {
          await api.post(`/study/mocks/attempts/${attemptId}/answer`, {
            question_id: questionId,
            selected_option_id: selected_option_id || null,
            is_marked_for_review,
            client_seq: seq,
            time_spent_sec,
          });
        } catch {
          // silent — user can still navigate; next answer will include the change
        }
      }, DEBOUNCE_MS);
    },
    [attemptId],
  );

  // ── handle option select ──────────────────────────────────────────────────
  function selectOption(questionId, optionId) {
    setResponses((prev) => {
      const cur = prev[questionId] || {};
      const updated = { ...cur, selected_option_id: optionId };
      sendAnswer(questionId, optionId, updated.is_marked_for_review || false);
      return { ...prev, [questionId]: updated };
    });
  }

  function toggleReview(questionId) {
    setResponses((prev) => {
      const cur = prev[questionId] || {};
      const flipped = !cur.is_marked_for_review;
      const updated = { ...cur, is_marked_for_review: flipped };
      sendAnswer(questionId, cur.selected_option_id || null, flipped);
      return { ...prev, [questionId]: updated };
    });
  }

  // ── submit ────────────────────────────────────────────────────────────────
  async function doSubmit(isAuto = false) {
    if (submitting) return;
    setSubmitting(true);
    clearInterval(timerRef.current);
    try {
      await api.post(`/study/mocks/attempts/${attemptId}/submit`, {});
      navigate(`/app/study/mocks/attempts/${attemptId}/result`, { replace: true });
    } catch (e) {
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

  return (
    <div style={styles.shell}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.title}>{attempt.template_name || "Mock Test"}</span>
        <span style={timeRemaining !== null && timeRemaining < 60 ? styles.timerWarn : styles.timer}>
          {timeRemaining !== null ? formatTime(timeRemaining) : "--"}
        </span>
        <button style={styles.submitBtn} onClick={() => setConfirmOpen(true)} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit"}
        </button>
      </div>

      {/* Question nav strip */}
      <div style={styles.navStrip}>
        {questions.map((qq, i) => {
          const r = responses[qq.question_id] || {};
          const isAnswered = Boolean(r.selected_option_id);
          const isMarked = r.is_marked_for_review;
          const isCurrent = i === currentIdx;
          return (
            <button
              key={qq.question_id}
              onClick={() => setCurrentIdx(i)}
              style={{
                ...styles.navBtn,
                background: isCurrent ? "#1a56db" : isAnswered ? "#16a34a" : "#374151",
                border: isMarked ? "2px solid #f59e0b" : "2px solid transparent",
              }}
            >
              {i + 1}
            </button>
          );
        })}
      </div>

      {/* Question body */}
      {q && (
        <div style={styles.questionCard}>
          <div style={styles.qMeta}>
            Q {currentIdx + 1} of {total} &nbsp;|&nbsp; {q.marks} mark
            {q.negative_marks > 0 && ` | −${q.negative_marks} wrong`}
          </div>
          <p style={styles.qText}>{q.question_text}</p>
          <div style={styles.options}>
            {(q.options || []).map((opt) => {
              const selected = resp.selected_option_id === opt.id;
              return (
                <button
                  key={opt.id}
                  onClick={() => selectOption(q.question_id, opt.id)}
                  style={{
                    ...styles.optBtn,
                    background: selected ? "#1e40af" : "#1f2937",
                    border: selected ? "2px solid #60a5fa" : "2px solid #374151",
                  }}
                >
                  <span style={styles.optIndex}>{opt.option_index}.</span>
                  {opt.option_text}
                </button>
              );
            })}
          </div>
          <label style={styles.reviewLabel}>
            <input
              type="checkbox"
              checked={Boolean(resp.is_marked_for_review)}
              onChange={() => toggleReview(q.question_id)}
            />
            &nbsp; Mark for review
          </label>
        </div>
      )}

      {/* Prev / Next */}
      <div style={styles.navRow}>
        <button
          style={styles.navArrow}
          disabled={currentIdx === 0}
          onClick={() => setCurrentIdx((i) => i - 1)}
        >
          ← Prev
        </button>
        <span style={styles.progress}>
          {answered}/{total} answered
        </span>
        <button
          style={styles.navArrow}
          disabled={currentIdx === questions.length - 1}
          onClick={() => setCurrentIdx((i) => i + 1)}
        >
          Next →
        </button>
      </div>

      {/* Confirm dialog */}
      {confirmOpen && (
        <div style={styles.overlay}>
          <div style={styles.dialog}>
            <h3 style={{ marginTop: 0 }}>Submit test?</h3>
            <p>
              {answered} of {total} questions answered.
              {total - answered > 0 && ` ${total - answered} unattempted.`}
            </p>
            <div style={styles.dialogActions}>
              <button style={styles.cancelBtn} onClick={() => setConfirmOpen(false)}>
                Cancel
              </button>
              <button
                style={styles.confirmBtn}
                onClick={() => { setConfirmOpen(false); doSubmit(); }}
                disabled={submitting}
              >
                {submitting ? "Submitting…" : "Yes, submit"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  shell: { minHeight: "100vh", background: "#111827", color: "#f9fafb", display: "flex", flexDirection: "column" },
  center: { textAlign: "center", marginTop: 80, color: "#9ca3af" },
  header: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 20px", background: "#1f2937", borderBottom: "1px solid #374151" },
  title: { fontWeight: 600, fontSize: 16, color: "#f9fafb" },
  timer: { fontVariantNumeric: "tabular-nums", fontSize: 18, fontWeight: 700, color: "#60a5fa" },
  timerWarn: { fontVariantNumeric: "tabular-nums", fontSize: 18, fontWeight: 700, color: "#ef4444" },
  submitBtn: { padding: "6px 18px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 },
  navStrip: { display: "flex", flexWrap: "wrap", gap: 6, padding: "10px 16px", background: "#1f2937", borderBottom: "1px solid #374151" },
  navBtn: { width: 34, height: 34, borderRadius: 4, color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600 },
  questionCard: { flex: 1, padding: "24px 24px 8px", maxWidth: 760, margin: "0 auto", width: "100%" },
  qMeta: { fontSize: 13, color: "#6b7280", marginBottom: 10 },
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
