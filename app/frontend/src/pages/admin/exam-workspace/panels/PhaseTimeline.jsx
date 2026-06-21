/**
 * PhaseTimeline — standalone component extracted from SetupPanel (C1).
 *
 * Renders all phases as a timeline rail. Phases that are missing a structured
 * start date are flagged inline with a "Needs date" badge and, where the phase
 * belongs to a known cycle, a cycle-context label (H3 / UX-EI-5).
 *
 * Props:
 *   phases  — array of exam phase objects from ExamWorkspaceContext
 *   cycles  — array of exam cycle objects (used to resolve cycle labels)
 *
 * This component is display-only. Create/edit actions remain in SetupPanel.
 */
import React from "react";
import { formatDDMMYYYY } from "../../../../shared/forms/dateFormat";

function formatPhaseWindow(phase) {
  if (phase.phase_start) {
    const start = formatDDMMYYYY(phase.phase_start);
    const end = phase.phase_end ? ` – ${formatDDMMYYYY(phase.phase_end)}` : "";
    return start + end;
  }
  // Legacy freeform fallback for un-backfilled rows.
  return phase.metadata?.phase_window ?? phase.phase_window ?? "TBD";
}

/**
 * Returns true when a phase is missing a structured start date AND
 * has an explicit signal that date-authoring is needed.
 */
function needsPhaseDateAuthoring(phase) {
  if (phase.phase_start) return false;
  const metadata = phase.metadata || {};
  const legacyWindow = metadata.phase_window || phase.phase_window;
  return Boolean(
    legacyWindow ||
    metadata.needs_phase_date_authoring === true ||
    metadata.import_source === "exam_registry_workbook"
  );
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

export default function PhaseTimeline({ phases = [], cycles = [] }) {
  if (phases.length === 0) {
    return (
      <div className="empty" style={{ padding: "16px 0" }}>
        <div className="empty-title">No phases defined</div>
        <div>Add the first phase below.</div>
      </div>
    );
  }

  return (
    <div className="phase-rail" data-testid="phase-timeline">
      {phases.map((phase, i) => {
        const missingDate = needsPhaseDateAuthoring(phase);
        const cycleLabel = missingDate ? resolveCycleLabel(phase, cycles) : null;

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
          </div>
        );
      })}
    </div>
  );
}
