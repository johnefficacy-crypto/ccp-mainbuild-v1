/**
 * ExamGovernanceConsole — Wave 4.6A shell.
 *
 * Governance console that shows the work queue or focused per-exam action
 * console for the exam in the URL.
 *
 * Locks honored:
 *   D-B  selected-exam = URL single source of truth (useSelectedExamId reads
 *        the route param; no local selected-exam state lives here).
 *   D-C  route = /admin/exam-intelligence/console[/:exam_id]; the Registry at
 *        /admin/exam-intelligence is untouched.
 *   D-D  no create path here.
 *   D-E  no workspace/readiness requests from the selected-exam console route.
 *
 * Routes:
 *   /admin/exam-intelligence/console            → exam picker
 *   /admin/exam-intelligence/console/:exam_id   → action console
 */
import React from "react";
import useSelectedExamId from "../../lib/hooks/useSelectedExamId";
import ConsoleWorkQueue from "../../features/admin/exam-intelligence/ConsoleWorkQueue";
import ExamActionConsole from "../../features/admin/exam-intelligence/ExamActionConsole";

// ─── No-exam picker — the truthful work-queue list on the /console reads ─────
// (ExamListShell stays the generic /exams list for a future Registry adoption.)

function ExamPicker() {
  return (
    <div data-testid="exam-picker">
      <ConsoleWorkQueue />
    </div>
  );
}

// ─── Console ─────────────────────────────────────────────────────────────────

export default function ExamGovernanceConsole() {
  const examId = useSelectedExamId();

  if (!examId) {
    return <ExamPicker />;
  }

  // Per-exam: the focused, read-only action console (4.6I-FE) on the
  // /console/exams/:exam_id read. Triage only — editing follows each action's
  // CTA into /workspace/:exam_id.
  return (
    <div className="oc" data-testid="exam-governance-console">
      <ExamActionConsole examId={examId} />
    </div>
  );
}
