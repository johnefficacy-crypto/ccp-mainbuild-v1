/**
 * CycleActivationChecklist — 9-step cycle activation checklist (I9).
 *
 * Fetches /management/exams/{examId}/cycles/{cycleId}/activation-checklist
 * and renders each step with a status icon. Mounted inside SetupPanel.
 *
 * Design authority: I6 gate doc (PR #761), D01-D16 all APPROVED.
 * Frontend must not recompute completion or activation authority.
 */
import React, { useEffect, useState } from "react";
import { api } from "../../../lib/api";

const STATUS_ICON = {
  ready:          { icon: "✓", cls: "checklist-step--ready",          label: "Complete" },
  missing:        { icon: "○", cls: "checklist-step--missing",         label: "Not started" },
  uploaded:       { icon: "↑", cls: "checklist-step--uploaded",        label: "Uploaded" },
  extracting:     { icon: "⟳", cls: "checklist-step--extracting",      label: "Extracting" },
  review_pending: { icon: "!", cls: "checklist-step--review-pending",   label: "Needs review" },
  stale:          { icon: "⚠", cls: "checklist-step--stale",           label: "Stale" },
  failed:         { icon: "✗", cls: "checklist-step--failed",          label: "Failed" },
  not_applicable: { icon: "—", cls: "checklist-step--not-applicable",  label: "Not applicable" },
  unavailable:    { icon: "?", cls: "checklist-step--unavailable",     label: "Unavailable" },
};

const STEP_ORDER = [
  "cycle_details",
  "phases_schedule",
  "source_documents",
  "extraction",
  "syllabus_mapping",
  "pyq_readiness",
  "policy_updates",
  "competition_context",
  "review_activate",
];

function StepRow({ step }) {
  const s = STATUS_ICON[step.status] || STATUS_ICON.unavailable;
  return (
    <li
      className={`checklist-step ${s.cls}`}
      data-testid={`checklist-step-${step.step_id}`}
      data-status={step.status}
    >
      <span className="checklist-step__icon" aria-hidden="true">{s.icon}</span>
      <span className="checklist-step__label">{step.label}</span>
      <span className="checklist-step__status-label" aria-label={`Status: ${s.label}`}>{s.label}</span>
      {step.note && (
        <span className="checklist-step__note">{step.note}</span>
      )}
      {step.action_cta && step.status !== "ready" && step.status !== "not_applicable" && (
        <a
          href={step.action_cta.url}
          className="checklist-step__cta"
          data-testid={`checklist-cta-${step.step_id}`}
        >
          {step.action_cta.label}
        </a>
      )}
    </li>
  );
}

export default function CycleActivationChecklist({ examId, cycleId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!examId || !cycleId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    api
      .get(`/admin/exam-intelligence/management/exams/${examId}/cycles/${cycleId}/activation-checklist`)
      .then((res) => {
        if (cancelled) return;
        if (res.data?.cycle_readiness_error === "cycle_not_found") {
          setError("cycle_not_found");
        } else {
          setData(res.data);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.response?.status >= 500 ? "backend_unavailable" : "unknown");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [examId, cycleId]);

  if (!examId || !cycleId) return null;

  if (loading) {
    return (
      <div className="checklist-loading" data-testid="checklist-loading">
        Loading activation checklist…
      </div>
    );
  }

  if (error === "cycle_not_found") {
    return (
      <div className="checklist-error" data-testid="checklist-error-cycle-not-found">
        Requested cycle not found. All steps are unavailable.
      </div>
    );
  }

  if (error) {
    return (
      <div className="checklist-error" data-testid="checklist-error-unavailable">
        Activation checklist is temporarily unavailable.
      </div>
    );
  }

  const steps = data?.cycle_readiness?.steps || null;
  if (!steps) return null;

  const stepMap = Object.fromEntries(steps.map((s) => [s.step_id, s]));
  const orderedSteps = STEP_ORDER.map((id) => stepMap[id]).filter(Boolean);

  const readyCount = orderedSteps.filter((s) => s.status === "ready").length;
  const totalActive = orderedSteps.filter((s) => s.status !== "not_applicable").length;

  return (
    <div className="cycle-activation-checklist" data-testid="cycle-activation-checklist">
      <div className="checklist-header">
        <h3 className="oc-title">Cycle Activation Checklist</h3>
        <span className="checklist-progress" data-testid="checklist-progress">
          {readyCount} / {totalActive} complete
        </span>
      </div>
      <ol className="checklist-steps" role="list">
        {orderedSteps.map((step) => (
          <StepRow key={step.step_id} step={step} />
        ))}
      </ol>
    </div>
  );
}
