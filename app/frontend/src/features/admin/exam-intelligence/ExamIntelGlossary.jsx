import React from "react";

// ---------------------------------------------------------------------------
// REVIEWER_STATUS — lifecycle of a topic-coverage or competition-metrics row
// ---------------------------------------------------------------------------

export const REVIEWER_STATUS_LABELS = {
  draft:          { label: "Draft",          description: "Created, not reviewed" },
  pending_review: { label: "Pending review", description: "Waiting for reviewer" },
  reviewed:       { label: "Reviewed",       description: "Checked, usable in limited planner context" },
  locked:         { label: "Locked",         description: "Approved as stable planner truth" },
  rejected:       { label: "Rejected",       description: "Do not use" },
};

/** Sentence shared across all planner-readiness surfaces. */
export const REVIEWER_STATUS_PLANNER_NOTE =
  "Reviewed or locked rows feed the planner; locked preferred.";

// ---------------------------------------------------------------------------
// BUSINESS_PRIORITY_LABELS — management_mode on public.exams
// ---------------------------------------------------------------------------

export const BUSINESS_PRIORITY_LABELS = {
  core:       { label: "Core",          helper: "Full readiness expected." },
  light:      { label: "Managed light", helper: "Essential facts + major updates." },
  index_only: { label: "Index only",    helper: "Searchable reference, no deep Study OS." },
  archive:    { label: "Archived",      helper: "Low-priority, still live. Does not hide the exam — use is_active=false to retire." },
  null:       { label: "Unclassified",  helper: null },
};

/** Returns the display label for a management_mode value, including null/undefined. */
export function getBusinessPriorityLabel(mode) {
  if (mode == null) return BUSINESS_PRIORITY_LABELS.null.label;
  return (BUSINESS_PRIORITY_LABELS[mode] ?? BUSINESS_PRIORITY_LABELS.null).label;
}

// ---------------------------------------------------------------------------
// COVERAGE_DEPTH_LABELS — coverage_depth on exam_topic_coverage
// ---------------------------------------------------------------------------

export const COVERAGE_DEPTH_LABELS = {
  unknown:  "Unknown",
  none:     "Not in syllabus",
  mentioned:"Mentioned only",
  light:    "Light coverage",
  normal:   "Normal coverage",
  deep:     "Deep coverage",
  core:     "Core / deep",
};

export const COVERAGE_DEPTH_GROUP_LABEL = "Syllabus coverage";

export const COVERAGE_DEPTH_HELPER =
  "How strongly this topic belongs to this exam phase, from official syllabus + PYQ + admin review.";

// ---------------------------------------------------------------------------
// PRIORITY_BANDS — exam_priority_score (0–100 numeric)
// ---------------------------------------------------------------------------

const _PRIORITY_BANDS = [
  { min: 0,  max: 30,  band: "low",      label: "Low" },
  { min: 31, max: 60,  band: "medium",   label: "Medium" },
  { min: 61, max: 80,  band: "high",     label: "High" },
  { min: 81, max: 100, band: "critical", label: "Critical" },
];

export const PRIORITY_BANDS = _PRIORITY_BANDS;

/** Returns { band, label } for a given numeric priority score. */
export function band(score) {
  const n = Number(score ?? 0);
  return _PRIORITY_BANDS.find((b) => n >= b.min && n <= b.max) ?? _PRIORITY_BANDS[0];
}

export const PRIORITY_BANDS_GROUP_LABEL = "Planner priority";

export const PRIORITY_BANDS_HELPER =
  "Used by Study OS to decide how early and often a topic appears in plans.";

// ---------------------------------------------------------------------------
// EXAM_PURPOSE_LABELS — exam_type on public.exams
// ---------------------------------------------------------------------------

export const EXAM_PURPOSE_LABELS = {
  recruitment:  { label: "Recruitment exam",                       helper: null },
  entrance:     { label: "Entrance exam",                          helper: null },
  certification:{ label: "Certification",                          helper: null },
  opportunity:  {
    label:  "Opportunity / fellowship / scholarship",
    helper: "Use only for fellowships, internships, scholarships, grants, non-standard opportunities.",
  },
  other:        { label: "Other",                                  helper: null },
};

export const EXAM_PURPOSE_GROUP_LABEL = "Exam purpose";

// ---------------------------------------------------------------------------
// CADENCE_LABELS — cadence on public.exams
// ---------------------------------------------------------------------------

export const CADENCE_LABELS = {
  annual:    "Annual",
  recurring: "Recurring",
  irregular: "Irregular",
  one_off:   "One-off",
  unknown:   "Unknown",
};

// ---------------------------------------------------------------------------
// SOURCE_BASIS_LABELS — source_basis on exam_topic_coverage
// ---------------------------------------------------------------------------

export const SOURCE_BASIS_LABELS = {
  official_syllabus: "Official syllabus",
  pyq_analysis:      "PYQ analysis",
  admin_review:      "Admin review",
  hybrid:            "Hybrid",
  manual:            "Manual",
  model_generated:   "Model-generated",
};

// ---------------------------------------------------------------------------
// IS_HIGH_YIELD — boolean flag on exam_topic_coverage
// ---------------------------------------------------------------------------

export const IS_HIGH_YIELD_LABEL  = "High-yield for this phase";
export const IS_HIGH_YIELD_HELPER =
  "Turn on only when syllabus/PYQ evidence supports repeated importance.";

// ---------------------------------------------------------------------------
// IS_ACTIVE — boolean flag on public.exams
// ---------------------------------------------------------------------------

export const IS_ACTIVE_LABEL  = "Visible / usable";
export const IS_ACTIVE_HELPER =
  "true = available in admin/user selection per lifecycle; false = hidden but retained for history. " +
  "Not planner-readiness — readiness comes from lifecycle status.";

// ---------------------------------------------------------------------------
// RAW_ID_NOTE
// ---------------------------------------------------------------------------

export const RAW_ID_NOTE = "Raw UUIDs shown only in Advanced / Debug.";

// ---------------------------------------------------------------------------
// LifecycleLegend — renders the 5 reviewer_status rows + shared note
// ---------------------------------------------------------------------------

const STATUS_TONE = {
  draft:          "pill-dusk",
  pending_review: "pill-amber",
  reviewed:       "pill-amber",
  locked:         "pill-sage",
  rejected:       "pill-clay",
};

export function LifecycleLegend() {
  return (
    <div className="space-y-2">
      {Object.entries(REVIEWER_STATUS_LABELS).map(([key, { label, description }]) => (
        <div key={key} className="flex items-start gap-2">
          <span className={`pill ${STATUS_TONE[key]} shrink-0`}>{label}</span>
          <span className="text-sm text-secondary">{description}</span>
        </div>
      ))}
      <p className="text-sm text-tertiary pt-1">{REVIEWER_STATUS_PLANNER_NOTE}</p>
    </div>
  );
}
