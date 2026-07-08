import React from "react";

const STEPS = [
  { id: "queue_review", label: "Queue review" },
  { id: "field_fixes", label: "Field fixes" },
  { id: "official_source_resolved", label: "Official proof attached" },
  { id: "conflicts_resolved", label: "Conflicts resolved" },
  { id: "promoted_draft", label: "Draft created" },
  { id: "draft_blockers_fixed", label: "Draft blockers fixed" },
  { id: "validated", label: "Validated" },
  { id: "verified", label: "Verified" },
  { id: "published", label: "Published" },
  { id: "eligibility_monitored", label: "Post-publish health" },
];

// state: { queueItem, recruitment, validateResult, eligibilityOps, conflicts }
// Returns { id -> { status: "pending"|"active"|"complete"|"blocked", reason?: string } }
//
// Source/scrape-run readiness (formerly `source_ready`/`dry_scrape`/`live_scrape`,
// derived from `state.source`/`state.latestRun`) has been removed. Those are
// Source Registry / Scrape Monitor concerns (`/admin/sources`, `/admin/scraper`),
// not Review & Publish — see
// docs/architecture/operations-console-review-publish-split.md Section 6, Open
// Question 1 (resolved: drop entirely).
export function computeProgress(state = {}) {
  const out = {};
  const { queueItem, recruitment, validateResult, eligibilityOps, conflicts } = state;
  const openConflicts = (conflicts || []).filter((c) => (c?.status || "open") === "open");

  if (queueItem) {
    if (queueItem.status === "rejected" || queueItem.status === "duplicate") {
      out.queue_review = { status: "blocked", reason: `Item status: ${queueItem.status}` };
    } else if (queueItem.status === "approved" || queueItem.promoted_recruitment_id) {
      out.queue_review = { status: "complete" };
    } else {
      out.queue_review = { status: "active" };
    }
  } else {
    out.queue_review = { status: "pending", reason: "Select a queue item." };
  }

  if (queueItem) {
    const unverified = queueItem.unverified_fields || [];
    if (unverified.length === 0) {
      out.field_fixes = { status: "complete" };
    } else {
      out.field_fixes = { status: "blocked", reason: `Verify required fields: ${unverified.join(", ")}` };
    }
  } else {
    out.field_fixes = { status: "pending" };
  }

  if (queueItem) {
    if (queueItem.official_source_resolved === false) {
      out.official_source_resolved = { status: "blocked", reason: "Attach official proof before promotion." };
    } else if (queueItem.official_source_resolved === true) {
      out.official_source_resolved = { status: "complete" };
    } else {
      out.official_source_resolved = { status: "active", reason: "Official source resolution not required for this source." };
    }
  } else {
    out.official_source_resolved = { status: "pending" };
  }

  if (!queueItem) {
    out.conflicts_resolved = { status: "pending" };
  } else if (openConflicts.length > 0) {
    out.conflicts_resolved = {
      status: "blocked",
      reason: `Open consensus conflicts: ${openConflicts.map((c) => c.field_key).filter(Boolean).join(", ") || openConflicts.length}`,
    };
  } else {
    out.conflicts_resolved = { status: "complete" };
  }

  if (queueItem?.promoted_recruitment_id || recruitment) {
    out.promoted_draft = { status: "complete" };
  } else if (queueItem?.promotable && openConflicts.length === 0) {
    out.promoted_draft = { status: "active", reason: "Ready to promote." };
  } else {
    out.promoted_draft = { status: "pending", reason: "Promotion blocked until field & source gates pass." };
  }

  const blockers = validateResult?.blocking_issues || recruitment?.blocking_issues || [];
  if (recruitment) {
    if (blockers.length === 0) {
      out.draft_blockers_fixed = { status: "complete" };
    } else {
      out.draft_blockers_fixed = { status: "blocked", reason: blockers.join(", ") };
    }
  } else {
    out.draft_blockers_fixed = { status: "pending" };
  }

  if (validateResult) {
    out.validated = validateResult.ready
      ? { status: "complete" }
      : { status: "blocked", reason: "Validate-publish reports blockers." };
  } else if (recruitment) {
    out.validated = { status: "active", reason: "Run validate-publish to confirm readiness." };
  } else {
    out.validated = { status: "pending" };
  }

  if (recruitment) {
    if (recruitment.publish_status === "verified" || recruitment.publish_status === "published") {
      out.verified = { status: "complete" };
    } else if (validateResult?.ready) {
      out.verified = { status: "active", reason: "Mark verified, then publish." };
    } else {
      out.verified = { status: "pending" };
    }
  } else {
    out.verified = { status: "pending" };
  }

  if (recruitment) {
    if (recruitment.publish_status === "published") {
      out.published = { status: "complete" };
    } else if (recruitment.publish_status === "verified") {
      out.published = { status: "active", reason: "Ready to publish." };
    } else {
      out.published = { status: "pending" };
    }
  } else {
    out.published = { status: "pending" };
  }

  if (recruitment?.publish_status === "published") {
    if (eligibilityOps) {
      out.eligibility_monitored = { status: "complete" };
    } else {
      out.eligibility_monitored = { status: "active", reason: "Monitor recompute and alerts." };
    }
  } else {
    out.eligibility_monitored = { status: "pending" };
  }

  return out;
}

