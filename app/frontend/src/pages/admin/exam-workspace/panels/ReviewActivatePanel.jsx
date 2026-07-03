/**
 * Readiness & Activation panel (PR-0 §7).
 *
 * There is NO one-click activate endpoint. Activation = per-row
 * reviewer_status → 'locked' via PATCH /admin/exam-intelligence/{entity}/{id}/review,
 * gated by the exam_intelligence.review permission.
 *
 * Reviewable entities that appear in readiness sections:
 *   competition → PATCH /competition-metrics/{id}/review
 *   updates     → PATCH /policy-updates/{id}/review
 *   topic-coverage rows → PATCH /topic-coverage/{id}/review
 *
 * Lifecycle: draft → pending_review → reviewed → locked → rejected
 * Planner consumes: locked (preferred) or reviewed. pending/rejected never
 * reach aspirants.
 */
import React, { useState } from "react";
import { useAuth } from "../../../../lib/authContext";
import { api } from "../../../../lib/api";
import { useExamWorkspace } from "../ExamWorkspaceContext";

const REVIEW_BASE = "/api/admin/exam-intelligence";

// Sections that have directly-reviewable rows from the readiness payload
// and the PATCH endpoint pattern for locking them.
const SECTION_REVIEW_ENTITY = {
  competition: "competition-metrics",
  updates: "policy-updates",
  // topic-coverage rows are surfaced via the syllabus_mapper / pyq sections
  // but are not directly exposed by readiness metrics; left here for reference.
};

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

