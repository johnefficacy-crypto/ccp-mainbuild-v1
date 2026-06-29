import React from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";

const SUPPORTED_CONTRACT_VERSIONS = new Set([1]);

const STATUS_ICON = {
  ready: "✓",
  failed: "✗",
  missing: "✗",
  extracting: "⟳",
  not_applicable: "○",
  review_pending: "…",
  uploaded: "…",
  stale: "…",
};

export default function CycleActivationChecklist() {
  const { mgmt, mgmtLoading, mgmtError } = useExamWorkspace();

  if (mgmtLoading) {
    return (
      <div data-testid="cycle-checklist-loading" className="card">
        <p>Loading cycle activation checklist…</p>
      </div>
    );
  }

  // Show generic network/fetch error — but not the version sentinel (handled below after mgmt check)
  if (mgmtError && mgmtError !== "unsupported_contract_version") {
    return (
      <div data-testid="cycle-checklist-error" className="card">
        <p className="err-row">Error loading checklist: {mgmtError}</p>
      </div>
    );
  }

  if (!mgmt) return null;

  // D04: fail-closed version handling — suppress readiness interpretation for unsupported versions
  if (!SUPPORTED_CONTRACT_VERSIONS.has(mgmt.contract_version)) {
    return (
      <div data-testid="cycle-checklist-version-error" className="card">
        <p className="err-row">
          Checklist format version {mgmt.contract_version ?? "(missing)"} is not supported by
          this client. Reload or contact support.
        </p>
      </div>
    );
  }

  const cycleError = mgmt.cycle_readiness_error;
  if (cycleError && cycleError.code === "cycle_not_found") {
    return (
      <div data-testid="cycle-checklist-cycle-not-found" className="card">
        <p className="err-row">Cycle not found. Please select a valid cycle.</p>
      </div>
    );
  }

  const checklist = mgmt.cycle_readiness;
  // A7: cycle_readiness_error is null but cycle_readiness is also null — computation failed silently
  if (!checklist) {
    return (
      <div data-testid="cycle-checklist-unavailable" className="card">
        <p className="err-row">Cycle activation checklist is temporarily unavailable. Try refreshing.</p>
      </div>
    );
  }

  return (
    <div data-testid="cycle-checklist" className="card">
      <h3 style={{ margin: "0 0 12px" }}>Cycle Activation Checklist</h3>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <tbody>
          {(checklist.steps || []).map((step) => (
            <tr
              key={step.step}
              data-testid={`checklist-step-${step.step}`}
              style={{ borderBottom: "1px solid var(--border, #eee)" }}
            >
              <td style={{ width: 28, textAlign: "center", padding: "6px 4px" }}>
                <span data-testid={`checklist-step-${step.step}-icon`}>
                  {STATUS_ICON[step.status] || "?"}
                </span>
              </td>
              <td style={{ padding: "6px 8px" }}>
                <span style={{ fontWeight: 500 }}>{step.step}. {step.label}</span>
                {step.note && (
                  <span style={{ color: "var(--text-muted, #666)", fontSize: 12, marginLeft: 6 }}>
                    — {step.note}
                  </span>
                )}
              </td>
              <td style={{ width: 80, padding: "6px 4px" }}>
                <span className={step.gate_class === "hard" ? "badge blocker" : "badge neutral"}>
                  {step.gate_class}
                </span>
              </td>
              <td style={{ width: 80, padding: "6px 4px" }}>
                <span
                  className={
                    step.status === "ready"
                      ? "badge ink"
                      : step.status === "not_applicable"
                      ? "badge neutral"
                      : step.status === "missing" || step.status === "failed"
                      ? "badge blocker"
                      : "badge pending"
                  }
                  data-testid={`checklist-step-${step.step}-status`}
                >
                  {step.status}
                </span>
              </td>
              <td style={{ width: 80, padding: "6px 4px", textAlign: "right" }}>
                {step.action_cta && (
                  <a
                    href={step.action_cta.url}
                    data-testid={`checklist-step-${step.step}-cta`}
                    className="btn small"
                  >
                    {step.action_cta.label} →
                  </a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
