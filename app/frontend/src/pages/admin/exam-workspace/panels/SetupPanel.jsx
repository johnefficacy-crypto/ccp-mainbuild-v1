import React, { useEffect, useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { api } from "../../../../lib/api";
import DateField from "../../../../shared/ui/DateField";
import { formatDDMMYYYY } from "../../../../shared/forms/dateFormat";
import useApiAction from "../../../../lib/hooks/useApiAction";
import CycleForm from "../../../../features/admin/exam-intelligence/forms/CycleForm";
import PhaseForm from "../../../../features/admin/exam-intelligence/forms/PhaseForm";

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

function legacyWindow(phase) {
  return phase.metadata?.phase_window || phase.phase_window || null;
}

function needsPhaseDateAuthoring(phase) {
  if (phase.phase_start) return false;
  const metadata = phase.metadata || {};
  return Boolean(
    legacyWindow(phase) ||
    metadata.needs_phase_date_authoring === true ||
    metadata.import_source === "exam_registry_workbook"
  );
}

function phaseDateSourceLabel(phase) {
  const windowText = legacyWindow(phase);
  if (windowText) return `Legacy: ${windowText}`;
  return "Imported workbook phase stub";
}

const CYCLE_STATUSES = ["expected", "open", "active", "closed", "completed", "cancelled"];
const PHASE_STATUSES = ["expected", "active", "completed", "cancelled"];

export default function SetupPanel({ action = null }) {
  const { exam, cycles, phases, refetch } = useExamWorkspace();
  const [searchParams] = useSearchParams();

  // ── add-phase form ──────────────────────────────────────────────────────
  const EMPTY_PHASE = {
    phase_name: "", base_slug: "", phase_order: "",
    mode: "", createTemplate: false, phase_start: null, phase_end: null,
  };
  const [addingPhase, setAddingPhase] = useState(false);
  const [phaseFormValues, setPhaseFormValues] = useState(EMPTY_PHASE);
  const [pickedCycleId, setPickedCycleId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState("");

  // ── promote-template form ────────────────────────────────────────────────
  const [promotingTemplate, setPromotingTemplate] = useState(false);
  const [ptTemplateId, setPtTemplateId] = useState("");
  const [ptCycleId, setPtCycleId] = useState("");
  const [ptStart, setPtStart] = useState(null);
  const [ptEnd, setPtEnd] = useState(null);
  const [ptOrder, setPtOrder] = useState("");
  const [ptStatus, setPtStatus] = useState("expected");
  const [ptReason, setPtReason] = useState("");
  const [ptBusy, setPtBusy] = useState(false);
  const [ptError, setPtError] = useState(null); // null | {type, message, phaseId?, existingId?}
  const [ptSuccess, setPtSuccess] = useState("");

  // ── worklist: inline patch state per phase id ───────────────────────────
  const [patchEdits, setPatchEdits] = useState({});
  const [datedPhaseIds, setDatedPhaseIds] = useState(new Set());

  // ── cycle create form ───────────────────────────────────────────────────
  const EMPTY_CYCLE = {
    cycle_name: "", year: "", status: "expected",
    notification_date: null, application_start: null, application_end: null,
    exam_start: null, exam_end: null, source_url: "", reason: "",
  };
  const [addingCycle, setAddingCycle] = useState(false);
  const [cycleFormValues, setCycleFormValues] = useState(EMPTY_CYCLE);
  const { run: runCycleCreate, busy: cycleCreateBusy } = useApiAction();

  // ── cycle edit state ────────────────────────────────────────────────────
  const [editingCycleId, setEditingCycleId] = useState(null);
  const [editCycle, setEditCycle] = useState({});
  const [editReason, setEditReason] = useState("");
  const { run: runCycleEdit, busy: cycleEditBusy } = useApiAction();

  // Open the create-cycle form automatically when action=add-cycle is present.
  useEffect(() => {
    if (action === "add-cycle") {
      openCreateCycle();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action]);

  function editFor(id) {
    return patchEdits[id] ?? { start: null, end: null, saving: false, err: "" };
  }
  function setEdit(id, updates) {
    setPatchEdits(prev => ({ ...prev, [id]: { ...editFor(id), ...updates } }));
  }

  const templatePhases = phases.filter(p => p.exam_cycle_id == null);

  const ptDateError =
    ptEnd && ptStart && ptEnd < ptStart
      ? "Phase end must be on or after phase start."
      : null;
  const ptReasonInvalid = ptReason.length > 0 && (ptReason.length < 8 || ptReason.length > 500);
  const ptCanSubmit =
    !ptBusy &&
    !!ptTemplateId &&
    !!ptCycleId &&
    !!ptStart &&
    !ptDateError &&
    ptReason.length >= 8 &&
    ptReason.length <= 500;

  function openPromoteTemplate() {
    setPromotingTemplate(true);
    setPtTemplateId(templatePhases[0]?.id || "");
    setPtCycleId(cycles[0]?.id || "");
    setPtStart(null); setPtEnd(null); setPtOrder(""); setPtStatus("expected");
    setPtReason(""); setPtError(null); setPtSuccess("");
  }

  async function promoteTemplate() {
    if (!ptCanSubmit) return;
    setPtBusy(true);
    setPtError(null);
    setPtSuccess("");
    try {
      await api.post(
        "/api/admin/exam-intelligence-cms/exam-phases/promote-template",
        {
          template_phase_id: ptTemplateId,
          target_cycle_id: ptCycleId,
          phase_start: ptStart,
          ...(ptEnd ? { phase_end: ptEnd } : {}),
          ...(ptOrder !== "" ? { phase_order: parseInt(ptOrder, 10) } : {}),
          status: ptStatus,
          reason: ptReason,
        },
      );
      setPtSuccess("Cycle-bound copy created.");
      setPromotingTemplate(false);
      setPtTemplateId(""); setPtCycleId(""); setPtStart(null); setPtEnd(null);
      setPtOrder(""); setPtStatus("expected"); setPtReason("");
      refetch();
    } catch (e) {
      const status = e?.status;
      const detail = e?.detail;
      if (status === 409) {
        const existingId =
          detail && typeof detail === "object" ? detail.existing_phase_id : null;
        setPtError({
          type: "collision",
          message: "This cycle already has a phase with this template slug.",
          existingId,
        });
      } else if (status === 500 && e?.code === "audit_write_failed") {
        const phaseId =
          detail && typeof detail === "object" ? detail.phase_id : null;
        setPtError({ type: "audit_write_failed", phaseId });
      } else {
        const msg =
          typeof detail === "string"
            ? detail
            : detail?.message || e?.message || "Promote failed.";
        setPtError({ type: "generic", message: msg });
      }
    } finally {
      setPtBusy(false);
    }
  }

  const phaseDateWorklistPhases = phases.filter(needsPhaseDateAuthoring);
  const needsDates = phaseDateWorklistPhases.filter(
    p => !datedPhaseIds.has(p.id)
  );

  // ── cycle create/edit handlers ──────────────────────────────────────────

  function openCreateCycle() {
    setAddingCycle(true);
    setCycleFormValues(EMPTY_CYCLE);
  }

  function setCycleField(key, val) {
    setCycleFormValues(prev => ({ ...prev, [key]: val }));
  }

  async function createCycle() {
    const { cycle_name, year, status, notification_date, application_start,
      application_end, exam_start, exam_end, source_url, reason } = cycleFormValues;
    if (!cycle_name.trim() || !year || reason.length < 8) return;
    await runCycleCreate({
      action: () => api.post("/api/admin/exam-intelligence-cms/exam-cycles", {
        reason,
        payload: {
          exam_id: exam?.id,
          year: parseInt(year, 10),
          cycle_name: cycle_name.trim(),
          status: status || "expected",
          notification_date: notification_date || null,
          application_start: application_start || null,
          application_end: application_end || null,
          exam_start: exam_start || null,
          exam_end: exam_end || null,
          source_url: source_url.trim() || null,
        },
      }),
      successMessage: "Cycle created",
      onSuccess: () => { setAddingCycle(false); refetch(); },
    });
  }

  function openEditCycle(c) {
    setEditingCycleId(c.id);
    setEditCycle({
      cycle_name: c.cycle_name ?? "",
      year: c.year ?? "",
      status: c.status ?? "expected",
      notification_date: c.notification_date ?? null,
      application_start: c.application_start ?? null,
      application_end: c.application_end ?? null,
      exam_start: c.exam_start ?? null,
      exam_end: c.exam_end ?? null,
      source_url: c.source_url ?? "",
    });
    setEditReason("");
  }

  async function saveCycleEdit(cycleId) {
    if (editReason.length < 8) return;
    await runCycleEdit({
      action: () => api.patch(`/api/admin/exam-intelligence-cms/exam-cycles/${cycleId}`, {
        reason: editReason,
        payload: {
          ...editCycle,
          year: editCycle.year ? parseInt(String(editCycle.year), 10) : undefined,
        },
      }),
      successMessage: "Cycle updated",
      onSuccess: () => { setEditingCycleId(null); refetch(); },
    });
  }

  // ── add-phase handler ───────────────────────────────────────────────────

  function setPhaseField(key, val) {
    setPhaseFormValues(prev => ({ ...prev, [key]: val }));
  }

  async function addPhase() {
    const { phase_name, base_slug, phase_order, phase_start, phase_end } = phaseFormValues;
    if (!phase_name.trim()) return;
    setSaving(true);
    setSaveErr("");
    try {
      const activeCycle = cycles.find((c) => c.status === "active") || cycles[0];
      const targetCycleId = pickedCycleId || activeCycle?.id || null;
      const name = phase_name.trim();
      const slug = base_slug.trim() ? slugify(base_slug.trim()) : slugify(name);
      await api.post("/api/admin/exam-intelligence-cms/exam-phases", {
        reason: "Add exam phase via workspace setup panel",
        payload: {
          exam_id: exam?.id,
          exam_cycle_id: targetCycleId,
          phase_name: name,
          phase_slug: slug,
          phase_order: phase_order ? parseInt(phase_order, 10) : (phases.length + 1),
          status: "expected",
          phase_start: phase_start || null,
          phase_end: phase_end || null,
          metadata: {},
        },
      });
      setPhaseFormValues(EMPTY_PHASE);
      setPickedCycleId(null); setAddingPhase(false);
    } catch (e) {
      setSaveErr(e?.message || "Failed to add phase");
    } finally {
      setSaving(false);
    }
  }

  async function patchPhaseDate(phase) {
    const edit = editFor(phase.id);
    setEdit(phase.id, { saving: true, err: "" });
    try {
      await api.patch(`/api/admin/exam-intelligence-cms/exam-phases/${phase.id}`, {
        reason: "Set structured phase dates via worklist",
        payload: {
          phase_start: edit.start || null,
          phase_end: edit.end || null,
        },
      });
      setDatedPhaseIds(prev => new Set([...prev, phase.id]));
    } catch (e) {
      setEdit(phase.id, { saving: false, err: e?.message || "Failed to save" });
    }
  }

  const activeCycle = cycles.find((c) => c.status === "active");

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
          {!addingCycle && (
            <button
              className="btn small"
              data-testid="add-cycle-btn"
              onClick={openCreateCycle}
            >
              + Create cycle
            </button>
          )}
        </div>

        {cycles.length === 0 && !addingCycle ? (
          <div className="empty">
            <div className="empty-title">No cycles yet</div>
            <div>Use the button above to create the first cycle.</div>
          </div>
        ) : cycles.length > 0 ? (
          <table className="t">
            <thead>
              <tr>
                <th>Cycle</th>
                <th>Year</th>
                <th>Status</th>
                <th>Trust</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {cycles.map((c) => (
                <React.Fragment key={c.id}>
                  {editingCycleId === c.id ? (
                    <tr>
                      <td colSpan={5}>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", padding: "8px 0", alignItems: "center" }}>
                          <input
                            data-testid={`edit-cycle-name-${c.id}`}
                            className="input"
                            style={{ maxWidth: 200 }}
                            placeholder="Cycle name"
                            value={editCycle.cycle_name || ""}
                            onChange={e => setEditCycle(prev => ({ ...prev, cycle_name: e.target.value }))}
                          />
                          <input
                            className="input"
                            style={{ maxWidth: 80 }}
                            placeholder="Year"
                            type="number"
                            value={editCycle.year || ""}
                            onChange={e => setEditCycle(prev => ({ ...prev, year: e.target.value }))}
                          />
                          <select
                            className="input"
                            style={{ maxWidth: 130 }}
                            value={editCycle.status || "expected"}
                            onChange={e => setEditCycle(prev => ({ ...prev, status: e.target.value }))}
                          >
                            {CYCLE_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                          </select>
                          <input
                            data-testid={`edit-cycle-reason-${c.id}`}
                            className="input"
                            style={{ flex: 1, minWidth: 200 }}
                            placeholder="Reason for edit (required)"
                            value={editReason}
                            onChange={e => setEditReason(e.target.value)}
                          />
                          <button
                            data-testid={`save-cycle-${c.id}`}
                            className="btn primary small"
                            onClick={() => saveCycleEdit(c.id)}
                            disabled={cycleEditBusy || editReason.length < 8}
                          >
                            {cycleEditBusy ? "Saving…" : "Save"}
                          </button>
                          <button
                            className="btn ghost small"
                            onClick={() => setEditingCycleId(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <tr>
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
                      <td>
                        <button
                          data-testid={`edit-cycle-${c.id}`}
                          className="btn ghost small"
                          onClick={() => openEditCycle(c)}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        ) : null}

        {addingCycle && (
          <div
            className="card-foot"
            data-testid="cycle-create-section"
            style={{
              flexDirection: "column",
              gap: 10,
              background: "var(--paper)",
              padding: "12px 16px",
            }}
          >
            <CycleForm
              values={cycleFormValues}
              onChange={setCycleField}
              showReason
            />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 4 }}>
              <button
                className="btn primary small"
                onClick={createCycle}
                disabled={cycleCreateBusy || !cycleFormValues.cycle_name.trim() || !cycleFormValues.year || cycleFormValues.reason.length < 8}
                data-testid="add-cycle-submit"
              >
                {cycleCreateBusy ? "Creating…" : "Create cycle"}
              </button>
              <button
                className="btn ghost small"
                onClick={() => setAddingCycle(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Phases */}
      <div className="card">
        <div className="card-head">
          <h3 className="oc-title">
            Phases
            {activeCycle && (
              <span className="row-sub" style={{ marginLeft: 8, fontWeight: 400 }}>
                · {activeCycle.cycle_name}
              </span>
            )}
          </h3>
          {!addingPhase && (
            <button
              className="btn small"
              onClick={() => {
                const ac = cycles.find((c) => c.status === "active") || cycles[0];
                setPickedCycleId(ac?.id || null);
                setAddingPhase(true);
              }}
            >
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
              flexDirection: "column",
              gap: 8,
              background: "var(--paper)",
              padding: "12px 16px",
            }}
          >
            {cycles.length > 0 && (
              <div>
                <label className="text-xs font-medium text-muted-foreground">Cycle</label>
                <select
                  className="input"
                  style={{ maxWidth: 220 }}
                  data-testid="cycle-picker"
                  value={pickedCycleId || ""}
                  onChange={e => setPickedCycleId(e.target.value)}
                >
                  {cycles.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.cycle_name ?? c.id}{c.year ? ` (${c.year})` : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <PhaseForm
              values={phaseFormValues}
              onChange={setPhaseField}
              showSlug
              showMode={false}
              showTemplate={false}
              showDates
            />
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn primary small" onClick={addPhase} disabled={saving} data-testid="add-phase-submit">
                {saving ? "Saving…" : "Add phase"}
              </button>
              <button
                className="btn ghost small"
                onClick={() => {
                  setAddingPhase(false); setSaveErr(""); setPickedCycleId(null);
                  setPhaseFormValues(EMPTY_PHASE);
                }}
              >
                Cancel
              </button>
            </div>
            {saveErr && (
              <span className="err-row" style={{ padding: "3px 8px" }}>{saveErr}</span>
            )}
          </div>
        )}
      </div>

      {/* Promote template to cycle */}
      <div className="card" data-testid="promote-template-card">
        <div className="card-head">
          <h3 className="oc-title">Template phases</h3>
          {templatePhases.length > 0 && cycles.length > 0 && !promotingTemplate && (
            <button
              className="btn small"
              data-testid="promote-template-btn"
              onClick={openPromoteTemplate}
            >
              + Create cycle-bound copy
            </button>
          )}
        </div>

        {ptSuccess && (
          <div className="success-row" data-testid="pt-success" style={{ margin: "8px 16px 0" }}>
            {ptSuccess}
          </div>
        )}

        {templatePhases.length === 0 ? (
          <div className="card-body">
            <div className="empty" style={{ padding: "12px 0" }} data-testid="promote-template-empty">
              <div className="empty-title">No promotable templates here.</div>
              <div>
                Open the exam-level workspace to promote a template into a cycle.
              </div>
            </div>
          </div>
        ) : (
          <div className="card-body" style={{ paddingBottom: 4 }}>
            <div className="row-sub" style={{ fontSize: 12, marginBottom: 8 }}>
              Generic templates are reusable phase definitions not bound to any cycle.
              "Create cycle-bound copy" clones a template into a specific cycle with real dates —
              the template itself is not moved or modified.
            </div>
            <div className="phase-rail">
              {templatePhases.map(p => (
                <div key={p.id} className="phase" data-testid={`template-phase-${p.id}`}>
                  <div className="phase-num">TPL</div>
                  <div className="phase-name">{p.phase_name ?? p.name}</div>
                  <div className="phase-count phase-slug">{p.phase_slug}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {templatePhases.length > 0 && cycles.length > 0 && promotingTemplate && (
            <div
              className="card-foot"
              style={{ flexDirection: "column", gap: 10, background: "var(--paper)", padding: "12px 16px" }}
            >
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
                {/* Template picker */}
                <div style={{ minWidth: 180 }}>
                  <label className="field-lbl" style={{ display: "block", marginBottom: 3 }}>
                    Template phase
                  </label>
                  <select
                    className="input"
                    data-testid="pt-template-picker"
                    value={ptTemplateId}
                    onChange={e => setPtTemplateId(e.target.value)}
                  >
                    <option value="">— select template —</option>
                    {templatePhases.map(p => (
                      <option key={p.id} value={p.id}>{p.phase_name ?? p.phase_slug}</option>
                    ))}
                  </select>
                </div>

                {/* Target cycle picker */}
                <div style={{ minWidth: 180 }}>
                  <label className="field-lbl" style={{ display: "block", marginBottom: 3 }}>
                    Target cycle
                  </label>
                  <select
                    className="input"
                    data-testid="pt-cycle-picker"
                    value={ptCycleId}
                    onChange={e => setPtCycleId(e.target.value)}
                  >
                    <option value="">— select cycle —</option>
                    {cycles.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.cycle_name ?? c.id}{c.year ? ` (${c.year})` : ""}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Status picker — enum only, no free text */}
                <div style={{ minWidth: 140 }}>
                  <label className="field-lbl" style={{ display: "block", marginBottom: 3 }}>
                    Status
                  </label>
                  <select
                    className="input"
                    data-testid="pt-status-picker"
                    value={ptStatus}
                    onChange={e => setPtStatus(e.target.value)}
                  >
                    {PHASE_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>

                {/* Phase order */}
                <div style={{ minWidth: 80 }}>
                  <label className="field-lbl" style={{ display: "block", marginBottom: 3 }}>
                    Order
                  </label>
                  <input
                    className="input"
                    data-testid="pt-order"
                    type="number"
                    placeholder="auto"
                    value={ptOrder}
                    onChange={e => setPtOrder(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-start" }}>
                <div style={{ minWidth: 180 }}>
                  <DateField
                    value={ptStart}
                    onChange={setPtStart}
                    mode="any"
                    label="Phase start (required)"
                    name="pt_phase_start"
                    id="pt-phase-start"
                  />
                </div>
                <div style={{ minWidth: 180 }}>
                  <DateField
                    value={ptEnd}
                    onChange={setPtEnd}
                    mode="any"
                    label="Phase end (optional)"
                    name="pt_phase_end"
                    id="pt-phase-end"
                  />
                </div>
              </div>

              {ptDateError && (
                <div className="err-row" data-testid="pt-date-error">{ptDateError}</div>
              )}

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <input
                  className="input"
                  data-testid="pt-reason"
                  style={{ flex: 1, minWidth: 220 }}
                  placeholder="Reason (required, 8–500 chars)"
                  value={ptReason}
                  onChange={e => setPtReason(e.target.value)}
                  maxLength={500}
                />
                <button
                  className="btn primary small"
                  data-testid="pt-submit"
                  onClick={promoteTemplate}
                  disabled={!ptCanSubmit}
                >
                  {ptBusy ? "Creating…" : "Create cycle-bound copy"}
                </button>
                <button
                  className="btn ghost small"
                  onClick={() => { setPromotingTemplate(false); setPtError(null); setPtSuccess(""); }}
                >
                  Cancel
                </button>
              </div>

              {ptReasonInvalid && (
                <div className="err-row" data-testid="pt-reason-error">
                  {ptReason.length < 8
                    ? "Reason must be at least 8 characters."
                    : "Reason must be 500 characters or fewer."}
                </div>
              )}

              {ptError && ptError.type === "collision" && (
                <div className="err-row" data-testid="pt-error-collision">
                  {ptError.message}
                  {ptError.existingId && (
                    <span> Existing phase id: <code>{ptError.existingId}</code></span>
                  )}
                </div>
              )}

              {ptError && ptError.type === "audit_write_failed" && (
                <div
                  className="err-row"
                  data-testid="pt-error-audit-failed"
                  style={{ background: "var(--color-background-warning, #fff3cd)", borderColor: "var(--color-border-warning, #f0c36d)" }}
                >
                  The phase was created
                  {ptError.phaseId && <> (id: <code data-testid="pt-error-phase-id">{ptError.phaseId}</code>)</>},
                  but its audit record failed to write. Do NOT re-promote — it will conflict.
                  Refresh, confirm the phase is present, and reconcile the missing audit record.
                </div>
              )}

              {ptError && ptError.type === "generic" && (
                <div className="err-row" data-testid="pt-error-generic">{ptError.message}</div>
              )}
            </div>
          )}
      </div>

      {/* Phases needing dates — missing phase_start plus explicit worklist signal */}
      {phaseDateWorklistPhases.length > 0 && (
        <div className="card" data-testid="phase-date-worklist">
          <div className="card-head">
            <h3 className="oc-title">Phases needing dates</h3>
            <span className="anno">
              {needsDates.length === 0
                ? "All phases have structured dates ✓"
                : `${needsDates.length} phase${needsDates.length !== 1 ? "s" : ""} without a structured start date`}
            </span>
          </div>
          {needsDates.length === 0 ? (
            <div className="card-body">
              <div className="empty" style={{ padding: "12px 0" }}>
                <div className="empty-title" data-testid="worklist-all-dated">
                  All phases have structured dates
                </div>
              </div>
            </div>
          ) : (
            <div className="card-body">
              {needsDates.map(phase => {
                const edit = editFor(phase.id);
                return (
                  <div
                    key={phase.id}
                    data-testid={`worklist-row-${phase.id}`}
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 10,
                      alignItems: "flex-start",
                      padding: "10px 0",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    <div style={{ minWidth: 160, flex: "0 0 auto" }}>
                      <div className="field-lbl">{phase.phase_name ?? phase.name}</div>
                      <div
                        className="row-sub"
                        data-testid={`worklist-legacy-${phase.id}`}
                        style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}
                      >
                        {phaseDateSourceLabel(phase)}
                      </div>
                    </div>
                    <div style={{ minWidth: 170 }}>
                      <DateField
                        value={edit.start}
                        onChange={v => setEdit(phase.id, { start: v })}
                        mode="any"
                        label="Phase start"
                        name={`worklist-phase-start-${phase.id}`}
                        id={`worklist-phase-start-${phase.id}`}
                      />
                    </div>
                    <div style={{ minWidth: 170 }}>
                      <DateField
                        value={edit.end}
                        onChange={v => setEdit(phase.id, { end: v })}
                        mode="any"
                        label="Phase end"
                        name={`worklist-phase-end-${phase.id}`}
                        id={`worklist-phase-end-${phase.id}`}
                      />
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 4, justifyContent: "flex-end", paddingTop: 20 }}>
                      <button
                        className="btn primary small"
                        data-testid={`worklist-save-${phase.id}`}
                        onClick={() => patchPhaseDate(phase)}
                        disabled={edit.saving || !edit.start}
                      >
                        {edit.saving ? "Saving…" : "Set dates"}
                      </button>
                      {edit.err && (
                        <span className="err-row" style={{ fontSize: 11 }}>{edit.err}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

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