const PHASES = [
  { id: "review", label: "Review", stepIds: ["queue_review", "field_fixes", "official_source_resolved", "conflicts_resolved"] },
  { id: "promote", label: "Promote", stepIds: ["promoted_draft", "draft_blockers_fixed"] },
  { id: "publish", label: "Publish & Monitor", stepIds: ["validated", "verified", "published", "eligibility_monitored"] },
];

function rollupPhaseStatus(phaseSteps, progress) {
  let anyActive = false;
  let anyPending = false;
  let allComplete = true;
  for (const id of phaseSteps) {
    const s = (progress[id] || { status: "pending" }).status;
    if (s === "blocked") return "blocked";
    if (s === "active") anyActive = true;
    if (s === "pending") anyPending = true;
    if (s !== "complete") allComplete = false;
  }
  if (allComplete) return "complete";
  if (anyActive) return "active";
  if (anyPending) return "pending";
  return "pending";
}

function phaseClass(status) {
  if (status === "complete") return "phase done";
  if (status === "active") return "phase active";
  if (status === "blocked") return "phase blocked";
  return "phase";
}

function phaseCountLabel(stepIds, progress, status) {
  const done = stepIds.filter((id) => (progress[id]?.status) === "complete").length;
  const total = stepIds.length;
  if (status === "blocked") {
    const blocked = stepIds.filter((id) => (progress[id]?.status) === "blocked").length;
    return `blocked · ${blocked} fix`;
  }
  if (status === "active") return `${done} / ${total} active`;
  if (status === "complete") return `${done} / ${total} done`;
  return `${done} / ${total} pending`;
}

export default function AdminProgressBar({ state = {}, onStepClick }) {
  const progress = computeProgress(state);
  return (
    <section className="card" data-testid="admin-progress-bar">
      <div className="card-body">
        <div className="lbl" style={{ marginBottom: 8 }}>Pipeline · 3 phases · 10 steps</div>
        <div className="phase-rail">
          {PHASES.map((phase, phaseIndex) => {
            const phaseStatus = rollupPhaseStatus(phase.stepIds, progress);
            return (
              <button
                type="button"
                key={phase.id}
                className={phaseClass(phaseStatus)}
                onClick={() => onStepClick?.(phase.stepIds[0])}
                data-testid={`progress-phase-${phase.id}`}
                data-status={phaseStatus}
              >
                <div className="phase-num">{String(phaseIndex + 1).padStart(2, "0")}</div>
                <div className="phase-name">{phase.label}</div>
                <div className="phase-count">{phaseCountLabel(phase.stepIds, progress, phaseStatus)}</div>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export { STEPS as ADMIN_PROGRESS_STEPS, PHASES as ADMIN_PROGRESS_PHASES };
