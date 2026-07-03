import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { useAuth } from "../../../../lib/authContext";
import { api } from "../../../../lib/api";
import useApiAction from "../../../../lib/hooks/useApiAction";

// Applied-vs-Appeared candidate-count editor + review surface (J3 PR2 follow-up).
//
// Lives ALONGSIDE the competition-metrics table on the Competition surface
// (no-new-surface rule, IA lock 2026-06-21). Permission contract (J2 gate §D,
// permissions.py 92-98):
//   create / edit / reopen-for-edit / evidence-attach  → exam_intelligence.manage
//     (normal Manage-Exam canonical editing; NOT Advanced Repair)
//   lifecycle transitions (review)                     → exam_intelligence.review
//   list / read                                        → manage OR review
//   super_admin bypasses all of the above.
//
// Backend routes:
//   create/patch  → /api/admin/exam-intelligence-cms/exam-candidate-counts
//   list/review/  → /api/admin/exam-intelligence/candidate-counts
//   evidence      → /api/admin/exam-intelligence/candidate-counts/{id}/evidence
//
// Only reviewed/locked official-total rows feed the ratio denominator; the
// denominator itself is derived SERVER-SIDE (candidate_counts.py, preference
// appeared → applied). This UI never reproduces denominator selection — each
// row is labelled only by its own scope/type.

const EI_BASE = "/api/admin/exam-intelligence";
const CMS_BASE = "/api/admin/exam-intelligence-cms";

const COUNT_TYPES = [
  { value: "applied", label: "Applied (registered)" },
  { value: "appeared", label: "Appeared (sat the exam)" },
];

// Mirrors _CANDIDATE_COUNT_SOURCE_BASIS (admin_exam_intel_cms.py).
const SOURCE_BASIS = ["manual", "official", "reviewed_analysis", "derived", "model_generated"];

// Evidence kinds mirror the migration 219 CHECK / CandidateCountEvidenceBody.
const EVIDENCE_KINDS = [
  "official_notification", "official_result", "official_statistics",
  "corrigendum", "official_page", "reviewed_analysis",
];

// Lifecycle transitions aligned EXACTLY to the cms_review_candidate_count RPC
// matrix (migration 219, lines 523-529):
//   draft          -> pending_review | rejected
//   pending_review -> reviewed | rejected | draft
//   reviewed       -> locked            (NOT rejected — 219 permits only ->locked)
//   locked         -> reviewed          (reopen; reviewer_notes required)
//   rejected       -> draft
const NEXT_ACTIONS = {
  draft: [
    { to: "pending_review", label: "Submit for review" },
    { to: "rejected", label: "Reject", tone: "danger" },
  ],
  pending_review: [
    { to: "reviewed", label: "Mark reviewed", requiresEvidence: true },
    { to: "rejected", label: "Reject", tone: "danger" },
    { to: "draft", label: "Return to draft" },
  ],
  reviewed: [
    { to: "locked", label: "Lock", tone: "primary" },
  ],
  locked: [{ to: "reviewed", label: "Reopen", requiresNotes: true }],
  rejected: [{ to: "draft", label: "Reset to draft" }],
};

const PUBLISHED = new Set(["reviewed", "locked"]);
const WORKING = new Set(["draft", "pending_review"]);

function TrustBadge({ status }) {
  const map = {
    draft: { cls: "badge neutral", text: "draft" },
    pending_review: { cls: "badge pending", text: "pending review" },
    reviewed: { cls: "badge info", text: "reviewed" },
    locked: { cls: "badge ink", text: "locked" },
    rejected: { cls: "badge blocker", text: "rejected" },
  };
  const b = map[status] || map.draft;
  return <span className={b.cls}>{b.text}</span>;
}
TrustBadge.propTypes = { status: PropTypes.string };

const emptyForm = () => ({
  count_type: "applied",
  scope_kind: "cycle",
  exam_phase_id: "",
  count_value: "",
  source_basis: "official",
  reviewer_notes: "",
});

