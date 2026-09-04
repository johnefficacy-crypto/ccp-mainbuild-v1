/**
 * Per-exam EDITORIAL for the reachability trend. No counts live here.
 *
 * Counts come from `GET /api/exam-intelligence/exams/{slug}/reachability`,
 * which computes eligibility per paper (every verified question carries a
 * non-NULL observed_difficulty, and the paper holds more than one distinct
 * band). This file holds only what a query cannot produce: what each band
 * MEANS for a given exam, the measure line, the provenance, the caveats, and
 * the written observation. Everything numeric was removed on purpose — it went
 * stale the moment a ninth paper was tagged, and Mains and CSAT are queued to
 * do the same again.
 *
 * WHAT THIS MEASURES — and what it does not.
 * Every question in an eligible paper was read and classified against a fixed
 * rubric measuring how reachable it was from standard preparation. It is NOT
 * observed difficulty: no candidate response data exists yet. Every string in
 * this file exists to keep that distinction visible in the UI, so none of it is
 * decorative — see `SHARED_MEASURE_LINE` and `PROVENANCE_LINE`, both of which
 * the card renders unconditionally whenever a chart appears.
 *
 * PHASE SCOPING — the trap the endpoint is shaped around.
 * `exam_phases` has no unique constraint, and UPSC has three phases named
 * "Prelims". The nine eligible GS-I papers are split across TWO phase ids —
 * 715de35f… (2018-2025) and 6566d50e… (2026) — despite being one continuous
 * series of the same paper. Scoping the series by phase would therefore return
 * eight papers or one, never nine, and would do so silently. So the series is
 * keyed by exam and enumerated by paper. `phaseId` is a NARROWING filter only,
 * and a caller that passes one is opting into that split knowingly.
 */

/** Stored `pyq_questions.observed_difficulty` values, in reading order. */
export const REACHABILITY_BANDS = ["easy", "medium", "hard"];

/**
 * Band labels are the stored enum, title-cased. Deliberately NOT a display
 * mapping layer: what the chart says is what the column holds.
 */
export const BAND_LABEL = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};

/**
 * Categorical series colors, fixed order, never cycled.
 *
 * Validated with the dataviz palette validator against the clay-50 (#FBF6EF)
 * card surface: lightness band, chroma floor, CVD separation, normal-vision
 * floor and contrast all pass. The worst adjacent protan separation is ΔE 8.2,
 * which sits just above the floor — so the chart also carries a legend AND
 * direct end-labels, and identity never rests on hue alone.
 */
export const BAND_COLOR = {
  easy: "#0E7A3D",
  medium: "#CC7A00",
  hard: "#5340A8",
};

/**
 * Rendered beside the chart, always. This is the line that stops the chart
 * being read as a difficulty curve.
 */
export const SHARED_MEASURE_LINE =
  "Measures how reachable a question was from standard preparation, not how " +
  "many candidates answered it correctly.";

/** Rendered whenever a chart renders. Not dismissible, not behind a control. */
export const PROVENANCE_LINE =
  "Classified by reading every question against a fixed rubric. Observed " +
  "difficulty from actual attempts will replace it as that data accumulates.";

export const PROVENANCE_SOURCE =
  "docs/operator-validation/2026-08-31-upsc-prelims-corpus-findings.md";

/** Y axis is fixed so papers stay comparable across exams and across reloads. */
export const Y_AXIS_MAX = 65;
export const Y_AXIS_LABEL = "Questions out of 100";
/** Explicit, so the 0-65 domain does not end on an uneven 40 → 65 step. */
export const Y_AXIS_TICKS = [0, 20, 40, 60];

/**
 * Fallback band copy.
 *
 * Eligibility is computed now, so ANY exam can become eligible the moment its
 * papers are judged — before anyone writes exam-specific copy for it. Without
 * this fallback such an exam would render Easy/Medium/Hard as bare labels,
 * which is the one thing the info buttons exist to prevent. The Hard entry says
 * "not reachable", never "difficult": that word is what separates this chart
 * from the difficulty curve it would otherwise be mistaken for.
 */
