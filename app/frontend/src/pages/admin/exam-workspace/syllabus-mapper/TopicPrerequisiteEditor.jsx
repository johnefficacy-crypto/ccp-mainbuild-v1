import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { api } from "../../../../lib/api";
import useApiAction from "../../../../lib/hooks/useApiAction";

/**
 * J2-A′ — topic prerequisite editor with trust lifecycle.
 *
 * Gate docs/status/Topic-Prerequisite-Semantics-Gate-2026-07-01.md:
 * - mounted for canManage || canReview; manage controls (add/edit/submit/
 *   delete, only while draft/rejected) gated on canManage; review controls
 *   (approve/reject/lock/reopen/return-to-draft) gated on canReview.
 * - all mutations run through useApiAction; edges show reviewer_status.
 */
const BASE = "/api/admin/exam-intelligence-manage";
const RELATIONS = ["requires", "recommended_before", "supports", "foundation_for"];
const EDITABLE = new Set(["draft", "rejected"]);

export default function TopicPrerequisiteEditor({
  examId,
  topic,
  candidateTopics = [],
  canManage = false,
  canReview = false,
}) {
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ prerequisite_topic_id: "", relation_type: "requires", strength: "1.0", reason: "" });
  const [editing, setEditing] = useState(null); // { id, relation_type, strength, reason }
  const action = useApiAction();

  const nameOf = useCallback(
    (id) => candidateTopics.find((t) => t.id === id)?.name || id,
    [candidateTopics],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const params = new URLSearchParams({ exam_id: examId, topic_id: topic.id, limit: "50" });
      const r = await api.get(`${BASE}/topic-prerequisites?${params}`);
      setEdges(r?.items || []);
    } catch {
      setEdges([]);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [examId, topic.id]);

  useEffect(() => { load(); }, [load]);

  const busy = action.busy;

  function addEdge() {
    if (!form.prerequisite_topic_id || (form.reason || "").trim().length < 8) {
      action.run({ action: () => Promise.reject(new Error("Pick a prerequisite and a reason (min 8 chars).")),
        errorMessage: "Pick a prerequisite and a reason (min 8 chars)." });
      return;
    }
    action.run({
      action: () => api.post(`${BASE}/topic-prerequisites?exam_id=${examId}`, {
        reason: form.reason.trim(),
        payload: {
          topic_id: topic.id,
          prerequisite_topic_id: form.prerequisite_topic_id,
          relation_type: form.relation_type,
          strength: Number(form.strength),
        },
      }),
      successMessage: "Prerequisite added (draft).",
      errorMessage: "Could not add prerequisite.",
      onSuccess: () => { setAdding(false); setForm({ prerequisite_topic_id: "", relation_type: "requires", strength: "1.0", reason: "" }); load(); },
    });
  }

  function saveEdit() {
    if ((editing.reason || "").trim().length < 8) {
      action.run({ action: () => Promise.reject(new Error("A reason of at least 8 characters is required.")),
        errorMessage: "A reason of at least 8 characters is required." });
      return;
    }
    action.run({
      action: () => api.patch(`${BASE}/topic-prerequisites/${editing.id}?exam_id=${examId}`, {
        reason: editing.reason.trim(),
        payload: { relation_type: editing.relation_type, strength: Number(editing.strength) },
      }),
      successMessage: "Prerequisite updated.",
      errorMessage: "Could not update prerequisite.",
      onSuccess: () => { setEditing(null); load(); },
    });
  }

  function deleteEdge(e) {
    const reason = window.prompt(`Delete this prerequisite? Reason (min 8 chars):`, "");
    if (!reason || reason.trim().length < 8) return;
    action.run({
      action: () => api.del(`${BASE}/topic-prerequisites/${e.id}?exam_id=${examId}&reason=${encodeURIComponent(reason.trim())}`),
      successMessage: "Prerequisite deleted.",
      errorMessage: "Could not delete prerequisite.",
      onSuccess: load,
    });
  }

  function submitEdge(e) {
    action.run({
      action: () => api.post(`${BASE}/topic-prerequisites/${e.id}/submit?exam_id=${examId}`, { reason: "submit prerequisite for review" }),
      successMessage: "Submitted for review.",
      errorMessage: "Could not submit.",
      onSuccess: load,
    });
  }

  function review(e, targetStatus, opts = {}) {
    let reviewNotes;
    if (targetStatus === "reviewed" && e.reviewer_status === "locked") {
      reviewNotes = window.prompt("Reopen: enter review notes (required):", "");
      if (!reviewNotes || !reviewNotes.trim()) return;
    }
    action.run({
      action: () => api.post(`${BASE}/topic-prerequisites/${e.id}/review?exam_id=${examId}`, {
        reason: opts.reason || `review: ${targetStatus}`,
        target_status: targetStatus,
        review_notes: reviewNotes,
      }),
      successMessage: `Moved to ${targetStatus}.`,
      errorMessage: "Could not update review state.",
      onSuccess: load,
    });
  }

  return (
    <div className="mt-3 bg-white border border-slate-200 rounded p-3" data-testid="tpe-editor">
      <div className="text-xs font-semibold text-slate-600 mb-2">Prerequisites · {topic.name}</div>
      {error && (
        <div className="text-sm text-rose-600 mb-2" role="alert" data-testid="tpe-error">
          Could not load prerequisites. Editing is blocked.
        </div>
      )}
      {loading ? (
        <div className="text-sm text-slate-400">Loading…</div>
      ) : (
        <ul className="text-sm divide-y divide-slate-100 mb-2" data-testid="tpe-list">
          {edges.length === 0 && <li className="py-1 text-slate-400">No prerequisites.</li>}
          {edges.map((e) => {
            const editable = EDITABLE.has(e.reviewer_status);
            const outgoing = e.topic_id === topic.id; // this topic depends on the other
            const otherId = outgoing ? e.prerequisite_topic_id : e.topic_id;
            const label = outgoing ? `→ ${nameOf(otherId)}` : `← ${nameOf(otherId)} (dependent)`;
            return (
              <li key={e.id} className="py-1.5 flex items-center gap-2 flex-wrap" data-testid={`tpe-edge-${e.id}`}>
                <span className="flex-1">
                  {label}
                  <span className="text-slate-400"> · {e.relation_type} · {Number(e.strength).toFixed(2)}</span>
                </span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-600" data-testid={`tpe-status-${e.id}`}>
                  {e.reviewer_status}
                </span>
                {canManage && editable && (
                  <>
                    <button type="button" className="text-xs px-2 py-0.5 border rounded disabled:opacity-40"
                      onClick={() => setEditing({ id: e.id, relation_type: e.relation_type, strength: String(e.strength), reason: "" })}
                      disabled={busy} data-testid={`tpe-edit-${e.id}`}>Edit</button>
                    <button type="button" className="text-xs px-2 py-0.5 border rounded disabled:opacity-40"
                      onClick={() => submitEdge(e)} disabled={busy} data-testid={`tpe-submit-${e.id}`}>Submit</button>
                    <button type="button" className="text-xs px-2 py-0.5 border rounded text-rose-600 disabled:opacity-40"
                      onClick={() => deleteEdge(e)} disabled={busy} data-testid={`tpe-delete-${e.id}`}>Delete</button>
                  </>
                )}
                {canReview && e.reviewer_status === "pending_review" && (
                  <>
                    <button type="button" className="text-xs px-2 py-0.5 border rounded disabled:opacity-40"
                      onClick={() => review(e, "reviewed")} disabled={busy} data-testid={`tpe-approve-${e.id}`}>Approve</button>
                    <button type="button" className="text-xs px-2 py-0.5 border rounded disabled:opacity-40"
                      onClick={() => review(e, "rejected")} disabled={busy} data-testid={`tpe-reject-${e.id}`}>Reject</button>
                  </>
                )}
                {canReview && e.reviewer_status === "reviewed" && (
                  <>
                    <button type="button" className="text-xs px-2 py-0.5 border rounded disabled:opacity-40"
                      onClick={() => review(e, "locked")} disabled={busy} data-testid={`tpe-lock-${e.id}`}>Lock</button>
                    <button type="button" className="text-xs px-2 py-0.5 border rounded disabled:opacity-40"
                      onClick={() => review(e, "draft")} disabled={busy} data-testid={`tpe-return-${e.id}`}>Return to draft</button>
                  </>
                )}
                {canReview && e.reviewer_status === "locked" && (
                  <button type="button" className="text-xs px-2 py-0.5 border rounded disabled:opacity-40"
                    onClick={() => review(e, "reviewed")} disabled={busy} data-testid={`tpe-reopen-${e.id}`}>Reopen</button>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {canManage && editing && (
        <div className="flex gap-2 flex-wrap items-center mb-2" data-testid="tpe-edit-form">
          <span className="text-xs text-slate-500">Edit:</span>
          <select className="text-sm border rounded px-2 py-1" value={editing.relation_type}
            onChange={(ev) => setEditing({ ...editing, relation_type: ev.target.value })}
            aria-label="Edit relation type" data-testid="tpe-edit-relation">
            {RELATIONS.map((rel) => <option key={rel} value={rel}>{rel}</option>)}
          </select>
          <input className="text-sm border rounded px-2 py-1 w-20" type="number" min="0" max="1" step="0.01"
            value={editing.strength} onChange={(ev) => setEditing({ ...editing, strength: ev.target.value })}
            aria-label="Edit strength" data-testid="tpe-edit-strength" />
          <input className="text-sm border rounded px-2 py-1 flex-1" placeholder="reason (min 8 chars)"
            value={editing.reason} onChange={(ev) => setEditing({ ...editing, reason: ev.target.value })}
            aria-label="Edit reason" data-testid="tpe-edit-reason" />
          <button type="button" className="text-sm px-3 py-1 border rounded bg-slate-800 text-white disabled:opacity-40"
            onClick={saveEdit} disabled={busy} data-testid="tpe-edit-save">Save</button>
          <button type="button" className="text-sm px-3 py-1 border rounded"
            onClick={() => setEditing(null)} data-testid="tpe-edit-cancel">Cancel</button>
        </div>
      )}

      {canManage && !adding && (
        <button type="button" className="text-sm px-2 py-1 border rounded disabled:opacity-40"
          onClick={() => setAdding(true)} disabled={busy || error} data-testid="tpe-add-toggle">
          + Add prerequisite
        </button>
      )}

      {canManage && adding && (
        <div className="flex gap-2 flex-wrap items-center" data-testid="tpe-add-form">
          <select className="text-sm border rounded px-2 py-1" value={form.prerequisite_topic_id}
            onChange={(e) => setForm({ ...form, prerequisite_topic_id: e.target.value })}
            aria-label="Prerequisite topic" data-testid="tpe-prereq-select">
            <option value="">Prerequisite topic…</option>
            {candidateTopics.filter((t) => t.id !== topic.id).map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
          <select className="text-sm border rounded px-2 py-1" value={form.relation_type}
            onChange={(e) => setForm({ ...form, relation_type: e.target.value })}
            aria-label="Relation type" data-testid="tpe-relation-select">
            {RELATIONS.map((rel) => <option key={rel} value={rel}>{rel}</option>)}
          </select>
          <input className="text-sm border rounded px-2 py-1 w-20" type="number" min="0" max="1" step="0.01"
            value={form.strength} onChange={(e) => setForm({ ...form, strength: e.target.value })}
            aria-label="Strength" data-testid="tpe-strength" />
          <input className="text-sm border rounded px-2 py-1 flex-1" placeholder="reason (min 8 chars)"
            value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })}
            aria-label="Reason" data-testid="tpe-reason" />
          <button type="button" className="text-sm px-3 py-1 border rounded bg-slate-800 text-white disabled:opacity-40"
            onClick={addEdge} disabled={busy} data-testid="tpe-add-save">Add</button>
          <button type="button" className="text-sm px-3 py-1 border rounded"
            onClick={() => setAdding(false)} data-testid="tpe-add-cancel">Cancel</button>
        </div>
      )}
    </div>
  );
}

TopicPrerequisiteEditor.propTypes = {
  examId: PropTypes.string,
  topic: PropTypes.object.isRequired,
  candidateTopics: PropTypes.array,
  canManage: PropTypes.bool,
  canReview: PropTypes.bool,
};
