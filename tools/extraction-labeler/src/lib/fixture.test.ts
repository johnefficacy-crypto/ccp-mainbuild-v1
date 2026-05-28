import { describe, it, expect } from 'vitest';
import { buildFixture, skippedCount } from './fixture';
import type { LabeledQuestion, PaperMeta } from '../types';

function makeQ(overrides?: Partial<LabeledQuestion>): LabeledQuestion {
  return {
    id: 'test-id-1',
    question_number: 1,
    question_text: 'Which of the following is correct?',
    regions: [{ page: 1, bbox: [0.1, 0.1, 0.9, 0.2] }],
    ...overrides,
  };
}

const defaultMeta: PaperMeta = {
  paper_name: 'General Studies Paper I 2023',
  year: 2023,
  page_count: 20,
};

describe('buildFixture', () => {
  it('includes in-scope questions in expected_questions', () => {
    const q1 = makeQ({ id: 'q1', question_number: 1 });
    const q2 = makeQ({ id: 'q2', question_number: 2 });
    const result = buildFixture('doc-id', 'exam-id', defaultMeta, [q1, q2]);
    expect(result.expected_questions).toHaveLength(2);
  });

  it('excludes out_of_scope_v1: true questions from expected_questions', () => {
    const q1 = makeQ({ id: 'q1', question_number: 1 });
    const q2 = makeQ({ id: 'q2', question_number: 2, out_of_scope_v1: true });
    const q3 = makeQ({ id: 'q3', question_number: 3 });
    const result = buildFixture('doc-id', 'exam-id', defaultMeta, [q1, q2, q3]);
    expect(result.expected_questions).toHaveLength(2);
    expect(result.expected_questions.map((q) => q.question_number)).toEqual([1, 3]);
  });

  it('does not include id in exported question objects', () => {
    const q = makeQ({ id: 'should-not-appear' });
    const result = buildFixture('doc-id', 'exam-id', defaultMeta, [q]);
    const exported = result.expected_questions[0];
    expect(exported).not.toHaveProperty('id');
  });

  it('does not include out_of_scope_v1 in exported question objects', () => {
    const q = makeQ({ out_of_scope_v1: false });
    const result = buildFixture('doc-id', 'exam-id', defaultMeta, [q]);
    const exported = result.expected_questions[0];
    expect(exported).not.toHaveProperty('out_of_scope_v1');
  });

  it('sets correct fixture metadata fields', () => {
    const result = buildFixture('my-doc-id', 'my-exam-id', defaultMeta, []);
    expect(result.corpus_id).toBe('upsc-cse-prelims-pyq-v1');
    expect(result.document_id).toBe('my-doc-id');
    expect(result.exam_id).toBe('my-exam-id');
    expect(result.document_kind).toBe('pyq_paper');
    expect(result.extractor_target).toBe('questions');
    expect(result.coord_system).toBe('top_left_normalized');
    expect(result.paper).toEqual(defaultMeta);
  });
});

describe('skippedCount', () => {
  it('returns 0 when no questions are out-of-scope', () => {
    const questions = [makeQ({ id: 'q1' }), makeQ({ id: 'q2' })];
    expect(skippedCount(questions)).toBe(0);
  });

  it('returns correct count of out-of-scope questions', () => {
    const questions = [
      makeQ({ id: 'q1' }),
      makeQ({ id: 'q2', out_of_scope_v1: true }),
      makeQ({ id: 'q3', out_of_scope_v1: true }),
      makeQ({ id: 'q4' }),
    ];
    expect(skippedCount(questions)).toBe(2);
  });

  it('returns 0 for empty array', () => {
    expect(skippedCount([])).toBe(0);
  });
});
