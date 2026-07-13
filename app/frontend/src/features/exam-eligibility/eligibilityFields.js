// Friendly labels for the profile fields the eligibility evaluator reports as
// `missing_fields`. Shared by EligibleExamsCard (exam-level rows) and
// ExamStreamBreakdown (per-stream rows) so the two surfaces speak with one
// vocabulary. The evaluator emits both the original baseline fields
// (date_of_birth, education_level, nationality, gender) and the stream-aware
// rule fields from PR #973 (disciplines, education_percentage, certifications,
// qualification_details).

export const FIELD_LABELS = {
  date_of_birth: "date of birth",
  education_level: "highest qualification",
  nationality: "nationality",
  gender: "gender",
  category: "reservation category",
  disciplines: "academic discipline",
  education_percentage: "marks percentage",
  certifications: "professional certification",
  qualification_details: "qualification details",
};

export function humanField(key) {
  return FIELD_LABELS[key] || String(key || "").replace(/_/g, " ");
}

export function humanFieldList(fields) {
  if (!fields || fields.length === 0) return "";
  const labels = fields.map(humanField);
  if (labels.length === 1) return labels[0];
  if (labels.length === 2) return `${labels[0]} and ${labels[1]}`;
  return `${labels.slice(0, -1).join(", ")}, and ${labels[labels.length - 1]}`;
}
