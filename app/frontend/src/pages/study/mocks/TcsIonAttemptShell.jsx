import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api";
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
  const [violationCount, setViolationCount] = useState(0);

  useEffect(() => {
    (async () => {
      const data = await api.get(`/study/mocks/attempts/${attemptId}`);
      setAttempt(data);
      setCurrentIdx(Math.max(0, Number(data.current_question_index || 0)));
    })();
  }, [attemptId]);

  const config = attempt?.template_config || {};
  const sections = attempt?.sections || [];
  const currentSection = sections[attempt?.current_section_index || 0] || null;
  const q = (attempt?.questions || [])[currentIdx] || null;

  const paletteItems = useMemo(() => (attempt?.questions || []).map((qq, i) => ({
    id: qq.question_id,
    label: String(i + 1),
    status: qq.selected_option_id ? "answered" : "not_visited",
    onClick: () => setCurrentIdx(i),
  })), [attempt]);

  const antiCheatPolicy = () => {
    const policy = config.anti_cheat_policy || "warn";
    const next = violationCount + 1;
    setViolationCount(next);
    if (policy === "strict" && next >= Number(config.anti_cheat_threshold || 3)) {
      api.post(`/study/mocks/attempts/${attemptId}/submit`, { reason: "anti_cheat_threshold" }).then(() => {
        navigate(`/app/study/mocks/attempts/${attemptId}/result`, { replace: true });
      });
    }
  };

  const handleAnswer = async (selected_option_id) => {
    if (!q) return;
    await api.post(`/study/mocks/attempts/${attemptId}/answer`, {
      question_id: q.question_id,
      selected_option_id,
      is_marked_for_review: Boolean(q.is_marked_for_review),
      client_seq: Date.now(),
      time_spent_sec: 0,
    });
  };

  if (!attempt) return <div>Loading…</div>;

  return (
    <AntiCheatProvider enforceFullscreen={Boolean(config.tcs_ion_fullscreen)} blockCopy blockPaste onViolation={antiCheatPolicy}>
      <SectionLockGuard locked={config.allow_switching === false}>
        <SectionTimer expiresAt={currentSection?.expires_at} onExpire={() => api.post(`/study/mocks/attempts/${attemptId}/enter-section`, {})} />
        <QuestionPalette items={paletteItems} />
        <div>{q?.question_text || "No question"}</div>
        <button onClick={() => setConfirmOpen(true)}>Submit</button>
        <SubmitConfirmDialog
          open={confirmOpen}
          summary={{ total: (attempt.questions || []).length }}
          onCancel={() => setConfirmOpen(false)}
          onConfirm={async () => {
            await api.post(`/study/mocks/attempts/${attemptId}/submit`, {});
            navigate(`/app/study/mocks/attempts/${attemptId}/result`, { replace: true });
          }}
        />
      </SectionLockGuard>
    </AntiCheatProvider>
  );
}
