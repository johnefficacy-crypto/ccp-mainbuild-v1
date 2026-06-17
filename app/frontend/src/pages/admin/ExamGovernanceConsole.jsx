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
import ExamWorkspace from "./exam-workspace/ExamWorkspace";
import ConsoleWorkQueue from "../../features/admin/exam-intelligence/ConsoleWorkQueue";

// ─── Thin top bar — identity from the URL only (D-E: no readiness %) ─────────

function ConsoleTopBar({ examId }) {
  return (
    <div
      className="row"
      style={{
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        padding: "10px 22px",
        borderBottom: "1px solid var(--rule)",
        background: "var(--paper-sunk)",
      }}
      data-testid="console-top-bar"
    >
      <div className="row" style={{ gap: 8, alignItems: "baseline" }}>
        <span className="lbl">Exam Governance Console</span>
        <span className="mono" style={{ fontSize: 11 }} data-testid="console-selected-exam">
          {examId}
        </span>
      </div>
    </div>
  );
}

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

  return (
    <div className="oc" data-testid="exam-governance-console">
      <ConsoleTopBar examId={examId} />
      {/* Mount the existing workspace, scoped to :exam_id via useParams. The
          "console" variant suppresses readiness percentages (D-E) and the
          in-workspace cycle picker (which would navigate out of the console
          frame) — no panel decomposition. */}
      <ExamWorkspace variant="console" />
    </div>
  );
}
