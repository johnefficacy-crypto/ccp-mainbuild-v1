/**
 * CoveragePanel — exam_topic_coverage derive / review / lock workbench.
 *
 * Sibling of ScoreSnapshotPanel (same exam-workspace PyQ workbench shell,
 * mounted as ?view=coverage). No standalone route — no-new-surface rule.
 *
 * This panel closes the loop documented in
 * docs/status/coverage-pipeline-and-design-inventory-2026-08-27.md Part C:
 * `exam_topic_coverage` already had working backend routes but NO frontend
 * caller. It wires the three EXISTING routes — no backend change:
 *   POST   .../exams/{exam_id}/coverage/derive   body: { exam_phase_id? } → draft coverage rows
 *   GET    .../topic-coverage?exam_id=&status=&limit=&offset=            → { items, count }
 *   PATCH  .../topic-coverage/{id}/review          body: { reviewer_status } → row transition
 *
 * Locking is a deliberate manual operator action (OD-4): derive NEVER
 * auto-locks. Only `locked` coverage reaches Study OS / learner surfaces.
 *
 * Permission gates (mirrors the backend):
 *   canManage (exam_intelligence.manage) → Derive button (writes draft rows).
 *   canReview (exam_intelligence.review) → Lock / Unlock / bulk-lock actions.
 *
 * The coverage review route is a plain update that accepts any target state
 * directly, so a draft row locks in one PATCH (no two-hop matrix — unlike the
 * snapshot route).
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { api } from "../../../../lib/api";
import useApiAction from "../../../../lib/hooks/useApiAction";

const EI_BASE = "/api/admin/exam-intelligence";
const PAGE_SIZE = 50;

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_BADGE = {
  draft:          { cls: "badge neutral",  text: "draft" },
  pending_review: { cls: "badge warn",     text: "pending review" },
  reviewed:       { cls: "badge info",     text: "reviewed" },
  locked:         { cls: "badge resolved", text: "locked" },
  rejected:       { cls: "badge blocker",  text: "rejected" },
};

function StatusBadge({ status }) {
  const b = STATUS_BADGE[status] || { cls: "badge neutral", text: status };
  return <span className={b.cls}>{b.text}</span>;
}

const STATUS_FILTERS = [
  { value: "",               label: "All" },
  { value: "draft",          label: "Draft" },
  { value: "pending_review", label: "Pending" },
  { value: "reviewed",       label: "Reviewed" },
  { value: "locked",         label: "Locked" },
  { value: "rejected",       label: "Rejected" },
];

function fmt(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
  });
}

// ─── Panel ────────────────────────────────────────────────────────────────────

export default function CoveragePanel({ canReview = false, canManage = false }) {
  const {
    exam, phases, cycles,
    loading: contextLoading,
    error: contextError,
  } = useExamWorkspace();

  const [searchParams, setSearchParams] = useSearchParams();

  // Scope: ?phase=<id> scopes the Derive action; absent = exam-wide.
  // The list route (GET /topic-coverage) has no phase filter, so the table
  // shows every coverage row for the exam regardless of scope — scope governs
  // derive only. Phase validation waits for context to finish loading.
  const phaseParam = searchParams.get("phase") || "";
  const contextReady = !contextLoading && !contextError;
  const validPhase = contextReady ? phases.find((p) => p.id === phaseParam) : undefined;
  const invalidPhase = contextReady && phaseParam !== "" && !validPhase;
  const effectivePhase = invalidPhase ? "" : phaseParam;

  const [rows, setRows]           = useState([]);
  const [loadingRows, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [statusFilter, setStatus] = useState("");
  const [page, setPage]           = useState(0);
  const [total, setTotal]         = useState(0);
  const [bulkBusy, setBulkBusy]   = useState(false);
  const [bulkNote, setBulkNote]   = useState("");

  const panelHeadingRef = useRef(null);
  const loadGenRef = useRef(0);

  const deriveAction = useApiAction();
  const reviewAction = useApiAction();

  const isMutating = deriveAction.busy || reviewAction.busy || bulkBusy;

  const load = useCallback(async (pageOverride) => {
    if (!exam?.id) return;
    if (!contextReady) return;
    const targetPage = pageOverride ?? page;
    const gen = ++loadGenRef.current;
    setLoading(true);
    setLoadError("");
    setRows([]);
    try {
      const qs = new URLSearchParams();
      qs.set("exam_id", exam.id);
      if (statusFilter) qs.set("status", statusFilter);
      qs.set("limit", String(PAGE_SIZE));
      qs.set("offset", String(targetPage * PAGE_SIZE));
      const d = await api.get(`${EI_BASE}/topic-coverage?${qs}`);
      if (gen !== loadGenRef.current) return;
      setRows(d?.items || []);
      setTotal(d?.count ?? 0);
    } catch (e) {
      if (gen !== loadGenRef.current) return;
      setLoadError(e?.message || "Failed to load coverage rows");
      setRows([]);
    } finally {
      if (gen === loadGenRef.current) setLoading(false);
    }
  }, [exam?.id, statusFilter, contextReady, page]);

  const loadRef = useRef(load);
  useEffect(() => { loadRef.current = load; }, [load]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(0); }, [statusFilter]);

  function setScope(phaseId) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (phaseId) next.set("phase", phaseId);
      else next.delete("phase");
      return next;
    });
  }

  async function derive() {
    const body = effectivePhase ? { exam_phase_id: effectivePhase } : {};
    const result = await deriveAction.run({
      action: () => api.post(
        `${EI_BASE}/exams/${encodeURIComponent(exam.id)}/coverage/derive`,
        body,
      ),
      successMessage: "Derive finished.",
      errorMessage: "Derive failed.",
    });
    if (result?.ok) await loadRef.current();
  }

  async function setRowStatus(rowId, reviewerStatus) {
    return reviewAction.run({
      action: () => api.patch(
        `${EI_BASE}/topic-coverage/${encodeURIComponent(rowId)}/review`,
        { reviewer_status: reviewerStatus },
      ),
      errorMessage: "Review action failed.",
    });
  }

  async function handleRow(row, reviewerStatus) {
    const result = await setRowStatus(row.id, reviewerStatus);
    if (result?.ok) await loadRef.current();
  }

  // Bulk-lock: loop the EXISTING per-row PATCH over every draft row currently
  // shown. No backend bulk endpoint — one PATCH per row, sequential so a mid-
  // loop failure stops cleanly and the count reflects what actually locked.
  const draftRows = rows.filter((r) => r.status === "draft");

  async function bulkLockDrafts() {
    if (draftRows.length === 0) return;
    setBulkBusy(true);
    setBulkNote("");
    let locked = 0;
    let failed = 0;
    for (const row of draftRows) {
      try {
        await api.patch(
          `${EI_BASE}/topic-coverage/${encodeURIComponent(row.id)}/review`,
          { reviewer_status: "locked" },
        );
        locked += 1;
      } catch {
        failed += 1;
      }
    }
    setBulkBusy(false);
    setBulkNote(
      failed === 0
        ? `Locked ${locked} draft row${locked === 1 ? "" : "s"}.`
        : `Locked ${locked}, ${failed} failed.`,
    );
    await loadRef.current();
  }

  function rowActions(row) {
    const busy = reviewAction.busy || bulkBusy;
    if (row.status === "locked") {
      return (
        <button
          className="btn small"
          disabled={busy}
          onClick={() => handleRow(row, "draft")}
          data-testid={`action-${row.id}-unlock`}
        >
          {busy ? "…" : "Unlock"}
        </button>
      );
    }
    return (
      <button
        className="btn primary small"
        disabled={busy}
        onClick={() => handleRow(row, "locked")}
        data-testid={`action-${row.id}-lock`}
      >
        {busy ? "…" : "Lock"}
      </button>
    );
  }

  const cycleLabel = (examCycleId) => {
    if (!examCycleId) return null;
    const c = (cycles || []).find((cy) => cy.id === examCycleId);
    if (!c) return examCycleId;
    return c.cycle_name || c.year || examCycleId;
  };

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

  const totalPages = Math.ceil(total / PAGE_SIZE);

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
      {/* Header */}
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">PYQ Intelligence · topic coverage</div>
          <h2
            ref={panelHeadingRef}
            tabIndex={-1}
            className="oc-title disp"
            style={{ fontSize: 20, marginTop: 3 }}
          >
            Topic Coverage
          </h2>
        </div>
        <div className="row" style={{ justifyContent: "flex-end", gap: 6 }}>
          <button className="btn small" onClick={() => load()} disabled={loadingRows || isMutating}>
            {loadingRows ? "Loading…" : "Refresh"}
          </button>
          {canReview && (
            <button
              className="btn small"
              onClick={bulkLockDrafts}
              disabled={isMutating || draftRows.length === 0}
              data-testid="bulk-lock-btn"
            >
              {bulkBusy ? "Locking…" : `Lock all drafts (${draftRows.length})`}
            </button>
          )}
          {canManage && (
            <button
              className="btn primary small"
              onClick={derive}
              disabled={deriveAction.busy || isMutating}
              data-testid="derive-btn"
            >
              {deriveAction.busy ? "Deriving…" : "Derive coverage"}
            </button>
          )}
        </div>
      </div>

      {/* Info strip */}
      <div style={{ padding: "9px 12px", borderRadius: 4, border: "1px solid var(--rule-soft)", background: "var(--paper-sunk)", fontSize: 12, color: "var(--ink-soft)" }}>
        Only <strong>locked</strong> coverage rows reach Study OS. Derive projects
        draft rows from locked score snapshots + verified syllabus mentions;
        review and lock them deliberately — derivation never auto-locks. The scope
        below applies to <strong>Derive</strong> only; the table lists all coverage
        rows for this exam.
        {!canManage && !canReview && (
          <span style={{ marginLeft: 8, color: "var(--ink-mute)" }}>
            (read-only — <code>exam_intelligence.manage</code> to derive,{" "}
            <code>exam_intelligence.review</code> to lock)
          </span>
        )}
      </div>

      {/* Invalid scope warning */}
      {invalidPhase && (
        <div className="err-row" data-testid="invalid-scope-error">
          Unknown scope &ldquo;{phaseParam}&rdquo; — defaulting to exam-wide.{" "}
          <button className="btn ghost small" onClick={() => setScope("")} style={{ marginLeft: 6 }}>
            Clear
          </button>
        </div>
      )}

      {/* Derive scope selector */}
      <div className="row" style={{ gap: 6, alignItems: "center" }}>
        <span style={{ fontSize: 12, color: "var(--ink-mute)", marginRight: 2 }}>Derive scope:</span>
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

      {/* Status filter */}
      <div className="row" style={{ gap: 6 }}>
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            className={"btn small" + (statusFilter === f.value ? " active" : "")}
            onClick={() => setStatus(f.value)}
            disabled={isMutating}
            data-testid={`filter-${f.value || "all"}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {bulkNote && <div className="row" style={{ fontSize: 12, color: "var(--ink-mute)" }} data-testid="bulk-note">{bulkNote}</div>}
      {loadError && <div className="err-row" data-testid="load-error">{loadError}</div>}

      {/* Table */}
      <div className="card">
        {rows.length === 0 && !loadingRows ? (
          <div className="empty">
            <div className="empty-title">No coverage rows</div>
            <div>
              {statusFilter
                ? `No coverage rows with status "${statusFilter}".`
                : 'Run "Derive coverage" to project draft rows from locked snapshots + verified syllabus mentions.'}
            </div>
          </div>
        ) : (
          <table className="t">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Subject</th>
                <th>Status</th>
                <th className="num">Priority</th>
                <th>High yield</th>
                <th className="num">Evidence</th>
                <th>Reviewed</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {loadingRows
                ? Array.from({ length: 3 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 8 }).map((__, j) => (
                        <td key={j}><div className="skel" style={{ height: 12, borderRadius: 3 }} /></td>
                      ))}
                    </tr>
                  ))
                : rows.map((row) => (
                    <tr key={row.id} data-testid={`coverage-row-${row.id}`}>
                      <td>
                        <div className="row-ttl" style={{ fontSize: 12 }} title={row.topic_id}>
                          {row.topic || row.topic_id || "—"}
                        </div>
                      </td>
                      <td style={{ fontSize: 12, color: "var(--ink-mute)" }}>{row.subject || "—"}</td>
                      <td><StatusBadge status={row.status} /></td>
                      <td className="num">
                        {row.priority_score != null ? Number(row.priority_score).toFixed(1) : "—"}
                      </td>
                      <td>
                        {row.high_yield
                          ? <span className="badge info no-dot">yes</span>
                          : <span style={{ color: "var(--ink-mute)", fontSize: 12 }}>no</span>}
                      </td>
                      <td className="num">{row.evidence_count ?? "—"}</td>
                      <td style={{ color: "var(--ink-mute)", fontSize: 12 }}>{fmt(row.reviewed_at)}</td>
                      <td>
                        <div className="row" style={{ gap: 4, justifyContent: "flex-end" }}>
                          {canReview && rowActions(row)}
                        </div>
                      </td>
                    </tr>
                  ))}
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
            disabled={page === 0 || loadingRows}
            data-testid="page-prev-btn"
          >
            ← Prev
          </button>
          <button
            className="btn small"
            onClick={() => { const p = page + 1; setPage(p); load(p); }}
            disabled={page >= totalPages - 1 || loadingRows}
            data-testid="page-next-btn"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
