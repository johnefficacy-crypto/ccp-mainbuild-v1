/**
 * Readiness & Activation panel (PR-0 §7).
 *
 * There is NO one-click activate endpoint. This panel is an aggregate readiness
 * summary: it surfaces per-section status/blockers and routes the operator to
 * the section's own tab to resolve them. It does NOT lock individual rows —
 * `compute_exam_workspace_readiness` returns per-section counts only (no
 * actionable row id), so there is no deterministic single row to lock here.
 * Row locking (reviewer_status transitions) happens in each section's own tab
 * against its real, ID-bearing rows, gated by exam_intelligence.review.
 *
 * Lifecycle: draft → pending_review → reviewed → locked → rejected
 * Planner consumes reviewed or locked rows (locked preferred); pending/rejected
 * never reach aspirants.
 */
import React, { useState } from "react";
import { useAuth } from "../../../../lib/authContext";
import { useExamWorkspace } from "../ExamWorkspaceContext";

// NOTE: this aggregate readiness panel does NOT lock individual rows. The
// per-section `metrics` from `compute_exam_workspace_readiness` are counts only
// (e.g. competition → {present_for_cycle, reviewer_status, breakdown}; updates →
// {total, pending, verified, stale, rejected}); they carry no actionable row id,
// so there is no deterministic single row to lock here. Locking happens in each
// section's own tab against its real, ID-bearing rows. Unresolved sections route
// there via the "Resolve →" / "View →" CTA.

const TAB_FOR_SECTION = {
  setup: "setup",
  documents: "documents",
  syllabus_mapper: "syllabus",
  pyq_workbench: "pyq",
  updates: "updates",
  competition: "competition",
};

const STATUS_LABELS = {
  empty: "Empty",
  partial: "In progress",
  ready: "Ready",
  locked: "Locked",
  rejected: "Rejected",
  pending_review: "Pending review",
  reviewed: "Reviewed",
  draft: "Draft",
};

// EI-CLEAN-03: explicit PYQ readiness metrics. planner-ready is the strict
// three-gate subset of reviewed — these must never collapse into one
// "verified" number (the old "0 of 100 verified" copy was ambiguous).
function PyqReadinessBreakdown({ pyq }) {
  const total = pyq.questions_total ?? 0;
  const plannerReady =
    pyq.planner_ready_question_count ?? pyq.verified_question_count ?? 0;
  const reviewed = pyq.reviewed_question_count ?? 0;
  const missingTag = pyq.missing_verified_tag_count ?? 0;
  const rejected = pyq.rejected_question_count ?? 0;
  return (
    <div className="csub" style={{ marginTop: 5 }} data-testid="pyq-readiness-breakdown">
      <strong data-testid="pyq-planner-ready">
        {plannerReady} / {total} planner-ready
      </strong>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 3 }}>
        <span data-testid="pyq-reviewed">
          {reviewed} question{reviewed === 1 ? "" : "s"} reviewed
        </span>
        {missingTag > 0 && (
          <span data-testid="pyq-missing-tag">
            {missingTag} need a verified topic tag
          </span>
        )}
        {rejected > 0 && (
          <span data-testid="pyq-rejected">{rejected} rejected</span>
        )}
      </div>
    </div>
  );
}

// EI-CLEAN-03: missing-tag remediation is independent of D10 readiness — a PYQ
// section can be "ok" (≥1 planner-ready) yet still have untagged questions that
// need attention. Used both to keep such a section in the failed-first group and
// to surface the remediation CTA.
function pyqMissingTagsFor(s) {
  return (
    s.section === "pyq_workbench" &&
    (s.metrics?.pyq_readiness?.missing_verified_tag_count || 0) > 0
  );
}


function StatusDot({ status, label }) {
  const cls =
    status === "ready" || status === "locked"
      ? "sdot ok"
      : status === "empty"
      ? "sdot bad"
      : "sdot warn";
  // Paired with a visible text label — not color-only (a11y).
  return (
    <span className="row" style={{ gap: 6, alignItems: "center" }}>
      <span className={cls} aria-hidden="true" style={{ marginTop: 2 }} />
      <span className="csub" style={{ fontSize: 11 }}>
        {label || STATUS_LABELS[status] || status}
      </span>
    </span>
  );
}

function StatusBadge({ status }) {
  const map = {
    empty: { cls: "badge neutral", text: "empty" },
    partial: { cls: "badge pending", text: "in progress" },
    ready: { cls: "badge info", text: "ready" },
    locked: { cls: "badge resolved", text: "locked" },
    reviewed: { cls: "badge info", text: "reviewed" },
    pending_review: { cls: "badge pending", text: "pending review" },
    draft: { cls: "badge neutral", text: "draft" },
    rejected: { cls: "badge err", text: "rejected" },
  };
  const b = map[status] || map.empty;
  return (
    <span className={b.cls} style={{ fontSize: 10, padding: "1px 6px" }}>
      {b.text}
    </span>
  );
}

