// The six criteria an aspirant judges their own answer against, 0/1/2 each.
//
// HUMAN DECISION AUTHORITY. Nothing scores a descriptive answer but the person
// who wrote it. These descriptors exist so the same answer gets roughly the same
// score from the same person in March as in September — that is the whole value
// of a rubric you apply to yourself — not so a machine can apply it later.
//
// Keys and the 0..2 range mirror `app/backend/app/study_os/descriptive.py`
// (`RUBRIC_KEYS`). A key added on one side and not the other is a 422.

export const RUBRIC = [
  {
    key: "structure",
    label: "Structure",
    descriptors: [
      "One block of prose — no visible intro, body or conclusion.",
      "Parts are there but run together, or the order wanders.",
      "Clear intro, a body that moves in steps, and a close.",
    ],
  },
  {
    key: "relevance",
    label: "Relevance to the question",
    descriptors: [
      "Answers a nearby question, not this one.",
      "On topic, but drifts or misses part of what was asked.",
      "Answers exactly what was asked, including every part of it.",
    ],
  },
  {
    key: "coverage",
    label: "Coverage of the syllabus content",
    descriptors: [
      "Thin — the obvious points only.",
      "The main points, but a well-known dimension is missing.",
      "The expected ground plus a dimension most answers would skip.",
    ],
  },
  {
    key: "examples",
    label: "Examples and substantiation",
    descriptors: [
      "Assertion without evidence.",
      "Some examples, generic or unattached to the argument.",
      "Specific examples — case, report, data, thinker — doing real work.",
    ],
  },
  {
    key: "conclusion",
    label: "Conclusion",
    descriptors: [
      "Stops rather than concludes.",
      "A summary that repeats the intro.",
      "Closes on a considered position that follows from the body.",
    ],
  },
  {
    key: "within_limit",
    label: "Within the word limit",
    descriptors: [
      "Well over or well under — length itself would cost marks.",
      "Close to the limit but over or under enough to notice.",
      "Inside the limit, or no limit set and the length suits the marks.",
    ],
  },
];

export const RUBRIC_KEYS = RUBRIC.map((r) => r.key);
export const RUBRIC_MAX_PER_KEY = 2;
export const RUBRIC_MAX_TOTAL = RUBRIC.length * RUBRIC_MAX_PER_KEY;

/** Sum of a filled rubric, or null while any criterion is unscored. */
export function rubricTotal(scores) {
  if (!scores) return null;
  const values = RUBRIC_KEYS.map((k) => scores[k]);
  if (values.some((v) => typeof v !== "number")) return null;
  return values.reduce((sum, v) => sum + v, 0);
}

/** Whether every criterion has been judged — the submit gate. */
export function isRubricComplete(scores) {
  return rubricTotal(scores) !== null;
}

/** Seconds → "12:05", for the timer and the stored time on a past attempt. */
export function formatDuration(totalSeconds) {
  const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0));
  const mins = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${mins}:${String(rest).padStart(2, "0")}`;
}
