/**
 * ExamIntelGlossary — shared labels and legend component for exam-intelligence
 * admin UI.
 */
import React from "react";

export const EXAM_PURPOSE_LABELS = {
  recruitment: "Recruitment",
  entrance: "Entrance",
  certification: "Certification",
  opportunity: "Opportunity",
  other: "Other",
};

export const BUSINESS_PRIORITY_LABELS = {
  core: "Core",
  light: "Light",
  index_only: "Index only",
  archive: "Archive",
};

const LIFECYCLE_ITEMS = [
  { cls: "draft",   label: "draft",    desc: "created, not yet reviewed" },
  { cls: "pending", label: "pending",  desc: "in review queue" },
  { cls: "info",    label: "reviewed", desc: "reviewed, not yet live" },
  { cls: "ink",     label: "locked",   desc: "live to aspirants" },
  { cls: "blocker", label: "rejected", desc: "sent back for correction" },
];

export function LifecycleLegend() {
  return (
    <div className="ctx-strip" style={{ marginTop: 4, flexWrap: "wrap", gap: "6px 12px" }}>
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