export default function ReviewActivatePanel({ onGotoTab }) {
  const { readiness, readiness_loading, mgmtVersionError, refetchMgmt } = useExamWorkspace();
  const { user } = useAuth();
  const [showCompleted, setShowCompleted] = useState(false);

  const canReview = Array.isArray(user?.permissions)
    ? user.permissions.includes("exam_intelligence.review")
    : false;

  // D04: unsupported contract version — show inline compat error, not a skeleton.
  // The workspace-level banner is already visible; this ensures the panel itself
  // does not render an indefinite loading state when readiness is suppressed.
  if (mgmtVersionError) {
    return (
      <div className="stack" data-testid="review-panel-compat-error">
        <div className="scrn-head">
          <div className="scrn-tag">Terminal · readiness &amp; activation</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>
            Readiness &amp; Activation
          </h2>
        </div>
        <div className="card">
          <div className="card-body">
            <p className="err-row" style={{ marginBottom: 10 }}>
              Readiness data is unavailable because the workspace version is not supported by this
              client. Reload or contact support.
            </p>
            <button className="btn" onClick={refetchMgmt}>Retry</button>
          </div>
        </div>
      </div>
    );
  }

  if (readiness_loading || !readiness) {
    return (
      <div className="stack">
        <div className="scrn-head">
          <div className="scrn-tag">Terminal · readiness &amp; activation</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>
            Readiness &amp; Activation
          </h2>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="skel" style={{ height: 48, marginBottom: 10 }} />
            <div className="skel" style={{ height: 20, marginBottom: 6 }} />
            <div className="skel" style={{ height: 20 }} />
          </div>
        </div>
      </div>
    );
  }

  const sections = (readiness.sections || []).filter(
    (s) => s.section !== "review_activate",
  );
  const overall = readiness.overall || {};
  const scorePercent = overall.score_percent ?? 0;

  const isOk = (s) => s.status === "ready" || s.status === "locked";
  // A section still needs attention if it is not ready/locked OR (EI-CLEAN-03) it
  // is a PYQ section with untagged questions — the missing-tag CTA must stay
  // visible even when D10 marks the section ready.
  const needsAttention = (s) => !isOk(s) || pyqMissingTagsFor(s);
  // Failed-first: unresolved sections surface at the top; completed sections
  // collapse behind a "Show completed" toggle so the checklist stays compact.
  const failedSections = sections.filter(needsAttention);
  const clearSections = sections.filter((s) => !needsAttention(s));
  const clearCount = clearSections.length;

  function renderSectionRow(s) {
    const ok = isOk(s);
    const tabTarget = TAB_FOR_SECTION[s.section];
    const pyqMissingTags = pyqMissingTagsFor(s);

    return (
      <div key={s.section} className="check-row" style={{ cursor: "default" }}>
        {/* Status dot + text label — not color-only */}
        <StatusDot status={s.status} />
        <div>
          <div className="row" style={{ gap: 8 }}>
            <span className="ctxt" style={{ fontWeight: 500 }}>
              {s.label}
            </span>
            <StatusBadge status={s.status} />
            {s.weight > 0 && <span className="csub">weight {s.weight}</span>}
          </div>
          <div className="csub" style={{ marginTop: 3 }}>
            {s.note}
          </div>
          {/* Blocker reasons as text labels, not color-only */}
          {(s.blockers?.length || 0) > 0 && (
            <ul
              style={{
                margin: "6px 0 0",
                padding: 0,
                listStyle: "none",
                display: "flex",
                flexWrap: "wrap",
                gap: 6,
              }}
              aria-label={`Blockers for ${s.label}`}
            >
              {s.blockers.map((b, i) => (
                <li key={i} className="err-row" style={{ padding: "3px 7px" }}>
                  <span aria-hidden="true">⛔ </span>
                  {b}
                </li>
              ))}
            </ul>
          )}
          {/* EI-CLEAN-03: PYQ four-metric breakdown (planner-ready vs reviewed
              vs missing-tag vs rejected). */}
          {s.section === "pyq_workbench" && s.metrics?.pyq_readiness && (
            <PyqReadinessBreakdown pyq={s.metrics.pyq_readiness} />
          )}
        </div>
        <div style={{ textAlign: "right", minWidth: 120 }}>
          {/* EI-CLEAN-03: missing-tag CTA takes priority for the PYQ section even
              when the section is otherwise "ok" (planner-ready ≥ 1). */}
          {pyqMissingTags ? (
            <button
              className="btn small"
              onClick={() => onGotoTab("pyq")}
              data-testid="pyq-review-missing-cta"
            >
              Review missing topic tags →
            </button>
          ) : /* Resolve/lock happens in the section's own tab (rows there carry
                 real IDs); this aggregate panel only routes there. */
          canReview && !ok && tabTarget ? (
            <button className="btn small" onClick={() => onGotoTab(tabTarget)}>
              Resolve →
            </button>
          ) : !canReview && !ok && tabTarget ? (
            <button
              className="btn small secondary"
              onClick={() => onGotoTab(tabTarget)}
            >
              View →
            </button>
          ) : ok ? (
            <span className="seal" style={{ fontSize: 11 }}>
              {STATUS_LABELS[s.status] ?? s.status}
            </span>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">Terminal · readiness &amp; activation</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>
            Readiness &amp; Activation
          </h2>
        </div>
        <span className="badge pending no-dot">{scorePercent}% ready</span>
      </div>

      {!canReview && (
        <div
          className="card"
          style={{ borderLeft: "3px solid var(--warn)", padding: "10px 14px" }}
          role="status"
        >
          <span className="csub">
            Read-only — <strong>exam_intelligence.review</strong> permission
            required to lock rows.
          </span>
        </div>
      )}

      {/* Per-section readiness checklist — failed-first, completed collapsed */}
      <div className="card">
        <div className="card-head">
          <h3 className="oc-title">Section readiness checklist</h3>
          <span className="row-sub">
            {clearCount} / {sections.length} clear
          </span>
        </div>
        <div data-testid="failed-sections">
          {failedSections.length === 0 ? (
            <div className="check-row" style={{ cursor: "default" }}>
              <span className="csub" data-testid="all-sections-clear">
                Every section is ready or locked. Lock individual rows below to
                mark them planner-ready.
              </span>
            </div>
          ) : (
            failedSections.map(renderSectionRow)
          )}
          {clearSections.length > 0 && (
            <div style={{ padding: "8px 0 0" }}>
              <button
                type="button"
                className="btn small secondary"
                aria-expanded={showCompleted}
                onClick={() => setShowCompleted((v) => !v)}
                data-testid="toggle-completed-sections"
              >
                {showCompleted ? "Hide" : "Show"} completed ({clearSections.length})
              </button>
            </div>
          )}
          {showCompleted && (
            <div data-testid="completed-sections">
              {clearSections.map(renderSectionRow)}
            </div>
          )}
        </div>
      </div>

      {/* Created ≠ planner-ready note + row lifecycle behind an ⓘ disclosure so
          the terminal surface leads with the checklist, not reference copy. */}
      <details className="card" data-testid="planner-readiness-disclosure">
        <summary
          className="csub"
          style={{ cursor: "pointer", padding: "10px 14px", userSelect: "none" }}
          data-testid="planner-readiness-disclosure-summary"
        >
          <span aria-hidden="true">ⓘ </span>
          How planner readiness &amp; the row lifecycle work
        </summary>
        <div
          className="card-body"
          role="note"
          aria-label="Planner readiness note"
          data-testid="created-not-planner-ready-note"
        >
          <p className="csub" style={{ lineHeight: 1.6, margin: 0 }}>
            <strong>Created ≠ planner-ready.</strong> An exam with rows in the
            database is <em>not</em> automatically visible in Study OS. The
            planner requires at least one topic-coverage row that is{" "}
            <span className="font-mono" style={{ fontSize: 11 }}>
              reviewed
            </span>{" "}
            or{" "}
            <span className="font-mono" style={{ fontSize: 11 }}>
              locked
            </span>{" "}
            — reviewed or locked rows feed the planner, locked preferred. Until
            at least one such row exists, the exam shows{" "}
            <span className="font-mono" style={{ fontSize: 11 }}>
              planner_ready: false
            </span>{" "}
            to aspirants.
          </p>
          <div
            className="row"
            style={{ gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 12 }}
          >
            {["draft", "pending_review", "reviewed", "locked", "rejected"].map(
              (st, i, arr) => (
                <React.Fragment key={st}>
                  <StatusBadge status={st} />
                  {i < arr.length - 1 && (
                    <span className="csub" aria-hidden="true">
                      →
                    </span>
                  )}
                </React.Fragment>
              ),
            )}
          </div>
          <p className="csub" style={{ marginTop: 8, lineHeight: 1.6 }}>
            Planner consumes <strong>locked</strong> (preferred) or{" "}
            <strong>reviewed</strong> rows only. Rows in{" "}
            <strong>pending_review</strong> or <strong>rejected</strong> state
            never reach aspirants.
          </p>
        </div>
      </details>
    </div>
  );
}
