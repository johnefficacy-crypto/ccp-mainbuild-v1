/**
 * Editorial and derivations for the CSAT composition section.
 *
 * WHY THIS IS NOT THE REACHABILITY CHART. The reachability trend measures how
 * reachable a question was from standard preparation, against a rubric written
 * for UPSC GS-I. That rubric does not transfer: "reachable from an NCERT
 * textbook" says nothing about a percentages question, and CSAT's stored
 * observed_difficulty was assigned by keyword rule rather than judged against
 * any rubric at all. So CSAT is absent from that chart, and nothing here
 * reports difficulty — no band, no scale, no derived label.
 *
 * This section answers a different question off a different column: what each
 * paper was MADE OF, by the primary topic tag on each question.
 *
 * NO COUNTS LIVE IN THIS FILE. Every number the section shows, the analysis
 * paragraphs included, is computed from the endpoint payload — see
 * `csatAnalysis` below. The reachability config was emptied of its hardcoded
 * counts for going stale the moment a paper was tagged; writing the same
 * figures here in prose would reintroduce exactly that drift, one sentence at a
 * time.
 */

/**
 * Categorical subject colors, fixed per subject, never cycled. Reuses the
 * palette already carried elsewhere on this page (see CATEGORY_COLORS in
 * ExamIntelligenceTab) so the exam page stays one system rather than two.
 * Identity never rests on hue alone: every bar is labelled and every subject
 * appears in the legend and in the tab strip.
 */
export const SUBJECT_COLOR = {
  "55555555-5555-5555-5555-555555555551": "#54794E", // Quantitative Aptitude
  "55555555-5555-5555-5555-555555555553": "#524864", // Reasoning
  "55555555-5555-5555-5555-555555555552": "#A68057", // English Language
};

export const SUBJECT_FALLBACK_COLOR = "#7A6A55";

export function subjectColor(subjectId) {
  return SUBJECT_COLOR[subjectId] || SUBJECT_FALLBACK_COLOR;
}

/**
 * Rendered whenever the section renders. Not dismissible, not behind a
 * disclosure. The second sentence is the one that stops a topic ranking being
 * read as a difficulty ranking.
 */
export const PROVENANCE_LINE =
  "Composition of four CSAT papers (2023-2026), from the primary topic tag on " +
  "each question. Shows what the paper was made of, not how hard the " +
  "questions were.";

/** Quant carries twenty microtopics; the rest sit behind a control. */
export const QUANT_VISIBLE_TOPICS = 12;

/** The overall ranking opens at twelve and expands to the full list. */
export const OVERALL_VISIBLE_TOPICS = 12;

/** Which subject the topic tabs open on. */
export const DEFAULT_SUBJECT_ID = "55555555-5555-5555-5555-555555555551";

/**
 * Subjects that show only their top slice by default. Reasoning and English
 * are short enough to show whole; Quant is not.
 */
export const TRUNCATED_SUBJECTS = new Set([DEFAULT_SUBJECT_ID]);

const PROVENANCE_SOURCE = "GET /api/exam-intelligence/exams/{slug}/csat-composition";
export { PROVENANCE_SOURCE };

/** Papers that carry at least one primary tag — the ones with a chart to draw. */
export function taggedPapers(papers) {
  return (papers || []).filter((p) => (p.tagged_questions || 0) > 0);
}

/** Papers in the series that carry no primary tag at all — an empty state each. */
export function untaggedPapers(papers) {
  return (papers || []).filter((p) => (p.tagged_questions || 0) === 0);
}

export function paperLabel(paper) {
  return paper.year != null ? String(paper.year) : paper.paper_id;
}

/**
 * One row per paper, one numeric key per subject: the stacked subject split.
 */
export function subjectSplitRows(papers, subjects) {
  return taggedPapers(papers).map((p) => {
    const row = { key: p.paper_id, label: paperLabel(p), total: p.tagged_questions };
    (subjects || []).forEach((s) => {
      row[s.subject_id] = (p.by_subject || {})[s.subject_id] || 0;
    });
    return row;
  });
}

/**
 * Topics of one subject, ranked by total across every paper, each carrying its
 * per-paper counts as numeric keys so the bar can stack by year.
 *
 * The per-year counts are the point, not decoration: a topic that ran 16, 8,
 * 16, 8 and one that ran 12, 12, 12, 12 aggregate to the same 48, and only one
 * of those is a paper alternating between two shapes.
 */
