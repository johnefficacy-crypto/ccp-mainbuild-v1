/**
 * ScoreSnapshotPanel — Score snapshot compute/review/lock workbench.
 *
 * Embedded inside PyqWorkbenchPanel as the "Score Snapshots" view (?view=snapshots).
 * No standalone route — architecture constraint from pyq-intelligence-v2.md.
 *
 * URL params (owned by this panel, set within the ?tab=pyq context):
 *   ?phase=<phase_id>   explicit phase scope; absent = exam-wide
 *
 * Workflow:
 *   POST   .../score-snapshots/compute[?exam_phase_id=]     → draft snapshots
 *   GET    .../score-snapshots[?status=&exam_phase_id=]     → list (one scope)
 *   PATCH  .../score-snapshots/{id}/review                  → status transition
 *
 * Transition matrix:
 *   draft     → reviewed | rejected
 *   reviewed  → locked | rejected | draft
 *   locked    → reviewed  (reviewer_notes required)
 *   rejected  → draft
 *
 * Scope rule (list and compute must always be identical):
 *   phase selected → exam_phase_id=<id>  (phase rows only)
 *   exam-wide      → exam_phase_id absent (null rows only)
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { api } from "../../../../lib/api";
import useApiAction from "../../../../lib/hooks/useApiAction";

const EI_BASE = "/api/admin/exam-intelligence";

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_BADGE = {
  draft:    { cls: "badge neutral",  text: "draft" },
  reviewed: { cls: "badge info",     text: "reviewed" },
  locked:   { cls: "badge resolved", text: "locked" },
  rejected: { cls: "badge blocker",  text: "rejected" },
};

function StatusBadge({ status }) {
  const b = STATUS_BADGE[status] || { cls: "badge neutral", text: status };
  return <span className={b.cls}>{b.text}</span>;
}

// ─── Reviewer-notes modal (locked → reviewed) ─────────────────────────────────

function ReviewerNotesModal({ open, onCancel, onConfirm, busy, error, invokerRef }) {
  const [notes, setNotes] = useState("");
  const textareaRef = useRef(null);
  const dialogRef = useRef(null);

  useEffect(() => {
    if (open) {
      setNotes("");
      setTimeout(() => textareaRef.current?.focus(), 50);
    } else {
      invokerRef?.current?.focus();
    }
  }, [open, invokerRef]);

  function handleKeyDown(e) {
    if (e.key === "Escape") { onCancel(); return; }
    if (e.key !== "Tab") return;
    const focusable = dialogRef.current?.querySelectorAll(
      'button:not([disabled]), textarea, [tabindex]:not([tabindex="-1"])',
    );
    if (!focusable || focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onKeyDown={handleKeyDown}
    >
      <div className="absolute inset-0 bg-black/30" onClick={onCancel} />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="reviewer-notes-title"
        className="relative w-full max-w-md rounded-xl border border-border bg-[#FBF6EF] p-4 space-y-3"
        style={{ zIndex: 1 }}
      >
        <h2 id="reviewer-notes-title" className="font-semibold">
          Revert locked snapshot to reviewed
        </h2>
        <p className="text-sm" style={{ color: "var(--ink-mute)" }}>
          Describe why this locked snapshot is being reverted. This note is
          required and will be stored in the audit log.
        </p>
        <label htmlFor="reviewer-notes-textarea" className="sr-only">
          Reversal rationale (required)
        </label>
        <textarea
          id="reviewer-notes-textarea"
          ref={textareaRef}
          className="input"
          style={{ width: "100%", minHeight: 80, resize: "vertical" }}
          placeholder="e.g. PYQ counts rechecked — evidence count was wrong"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          data-testid="reviewer-notes-input"
          aria-label="Reversal rationale (required)"
        />
        {error && (
          <div className="err-row" style={{ fontSize: 12 }} data-testid="notes-modal-error">
            {error}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button className="btn ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button
            className="btn primary"
            disabled={!notes.trim() || busy}
            onClick={() => onConfirm(notes.trim())}
            data-testid="reviewer-notes-submit"
          >
            {busy ? "Saving…" : "Revert to reviewed"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Evidence drawer ──────────────────────────────────────────────────────────

function EvidenceDrawer({ snap, phases }) {
  const sc = snap.score_components;
  const is = snap.input_summary;
  const phaseName = snap.exam_phase_id
    ? (phases.find((p) => p.id === snap.exam_phase_id)?.phase_name || snap.exam_phase_id)
    : "Exam-wide";

  return (
    <tr data-testid={`evidence-drawer-${snap.id}`}>
      <td
        colSpan={10}
        style={{ padding: "6px 12px 10px", background: "var(--paper-sunk)", borderBottom: "1px solid var(--rule-soft)" }}
      >
        <div className="row" style={{ gap: 24, alignItems: "flex-start", flexWrap: "wrap", fontSize: 12 }}>
          <div>
            <div style={{ fontWeight: 600, marginBottom: 2 }}>Scope</div>
            <div style={{ color: "var(--ink-mute)" }}>{phaseName}</div>
          </div>
          {is && (
            <div>
              <div style={{ fontWeight: 600, marginBottom: 2 }}>Corpus</div>
              <div style={{ color: "var(--ink-mute)" }}>
                {is.paper_count != null && <span>{is.paper_count} paper{is.paper_count !== 1 ? "s" : ""}</span>}
                {is.question_count != null && <span> · {is.question_count} questions</span>}
                {is.primary_tag_count != null && <span> · {is.primary_tag_count} primary tags</span>}
              </div>
            </div>
          )}
          {sc && Object.keys(sc).length > 0 && (
            <div>
              <div style={{ fontWeight: 600, marginBottom: 2 }}>Score components</div>
              <div style={{ color: "var(--ink-mute)" }}>
                {Object.entries(sc).map(([k, v], i) => (
                  <span key={k}>
                    {i > 0 && " · "}
                    {k}: {typeof v === "number" ? v.toFixed(2) : String(v)}
                  </span>
                ))}
              </div>
            </div>
          )}
          <div>
            <div style={{ fontWeight: 600, marginBottom: 2 }}>Model · computed</div>
            <div className="mono" style={{ color: "var(--ink-mute)", fontSize: 11 }}>
              {snap.model_version}
              {snap.computed_at && ` · ${new Date(snap.computed_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}`}
            </div>
          </div>
        </div>
      </td>
    </tr>
  );
}

// ─── Status filter chips ──────────────────────────────────────────────────────

const STATUS_FILTERS = [
  { value: "",         label: "All" },
  { value: "draft",    label: "Draft" },
  { value: "reviewed", label: "Reviewed" },
  { value: "locked",   label: "Locked" },
  { value: "rejected", label: "Rejected" },
];

function fmt(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
  });
}

// ─── Panel ────────────────────────────────────────────────────────────────────

export default function ScoreSnapshotPanel() {
  const { exam, phases } = useExamWorkspace();
  const [searchParams, setSearchParams] = useSearchParams();

  // Scope: ?phase=<id> → phase-scoped; absent → exam-wide (IS NULL rows only)
  const phaseParam = searchParams.get("phase") || "";

  const [snapshots, setSnapshots]       = useState([]);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [expandedId, setExpandedId]     = useState(null);

  // locked → reviewed modal state
  const [notesModal, setNotesModal]   = useState(null); // { snapshotId } | null
  const [notesError, setNotesError]   = useState("");
  const invokerRef = useRef(null);

  const computeAction = useApiAction();
  const reviewAction  = useApiAction();

  const load = useCallback(async () => {
    if (!exam?.id) return;
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams();
      if (statusFilter) qs.set("status", statusFilter);
      if (phaseParam) qs.set("exam_phase_id", phaseParam);
      const d = await api.get(
        `${EI_BASE}/exams/${encodeURIComponent(exam.id)}/score-snapshots?${qs}`,
      );
      setSnapshots(d?.snapshots || []);
    } catch (e) {
      setError(e?.message || "Failed to load snapshots");
    } finally {
      setLoading(false);
    }
  }, [exam?.id, statusFilter, phaseParam]);

  useEffect(() => { load(); }, [load]);

  function setScope(phaseId) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (phaseId) {
        next.set("phase", phaseId);
      } else {
        next.delete("phase");
      }
      return next;
    });
  }

  async function compute() {
    const qs = phaseParam ? `?exam_phase_id=${encodeURIComponent(phaseParam)}` : "";
    const result = await computeAction.run({
      action: () => api.post(
        `${EI_BASE}/exams/${encodeURIComponent(exam.id)}/score-snapshots/compute${qs}`,
        {},
      ),
      successMessage: "Compute finished.",
      errorMessage: "Compute failed.",
    });
    if (result?.ok) await load();
  }

  async function review(snapshotId, newStatus, reviewerNotes) {
    const body = { status: newStatus };
    if (reviewerNotes != null) body.reviewer_notes = reviewerNotes;
    return reviewAction.run({
      action: () => api.patch(
        `${EI_BASE}/score-snapshots/${encodeURIComponent(snapshotId)}/review`,
        body,
      ),
      errorMessage: "Review action failed.",
    });
  }

  async function handleLockedReversal(notes) {
    setNotesError("");
    const result = await review(notesModal.snapshotId, "reviewed", notes);
    if (result?.ok) {
      setNotesModal(null);
      await load();
    } else {
      // Keep modal open — preserve typed notes so operator can retry
      setNotesError(result?.error?.message || "Could not revert snapshot. Please try again.");
    }
  }

  async function handleReview(snap, status) {
    const result = await review(snap.id, status);
    if (result?.ok) await load();
  }

  function actions(snap) {
    const busy = reviewAction.busy;

    function btn(label, status, variant = "small") {
      const isLockedReversal = snap.status === "locked" && status === "reviewed";
      return (
        <button
          key={`${snap.id}-${status}`}
          className={`btn ${variant} small`}
          disabled={busy}
          onClick={(e) => {
            if (isLockedReversal) {
              invokerRef.current = e.currentTarget;
              setNotesModal({ snapshotId: snap.id });
            } else {
              handleReview(snap, status);
            }
          }}
          data-testid={`action-${snap.id}-${status}`}
        >
          {busy ? "…" : label}
        </button>
      );
    }

    const map = {
      draft:    [btn("Approve", "reviewed", "primary"), btn("Reject", "rejected")],
      reviewed: [btn("Lock", "locked", "primary"), btn("Reject", "rejected"), btn("Revert draft", "draft")],
      locked:   [btn("Revert", "reviewed")],
      rejected: [btn("Restore draft", "draft")],
    };
    return map[snap.status] || null;
  }

  // Scope selector options: exam-wide + each phase from context
  const scopeOptions = [
    { id: "", label: "Exam-wide" },
    ...phases.map((ph) => ({ id: ph.id, label: ph.phase_name || ph.id })),
  ];

  return (
    <div className="stack">
      <ReviewerNotesModal
        open={!!notesModal}
        onCancel={() => { setNotesModal(null); setNotesError(""); }}
        onConfirm={handleLockedReversal}
        busy={reviewAction.busy}
        error={notesError}
        invokerRef={invokerRef}
      />

      {/* Header */}
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">PYQ Intelligence · score snapshots</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>
            Score Snapshots
          </h2>
        </div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn small" onClick={load} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
          <button
            className="btn primary small"
            onClick={compute}
            disabled={computeAction.busy}
            data-testid="compute-btn"
          >
            {computeAction.busy ? "Computing…" : "Compute snapshots"}
          </button>
        </div>
      </div>

      {/* Info strip */}
      <div style={{ padding: "9px 12px", borderRadius: 4, border: "1px solid var(--rule-soft)", background: "var(--paper-sunk)", fontSize: 12, color: "var(--ink-soft)" }}>
        Only <strong>locked</strong> snapshots are consumed by the planner. Approve
        and lock snapshots after verifying PYQ evidence counts. Compute and list always
        use the same scope — select it below before running compute.
      </div>

      {/* Scope selector */}
      <div className="row" style={{ gap: 6, alignItems: "center" }}>
        <span style={{ fontSize: 12, color: "var(--ink-mute)", marginRight: 2 }}>Scope:</span>
        {scopeOptions.map((opt) => (
          <button
            key={opt.id}
            className={"btn small" + (phaseParam === opt.id ? " active" : "")}
            onClick={() => setScope(opt.id)}
            data-testid={`scope-${opt.id || "exam"}`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Status filter */}
      <div className="row" style={{ gap: 6 }}>
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            className={"btn small" + (statusFilter === f.value ? " active" : "")}
            onClick={() => setStatusFilter(f.value)}
            data-testid={`filter-${f.value || "all"}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Load error */}
      {error && <div className="err-row" data-testid="load-error">{error}</div>}

      {/* Table */}
      <div className="card">
        {snapshots.length === 0 && !loading ? (
          <div className="empty">
            <div className="empty-title">No snapshots</div>
            <div>
              {statusFilter
                ? `No snapshots with status "${statusFilter}".`
                : 'Run "Compute snapshots" to generate draft snapshots from verified PYQ evidence.'}
            </div>
          </div>
        ) : (
          <table className="t">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Status</th>
                <th className="num">Priority</th>
                <th className="num">Confidence</th>
                <th className="num">Evidence</th>
                <th>High yield</th>
                <th>Reviewed</th>
                <th>Notes</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 3 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 9 }).map((__, j) => (
                        <td key={j}>
                          <div className="skel" style={{ height: 12, borderRadius: 3 }} />
                        </td>
                      ))}
                    </tr>
                  ))
                : snapshots.flatMap((snap) => {
                    const expanded = expandedId === snap.id;
                    const rows = [
                      <tr
                        key={snap.id}
                        data-testid={`snapshot-row-${snap.id}`}
                        style={{ cursor: "pointer" }}
                        onClick={() => setExpandedId(expanded ? null : snap.id)}
                      >
                        <td>
                          <div
                            className="row-ttl"
                            style={{ fontSize: 12 }}
                            title={snap.topic_id}
                          >
                            {snap.topic_name || snap.topic?.name || snap.topic_id || "—"}
                          </div>
                          {snap.topic_path && (
                            <div className="row-sub" style={{ fontSize: 10, color: "var(--ink-mute)" }}>
                              {snap.topic_path}
                            </div>
                          )}
                        </td>
                        <td>
                          <StatusBadge status={snap.status} />
                        </td>
                        <td className="num">
                          {snap.exam_priority_score != null
                            ? snap.exam_priority_score.toFixed(1)
                            : "—"}
                        </td>
                        <td className="num">
                          {snap.confidence_score != null
                            ? (snap.confidence_score * 100).toFixed(0) + "%"
                            : "—"}
                        </td>
                        <td className="num">{snap.evidence_count ?? "—"}</td>
                        <td>
                          {snap.is_high_yield ? (
                            <span className="badge info no-dot">yes</span>
                          ) : (
                            <span style={{ color: "var(--ink-mute)", fontSize: 12 }}>no</span>
                          )}
                        </td>
                        <td style={{ color: "var(--ink-mute)", fontSize: 12 }}>
                          {fmt(snap.reviewed_at)}
                        </td>
                        <td
                          style={{ maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 12, color: "var(--ink-mute)" }}
                          title={snap.reviewer_notes || ""}
                        >
                          {snap.reviewer_notes || "—"}
                        </td>
                        <td onClick={(e) => e.stopPropagation()}>
                          <div className="row" style={{ gap: 4, justifyContent: "flex-end" }}>
                            {actions(snap)}
                          </div>
                        </td>
                      </tr>,
                    ];
                    if (expanded) {
                      rows.push(
                        <EvidenceDrawer key={`${snap.id}-drawer`} snap={snap} phases={phases} />,
                      );
                    }
                    return rows;
                  })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
