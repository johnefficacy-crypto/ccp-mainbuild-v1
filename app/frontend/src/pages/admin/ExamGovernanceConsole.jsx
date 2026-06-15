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
import { useNavigate } from "react-router-dom";
import useSelectedExamId from "../../lib/hooks/useSelectedExamId";
import useApiCollection from "../../lib/hooks/useApiCollection";
import ExamWorkspace from "./exam-workspace/ExamWorkspace";

// Reuse the exact list read the Registry uses (no new fetch path / endpoint).
const EXAM_LIST_URL = "/api/admin/exam-intelligence/exams";
const EXAM_LIST_PARAMS = { limit: "200", active_state: "active" };

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

// ─── No-exam picker — built from the Registry exam-list read ─────────────────

function ExamPicker() {
  const navigate = useNavigate();
  const { items, status, refresh } = useApiCollection(EXAM_LIST_URL, [], {
    params: EXAM_LIST_PARAMS,
  });

  function select(id) {
    // URL is the store — navigation IS the selection. No local state.
    navigate(`/admin/exam-intelligence/console/${encodeURIComponent(id)}`);
  }

  return (
    <div className="oc-main" style={{ padding: 22 }} data-testid="exam-picker">
      <div className="lbl" style={{ marginBottom: 4 }}>Exam Governance Console</div>
      <h1 className="oc-title disp" style={{ fontSize: 24, marginBottom: 12 }}>
        Select an exam
      </h1>

      {status === "loading" && (
        <div className="row-sub" data-testid="exam-picker-loading">Loading exams…</div>
      )}

      {status === "error" && (
        <div className="err-row" data-testid="exam-picker-error">
          Could not load exams.{" "}
          <button className="btn" onClick={refresh}>Retry</button>
        </div>
      )}

      {status === "empty" && (
        <div className="row-sub" data-testid="exam-picker-empty">No exams available.</div>
      )}

      {status === "live" && (
        <ul
          style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 6 }}
          data-testid="exam-picker-list"
        >
          {items.map((exam) => (
            <li key={exam.id}>
              <button
                className="btn"
                style={{ width: "100%", justifyContent: "flex-start", textAlign: "left" }}
                onClick={() => select(exam.id)}
                data-testid={`exam-picker-item-${exam.id}`}
              >
                <span>{exam.name ?? exam.slug ?? exam.id}</span>
                {exam.slug && (
                  <span className="mono" style={{ marginLeft: 8, fontSize: 10, color: "var(--ink-mute)" }}>
                    {exam.slug}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
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
      {/* Mount the existing workspace as-is. It reads :exam_id from the same
          route via useParams — no internal edits, no panel decomposition. */}
      <ExamWorkspace />
    </div>
  );
}