export function topicRows(topics, subjectId, papers) {
  const cols = taggedPapers(papers);
  return (topics || [])
    .filter((t) => !subjectId || t.subject_id === subjectId)
    .map((t) => {
      const row = {
        key: t.topic_id,
        label: t.topic_name || t.topic_id,
        subjectId: t.subject_id,
        total: t.total,
        perPaper: cols.map((p) => ({
          paperId: p.paper_id,
          label: paperLabel(p),
          count: (t.by_paper || {})[p.paper_id] || 0,
        })),
      };
      cols.forEach((p) => {
        row[p.paper_id] = (t.by_paper || {})[p.paper_id] || 0;
      });
      return row;
    })
    .sort((a, b) => b.total - a.total || a.label.localeCompare(b.label));
}

function subjectName(subjects, subjectId) {
  const hit = (subjects || []).find((s) => s.subject_id === subjectId);
  return hit?.name || "this subject";
}

function listOf(names) {
  if (names.length <= 1) return names[0] || "";
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

/**
 * The written observation, computed from the payload rather than typed.
 *
 * Every figure quoted below is read off the same rows the charts are drawn
 * from, so the prose cannot drift from the chart above it the way a hardcoded
 * paragraph would as papers are tagged.
 *
 * It stays an OBSERVATION about this corpus. No second person, no imperative,
 * no ordering of what to study, and no claim about what a future paper will
 * contain — a test asserts the absence of all four, because the line between
 * "here is what these four papers held" and "here is what to do about it" is
 * what makes this publishable at all.
 */
export function csatAnalysis(payload) {
  const papers = taggedPapers(payload?.papers);
  const topics = payload?.topics || [];
  const subjects = payload?.subjects || [];
  if (papers.length === 0 || topics.length === 0) return [];

  const totalQuestions = papers.reduce((n, p) => n + (p.tagged_questions || 0), 0);
  const quantId = subjects[0]?.subject_id || DEFAULT_SUBJECT_ID;
  const quantCounts = papers.map((p) => (p.by_subject || {})[quantId] || 0);
  const quantLow = Math.min(...quantCounts);
  const quantHigh = Math.max(...quantCounts);
  const paperSizes = papers.map((p) => p.tagged_questions || 0);
  const biggestPaper = Math.max(...paperSizes);

  const everyPaper = topics.filter((t) =>
    papers.every((p) => ((t.by_paper || {})[p.paper_id] || 0) > 0)
  ).length;

  const top3 = topics.slice(0, 3);
  const top3Share = top3.reduce((n, t) => n + t.total, 0);

  const bySubject = (sid) => topics.filter((t) => t.subject_id === sid);
  const subjectTotal = (sid) => bySubject(sid).reduce((n, t) => n + t.total, 0);

  const quantTop = bySubject(quantId)[0];
  const quantSeries = quantTop
    ? papers.map((p) => (quantTop.by_paper || {})[p.paper_id] || 0)
    : [];

  const paras = [
    `${subjectName(subjects, quantId)} is about half of every paper in this ` +
      `set — between ${quantLow} and ${quantHigh} questions of a paper of up ` +
      `to ${biggestPaper}. Across the four years that share barely moves.`,
    `Only ${topics.length} distinct topics appear across ${totalQuestions} ` +
      `questions, and ${everyPaper} of them appear in every paper. Three of ` +
      `them carry ${top3Share} questions between them — ` +
      `${listOf(top3.map((t) => `${t.topic_name} (${t.total})`))}.`,
  ];

  if (quantTop) {
    paras.push(
      `Inside ${subjectName(subjects, quantId).toLowerCase()}, ` +
        `${quantTop.topic_name} alone accounts for ${quantTop.total} of ` +
        `${subjectTotal(quantId)} questions, and it does not sit flat: it runs ` +
        `${quantSeries.join(", ")} across the four papers.`
    );
  }

  subjects.slice(1).forEach((s) => {
    const rows = bySubject(s.subject_id);
    if (rows.length === 0) return;
    const total = subjectTotal(s.subject_id);
    // A subject dominated by one topic reads differently from one spread over
    // a handful, so the sentence follows the shape of the data rather than a
    // fixed template: "one topic and a tail" only when the leader really is one.
    if (rows[0].total / total >= 0.4) {
      paras.push(
        `${s.name} is one topic and a tail: ${rows[0].topic_name} is ` +
          `${rows[0].total} of ${total}, spread over ${rows.length} topics in all.`
      );
    } else {
      const head = rows.slice(0, 4);
      paras.push(
        `${s.name} is ${rows.length} topics — ` +
          `${listOf(head.map((t) => t.topic_name.toLowerCase()))} — ` +
          `carrying ${head.reduce((n, t) => n + t.total, 0)} of ${total}.`
      );
    }
  });

  paras.push(
    "These are counts of what these four papers contained. They describe this " +
      "corpus and nothing beyond it."
  );
  return paras;
}
