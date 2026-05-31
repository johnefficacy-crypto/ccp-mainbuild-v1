import type { LabeledQuestion, PaperMeta } from '../types';

export interface SkippedEntry {
  question_number: number;
  reason: string;
}

export interface FixtureDoc {
  corpus_id: 'upsc-cse-prelims-pyq-v1';
  document_id: string;
  document_kind: 'pyq_paper';
  exam_id: string;
  paper: {
    paper_name: string;
    year: number;
    page_count: number;
  };
  extractor_target: 'questions';
  coord_system: 'top_left_normalized';
  expected_questions: Array<Omit<LabeledQuestion, 'id' | 'out_of_scope_v1'>>;
  skipped: SkippedEntry[];
}

/**
 * Returns the number of questions marked out_of_scope_v1.
 */
export function skippedCount(questions: LabeledQuestion[]): number {
  return questions.filter((q) => q.out_of_scope_v1).length;
}

/**
 * Builds the exportable fixture document from the current session state.
 * In-scope questions go to expected_questions; OOS questions go to skipped[].
 */
export function buildFixture(
  documentId: string,
  examId: string,
  paperMeta: PaperMeta,
  questions: LabeledQuestion[],
): FixtureDoc {
  const inScope = questions.filter((q) => !q.out_of_scope_v1);
  const outOfScope = questions.filter((q) => q.out_of_scope_v1);
  return {
    corpus_id: 'upsc-cse-prelims-pyq-v1',
    document_id: documentId,
    document_kind: 'pyq_paper',
    exam_id: examId,
    paper: {
      paper_name: paperMeta.paper_name,
      year: paperMeta.year,
      page_count: paperMeta.page_count,
    },
    extractor_target: 'questions',
    coord_system: 'top_left_normalized',
    expected_questions: inScope.map(({ id: _id, out_of_scope_v1: _oos, ...rest }) => rest),
    skipped: outOfScope.map((q) => ({ question_number: q.question_number, reason: 'out_of_scope_v1' })),
  };
}
