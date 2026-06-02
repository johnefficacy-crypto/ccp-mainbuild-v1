import React, { useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { api } from "../../../../lib/api";
import DateField from "../../../../shared/ui/DateField";
import { formatDDMMYYYY } from "../../../../shared/forms/dateFormat";

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

// exam_phases.phase_slug is a required column with no server-side default —
// it must be sent explicitly (see _PHASE_FIELDS, admin_exam_intel_cms.py:433).
function slugify(s) {
  return String(s || "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function formatPhaseWindow(phase) {
  if (phase.phase_start) {
    const start = formatDDMMYYYY(phase.phase_start);
    const end = phase.phase_end ? ` – ${formatDDMMYYYY(phase.phase_end)}` : "";
    return start + end;
  }
  // Legacy freeform fallback for un-backfilled rows.
  return phase.metadata?.phase_window ?? phase.phase_window ?? "TBD";
}

export default function SetupPanel() {
  const { exam, cycles, phases } = useExamWorkspace();

  const [addingPhase, setAddingPhase] = useState(false);
  const [pName, setPName] = useState("");
  const [pStart, setPStart] = useState(null);
  const [pEnd, setPEnd] = useState(null);
  const [phaseOrder, setPhaseOrder] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState("");

  async function addPhase() {
    if (!pName.trim()) return;
    setSaving(true);
    setSaveErr("");
    try {
      const activeCycle = cycles.find((c) => c.status === "active") || cycles[0];
      const name = pName.trim();
      await api.post("/api/admin/exam-intelligence-cms/exam-phases", {
        reason: "Add exam phase via workspace setup panel",
        payload: {
          exam_id: exam?.id,
          exam_cycle_id: activeCycle?.id || null,
          phase_name: name,
          phase_slug: slugify(name),
          phase_order: phaseOrder ? parseInt(phaseOrder, 10) : (phases.length + 1),
          // status enum: expected | active | completed | cancelled.
          status: "expected",
          phase_start: pStart || null,
          phase_end: pEnd || null,
          metadata: {},
        },
      });
      setPName(""); setPStart(null); setPEnd(null); setPhaseOrder(""); setAddingPhase(false);
      // context will refetch on next load; prompt user to refresh
    } catch (e) {
      setSaveErr(e?.message || "Failed to add phase");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack">
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">Always open · exam configuration</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>
            Set up this exam's cycles, phases &amp; sections.
          </h2>
        </div>
        <span className="anno">
          Edits land as <b>draft</b> — locked rows already live
        </span>
      </div>

      {/* Cycles */}
      <div className="card">
        <div className="card-head">
          <h3 className="oc-title">Cycles</h3>
        </div>
        {cycles.length === 0 ? (
          <div className="empty">
            <div className="empty-title">No cycles yet</div>
            <div>Create cycles in the Exam CMS.</div>
          </div>
        ) : (
          <table className="t">
            <thead>
              <tr>
                <th>Cycle</th>
                <th>Year</th>
                <th>Status</th>
                <th>Trust</th>
              </tr>
            </thead>
            <tbody>
              {cycles.map((c) => (
                <tr key={c.id}>
                  <td className="row-ttl">{c.cycle_name ?? c.name ?? c.id}</td>
                  <td className="num">{c.year}</td>
                  <td>
                    {c.status === "active"
                      ? <span className="badge info no-dot">active</span>
                      : <span className="badge neutral no-dot">{c.status ?? "archived"}</span>}
                  </td>
                  <td>
                    <TrustBadge status={c.status === "active" ? "locked" : "verified"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Phases */}
      <div className="card">
        <div className="card-head">
          <h3 className="oc-title">
            Phases
            {cycles.find((c) => c.status === "active") && (
              <span className="row-sub" style={{ marginLeft: 8, fontWeight: 400 }}>
                · {cycles.find((c) => c.status === "active")?.cycle_name}
              </span>
            )}
          </h3>
          {!addingPhase && (
            <button className="btn small" onClick={() => setAddingPhase(true)}>
              + Add phase
            </button>
          )}
        </div>
        <div className="card-body" style={{ paddingBottom: 4 }}>
          {phases.length === 0 ? (
            <div className="empty" style={{ padding: "16px 0" }}>
              <div className="empty-title">No phases defined</div>
              <div>Add the first phase below.</div>
            </div>
          ) : (
            <div className="phase-rail">
              {phases.map((p, i) => (
                <div
                  key={p.id}
                  className={
                    "phase" +
                    (p.status === "active" ? " active" : p.status === "completed" ? " done" : "")
                  }
                >
                  <div className="phase-num">PH-{i + 1}</div>
                  <div className="phase-name">{p.phase_name ?? p.name}</div>
                  <div className="phase-count">{formatPhaseWindow(p)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
        {addingPhase && (
          <div
            className="card-foot"
            style={{
              justifyContent: "flex-start",
              gap: 8,
              background: "var(--paper)",
              flexWrap: "wrap",
            }}
          >
            <input
              className="input"
              style={{ maxWidth: 200 }}
              placeholder="Phase name"
              value={pName}
              onChange={(e) => setPName(e.target.value)}
              autoFocus
            />
            <div style={{ minWidth: 180 }}>
              <DateField
                value={pStart}
                onChange={setPStart}
                mode="any"
                label="Phase start"
                name="phase_start"
                id="setup-phase-start"
              />
            </div>
            <div style={{ minWidth: 180 }}>
              <DateField
                value={pEnd}
                onChange={setPEnd}
                mode="any"
                label="Phase end"
                name="phase_end"
                id="setup-phase-end"
              />
            </div>
            <input
              className="input"
              style={{ maxWidth: 80 }}
              placeholder="Order"
              type="number"
              value={phaseOrder}
              onChange={(e) => setPhaseOrder(e.target.value)}
            />
            <button className="btn primary small" onClick={addPhase} disabled={saving}>
              {saving ? "Saving…" : "Add phase"}
            </button>
            <button
              className="btn ghost small"
              onClick={() => { setAddingPhase(false); setSaveErr(""); }}
            >
              Cancel
            </button>
            {saveErr && (
              <span className="err-row" style={{ padding: "3px 8px" }}>{saveErr}</span>
            )}
          </div>
        )}
      </div>

      {/* Exam info */}
      <div className="card">
        <div className="card-head"><h3 className="oc-title">Exam details</h3></div>
        <div className="card-body grid2">
          <div className="field">
            <div className="field-lbl">Name</div>
            <div className="field-val">{exam?.name ?? "—"}</div>
          </div>
          <div className="field">
            <div className="field-lbl">Slug</div>
            <div className="field-val mono">{exam?.slug ?? "—"}</div>
          </div>
          <div className="field">
            <div className="field-lbl">Type</div>
            <div className="field-val">{exam?.exam_type ?? "—"}</div>
          </div>
          <div className="field">
            <div className="field-lbl">Family</div>
            <div className="field-val">{exam?.family_name ?? exam?.family ?? "—"}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