// Per-row lock action for a single reviewable entity row.
function RowLockButton({ entity, rowId, onLocked }) {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function handleLock() {
    setLoading(true);
    setErr("");
    try {
      await api.patch(`${REVIEW_BASE}/${entity}/${rowId}/review`, {
        reviewer_status: "locked",
      });
      onLocked?.();
    } catch (e) {
      setErr(e?.message || "Lock failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <span className="row" style={{ gap: 6, alignItems: "center" }}>
      {err && (
        <span className="csub" style={{ color: "var(--err)", fontSize: 11 }}>
          {err}
        </span>
      )}
      <button
        className="btn small"
        disabled={loading}
        onClick={handleLock}
        aria-label="Lock this row"
      >
        {loading ? "Locking…" : "Lock row"}
      </button>
    </span>
  );
}

export default function ReviewActivatePanel({ onGotoTab }) {
  const { readiness, readiness_loading, refetchReadiness, mgmtVersionError, refetchMgmt } = useExamWorkspace();
  const { user } = useAuth();

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

  const totalBlockers = sections.reduce(
    (n, s) => n + (s.blockers?.length || 0),
    0,
  );
  const blockedSections = sections.filter((s) => (s.blockers?.length || 0) > 0);
  const clearCount = sections.filter(
    (s) => s.status === "ready" || s.status === "locked",
  ).length;

  const allClear = totalBlockers === 0 && clearCount === sections.length;

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

      {/* Activation status — informational only; no one-click endpoint exists */}
      <div className={"next-action" + (allClear ? "" : " warn")}>
        <div>
          <span className="lbl">
            {allClear ? "All sections reviewed or locked" : "Activation blocked"}
          </span>
          <div
            className="oc-title"
            style={{ fontSize: 16, marginTop: 4, color: "var(--paper)" }}
          >
            {allClear
              ? "Every section is ready or locked. Lock individual rows below to mark them planner-ready."
              : `${totalBlockers} blocker${totalBlockers === 1 ? "" : "s"} across ${blockedSections.length} section${blockedSections.length === 1 ? "" : "s"} must clear first.`}
          </div>
        </div>
        <div
          className="csub"
          style={{
            fontSize: 11,
            color: "var(--paper)",
            opacity: 0.8,
            maxWidth: 220,
            lineHeight: 1.5,
          }}
        >
          Activation = per-row lock via the actions below.
          <br />
          Locked (preferred) or reviewed rows feed the planner.
          <br />
          Pending &amp; rejected rows never reach aspirants.
        </div>
      </div>

      {/* Created ≠ planner-ready callout — always visible so operators don't mistake
          row existence for planner activation. */}
      <div
        className="card"
        style={{ borderLeft: "3px solid var(--info)", padding: "10px 14px" }}
        role="note"
        aria-label="Planner readiness note"
        data-testid="created-not-planner-ready-note"
      >
        <p className="csub" style={{ lineHeight: 1.6, margin: 0 }}>
          <strong>Created ≠ planner-ready.</strong> An exam with rows in the
          database is <em>not</em> automatically visible in Study OS. The planner
          requires at least one topic-coverage row at{" "}
          <span className="font-mono" style={{ fontSize: 11 }}>
            locked
          </span>{" "}
          status (
          <span className="font-mono" style={{ fontSize: 11 }}>
            reviewed
          </span>{" "}
          is also accepted). Until that threshold is met, the exam shows{" "}
          <span className="font-mono" style={{ fontSize: 11 }}>
            planner_ready: false
          </span>{" "}
          to aspirants.
        </p>
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

      {/* Per-section readiness checklist */}
      <div className="card">
        <div className="card-head">
          <h3 className="oc-title">Section readiness checklist</h3>
          <span className="row-sub">
            {clearCount} / {sections.length} clear
          </span>
        </div>
        <div>
          {sections.map((s) => {
            const ok = s.status === "ready" || s.status === "locked";
            const tabTarget = TAB_FOR_SECTION[s.section];
            const reviewEntity = SECTION_REVIEW_ENTITY[s.section];
            // metrics may carry a single row id for competition / policy rows
            const singleRowId =
              s.metrics?.row_id || s.metrics?.id || null;
            // EI-CLEAN-03: missing-tag remediation is independent of D10 readiness.
            // Once one question is planner-ready the section is "ok", but untagged
            // questions still need attention — surface the CTA regardless of `ok`.
            const pyqMissingTags =
              s.section === "pyq_workbench" &&
              (s.metrics?.pyq_readiness?.missing_verified_tag_count || 0) > 0;

            return (
              <div
                key={s.section}
                className="check-row"
                style={{ cursor: "default" }}
              >
                {/* Status dot + text label — not color-only */}
                <StatusDot status={s.status} />
                <div>
                  <div className="row" style={{ gap: 8 }}>
                    <span className="ctxt" style={{ fontWeight: 500 }}>
                      {s.label}
                    </span>
                    <StatusBadge status={s.status} />
                    {s.weight > 0 && (
                      <span className="csub">weight {s.weight}</span>
                    )}
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
                        <li
                          key={i}
                          className="err-row"
                          style={{ padding: "3px 7px" }}
                        >
                          <span aria-hidden="true">⛔ </span>
                          {b}
                        </li>
                      ))}
                    </ul>
                  )}
                  {/* EI-CLEAN-03: PYQ four-metric breakdown (planner-ready vs
                      reviewed vs missing-tag vs rejected). */}
                  {s.section === "pyq_workbench" && s.metrics?.pyq_readiness && (
                    <PyqReadinessBreakdown pyq={s.metrics.pyq_readiness} />
                  )}
                </div>
                <div style={{ textAlign: "right", minWidth: 120 }}>
                  {/* Missing-tag CTA takes priority for the PYQ section even when
                      the section is otherwise "ok" (planner-ready ≥ 1). */}
                  {pyqMissingTags ? (
                    <button
                      className="btn small"
                      onClick={() => onGotoTab("pyq")}
                      data-testid="pyq-review-missing-cta"
                    >
                      Review missing topic tags →
                    </button>
                  ) : /* Per-row lock action — gated on exam_intelligence.review */
                  canReview && reviewEntity && singleRowId && !ok ? (
                    <RowLockButton
                      entity={reviewEntity}
                      rowId={singleRowId}
                      onLocked={refetchReadiness}
                    />
                  ) : canReview && !ok && tabTarget ? (
                    <button
                      className="btn small"
                      onClick={() => onGotoTab(tabTarget)}
                    >
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
          })}
        </div>
      </div>

      {/* Lifecycle reference */}
      <div className="card">
        <div className="card-head">
          <h3 className="oc-title">Row lifecycle</h3>
        </div>
        <div className="card-body">
          <div
            className="row"
            style={{ gap: 8, flexWrap: "wrap", alignItems: "center" }}
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
      </div>
    </div>
  );
}
