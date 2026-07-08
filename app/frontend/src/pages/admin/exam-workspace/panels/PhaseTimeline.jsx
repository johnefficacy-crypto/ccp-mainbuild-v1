/**
 * PhaseTimeline — single canonical phase list for the workspace Setup panel
 * (C1/C2/D3, restored by EI-CLEAN-07).
 *
 * Renders all phases as one timeline rail. Phases missing a structured start
 * date are flagged inline with a "Needs date" badge and, where the phase belongs
 * to a known cycle, a cycle-context label (H3 / UX-EI-5). This is the ONLY phase
 * list in Setup — there is no separate "Phases needing dates" card duplicating it.
 *
 * Display-only by default. When `onSaveDates` is provided the needs-date rows
 * additionally render an inline date editor (start/end + Set dates), so date
 * authoring happens in-place on the canonical timeline rather than in a second,
 * filtered-duplicate card.
 *
 * Props:
 *   phases        — array of exam phase objects from ExamWorkspaceContext
 *   cycles        — array of exam cycle objects (used to resolve cycle labels)
 *   onSaveDates   — (phase) => void; presence enables the inline date editor
 *   editFor       — (phaseId) => { start, end, saving, err }; editor state
 *   onEditChange  — (phaseId, patch) => void; update editor state
 */
import React from "react";
import { formatDDMMYYYY } from "../../../../shared/forms/dateFormat";
import DateField from "../../../../shared/ui/DateField";

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

/**
 * Returns true when a phase is missing a structured start date AND
 * has an explicit signal that date-authoring is needed.
 */
function needsPhaseDateAuthoring(phase) {
  if (phase.phase_start) return false;
  const metadata = phase.metadata || {};
  return Boolean(
    legacyWindow(phase) ||
    metadata.needs_phase_date_authoring === true ||
    metadata.import_source === "exam_registry_workbook"
  );
}

// Operator-facing provenance for a needs-date row: the legacy window text if
// present, otherwise the workbook-stub origin.
function phaseDateSourceLabel(phase) {
  const windowText = legacyWindow(phase);
  if (windowText) return `Legacy: ${windowText}`;
  return "Imported workbook phase stub";
}

/**
 * Resolve the display label for the cycle this phase belongs to.
 * Returns null if cycle_id is absent or no matching cycle is found.
 */
function resolveCycleLabel(phase, cycles) {
  const cycleId = phase.exam_cycle_id ?? phase.cycle_id;
  if (!cycleId) return null;
  const cycle = cycles.find(c => c.id === cycleId);
  if (!cycle) return null;
  const name = cycle.cycle_name ?? cycle.name ?? "Cycle";
  return cycle.year ? `${name} (${cycle.year})` : name;
}

const NOOP_EDIT = { start: null, end: null, saving: false, err: "" };

export default function PhaseTimeline({
  phases = [],
  cycles = [],
  onSaveDates = null,
  editFor = null,
  onEditChange = null,
  datedPhaseIds = null,
}) {
  if (phases.length === 0) {
    return (
      <div className="empty" style={{ padding: "16px 0" }}>
        <div className="empty-title">No phases defined</div>
        <div>Add the first phase below.</div>
      </div>
    );
  }

  const editable = typeof onSaveDates === "function";

  return (
    <div className="phase-rail" data-testid="phase-timeline">
      {phases.map((phase, i) => {
        // A row just saved this session (datedPhaseIds) is treated as dated
        // immediately, so its badge + editor drop without waiting for a refetch.
        const missingDate =
          needsPhaseDateAuthoring(phase) && !(datedPhaseIds?.has(phase.id));
        const cycleLabel = missingDate ? resolveCycleLabel(phase, cycles) : null;
        const edit = editable && missingDate ? (editFor?.(phase.id) ?? NOOP_EDIT) : NOOP_EDIT;

        return (
          <div
            key={phase.id}
            data-testid={`phase-timeline-row-${phase.id}`}
            className={
              "phase" +
              (phase.status === "active" ? " active" : phase.status === "completed" ? " done" : "")
            }
          >
            <div className="phase-num">PH-{i + 1}</div>
            <div className="phase-name">
              {phase.phase_name ?? phase.name}
              {missingDate && (
                <span
                  className="badge blocker"
                  data-testid={`phase-needs-date-badge-${phase.id}`}
                  style={{ marginLeft: 6, fontSize: 10, verticalAlign: "middle" }}
                >
                  Needs date
                </span>
              )}
            </div>
            {cycleLabel && (
              <div
                className="row-sub"
                data-testid={`phase-cycle-label-${phase.id}`}
                style={{ fontSize: 11, color: "var(--info)", fontWeight: 500 }}
              >
                {cycleLabel}
              </div>
            )}
            <div className="phase-count">{formatPhaseWindow(phase)}</div>

            {/* Inline date authoring — only when editing is enabled and this row
                is a needs-date phase. This is the single place dates are set;
                there is no separate worklist card. */}
            {editable && missingDate && (
              <div
                data-testid={`phase-date-editor-${phase.id}`}
                style={{
                  marginTop: 8,
                  paddingTop: 8,
                  borderTop: "1px solid var(--border)",
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 10,
                  alignItems: "flex-start",
                }}
              >
                <div
                  className="row-sub"
                  data-testid={`phase-date-source-${phase.id}`}
                  style={{ fontSize: 11, color: "var(--muted)", flexBasis: "100%" }}
                >
                  {phaseDateSourceLabel(phase)}
                </div>
                <div style={{ minWidth: 160 }}>
                  <DateField
                    value={edit.start}
                    onChange={v => onEditChange?.(phase.id, { start: v })}
                    mode="any"
                    label="Phase start"
                    name={`phase-date-start-${phase.id}`}
                    id={`phase-date-start-${phase.id}`}
                  />
                </div>
                <div style={{ minWidth: 160 }}>
                  <DateField
                    value={edit.end}
                    onChange={v => onEditChange?.(phase.id, { end: v })}
                    mode="any"
                    label="Phase end"
                    name={`phase-date-end-${phase.id}`}
                    id={`phase-date-end-${phase.id}`}
                  />
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 4, justifyContent: "flex-end", paddingTop: 20 }}>
                  <button
                    className="btn primary small"
                    data-testid={`phase-date-save-${phase.id}`}
                    onClick={() => onSaveDates(phase)}
                    disabled={edit.saving || !edit.start}
                  >
                    {edit.saving ? "Saving…" : "Set dates"}
                  </button>
                  {edit.err && (
                    <span className="err-row" style={{ fontSize: 11 }}>{edit.err}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
