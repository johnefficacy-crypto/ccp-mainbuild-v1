// Learner-friendly labels for the attempt-analytics classifier codes.
//
// The backend classifier (app/backend/app/study_os/attempt_analytics/classifier.py)
// stores machine codes such as `silly_mistake`, `concept_gap`, and
// `time_pressure_unattempted`. Those codes must never leak to aspirants — the
// review UI maps them through this table. Keep this in sync with the RULES in
// classifier.py.

export const ERROR_TYPE_LABELS = {
  correct: "Correct",
  silly_mistake: "Careless mistake",
  knowledge_gap: "Knowledge gap",
  concept_gap: "Concept gap",
  time_pressure_unattempted: "Time pressure / not attempted",
  option_trap: "Distractor trap",
  calc_error: "Calculation error",
  marked_unanswered: "Marked but unanswered",
};

/**
 * Resolve a classifier code to a learner-facing label. Unknown or missing
 * codes fall back to "Not analyzed" so a raw machine code is never rendered.
 */
export function errorTypeLabel(code) {
  if (!code) return "Not analyzed";
  return ERROR_TYPE_LABELS[code] || "Not analyzed";
}
