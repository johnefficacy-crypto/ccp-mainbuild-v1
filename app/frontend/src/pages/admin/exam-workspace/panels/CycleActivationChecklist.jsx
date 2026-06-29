import React, { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

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

const OVERALL_LABEL = {
  ready: "Ready to activate",
  blocked: "Blocked — hard gates unmet",
  needs_action: "Needs action",
};

export default function CycleActivationChecklist({ examId, cycleId }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [checklist, setChecklist] = useState(null);
  const [cycleError, setCycleError] = useState(null);

  useEffect(() => {
    if (!examId) return;
    setLoading(true);
    setError(null);
    const url = cycleId
      ? `/api/admin/exam-intelligence/management/exams/${examId}?cycle_id=${cycleId}`
      : `/api/admin/exam-intelligence/management/exams/${examId}`;
    api
      .get(url)
      .then((data) => {
        setCycleError(data.cycle_readiness_error || null);
        setChecklist(data.cycle_readiness || null);
        setLoading(false);
      })
      .catch((err) => {
        setError(err?.message || "Failed to load checklist");
        setLoading(false);
      });
  }, [examId, cycleId]);

  if (loading) {
    return (
      <div data-testid="cycle-checklist-loading" className="card">
        <p>Loading cycle activation checklist…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="cycle-checklist-error" className="card">
        <p className="err-row">Error loading checklist: {error}</p>
      </div>
    );
  }

  if (cycleError === "cycle_not_found") {
    return (
      <div data-testid="cycle-checklist-cycle-not-found" className="card">
        <p className="err-row">Cycle not found. Please select a valid cycle.</p>
      </div>
    );
  }

  if (!checklist) {
    return null;
  }

  const overallClass =
    checklist.overall === "ready"
      ? "badge ink"
      : checklist.overall === "blocked"
      ? "badge blocker"
      : "badge pending";

  return (
    <div data-testid="cycle-checklist" className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Cycle Activation Checklist</h3>
        <span className={overallClass} data-testid="cycle-checklist-overall">
          {OVERALL_LABEL[checklist.overall] || checklist.overall}
        </span>
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <tbody>
          {checklist.steps.map((step) => (
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
