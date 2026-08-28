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
 *   POST   .../score-snapshots/compute   body: { exam_phase_id? } → draft snapshots
 *   GET    .../score-snapshots[?status=&exam_phase_id=]            → list (one scope)
 *   PATCH  .../score-snapshots/{id}/review                         → status transition
 *
 * GET scope contract (breaking change from pre-PR-B):
 *   exam_phase_id absent → IS NULL rows only (exam-wide).  All-scope reads are
 *   not supported — operators review one scope at a time to prevent comparing
 *   incomparable evidence sets.
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
 *
 * input_summary keys (written by score_snapshots.py):
 *   fingerprint, paper_count, question_count, topic_primary_count, corpus_total_primary
 *
 * score_components keys:
 *   frequency_component, coverage_component, evidence_quality
 *
 * Race safety:
 *   loadRef always points to the latest load() so post-mutation reloads use
 *   the current scope even if scope changed while the mutation was in flight.
 *   isMutating disables scope/status controls while either action is busy.
 *
 * Context loading guard:
 *   Phase param validation and all mutations are blocked until useExamWorkspace()
 *   reports loading=false and error="". This ensures we never classify an unknown
 *   phase as invalid while context data is still in flight.
 *
 * Permission gate:
 *   The panel accepts a canReview prop from PyqWorkbenchPanel. When false the
 *   Compute button and all status-transition actions are hidden.
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

// ─── Subject-group sectioning ──────────────────────────────────────────────────
// The scorer pools every verified paper when run exam-wide, so GS Paper I and
// CSAT Paper II topics arrive in one flat list. subject_group (enriched by the
// backend from subjects.subject_group) is the paper-level discriminator; we
// section by it so the two papers read as two papers, not one bucket.
// Known groups get a friendly, paper-anchored label; anything else falls
// through to a title-cased label, and rows with no subject land in an explicit
// "Unclassified" section (never silently merged into another paper).
const NO_GROUP = "__none__";
const SUBJECT_GROUP_LABEL = {
  gs:        "GS Paper I — General Studies",
  reasoning: "CSAT Paper II — Aptitude",
};
// Stable display order: GS first, CSAT second, any other named group next,
// unclassified always last.
const SUBJECT_GROUP_ORDER = ["gs", "reasoning"];

function subjectGroupLabel(group) {
  if (!group) return "Unclassified — no subject";
  if (SUBJECT_GROUP_LABEL[group]) return SUBJECT_GROUP_LABEL[group];
  return group.charAt(0).toUpperCase() + group.slice(1);
}

function groupRank(group) {
  if (!group || group === NO_GROUP) return Number.MAX_SAFE_INTEGER;
  const i = SUBJECT_GROUP_ORDER.indexOf(group);
  return i === -1 ? SUBJECT_GROUP_ORDER.length : i;
}

// Partition snapshots into ordered [{ group, label, rows }] sections without
// disturbing within-group order (the backend already sorts by computed_at).
function groupSnapshots(snaps) {
  const byGroup = new Map();
  for (const s of snaps) {
    const key = s.subject_group || NO_GROUP;
    if (!byGroup.has(key)) byGroup.set(key, []);
    byGroup.get(key).push(s);
  }
  return [...byGroup.entries()]
    .sort((a, b) => {
      const r = groupRank(a[0]) - groupRank(b[0]);
      return r !== 0 ? r : String(a[0]).localeCompare(String(b[0]));
    })
    .map(([group, rows]) => ({
      group,
      label: subjectGroupLabel(group === NO_GROUP ? null : group),
      rows,
    }));
}

