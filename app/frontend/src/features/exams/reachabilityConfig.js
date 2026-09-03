/**
 * Per-exam configuration for the reachability trend.
 *
 * WHAT THIS MEASURES — and what it does not.
 * Every question in an eligible paper was read and classified against a fixed
 * rubric measuring how reachable it was from standard preparation. It is NOT
 * observed difficulty: no candidate response data exists yet. Every string in
 * this file exists to keep that distinction visible in the UI, so none of it is
 * decorative — see `SHARED_MEASURE_LINE` and `PROVENANCE_LINE`, both of which
 * the card renders unconditionally whenever a chart appears.
 *
 * ELIGIBILITY — read it, never assume it.
 * A paper is eligible only once it has been through a judging pass. Everything
 * else in the corpus carries a bulk-defaulted 'medium' from import and has
 * never been assessed, and nothing in the schema currently tells the two apart.
 * Until it does, `papers` below IS the allowlist: a paper that is not listed is
 * not plotted, and an exam with no entry renders the empty state rather than a
 * chart of import defaults. See `docs` note in the PR body for the proposed
 * per-paper `difficulty_judged` marker that replaces this.
 *
 * PHASE SCOPING — the trap this config is shaped around.
 * `exam_phases` has no unique constraint, and UPSC has three phases named
 * "Prelims". The eight eligible papers are split across TWO phase ids —
 * seven under 715de35f… and 2026 under 6566d50e… — despite being one continuous
 * series of the same paper. Scoping the series by phase id would therefore
 * return seven papers or one, never eight, and would do so silently. So the
 * series is keyed by exam and enumerated by paper, never gathered by phase.
 * `phaseId` is accepted as an optional NARROWING filter only, and a caller that
 * passes one is opting into that split knowingly.
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

/**
 * Per-exam config, keyed by exam slug. `bandCopy` is per-exam because what
 * "reachable" means is exam-specific — an NCERT textbook is the UPSC baseline
 * and would be meaningless for a banking exam.
 *
 * `papers` is the interim allowlist AND the interim data source. Counts are the
 * 2026-09-02 tagging pass over the UPSC Prelims GS Paper I corpus, recorded in
 * PROVENANCE_SOURCE. When the per-paper judged marker lands, `papers` becomes a
 * list of paper ids and the counts come from a read endpoint; nothing else in
 * this file or the component changes shape.
 */
const EXAM_REACHABILITY = {
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
    papers: [
      { year: 2018, easy: 39, medium: 45, hard: 16 },
      { year: 2019, easy: 22, medium: 59, hard: 19 },
      { year: 2020, easy: 18, medium: 50, hard: 32 },
      { year: 2021, easy: 18, medium: 54, hard: 28 },
      { year: 2022, easy: 21, medium: 53, hard: 26 },
      { year: 2023, easy: 17, medium: 55, hard: 28 },
      { year: 2024, easy: 23, medium: 50, hard: 27 },
      { year: 2026, easy: 10, medium: 56, hard: 34 },
    ],
  },
};

/**
 * Resolve the reachability config for an exam.
 *
 * `examKey` accepts a slug or an id — the landing page holds a slug, while the
 * component contract is written in terms of an exam id, and both should work
 * without the caller knowing which it has.
 *
 * `phaseId` narrows the series to papers explicitly carrying that phase. Read
 * the phase-scoping note at the top of this file before using it: on UPSC it
 * splits one continuous series in two.
 *
 * Returns `null` when the exam has no judged papers — the caller must render
 * the empty state, never a chart of import defaults.
 */
export function reachabilityConfigFor(examKey, phaseId = null) {
  if (!examKey) return null;
  const entry = EXAM_REACHABILITY[String(examKey)];
  if (!entry) return null;

  const papers = phaseId
    ? entry.papers.filter((p) => p.phaseId === phaseId)
    : entry.papers;
  if (!papers.length) return null;

  return {
    ...entry,
    papers: [...papers].sort((a, b) => a.year - b.year),
  };
}

export default EXAM_REACHABILITY;
