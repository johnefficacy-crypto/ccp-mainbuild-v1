import React from "react";
import { ADMIN_PROGRESS_STEPS } from "./AdminProgressBar";

// CurrentActionCard renders the single most-actionable item out of the
// pipeline progress map, so the review surface stays focused on one decision
// at a time instead of a long multi-step checklist.
//
// Contract:
//   progress        — return value of computeProgress() in AdminProgressBar.jsx,
//                     shape `{ [stepId]: { status, reason? } }`
//   onPrimaryAction — (kind: string) => void. Fired when the admin clicks the
//                     primary action button. The parent maps the kind to the
//                     right AdminFixPanel section and scrolls it into view.
//                     Without this prop the primary button is disabled rather
//                     than rendered as a dead control.

function findCurrentStep(progress) {
  const order = ["blocked", "active", "pending"];
  for (const wanted of order) {
    for (const step of ADMIN_PROGRESS_STEPS) {
      const entry = progress?.[step.id];
      if ((entry?.status || "pending") === wanted) {
        return { step, entry };
      }
    }
  }
  return null;
}

function actionLabelFor(step) {
  if (!step) return "Open workflow";
  switch (step.id) {
    case "source_ready": return "Pick verified source";
    case "dry_scrape": return "Run dry scrape";
    case "live_scrape": return "Run live scrape";
    case "queue_review": return "Open candidate review";
    case "field_fixes": return "Verify required fields";
    case "official_source_resolved": return "Attach official proof";
    case "conflicts_resolved": return "Resolve conflicts";
    case "promoted_draft": return "Promote to draft";
    case "draft_blockers_fixed": return "Fix draft blockers";
    case "validated": return "Validate publish readiness — server-side check";
    case "verified": return "Mark verified";
    case "published": return "Publish";
    case "eligibility_monitored": return "Monitor post-publish health";
    default: return "Open step";
  }
}

// Map a progress step to the semantic action kind the parent handler
// understands. Defaults to the step id so new steps still emit a usable
// kind without a code change here.
function actionKindFor(step) {
  if (!step) return null;
  switch (step.id) {
    case "official_source_resolved": return "attach_official_source";
    case "field_fixes": return "verify_fields";
    case "conflicts_resolved": return "resolve_conflicts";
    case "promoted_draft": return "promote_to_draft";
    default: return step.id;
  }
}

function statusToBadge(status) {
  if (status === "blocked") return { cls: "badge blocker", text: "blocked" };
  if (status === "active") return { cls: "badge info", text: "current" };
  if (status === "complete") return { cls: "badge resolved", text: "complete" };
  return { cls: "badge pending", text: "next" };
}

export default function CurrentActionCard({ progress, onPrimaryAction }) {
  const total = ADMIN_PROGRESS_STEPS.length;
  const done = ADMIN_PROGRESS_STEPS.filter((s) => (progress?.[s.id]?.status) === "complete").length;
  const current = findCurrentStep(progress);
  const status = current?.entry?.status || "pending";
  const badge = statusToBadge(status);
  const reason = current?.entry?.reason || null;
  const primaryLabel = actionLabelFor(current?.step);
  const primaryKind = actionKindFor(current?.step);
  const allComplete = done === total;
  const canAct = !allComplete && Boolean(primaryKind) && typeof onPrimaryAction === "function";

  return (
    <section className="card oc-current-action" data-testid="oc-current-action">
      <div className="card-body">
        <div className="row" style={{ gap: 6 }}>
          <span className="lbl">Next action</span>
          <span className={allComplete ? "badge resolved" : badge.cls}>{allComplete ? "complete" : badge.text}</span>
        </div>
        <div className="oc-title" style={{ fontSize: 16, marginTop: 6 }}>
          {allComplete ? "All steps clear — ready to publish" : (current?.step?.label || "Pick a candidate or draft to start")}
        </div>
        {reason ? <div className="field-sub" style={{ marginTop: 4 }}>{reason}</div> : null}
        <div className="row" style={{ marginTop: 10 }}>
          <button
            type="button"
            className="btn primary small"
            disabled={!canAct}
            onClick={canAct ? () => onPrimaryAction(primaryKind) : undefined}
            data-testid="oc-current-action-primary"
          >
            {primaryLabel}
          </button>
        </div>
      </div>
    </section>
  );
}