// A snapshot is a "0-evidence" node when it carries no verified primary tags
// (evidence_count === 0). By construction (score_snapshots.py: the topic
// universe is primary-tag topics UNION locked-coverage topics) such a row is
// present ONLY because a locked coverage row seeded it — a rollup/header node,
// not a real evidence-backed leaf. A genuinely-new, not-yet-tagged real topic
// has neither tags nor coverage and so never appears here at all, so this flag
// cannot hide such a topic. These rows must not be orderable/approvable as
// peers of real leaves, but stay visible and rejectable.
function isZeroEvidence(snap) {
  return snap?.evidence_count === 0;
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
      if (invokerRef?.current && document.contains(invokerRef.current)) {
        invokerRef.current.focus();
      }
    }
  }, [open, invokerRef]);

  function handleKeyDown(e) {
    // Ignore all dismissal paths while a mutation is in flight to prevent
    // losing operator-typed rationale if the PATCH then fails.
    if (e.key === "Escape") { if (!busy) onCancel(); return; }
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
      {/* Backdrop — ignored while mutation is in flight */}
      <div
        className="absolute inset-0 bg-black/30"
        onClick={() => { if (!busy) onCancel(); }}
      />
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
          <div
            className="err-row"
            style={{ fontSize: 12 }}
            data-testid="notes-modal-error"
            role="alert"
          >
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

function EvidenceDrawer({ snap, scopeLabel }) {
  const sc = snap.score_components;
  const is = snap.input_summary;

  return (
    <tr data-testid={`evidence-drawer-${snap.id}`}>
      <td
        colSpan={10}
        style={{ padding: "6px 12px 10px", background: "var(--paper-sunk)", borderBottom: "1px solid var(--rule-soft)" }}
      >
        <div className="row" style={{ gap: 24, alignItems: "flex-start", flexWrap: "wrap", fontSize: 12 }}>
          <div>
            <div style={{ fontWeight: 600, marginBottom: 2 }}>Scope</div>
            <div style={{ color: "var(--ink-mute)" }}>{scopeLabel}</div>
          </div>
          {is && (
            <div>
              <div style={{ fontWeight: 600, marginBottom: 2 }}>Corpus</div>
              <div style={{ color: "var(--ink-mute)" }}>
                {is.paper_count != null && <span>{is.paper_count} paper{is.paper_count !== 1 ? "s" : ""}</span>}
                {is.question_count != null && <span> · {is.question_count} questions</span>}
                {is.topic_primary_count != null && <span> · {is.topic_primary_count} primary tags (topic)</span>}
                {is.corpus_total_primary != null && <span> / {is.corpus_total_primary} corpus total</span>}
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
                    {k}: {typeof v === "number" ? v.toFixed(4) : String(v)}
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
          {is?.fingerprint && (
            <div>
              <div style={{ fontWeight: 600, marginBottom: 2 }}>Fingerprint</div>
              <div className="mono" style={{ color: "var(--ink-mute)", fontSize: 10, wordBreak: "break-all" }} data-testid="evidence-fingerprint">
                {is.fingerprint}
              </div>
            </div>
          )}
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

const PAGE_SIZE = 50;

// ─── Panel ────────────────────────────────────────────────────────────────────

export default function ScoreSnapshotPanel({ canReview = false }) {
  const {
    exam, phases, cycles,
    loading: contextLoading,
    error: contextError,
  } = useExamWorkspace();

  const [searchParams, setSearchParams] = useSearchParams();

  // Scope: ?phase=<id> → phase-scoped; absent → exam-wide (IS NULL rows only).
  // Phase validation is deferred until context has finished loading. While context
  // is still loading, treat all phase params as "pending" to avoid false invalids.
  const phaseParam = searchParams.get("phase") || "";
  const contextReady = !contextLoading && !contextError;
  const validPhase = contextReady ? phases.find((p) => p.id === phaseParam) : undefined;
  const invalidPhase = contextReady && phaseParam !== "" && !validPhase;
  const effectivePhase = invalidPhase ? "" : phaseParam;

  const [snapshots, setSnapshots]       = useState([]);
  const [loadingSnaps, setLoadingSnaps] = useState(false);
  const [loadError, setLoadError]       = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [expandedId, setExpandedId]     = useState(null);
  const [page, setPage]                 = useState(0);
  const [total, setTotal]               = useState(0);

  const [notesModal, setNotesModal]   = useState(null);
  const [notesError, setNotesError]   = useState("");
  const invokerRef = useRef(null);
  const panelHeadingRef = useRef(null);
  const loadGenRef = useRef(0);

  const computeAction = useApiAction();
  const reviewAction  = useApiAction();

  // True while any mutation is in flight — scope/status changes are disabled.
  const isMutating = computeAction.busy || reviewAction.busy;

  const load = useCallback(async (pageOverride) => {
    if (!exam?.id) return;
    // Do not issue list requests while context is still loading or errored.
    if (!contextReady) return;
    const targetPage = pageOverride ?? page;
    const gen = ++loadGenRef.current;
    setLoadingSnaps(true);
    setLoadError("");
    setSnapshots([]);
    try {
      const qs = new URLSearchParams();
      if (statusFilter) qs.set("status", statusFilter);
      if (effectivePhase) qs.set("exam_phase_id", effectivePhase);
      qs.set("limit", String(PAGE_SIZE));
      qs.set("offset", String(targetPage * PAGE_SIZE));
      const d = await api.get(
        `${EI_BASE}/exams/${encodeURIComponent(exam.id)}/score-snapshots?${qs}`,
      );
      if (gen !== loadGenRef.current) return;
      setSnapshots(d?.snapshots || []);
      setTotal(d?.total ?? 0);
    } catch (e) {
      if (gen !== loadGenRef.current) return;
      setLoadError(e?.message || "Failed to load snapshots");
      setSnapshots([]);
    } finally {
      if (gen === loadGenRef.current) setLoadingSnaps(false);
    }
  }, [exam?.id, statusFilter, effectivePhase, contextReady, page]);

  // loadRef always points to the latest load closure so post-mutation reloads
  // use the current scope even if scope changed during the mutation.
  const loadRef = useRef(load);
  useEffect(() => { loadRef.current = load; }, [load]);

  useEffect(() => { load(); }, [load]);

  // Reset to page 0 when scope or filter changes.
  useEffect(() => { setPage(0); }, [effectivePhase, statusFilter]);

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
    const body = effectivePhase ? { exam_phase_id: effectivePhase } : {};
    const result = await computeAction.run({
      action: () => api.post(
        `${EI_BASE}/exams/${encodeURIComponent(exam.id)}/score-snapshots/compute`,
        body,
      ),
      successMessage: "Compute finished.",
      errorMessage: "Compute failed.",
    });
    // Use loadRef so reload uses current scope even if it changed during compute.
    if (result?.ok) await loadRef.current();
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
      await loadRef.current();
      setTimeout(() => panelHeadingRef.current?.focus(), 50);
    } else {
      setNotesError(result?.error?.message || "Could not revert snapshot. Please try again.");
    }
  }

  async function handleReview(snap, status) {
    const result = await review(snap.id, status);
    // Use loadRef so reload uses current scope even if it changed during review.
    if (result?.ok) await loadRef.current();
  }

  function actions(snap) {
    const busy = reviewAction.busy;
    const zeroEvidence = isZeroEvidence(snap);

    function btn(label, status, variant = "small") {
      const isLockedReversal = snap.status === "locked" && status === "reviewed";
      const isLockWithoutIdentity = status === "locked" && !snap.topic_name;
      // A 0-evidence rollup/header node must not be promotable as if it were a
      // real leaf: block Approve (draft→reviewed) and Lock (→locked). Reject
      // and the walk-back moves (→draft, locked→reviewed) stay enabled so an
      // operator can consciously reject or unwind it.
      const isPromotion =
        status === "locked" || (snap.status === "draft" && status === "reviewed");
      const blockedZeroEvidence = zeroEvidence && isPromotion;
      return (
        <button
          key={`${snap.id}-${status}`}
          className={`btn ${variant} small`}
          disabled={busy || isLockWithoutIdentity || blockedZeroEvidence}
          title={
            blockedZeroEvidence
              ? "No PYQ evidence (0 verified tags) — reject or add evidence; cannot promote a rollup/header node"
              : isLockWithoutIdentity
                ? "Topic identity not resolved — cannot lock"
                : undefined
          }
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

  // Build a lookup from exam_cycle_id → human label using cycles[] from context.
  // Falls back to raw exam_cycle_id if the cycle isn't in context (shouldn't happen).
  const cycleLabel = (examCycleId) => {
    if (!examCycleId) return null;
    const c = (cycles || []).find((cy) => cy.id === examCycleId);
    if (!c) return examCycleId;
    return c.cycle_name || c.year || examCycleId;
  };

  // Detect duplicate phase_name values (across different exam cycles).
  // When duplicates exist, append the human cycle label to disambiguate.
  const phaseNameCount = phases.reduce((acc, ph) => {
    acc[ph.phase_name] = (acc[ph.phase_name] || 0) + 1;
    return acc;
  }, {});

  const scopeOptions = [
    { id: "", label: "Exam-wide" },
    ...phases.map((ph) => ({
      id: ph.id,
      label: phaseNameCount[ph.phase_name] > 1
        ? `${ph.phase_name} · ${cycleLabel(ph.exam_cycle_id)}`
        : (ph.phase_name || ph.id),
    })),
  ];

  // Scope label for evidence drawer — uses the same disambiguated label.
  function snapScopeLabel(snap) {
    if (!snap.exam_phase_id) return "Exam-wide";
    const opt = scopeOptions.find((o) => o.id === snap.exam_phase_id);
    return opt?.label || snap.exam_phase_id;
  }

  // Render one snapshot as its table row (+ evidence drawer when expanded).
  // Extracted so the tbody can wrap rows in subject-group sections.
  function renderSnapshotRow(snap) {
    const expanded = expandedId === snap.id;
    const zeroEvidence = isZeroEvidence(snap);
    const out = [
      <tr key={snap.id} data-testid={`snapshot-row-${snap.id}`}>
        <td>
          <div className="row" style={{ gap: 4, alignItems: "flex-start" }}>
            <button
              aria-expanded={expanded}
              aria-label={expanded ? "Hide evidence" : "Show evidence"}
              className="btn ghost small"
              onClick={() => setExpandedId(expanded ? null : snap.id)}
              data-testid={`expand-btn-${snap.id}`}
              style={{ flexShrink: 0, padding: "0 4px", fontSize: 10 }}
            >
              {expanded ? "▲" : "▼"}
            </button>
            <div>
              <div className="row-ttl" style={{ fontSize: 12 }} title={snap.topic_id}>
                {snap.topic_name || snap.topic_id || "—"}
                {zeroEvidence && (
                  <span
                    className="badge warn no-dot"
                    style={{ marginLeft: 6, fontSize: 10 }}
                    title="No PYQ evidence (0 verified primary tags) — present only via a locked coverage row. A rollup/header node, not a real leaf; cannot be approved or locked."
                    data-testid={`zero-evidence-flag-${snap.id}`}
                  >
                    no evidence
                  </span>
                )}
              </div>
              {snap.topic_path && (
                <div className="row-sub" style={{ fontSize: 10, color: "var(--ink-mute)" }}>
                  {snap.topic_path}
                </div>
              )}
            </div>
          </div>
        </td>
        <td>
          <StatusBadge status={snap.status} />
        </td>
        <td className="num">
          {snap.exam_priority_score != null ? snap.exam_priority_score.toFixed(1) : "—"}
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
        <td style={{ color: "var(--ink-mute)", fontSize: 12 }}>{fmt(snap.reviewed_at)}</td>
        <td
          style={{ maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 12, color: "var(--ink-mute)" }}
          title={snap.reviewer_notes || ""}
        >
          {snap.reviewer_notes || "—"}
        </td>
        <td>
          <div className="row" style={{ gap: 4, justifyContent: "flex-end" }}>
            {canReview && actions(snap)}
          </div>
        </td>
      </tr>,
    ];
    if (expanded) {
      out.push(
        <EvidenceDrawer
          key={`${snap.id}-drawer`}
          snap={snap}
          scopeLabel={snapScopeLabel(snap)}
        />,
      );
    }
    return out;
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // ── Context loading / error states ────────────────────────────────────────
  if (contextLoading) {
    return (
      <div className="stack" role="status" aria-live="polite" data-testid="context-loading">
        <div style={{ padding: 24, color: "var(--ink-mute)", fontSize: 14 }}>
          Loading workspace…
        </div>
      </div>
    );
  }

  if (contextError) {
    return (
      <div className="stack" data-testid="context-error">
        <div className="err-row">
          Workspace failed to load: {contextError}. Refresh the page to try again.
        </div>
      </div>
    );
  }

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
          <h2
            ref={panelHeadingRef}
            tabIndex={-1}
            className="oc-title disp"
            style={{ fontSize: 20, marginTop: 3 }}
          >
            Score Snapshots
          </h2>
        </div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn small" onClick={() => load()} disabled={loadingSnaps || isMutating}>
            {loadingSnaps ? "Loading…" : "Refresh"}
          </button>
          {canReview && (
            <button
              className="btn primary small"
              onClick={compute}
              disabled={computeAction.busy}
              data-testid="compute-btn"
            >
              {computeAction.busy ? "Computing…" : "Compute snapshots"}
            </button>
          )}
        </div>
      </div>

      {/* Info strip */}
      <div style={{ padding: "9px 12px", borderRadius: 4, border: "1px solid var(--rule-soft)", background: "var(--paper-sunk)", fontSize: 12, color: "var(--ink-soft)" }}>
        Only <strong>locked</strong> snapshots are consumed by the planner. Approve
        and lock snapshots after verifying PYQ evidence counts. Compute and list always
        use the same scope — select it below before running compute.
        {!canReview && (
          <span style={{ marginLeft: 8, color: "var(--ink-mute)" }}>
            (read-only — you need the <code>exam_intelligence.review</code> permission to make changes)
          </span>
        )}
      </div>

      {/* Invalid scope warning — only shown after context is ready */}
      {invalidPhase && (
        <div className="err-row" data-testid="invalid-scope-error">
          Unknown scope &ldquo;{phaseParam}&rdquo; — defaulting to exam-wide.{" "}
          <button className="btn ghost small" onClick={() => setScope("")} style={{ marginLeft: 6 }}>
            Clear
          </button>
        </div>
      )}

      {/* Scope selector — disabled while a mutation is in flight */}
      <div className="row" style={{ gap: 6, alignItems: "center" }}>
        <span style={{ fontSize: 12, color: "var(--ink-mute)", marginRight: 2 }}>Scope:</span>
        {scopeOptions.map((opt) => (
          <button
            key={opt.id}
            className={"btn small" + (effectivePhase === opt.id ? " active" : "")}
            onClick={() => setScope(opt.id)}
            disabled={isMutating}
            data-testid={`scope-${opt.id || "exam"}`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Status filter — disabled while a mutation is in flight */}
      <div className="row" style={{ gap: 6 }}>
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            className={"btn small" + (statusFilter === f.value ? " active" : "")}
            onClick={() => setStatusFilter(f.value)}
            disabled={isMutating}
            data-testid={`filter-${f.value || "all"}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Load error */}
      {loadError && <div className="err-row" data-testid="load-error">{loadError}</div>}

      {/* Table */}
      <div className="card">
        {snapshots.length === 0 && !loadingSnaps ? (
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
              {loadingSnaps
                ? Array.from({ length: 3 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 9 }).map((__, j) => (
                        <td key={j}>
                          <div className="skel" style={{ height: 12, borderRadius: 3 }} />
                        </td>
                      ))}
                    </tr>
                  ))
                : groupSnapshots(snapshots).flatMap((section) => {
                    const header = (
                      <tr
                        key={`group-${section.group}`}
                        data-testid={`group-header-${section.group}`}
                      >
                        <td
                          colSpan={9}
                          style={{
                            background: "var(--paper-sunk)",
                            borderTop: "1px solid var(--rule-soft)",
                            fontSize: 11,
                            fontWeight: 600,
                            letterSpacing: "0.02em",
                            color: "var(--ink-soft)",
                            padding: "6px 10px",
                          }}
                        >
                          {section.label}{" "}
                          <span style={{ color: "var(--ink-mute)", fontWeight: 400 }}>
                            ({section.rows.length})
                          </span>
                        </td>
                      </tr>
                    );
                    return [header, ...section.rows.flatMap(renderSnapshotRow)];
                  })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="row" style={{ gap: 6, justifyContent: "flex-end", alignItems: "center", fontSize: 12 }}>
          <span style={{ color: "var(--ink-mute)" }}>
            Page {page + 1} of {totalPages} ({total} total)
          </span>
          <button
            className="btn small"
            onClick={() => { const p = page - 1; setPage(p); load(p); }}
            disabled={page === 0 || loadingSnaps}
            data-testid="page-prev-btn"
          >
            ← Prev
          </button>
          <button
            className="btn small"
            onClick={() => { const p = page + 1; setPage(p); load(p); }}
            disabled={page >= totalPages - 1 || loadingSnaps}
            data-testid="page-next-btn"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