export const DEFAULT_BAND_COPY = {
  easy: "Reachable from the introductory sources this exam is normally prepared from.",
  medium: "Reachable from the reference material most candidates already use.",
  hard:
    "Not reachable from any standard source: a one-off institution or " +
    "initiative, an obscure statistic, or incidental detail.",
};

/**
 * Per-exam editorial, keyed by exam slug. Everything here is a judgement, not a
 * measurement — `bandCopy` because what "reachable" means is exam-specific (an
 * NCERT textbook is the UPSC baseline and would be meaningless for a banking
 * exam), `analysis` because a cutoff threshold is not derivable from band
 * counts.
 *
 * `analysisPaperCount` pins which corpus the prose was written against. The
 * card compares it to the number of papers the endpoint actually returned and
 * flags a mismatch rather than letting stale prose sit silently under fresh
 * data — the drift this file was just emptied of counts to avoid.
 */
const EXAM_REACHABILITY_COPY = {
  "upsc-cse": {
    seriesLabel: "Prelims GS Paper I",
    bandCopy: {
      easy:
        "Reachable from an NCERT textbook, or from current affairs prominent " +
        "enough that a regular newspaper reader would have met it.",
      medium: "Reachable from the reference books most aspirants already use.",
      hard:
        "Not reachable from any standard source: a one-off institution or " +
        "initiative, an obscure statistic, or incidental detail.",
    },
    caveat:
      "2018's figure is the least reliable in this series — judging what was " +
      "prominent in 2016-18 at this distance tends to overstate reachability.",
    analysisPaperCount: 9,
    /**
     * An observation about this corpus. Never advice: no study plan, no book
     * list, no second person, no imperative. A test asserts the absence of
     * imperative study language, because the line between "here is what the
     * corpus shows" and "here is what you should do about it" is exactly what
     * makes this publishable at all.
     */
    analysis: [
      "Across all nine papers the Medium band barely moves — it sits flat " +
        "near 55 questions every year. What changed sits either side of it. " +
        "Easy fell from 39 in 2018 to 10 in 2026, while Hard roughly doubled " +
        "over the same span. On this classification those are one movement, " +
        "not two: questions once reachable from a textbook or a newspaper " +
        "have become questions reachable from no standard source at all.",
      "The reachable pool — Easy plus Medium together — averages about 72 " +
        "questions per paper. Cutoffs have needed roughly 40 to 45 net " +
        "correct once negative marking is applied.",
      "Placing those two figures side by side, one observation follows from " +
        "this corpus: on this classification a candidate who answers most of " +
        "the reachable pool correctly clears without answering any Hard " +
        "question. That is a property of how these papers were classified, " +
        "not a prediction about any individual attempt.",
    ],
  },
};

/**
 * Resolve the editorial for an exam.
 *
 * `examKey` accepts a slug or an id — the landing page holds a slug, while the
 * component contract is written in terms of an exam id, and both should work
 * without the caller knowing which it has.
 *
 * Always returns a usable object: `bandCopy` is the per-exam copy merged over
 * `DEFAULT_BAND_COPY`, so a newly eligible exam still gets info buttons that
 * carry the reachability meaning. `analysis` and `caveat` are null when no one
 * has written them — the card omits those blocks rather than inventing them.
 */
export function reachabilityCopyFor(examKey) {
  const entry = (examKey && EXAM_REACHABILITY_COPY[String(examKey)]) || null;
  return {
    seriesLabel: entry?.seriesLabel || "Past papers",
    bandCopy: { ...DEFAULT_BAND_COPY, ...(entry?.bandCopy || {}) },
    caveat: entry?.caveat || null,
    analysis: entry?.analysis || null,
    analysisPaperCount: entry?.analysisPaperCount ?? null,
  };
}

export default EXAM_REACHABILITY_COPY;