// Safe non-negative integer parse (checkpost P1-7). Rejects fractions (12.9)
// and exponent syntax (1e3) rather than truncating them via parseInt. Commas
// are allowed as thousands separators only.
function parseCount(raw) {
  const s = String(raw).replace(/,/g, "").trim();
  if (s === "") return { error: "Count value is required." };
  if (!/^\d+$/.test(s)) {
    return { error: "Count value must be a whole number (no decimals, exponents or signs)." };
  }
  const n = Number(s);
  if (!Number.isSafeInteger(n) || n < 0) {
    return { error: "Count value must be a non-negative whole number." };
  }
  return { value: n };
}

// Client-side mirror of _validate_candidate_count_scope (OD-3). The server is
// the authority; this stops the operator building an obviously invalid payload.
function scopeError(form) {
  if (form.count_type === "applied") {
    if (form.scope_kind !== "cycle" || form.exam_phase_id) {
      return "Applied counts must be cycle-scoped with no phase.";
    }
  }
  if (form.count_type === "appeared") {
    if (form.scope_kind === "phase" && !form.exam_phase_id) {
      return "A phase-scoped appeared count requires a phase.";
    }
    if (form.scope_kind === "cycle" && form.exam_phase_id) {
      return "A cycle-scoped appeared count must not carry a phase.";
    }
  }
  return parseCount(form.count_value).error || "";
}

