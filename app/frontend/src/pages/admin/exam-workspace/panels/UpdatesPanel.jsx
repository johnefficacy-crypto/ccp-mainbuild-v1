import React, { useCallback, useEffect, useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { api } from "../../../../lib/api";

function TrustBadge({ status }) {
  const map = {
    pending:          { cls: "badge pending",  text: "pending" },
    needs_correction: { cls: "badge blocker",  text: "needs fix" },
    draft:            { cls: "badge neutral",  text: "draft" },
    verified:         { cls: "badge info",     text: "verified" },
    locked:           { cls: "badge ink",      text: "locked" },
  };
  const b = map[status] || map.pending;
  return <span className={b.cls}>{b.text}</span>;
}

const EI_BASE = "/api/admin/exam-intelligence";

export default function UpdatesPanel({ status: statusFilter = null, rowId = null }) {
  const { exam } = useExamWorkspace();

  const [updates, setUpdates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [adding, setAdding] = useState(false);
  const [deepLinkNotFound, setDeepLinkNotFound] = useState(false);

  const [newTitle, setNewTitle] = useState("");
  const [newSource, setNewSource] = useState("");
  const [newKind, setNewKind] = useState("official");
  const [savingNew, setSavingNew] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams({ limit: "200" });
      if (exam?.id) qs.set("exam_id", exam.id);
      qs.set("status", statusFilter || "all");
      const d = await api.get(`${EI_BASE}/policy-updates?${qs}`);
      setUpdates(d?.items || []);
    } catch (e) {
      setError(e?.message || "Failed to load updates");
    } finally {
      setLoading(false);
    }
  }, [exam?.id, statusFilter]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!rowId || loading) return;
    setDeepLinkNotFound(!updates.some((u) => u.id === rowId));
  }, [rowId, updates, loading]);

  async function verify(id) {
    setBusyId(id);
    setError("");
    try {
      await api.patch(`${EI_BASE}/policy-updates/${encodeURIComponent(id)}/review`, {
        reviewer_status: "verified",
      });
      await load();
    } catch (e) {
      setError(e?.message || "Verify failed");
    } finally {
      setBusyId(null);
    }
  }

  async function addUpdate() {
    if (!newTitle.trim()) return;
    setSavingNew(true);
    setError("");
    try {
      await api.post("/api/admin/exam-intelligence-cms/policy-updates", {
        reason: "Add policy update via workspace updates panel",
        payload: {
          exam_id: exam?.id || null,
          // update_type is required and must be in _POLICY_UPDATE_TYPES
          // (admin_exam_intel_cms.py:1256). "notification_change" is the
          // generic default for an operator-entered update.
          update_type: "notification_change",
          title: newTitle.trim(),
          source_url: newSource.trim() || null,
          source_type: newKind,
        },
      });
      setNewTitle(""); setNewSource(""); setNewKind("official"); setAdding(false);
      await load();
    } catch (e) {
      setError(e?.message || "Failed to add update");
    } finally {
      setSavingNew(false);
    }
  }

  const impactClass = (u) => {
    if (u.affects_plan) return "impact-pill warn";
    if (u.claim_status === "blocked" || u.reviewer_status === "needs_correction") return "impact-pill bad";
    return "impact-pill";
  };

  const impactLabel = (u) => {
    if (u.change_summary) return u.change_summary;
    if (u.affects_plan) return "May affect plan";
    return "No plan impact";
  };

  return (
    <div className="stack">
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">Readiness · policy updates</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>Updates</h2>
        </div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn small" onClick={load} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
          <button className="btn primary small" onClick={() => setAdding((v) => !v)}>
            + Add update
          </button>
        </div>
      </div>

      <div
        className="banner"
        style={{
          padding: "9px 12px",
          borderRadius: 4,
          border: "1px solid var(--rule-soft)",
          background: "var(--paper-sunk)",
          fontSize: 12,
          color: "var(--ink-soft)",
        }}
      >
        Aggregator updates can't change the plan until paired with an official source. Research
        informs strategy only.
      </div>

      {adding && (
        <div className="card">
          <div className="card-body row" style={{ gap: 8, flexWrap: "wrap" }}>
            <input
              className="input"
              style={{ maxWidth: 320 }}
              placeholder="Update title"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              autoFocus
            />
            <input
              className="input"
              style={{ maxWidth: 260 }}
              placeholder="Source URL"
              value={newSource}
              onChange={(e) => setNewSource(e.target.value)}
            />
            <select
              className="input"
              style={{ maxWidth: 150 }}
              value={newKind}
              onChange={(e) => setNewKind(e.target.value)}
            >
              <option value="official">official</option>
              <option value="aggregator">aggregator</option>
              <option value="research">research</option>
            </select>
            <button className="btn primary small" onClick={addUpdate} disabled={savingNew}>
              {savingNew ? "Saving…" : "Add as draft"}
            </button>
            <button className="btn ghost small" onClick={() => setAdding(false)}>Cancel</button>
          </div>
        </div>
      )}

      {error && <div className="err-row">{error}</div>}
      {deepLinkNotFound && (
        <div className="warn-row" data-testid="update-deep-link-not-found">
          Update {rowId} was not found for this exam.
        </div>
      )}

      <div className="card">
        {updates.length === 0 && !loading ? (
          <div className="empty">
            <div className="empty-title">No updates yet</div>
            <div>Add official, aggregator or research updates above.</div>
          </div>
        ) : (
          <table className="t">
            <thead>
              <tr>
                <th>Update</th>
                <th>Source</th>
                <th>Plan impact</th>
                <th>Added</th>
                <th>Trust</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {updates.map((u) => (
                <tr
                  key={u.id}
                  data-testid={`update-row-${u.id}`}
                  style={u.id === rowId ? { background: "var(--paper-light)", outline: "2px solid var(--ink-accent)" } : undefined}
                >
                  <td>
                    <div className="row-ttl">{u.title}</div>
                    <div className="row-sub">
                      <span
                        className={
                          "stamp stamp-" +
                          (u.source_type === "official"
                            ? "official"
                            : u.source_type === "aggregator"
                            ? "aggregator"
                            : "research")
                        }
                      >
                        {u.source_type ?? "official"}
                      </span>
                    </div>
                  </td>
                  <td className="row-sub" style={{ wordBreak: "break-all", maxWidth: 200 }}>
                    {u.source_url ?? u.source ?? "—"}
                  </td>
                  <td>
                    <span className={impactClass(u)}>{impactLabel(u)}</span>
                  </td>
                  <td className="num" style={{ color: "var(--ink-mute)" }}>
                    {u.created_at
                      ? new Date(u.created_at).toLocaleDateString("en-IN", {
                          day: "numeric", month: "short", year: "numeric",
                        })
                      : "—"}
                  </td>
                  <td>
                    <TrustBadge status={u.reviewer_status ?? "pending"} />
                  </td>
                  <td style={{ textAlign: "right" }}>
                    {u.reviewer_status !== "verified" && u.reviewer_status !== "locked" && (
                      <button
                        className="btn small primary"
                        disabled={busyId === u.id}
                        onClick={() => verify(u.id)}
                      >
                        {busyId === u.id ? "…" : "Verify"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
