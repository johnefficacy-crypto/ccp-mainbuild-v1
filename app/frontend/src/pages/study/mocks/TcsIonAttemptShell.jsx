import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api";
import useAnswerSync from "./useAnswerSync";
import AnswerSyncIndicator from "./AnswerSyncIndicator";
import {
  AntiCheatProvider,
  QuestionPalette,
  SectionLockGuard,
  SectionTimer,
  SubmitConfirmDialog,
} from "./components/shell";

export default function TcsIonAttemptShell() {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(null);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [failedModalOpen, setFailedModalOpen] = useState(false);
  const [violationCount, setViolationCount] = useState(0);
  const [responses, setResponses] = useState({});

  const postAnswer = useCallback(
    (payload) => api.post(`/api/study/mocks/attempts/${attemptId}/answer`, payload),
    [attemptId],
  );
  const answerSync = useAnswerSync({ postAnswer });

  useEffect(() => {
    (async () => {
      const data = await api.get(`/api/study/mocks/attempts/${attemptId}`);
      setAttempt(data);
      setCurrentIdx(Math.max(0, Number(data.current_question_index || 0)));
      const initial = {};
      for (const qq of data.questions || []) {
        initial[qq.question_id] = { selected_option_id: qq.selected_option_id || null };
      }
      setResponses(initial);
    })();
  }, [attemptId]);

  // Warn (don't block) on leave while answers are still un-synced.
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

  useEffect(() => {
    if (answerSync.failedCount === 0) setFailedModalOpen(false);
  }, [answerSync.failedCount]);

  const config = attempt?.template_config || {};
  const sections = attempt?.sections || [];
  const currentSection = sections[attempt?.current_section_index || 0] || null;
  const q = (attempt?.questions || [])[currentIdx] || null;

  const paletteItems = useMemo(() => (attempt?.questions || []).map((qq, i) => ({
    id: qq.question_id,
    label: String(i + 1),
    status: (responses[qq.question_id]?.selected_option_id) ? "answered" : "not_visited",
    onClick: () => setCurrentIdx(i),
  })), [attempt, responses]);

  const selectOption = useCallback((questionId, optionId) => {
    setResponses((prev) => ({ ...prev, [questionId]: { ...prev[questionId], selected_option_id: optionId } }));
    answerSync.queueSave(questionId, {
      question_id: questionId,
      selected_option_id: optionId,
      is_marked_for_review: false,
      time_spent_sec: 0,
    });
  }, [answerSync]);

  const antiCheatPolicy = () => {
    const policy = config.anti_cheat_policy || "warn";
    const next = violationCount + 1;
    setViolationCount(next);
    if (policy === "strict" && next >= Number(config.anti_cheat_threshold || 3)) {
      api.post(`/api/study/mocks/attempts/${attemptId}/submit`, { reason: "anti_cheat_threshold" }).then(() => {
        navigate(`/app/study/mocks/attempts/${attemptId}/result`, { replace: true });
      });
    }
  };

  if (!attempt) return <div>Loading…</div>;

  const { pendingCount, failedCount } = answerSync;
  const submitDisabled = pendingCount > 0;
  const submitTooltip = pendingCount > 0
    ? `Waiting for ${pendingCount} answer${pendingCount === 1 ? "" : "s"} to save`
    : undefined;
  const onSubmitClick = () => {
    if (failedCount > 0) {
      setFailedModalOpen(true);
      return;
    }
    setConfirmOpen(true);
  };
  const resp = responses[q?.question_id] || {};

  return (
    <AntiCheatProvider enforceFullscreen={Boolean(config.tcs_ion_fullscreen)} blockCopy blockPaste onViolation={antiCheatPolicy}>
      <SectionLockGuard locked={config.allow_switching === false}>
        <SectionTimer expiresAt={currentSection?.expires_at} onExpire={() => api.post(`/api/study/mocks/attempts/${attemptId}/enter-section`, {})} />
        <QuestionPalette items={paletteItems} />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <div data-testid="tcs-question">{q?.question_text || "No question"}</div>
          <AnswerSyncIndicator
            entry={answerSync.syncStates[q?.question_id]}
            onRetry={() => q && answerSync.retryNow(q.question_id)}
          />
        </div>
        <div>
          {(q?.options || []).map((opt, optIdx) => (
            <button
              key={opt.id}
              type="button"
              data-testid={`tcs-option-${optIdx}`}
              data-sync={answerSync.syncStates[q?.question_id]?.state || "none"}
              aria-pressed={resp.selected_option_id === opt.id}
              onClick={() => selectOption(q.question_id, opt.id)}
            >
              {opt.option_text}
            </button>
          ))}
        </div>
        <button data-testid="tcs-submit" onClick={onSubmitClick} disabled={submitDisabled} title={submitTooltip}>
          Submit
        </button>
        {failedModalOpen && (
          <div role="dialog" aria-modal="true" data-testid="tcs-failed-modal">
            <p>
              {failedCount} answer{failedCount === 1 ? "" : "s"} failed to save. Retry or remove before submitting.
            </p>
            <button data-testid="tcs-failed-modal-close" onClick={() => setFailedModalOpen(false)}>Back</button>
            <button data-testid="tcs-failed-modal-retry" onClick={() => answerSync.retryAllFailed()}>Retry all</button>
          </div>
        )}
        <SubmitConfirmDialog
          open={confirmOpen}
          summary={{ total: (attempt.questions || []).length }}
          onCancel={() => setConfirmOpen(false)}
          onConfirm={async () => {
            await api.post(`/api/study/mocks/attempts/${attemptId}/submit`, {});
            navigate(`/app/study/mocks/attempts/${attemptId}/result`, { replace: true });
          }}
        />
      </SectionLockGuard>
    </AntiCheatProvider>
  );
}