export default function CandidateCountsSection() {
  const { exam, cycle, phases } = useExamWorkspace();
  const { user } = useAuth();

  const canManage =
    user?.role === "super_admin" ||
    (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.manage"));
  const canReview =
    user?.role === "super_admin" ||
    (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.review"));

  // Candidate counts are cycle-scoped facts — a cycle MUST be selected before
  // any read or write (checkpost A). Without one we never load rows and never
  // submit exam_cycle_id: null (which the backend rejects).
  const hasCycle = !!cycle?.id;

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [reopenNotes, setReopenNotes] = useState({});
  const [editId, setEditId] = useState(null);
  const [editForm, setEditForm] = useState({ count_value: "", source_basis: "official", reviewer_notes: "" });
  const [expandedId, setExpandedId] = useState(null);
  const [evidenceByRow, setEvidenceByRow] = useState({}); // { [id]: [rows] }

  const createAction = useApiAction();
  const rowAction = useApiAction();
  const evidenceAction = useApiAction();

  const loadEvidence = useCallback(async (rowId) => {
    try {
      const d = await api.get(`${EI_BASE}/candidate-counts/${encodeURIComponent(rowId)}/evidence`);
      setEvidenceByRow((m) => ({ ...m, [rowId]: d?.items || [] }));
    } catch {
      setEvidenceByRow((m) => ({ ...m, [rowId]: [] }));
    }
  }, []);

  const load = useCallback(async () => {
    if (!exam?.id || !cycle?.id) {
      setRows([]);
      return;
    }
    setLoading(true);
    setError("");
    try {
      // Server-side cycle scoping (checkpost B): never rely on a client-side
      // slice of an exam-wide top-N.
      const qs = new URLSearchParams({ status: "all", limit: "100" });
      qs.set("exam_id", exam.id);
      qs.set("exam_cycle_id", cycle.id);
      const d = await api.get(`${EI_BASE}/candidate-counts?${qs}`);
      const items = d?.items || [];
      setRows(items);
      // Eagerly fetch evidence for pending_review rows so the reviewed-gate is
      // accurate without requiring the operator to expand each row first.
      items
        .filter((r) => r.reviewer_status === "pending_review")
        .forEach((r) => loadEvidence(r.id));
    } catch (e) {
      setError(e?.message || "Failed to load candidate counts");
    } finally {
      setLoading(false);
    }
  }, [exam?.id, cycle?.id, loadEvidence]);

  useEffect(() => { load(); }, [load]);

  function updateForm(patch) {
    setForm((f) => {
      const next = { ...f, ...patch };
      if (next.count_type === "applied") {
        next.scope_kind = "cycle";
        next.exam_phase_id = "";
      }
      if (next.scope_kind === "cycle") next.exam_phase_id = "";
      return next;
    });
  }

  const formError = scopeError(form);

  async function saveNew() {
    if (!hasCycle) { setError("Select a cycle before adding a candidate count."); return; }
    if (formError) { setError(formError); return; }
    const parsed = parseCount(form.count_value);
    const payload = {
      exam_id: exam?.id || null,
      exam_cycle_id: cycle.id,
      scope_kind: form.scope_kind,
      count_type: form.count_type,
      reservation_category_id: null, // official total — the value the denominator reads
      count_value: parsed.value,
      source_basis: form.source_basis,
    };
    if (form.scope_kind === "phase" && form.exam_phase_id) {
      payload.exam_phase_id = form.exam_phase_id;
    }
    if (form.reviewer_notes.trim()) payload.reviewer_notes = form.reviewer_notes.trim();
    const res = await createAction.run({
      action: () => api.post(`${CMS_BASE}/exam-candidate-counts`, {
        reason: "Add applied/appeared candidate count via competition panel",
        payload,
      }),
      successMessage: "Candidate count saved as draft.",
      errorMessage: "Failed to save candidate count.",
    });
    if (res.ok) {
      setAdding(false);
      setForm(emptyForm());
      await load();
    }
  }

  async function advance(row, action) {
    if (action.requiresEvidence && !(evidenceByRow[row.id]?.length > 0)) {
      setError("Attach source-trusted evidence before marking this count reviewed.");
      return;
    }
    const notes = action.requiresNotes ? (reopenNotes[row.id] || "").trim() : undefined;
    if (action.requiresNotes && !notes) {
      setError("Reopening a locked row requires reviewer notes.");
      return;
    }
    setBusyId(row.id);
    const res = await rowAction.run({
      action: () => api.patch(`${EI_BASE}/candidate-counts/${encodeURIComponent(row.id)}/review`, {
        reviewer_status: action.to,
        ...(notes ? { reviewer_notes: notes } : {}),
      }),
      successMessage: `Moved to ${action.to.replace("_", " ")}.`,
      errorMessage: "Transition failed.",
    });
    setBusyId(null);
    if (res.ok) {
      setReopenNotes((n) => ({ ...n, [row.id]: "" }));
      await load();
    }
  }

  async function reopenForEdit(row) {
    const notes = (reopenNotes[row.id] || "").trim();
    if (!notes) {
      setError("Reopening a published row for edit requires reviewer notes.");
      return;
    }
    setBusyId(row.id);
    const res = await rowAction.run({
      action: () => api.post(`${EI_BASE}/candidate-counts/${encodeURIComponent(row.id)}/reopen-for-edit`, {
        reviewer_notes: notes,
      }),
      successMessage: "Cloned a fresh draft revision for edit.",
      errorMessage: "Reopen-for-edit failed.",
    });
    setBusyId(null);
    if (res.ok) {
      setReopenNotes((n) => ({ ...n, [row.id]: "" }));
      await load();
    }
  }

  function startEdit(row) {
    setEditId(row.id);
    setEditForm({
      count_value: String(row.count_value ?? ""),
      source_basis: row.source_basis || "official",
      reviewer_notes: "",
    });
  }

  async function saveEdit(row) {
    const parsed = parseCount(editForm.count_value);
    if (parsed.error) { setError(parsed.error); return; }
    const payload = {
      count_value: parsed.value,
      source_basis: editForm.source_basis,
    };
    if (editForm.reviewer_notes.trim()) payload.reviewer_notes = editForm.reviewer_notes.trim();
    setBusyId(row.id);
    const res = await rowAction.run({
      action: () => api.patch(`${CMS_BASE}/exam-candidate-counts/${encodeURIComponent(row.id)}`, {
        reason: "Curate candidate count via competition panel",
        payload,
      }),
      successMessage: "Candidate count updated.",
      errorMessage: "Failed to update candidate count.",
    });
    setBusyId(null);
    if (res.ok) {
      setEditId(null);
      await load();
    }
  }

  async function attachEvidence(row, ev) {
    const claim_value = {
      count_type: row.count_type,
      scope_kind: row.scope_kind,
      exam_phase_id: row.exam_phase_id || null,
      reservation_category_code: null, // official total (reservation_category_id IS NULL)
      count_value: row.count_value,
    };
    const payload = {
      evidence_kind: ev.evidence_kind,
      evidence_role: ev.evidence_role,
      source_id: ev.source_id.trim() || null,
      evidence_url: ev.evidence_url.trim() || null,
      claim_value,
    };
    if (!payload.source_id && !payload.evidence_url) {
      setError("Attach a source: provide a source_id or an evidence URL.");
      return;
    }
    const res = await evidenceAction.run({
      action: () => api.post(`${EI_BASE}/candidate-counts/${encodeURIComponent(row.id)}/evidence`, payload),
      successMessage: "Evidence attached.",
      errorMessage: "Failed to attach evidence.",
    });
    if (res.ok) await loadEvidence(row.id);
  }

  function scopeLabel(row) {
    if (row.scope_kind === "phase") {
      const p = (phases || []).find((x) => x.id === row.exam_phase_id);
      return `phase · ${p?.phase_name || row.exam_phase_id || "—"}`;
    }
    return "cycle aggregate";
  }

  return (
    <div className="stack" style={{ marginTop: 22 }} data-testid="candidate-counts-section">
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">Readiness · applied vs appeared</div>
          <h3 className="oc-title disp" style={{ fontSize: 17, marginTop: 3 }}>Candidate counts</h3>
        </div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn small" onClick={load} disabled={loading || !hasCycle}>
            {loading ? "Loading…" : "Refresh"}
          </button>
          {canManage && hasCycle && !adding && (
            <button
              className="btn primary small"
              data-testid="candidate-count-add"
              onClick={() => { setForm(emptyForm()); setAdding(true); }}
            >
              + Add count
            </button>
          )}
        </div>
      </div>

      {!hasCycle && (
        <div className="card" style={{ borderStyle: "dashed" }} data-testid="candidate-count-no-cycle">
          <div className="empty" style={{ padding: "24px 18px" }}>
            <div className="empty-title">Select a cycle</div>
            <div style={{ maxWidth: 440, margin: "0 auto" }}>
              Candidate counts are cycle-scoped facts. Choose an exam cycle above to
              view or add applied / appeared totals.
            </div>
          </div>
        </div>
      )}

      {error && <div className="err-row">{error}</div>}

      {hasCycle && canManage && adding && (
        <div className="card">
          <div className="card-head">
            <h4 className="oc-title">New candidate count</h4>
          </div>
          <div className="card-body grid3">
            <div className="field">
              <label className="field-lbl" htmlFor="cc-count-type">Count type</label>
              <select
                className="input"
                id="cc-count-type"
                data-testid="candidate-count-type"
                value={form.count_type}
                onChange={(e) => updateForm({ count_type: e.target.value })}
              >
                {COUNT_TYPES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div className="field">
              <label className="field-lbl" htmlFor="cc-scope">Scope</label>
              <select
                className="input"
                id="cc-scope"
                data-testid="candidate-count-scope"
                value={form.scope_kind}
                disabled={form.count_type === "applied"}
                onChange={(e) => updateForm({ scope_kind: e.target.value })}
              >
                <option value="cycle">Cycle aggregate</option>
                {form.count_type === "appeared" && <option value="phase">Phase</option>}
              </select>
            </div>
            {form.scope_kind === "phase" && (
              <div className="field">
                <label className="field-lbl" htmlFor="cc-phase">Phase</label>
                <select
                  className="input"
                  id="cc-phase"
                  data-testid="candidate-count-phase"
                  value={form.exam_phase_id}
                  onChange={(e) => updateForm({ exam_phase_id: e.target.value })}
                >
                  <option value="">— select phase —</option>
                  {(phases || []).map((p) => (
                    <option key={p.id} value={p.id}>{p.phase_name}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="field">
              <label className="field-lbl" htmlFor="cc-value">Count value (official total)</label>
              <input
                className="input"
                id="cc-value"
                data-testid="candidate-count-value"
                inputMode="numeric"
                placeholder="e.g. 1,200,000"
                value={form.count_value}
                onChange={(e) => updateForm({ count_value: e.target.value })}
              />
            </div>
            <div className="field">
              <label className="field-lbl" htmlFor="cc-basis">Source basis</label>
              <select
                className="input"
                id="cc-basis"
                data-testid="candidate-count-basis"
                value={form.source_basis}
                onChange={(e) => updateForm({ source_basis: e.target.value })}
              >
                {SOURCE_BASIS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="field" style={{ gridColumn: "span 3" }}>
              <label className="field-lbl" htmlFor="cc-notes">Reviewer notes (optional)</label>
              <input
                className="input"
                id="cc-notes"
                placeholder="context for the reviewer"
                value={form.reviewer_notes}
                onChange={(e) => updateForm({ reviewer_notes: e.target.value })}
              />
            </div>
          </div>
          {formError && <div className="err-row" data-testid="candidate-count-form-error">{formError}</div>}
          <div className="card-foot" style={{ justifyContent: "flex-start" }}>
            <button
              className="btn primary small"
              data-testid="candidate-count-save"
              onClick={saveNew}
              disabled={createAction.busy || !!formError}
            >
              {createAction.busy ? "Saving…" : "Save as draft"}
            </button>
            <button className="btn ghost small" onClick={() => { setAdding(false); setError(""); }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {hasCycle && rows.length === 0 && !loading && !adding && (
        <div className="card" style={{ borderStyle: "dashed" }}>
          <div className="empty" style={{ padding: "24px 18px" }}>
            <div className="empty-title">No candidate counts for this cycle</div>
            <div style={{ maxWidth: 440, margin: "0 auto" }}>
              Add the official applied / appeared totals. Only a reviewed or locked count
              feeds the selection-rate denominator — drafts stay internal.
            </div>
          </div>
        </div>
      )}

      {hasCycle && rows.length > 0 && (
        <div className="card">
          <table className="t" data-testid="candidate-counts-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Scope</th>
                <th>Category</th>
                <th>Count</th>
                <th>Basis</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const actions = canReview ? (NEXT_ACTIONS[r.reviewer_status] || []) : [];
                const needsNotes = actions.some((a) => a.requiresNotes);
                const showReopenEdit = canManage && PUBLISHED.has(r.reviewer_status);
                const showEdit = canManage && WORKING.has(r.reviewer_status);
                const hasEvidence = (evidenceByRow[r.id]?.length || 0) > 0;
                const expanded = expandedId === r.id;
                return (
                  <React.Fragment key={r.id}>
                    <tr data-testid={`candidate-count-row-${r.id}`}>
                      <td><span className="badge neutral no-dot">{r.count_type}</span></td>
                      <td className="row-sub">{scopeLabel(r)}</td>
                      <td className="row-sub">
                        {r.reservation_category_id == null ? "official total" : "category"}
                      </td>
                      <td className="num">{r.count_value?.toLocaleString() ?? "—"}</td>
                      <td className="row-sub">{r.source_basis || "—"}</td>
                      <td><TrustBadge status={r.reviewer_status} /></td>
                      <td style={{ textAlign: "right" }}>
                        <div className="row" style={{ justifyContent: "flex-end", gap: 6, flexWrap: "wrap" }}>
                          <button
                            className="btn small"
                            data-testid={`candidate-count-evidence-toggle-${r.id}`}
                            onClick={() => {
                              const next = expanded ? null : r.id;
                              setExpandedId(next);
                              if (next) loadEvidence(r.id);
                            }}
                          >
                            {expanded ? "Hide evidence" : "Evidence"}
                          </button>
                          {showEdit && (
                            <button
                              className="btn small"
                              data-testid={`candidate-count-edit-${r.id}`}
                              onClick={() => startEdit(r)}
                            >
                              Edit
                            </button>
                          )}
                          {(needsNotes || showReopenEdit) && (
                            <input
                              className="input"
                              style={{ maxWidth: 150 }}
                              aria-label={`Reviewer notes for candidate count ${r.id}`}
                              placeholder="notes (required)"
                              value={reopenNotes[r.id] || ""}
                              onChange={(e) => setReopenNotes((n) => ({ ...n, [r.id]: e.target.value }))}
                            />
                          )}
                          {actions.map((a) => {
                            const evGated = a.requiresEvidence && !hasEvidence;
                            return (
                              <button
                                key={a.to}
                                className={`btn small${a.tone === "primary" ? " primary" : ""}`}
                                data-testid={`candidate-count-action-${r.id}-${a.to}`}
                                title={evGated ? "Attach source-trusted evidence first" : undefined}
                                disabled={busyId === r.id || evGated}
                                onClick={() => advance(r, a)}
                              >
                                {busyId === r.id ? "…" : a.label}
                              </button>
                            );
                          })}
                          {showReopenEdit && (
                            <button
                              className="btn small"
                              data-testid={`candidate-count-reopen-edit-${r.id}`}
                              disabled={busyId === r.id}
                              onClick={() => reopenForEdit(r)}
                            >
                              Reopen for edit
                            </button>
                          )}
                        </div>
                        {actions.some((a) => a.requiresEvidence) && !hasEvidence && (
                          <div
                            className="text-[11px] text-clay-500"
                            data-testid={`candidate-count-evidence-blocker-${r.id}`}
                            style={{ marginTop: 4 }}
                          >
                            Attach source-trusted evidence before this count can be marked reviewed.
                          </div>
                        )}
                      </td>
                    </tr>
                    {editId === r.id && (
                      <tr>
                        <td colSpan={7}>
                          <div
                            className="card"
                            data-testid={`candidate-count-edit-form-${r.id}`}
                            style={{ background: "var(--panel-2, #fafafa)" }}
                          >
                            <div className="card-body grid3">
                              <div className="field">
                                <label className="field-lbl" htmlFor={`cc-edit-value-${r.id}`}>Count value</label>
                                <input
                                  className="input"
                                  id={`cc-edit-value-${r.id}`}
                                  data-testid={`candidate-count-edit-value-${r.id}`}
                                  inputMode="numeric"
                                  value={editForm.count_value}
                                  onChange={(e) => setEditForm((f) => ({ ...f, count_value: e.target.value }))}
                                />
                              </div>
                              <div className="field">
                                <label className="field-lbl" htmlFor={`cc-edit-basis-${r.id}`}>Source basis</label>
                                <select
                                  className="input"
                                  id={`cc-edit-basis-${r.id}`}
                                  data-testid={`candidate-count-edit-basis-${r.id}`}
                                  value={editForm.source_basis}
                                  onChange={(e) => setEditForm((f) => ({ ...f, source_basis: e.target.value }))}
                                >
                                  {SOURCE_BASIS.map((s) => <option key={s} value={s}>{s}</option>)}
                                </select>
                              </div>
                              <div className="field">
                                <label className="field-lbl" htmlFor={`cc-edit-notes-${r.id}`}>Notes (optional)</label>
                                <input
                                  className="input"
                                  id={`cc-edit-notes-${r.id}`}
                                  value={editForm.reviewer_notes}
                                  onChange={(e) => setEditForm((f) => ({ ...f, reviewer_notes: e.target.value }))}
                                />
                              </div>
                            </div>
                            <div className="card-foot" style={{ justifyContent: "flex-start" }}>
                              <button
                                className="btn primary small"
                                data-testid={`candidate-count-edit-save-${r.id}`}
                                disabled={busyId === r.id}
                                onClick={() => saveEdit(r)}
                              >
                                {busyId === r.id ? "Saving…" : "Save changes"}
                              </button>
                              <button className="btn ghost small" onClick={() => setEditId(null)}>Cancel</button>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                    {expanded && (
                      <tr>
                        <td colSpan={7}>
                          <EvidencePanel
                            row={r}
                            items={evidenceByRow[r.id]}
                            canManage={canManage}
                            busy={evidenceAction.busy}
                            onAttach={(ev) => attachEvidence(r, ev)}
                          />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function EvidencePanel({ row, items, canManage, busy, onAttach }) {
  const [ev, setEv] = useState({
    evidence_kind: "official_notification",
    evidence_role: "primary",
    source_id: "",
    evidence_url: "",
  });
  const canAttach = canManage && WORKING.has(row.reviewer_status);
  const list = items || [];
  return (
    <div
      className="card"
      style={{ background: "var(--panel-2, #fafafa)" }}
      data-testid={`candidate-count-evidence-panel-${row.id}`}
    >
      <div className="card-head"><h4 className="oc-title">Evidence</h4></div>
      <div className="card-body">
        {list.length === 0 && (
          <div className="text-[12px] text-clay-500" data-testid={`candidate-count-evidence-empty-${row.id}`}>
            No evidence attached yet.
          </div>
        )}
        {list.length > 0 && (
          <ul style={{ fontSize: 12, listStyle: "none", padding: 0, margin: 0 }}>
            {list.map((it) => (
              <li key={it.id} style={{ padding: "4px 0", borderBottom: "1px solid var(--border, #eee)" }}>
                <strong>{it.evidence_kind}</strong> ({it.evidence_role})
                {it.evidence_url ? (
                  <> — <a href={it.evidence_url} target="_blank" rel="noreferrer">{it.evidence_url}</a></>
                ) : null}
                {" — claim: "}{JSON.stringify(it.claim_value)}
              </li>
            ))}
          </ul>
        )}
        {canAttach && (
          <div
            className="row"
            style={{ gap: 6, flexWrap: "wrap", marginTop: 10 }}
            data-testid={`candidate-count-evidence-form-${row.id}`}
          >
            <div className="field" style={{ minWidth: 170 }}>
              <label className="field-lbl" htmlFor={`cc-ev-kind-${row.id}`}>Evidence kind</label>
              <select
                className="input"
                id={`cc-ev-kind-${row.id}`}
                data-testid={`candidate-count-evidence-kind-${row.id}`}
                value={ev.evidence_kind}
                onChange={(e) => setEv((f) => ({ ...f, evidence_kind: e.target.value }))}
              >
                {EVIDENCE_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
            </div>
            <div className="field" style={{ minWidth: 130 }}>
              <label className="field-lbl" htmlFor={`cc-ev-role-${row.id}`}>Role</label>
              <select
                className="input"
                id={`cc-ev-role-${row.id}`}
                value={ev.evidence_role}
                onChange={(e) => setEv((f) => ({ ...f, evidence_role: e.target.value }))}
              >
                <option value="primary">primary</option>
                <option value="supporting">supporting</option>
              </select>
            </div>
            <div className="field" style={{ minWidth: 190 }}>
              <label className="field-lbl" htmlFor={`cc-ev-source-${row.id}`}>Source registry id</label>
              <input
                className="input"
                id={`cc-ev-source-${row.id}`}
                data-testid={`candidate-count-evidence-source-${row.id}`}
                placeholder="source_registry id (trusted)"
                value={ev.source_id}
                onChange={(e) => setEv((f) => ({ ...f, source_id: e.target.value }))}
              />
            </div>
            <div className="field" style={{ minWidth: 220 }}>
              <label className="field-lbl" htmlFor={`cc-ev-url-${row.id}`}>Evidence URL</label>
              <input
                className="input"
                id={`cc-ev-url-${row.id}`}
                data-testid={`candidate-count-evidence-url-${row.id}`}
                placeholder="official notification / result URL"
                value={ev.evidence_url}
                onChange={(e) => setEv((f) => ({ ...f, evidence_url: e.target.value }))}
              />
            </div>
            <button
              className="btn small primary"
              data-testid={`candidate-count-evidence-attach-${row.id}`}
              disabled={busy}
              onClick={() => onAttach(ev)}
            >
              {busy ? "Attaching…" : "Attach evidence"}
            </button>
          </div>
        )}
        {!canAttach && WORKING.has(row.reviewer_status) && (
          <div className="text-[11px] text-clay-500" style={{ marginTop: 8 }}>
            Manage permission is required to attach evidence.
          </div>
        )}
        {PUBLISHED.has(row.reviewer_status) && (
          <div className="text-[11px] text-clay-500" style={{ marginTop: 8 }}>
            Evidence is append-only and frozen once this row is reviewed/locked.
          </div>
        )}
      </div>
    </div>
  );
}

EvidencePanel.propTypes = {
  row: PropTypes.object.isRequired,
  items: PropTypes.array,
  canManage: PropTypes.bool,
  busy: PropTypes.bool,
  onAttach: PropTypes.func.isRequired,
};
