/**
 * ExamIntelGlossary — canonical labels and lifecycle legend for exam-intelligence
 * admin surfaces (workspace panels, overview, review queue).
 *
 * Single source of truth. Import from here; do not re-declare in local files.
 */
import React from "react";

// ── Lifecycle labels ─────────────────────────────────────────────────────────

export const REVIEWER_STATUS_LABELS = {
  draft: "Draft",
  pending_review: "Pending review",
  reviewed: "Reviewed",
  locked: "Locked",
  rejected: "Rejected",
};

/**
 * Planner note: which statuses reach Study OS and in what precedence.
 * - competition_context: reviewed OR locked rows feed the planner; locked preferred.
 * - exam_topic_coverage: locked-only rows reach the planner.
 */
export const REVIEWER_STATUS_PLANNER_NOTE =
  "reviewed or locked rows feed the planner (competition); locked-only for topic coverage — locked preferred for all";

// ── Exam-type labels ─────────────────────────────────────────────────────────

export const EXAM_PURPOSE_LABELS = {
  recruitment: "Recruitment",
  entrance: "Entrance",
  certification: "Certification",
  opportunity: "Opportunity",
  other: "Other",
};

// ── Management-mode labels ───────────────────────────────────────────────────

export const BUSINESS_PRIORITY_LABELS = {
  core: "Core",
  light: "Light",
  index_only: "Index only",
  archive: "Archive",
};

// ── LifecycleLegend component ────────────────────────────────────────────────

const LIFECYCLE_ITEMS = [
  { cls: "draft",   label: "draft",    desc: "created, not reviewed" },
  { cls: "pending", label: "pending",  desc: "in review queue" },
  { cls: "info",    label: "reviewed", desc: "reviewed — feeds planner (competition; locked preferred)" },
  { cls: "ink",     label: "locked",   desc: "locked — feeds planner (preferred)" },
  { cls: "blocker", label: "rejected", desc: "sent back for correction" },
];

export function LifecycleLegend() {
  return (
    <div className="ctx-strip" style={{ flexWrap: "wrap", gap: "6px 12px" }}>
      <span className="lbl" style={{ marginRight: 4 }}>Lifecycle</span>
      {LIFECYCLE_ITEMS.map(({ cls, label, desc }) => (
        <span className="ctx-chip" key={label} title={desc}>
          <span className={"badge " + cls} style={{ fontSize: 9.5, padding: "1px 6px" }}>
            {label}
          </span>
          <span style={{ color: "var(--ink-mute)", fontSize: 10.5 }}>{desc}</span>
        </span>
      ))}
    </div>
  );
}
