/**
 * ExamGovernanceConsole — Wave 4.6A shell.
 *
 * Additive, FE-only governance console that frames the EXISTING exam
 * workspace inside a thin shell. It does not decompose, fork, or modify any
 * workspace panel — it mounts the workspace as-is, scoped to the exam in the
 * URL.
 *
 * Locks honored:
 *   D-B  selected-exam = URL single source of truth (useSelectedExamId reads
 *        the route param; no local selected-exam state lives here).
 *   D-C  route = /admin/exam-intelligence/console[/:exam_id]; the Registry at
 *        /admin/exam-intelligence is untouched.
 *   D-D  no create path here.
 *   D-E  no readiness percentage anywhere in this shell. The top bar shows
 *        identity facts only and fetches nothing of its own.
 *
 * Routes:
 *   /admin/exam-intelligence/console            → exam picker
 *   /admin/exam-intelligence/console/:exam_id   → top bar + embedded workspace
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
  // CTA into /workspace/:exam_id. The legacy ExamWorkspace variant="console"
  // mount is retired here; removing that now-orphaned code is a cleanup
  // follow-up (it is not edited/deleted in this PR).
  return (
    <div className="oc" data-testid="exam-governance-console">
      <ExamActionConsole examId={examId} />
    </div>
  );
}
