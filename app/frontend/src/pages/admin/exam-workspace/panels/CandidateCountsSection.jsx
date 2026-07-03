import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { useAuth } from "../../../../lib/authContext";
import { api } from "../../../../lib/api";

// Applied-vs-Appeared candidate-count editor + review surface (J3 PR 3).
//
// Lives ALONGSIDE the competition-metrics table on the Competition surface
// (no-new-surface rule, IA lock 2026-06-21). Backend contract:
//   create/patch  → /api/admin/exam-intelligence-cms/exam-candidate-counts
//                   (exam_intelligence.cms — canManage)
//   list/review   → /api/admin/exam-intelligence/candidate-counts
//                   (exam_intelligence.review — canReview for lifecycle)
//
// Only reviewed/locked, official-total (reservation_category_id IS NULL) rows
// feed the ratio denominator (candidate_counts.py preference appeared→applied).
// The per-category breakdown requires a reservation_category_id lookup that is
// not yet exposed to the client, so this editor curates the official total —
// exactly the value that drives selection_rate / candidates_per_vacancy.

const EI_BASE = "/api/admin/exam-intelligence";
const CMS_BASE = "/api/admin/exam-intelligence-cms";

const COUNT_TYPES = [
  { value: "applied", label: "Applied (registered)" },
  { value: "appeared", label: "Appeared (sat the exam)" },
];

// Mirrors _CANDIDATE_COUNT_SOURCE_BASIS (admin_exam_intel_cms.py).
const SOURCE_BASIS = ["manual", "official", "reviewed_analysis", "derived", "model_generated"];

// Lifecycle matches cms_review_candidate_count (migration 217) — identical
// shape to the competition-metric matrix. Publication (aspirant visibility /
// denominator switch) happens at pending_review -> reviewed; reviewed -> locked
// is a status bump on the already-published row.
const NEXT_ACTIONS = {
  draft: [{ to: "pending_review", label: "Submit for review" }],
  pending_review: [
    { to: "reviewed", label: "Mark reviewed" },
    { to: "rejected", label: "Reject", tone: "danger" },
  ],
  reviewed: [
    { to: "locked", label: "Lock", tone: "primary" },
    { to: "rejected", label: "Reject", tone: "danger" },
  ],
  locked: [{ to: "reviewed", label: "Reopen", requiresNotes: true }],
  rejected: [{ to: "draft", label: "Reset to draft" }],
};

const PUBLISHED = new Set(["reviewed", "locked"]);

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
  const numeric = Number(String(form.count_value).replace(/,/g, ""));
  if (form.count_value === "" || Number.isNaN(numeric) || numeric < 0) {
    return "Count value must be a non-negative number.";
  }
  return "";
}

export default function CandidateCountsSection() {
  const { exam, cycle, phases } = useExamWorkspace();
  const { user } = useAuth();

  const canManage =
    user?.role === "super_admin" ||
    (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.cms"));
  const canReview =
    user?.role === "super_admin" ||
    (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.review"));

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [adding, setAdding] = useState(false);
  const [savingNew, setSavingNew] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [reopenNotes, setReopenNotes] = useState({});

  const load = useCallback(async () => {
    if (!exam?.id) return;
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams({ status: "all", limit: "100" });
      qs.set("exam_id", exam.id);
      const d = await api.get(`${EI_BASE}/candidate-counts?${qs}`);
      setRows(d?.items || []);
    } catch (e) {
      setError(e?.message || "Failed to load candidate counts");
    } finally {
      setLoading(false);
    }
  }, [exam?.id]);

  useEffect(() => { load(); }, [load]);

  // Scope-restricted rows for the current cycle only (candidate counts are
  // cycle-scoped facts — a cycle-less view would mix cycles).
  const cycleRows = cycle?.id ? rows.filter((r) => r.exam_cycle_id === cycle.id) : rows;

  // Current published official-total denominator, appeared preferred over
  // applied (mirrors candidate_counts.py _DENOMINATOR_PREFERENCE). Not a
  // client-side ratio computation — just a label for which basis is live.
  const publishedTotals = cycleRows.filter(
    (r) => r.is_current_published && r.reservation_category_id == null && PUBLISHED.has(r.reviewer_status),
  );
  const denominatorRow =
    publishedTotals.find((r) => r.count_type === "appeared") ||
    publishedTotals.find((r) => r.count_type === "applied") ||
    null;

  function updateForm(patch) {
    setForm((f) => {
      const next = { ...f, ...patch };
      // Applied is always cycle-scoped with no phase (OD-3): keep the form valid
      // as the operator flips count_type.
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
    if (formError) { setError(formError); return; }
    setSavingNew(true);
    setError("");
    try {
      const payload = {
        exam_id: exam?.id || null,
        exam_cycle_id: cycle?.id || null,
        scope_kind: form.scope_kind,
        count_type: form.count_type,
        // Official total — reservation_category_id NULL is the only breakdown
        // the denominator reads and the only one the client can resolve today.
        reservation_category_id: null,
        count_value: parseInt(String(form.count_value).replace(/,/g, ""), 10),
        source_basis: form.source_basis,
      };
      if (form.scope_kind === "phase" && form.exam_phase_id) {
        payload.exam_phase_id = form.exam_phase_id;
      }
      if (form.reviewer_notes.trim()) payload.reviewer_notes = form.reviewer_notes.trim();
      await api.post(`${CMS_BASE}/exam-candidate-counts`, {
        reason: "Add applied/appeared candidate count via competition panel",
        payload,
      });
      setAdding(false);
      setForm(emptyForm());
      await load();
    } catch (e) {
      setError(e?.message || "Failed to save candidate count");
    } finally {
      setSavingNew(false);
    }
  }

  async function advance(row, action) {
    const notes = action.requiresNotes ? (reopenNotes[row.id] || "").trim() : undefined;
    if (action.requiresNotes && !notes) {
      setError("Reopening a locked row requires reviewer notes.");
      return;
    }
    setBusyId(row.id);
    setError("");
    try {
      await api.patch(`${EI_BASE}/candidate-counts/${encodeURIComponent(row.id)}/review`, {
        reviewer_status: action.to,
        ...(notes ? { reviewer_notes: notes } : {}),
      });
      setReopenNotes((n) => ({ ...n, [row.id]: "" }));
      await load();
    } catch (e) {
      setError(e?.message || "Transition failed");
    } finally {
      setBusyId(null);
    }
  }

  async function reopenForEdit(row) {
    const notes = (reopenNotes[row.id] || "").trim();
    if (!notes) {
      setError("Reopening a published row for edit requires reviewer notes.");
      return;
    }
    setBusyId(row.id);
    setError("");
    try {
      await api.post(`${EI_BASE}/candidate-counts/${encodeURIComponent(row.id)}/reopen-for-edit`, {
        reviewer_notes: notes,
      });
      setReopenNotes((n) => ({ ...n, [row.id]: "" }));
      await load();
    } catch (e) {
      setError(e?.message || "Reopen-for-edit failed");
    } finally {
      setBusyId(null);
    }
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
          <button className="btn small" onClick={load} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
          {canManage && !adding && (
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

      {error && <div className="err-row">{error}</div>}

      {denominatorRow && (
        <p className="text-[11px] text-clay-500" data-testid="candidate-count-denominator">
          Ratio denominator in use: <strong>{denominatorRow.count_value?.toLocaleString()}</strong>{" "}
          ({denominatorRow.count_type}). selection_rate / candidates_per_vacancy are derived
          server-side from this provenance-proven official total.
        </p>
      )}

      {canManage && adding && (
        <div className="card">
          <div className="card-head">
            <h4 className="oc-title">New candidate count</h4>
          </div>
          <div className="card-body grid3">
            <div className="field">
              <div className="field-lbl">Count type</div>
              <select
                className="input"
                data-testid="candidate-count-type"
                value={form.count_type}
                onChange={(e) => updateForm({ count_type: e.target.value })}
              >
                {COUNT_TYPES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div className="field">
              <div className="field-lbl">Scope</div>
              <select
                className="input"
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
                <div className="field-lbl">Phase</div>
                <select
                  className="input"
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
              <div className="field-lbl">Count value (official total)</div>
              <input
                className="input"
                data-testid="candidate-count-value"
                placeholder="e.g. 1,200,000"
                value={form.count_value}
                onChange={(e) => updateForm({ count_value: e.target.value })}
              />
            </div>
            <div className="field">
              <div className="field-lbl">Source basis</div>
              <select
                className="input"
                value={form.source_basis}
                onChange={(e) => updateForm({ source_basis: e.target.value })}
              >
                {SOURCE_BASIS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="field" style={{ gridColumn: "span 3" }}>
              <div className="field-lbl">Reviewer notes (optional)</div>
              <input
                className="input"
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
              disabled={savingNew || !!formError}
            >
              {savingNew ? "Saving…" : "Save as draft"}
            </button>
            <button className="btn ghost small" onClick={() => { setAdding(false); setError(""); }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {cycleRows.length === 0 && !loading && !adding && (
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

      {cycleRows.length > 0 && (
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
              {cycleRows.map((r) => {
                const actions = canReview ? (NEXT_ACTIONS[r.reviewer_status] || []) : [];
                const needsNotes = actions.some((a) => a.requiresNotes);
                const showReopenEdit = canManage && PUBLISHED.has(r.reviewer_status);
                return (
                  <tr key={r.id} data-testid={`candidate-count-row-${r.id}`}>
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
                        {(needsNotes || showReopenEdit) && (
                          <input
                            className="input"
                            style={{ maxWidth: 150 }}
                            placeholder="notes (required)"
                            value={reopenNotes[r.id] || ""}
                            onChange={(e) => setReopenNotes((n) => ({ ...n, [r.id]: e.target.value }))}
                          />
                        )}
                        {actions.map((a) => (
                          <button
                            key={a.to}
                            className={`btn small${a.tone === "primary" ? " primary" : ""}`}
                            data-testid={`candidate-count-action-${r.id}-${a.to}`}
                            disabled={busyId === r.id}
                            onClick={() => advance(r, a)}
                          >
                            {busyId === r.id ? "…" : a.label}
                          </button>
                        ))}
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
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
