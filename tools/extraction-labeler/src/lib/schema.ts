import Ajv from 'ajv';
import addFormats from 'ajv-formats';

// Inlined from questions.schema.json — tool must not import from app/backend.
const QUESTIONS_SCHEMA = {
  $schema: 'http://json-schema.org/draft-07/schema#',
  $id: 'exam-intelligence-extraction-v1/questions',
  type: 'object',
  required: [
    'corpus_id',
    'document_id',
    'document_kind',
    'exam_id',
    'paper',
    'extractor_target',
    'expected_questions',
  ],
  properties: {
    corpus_id: { type: 'string', const: 'upsc-cse-prelims-pyq-v1' },
    document_id: { type: 'string', description: 'document_assets.id' },
    document_kind: { type: 'string', const: 'pyq_paper' },
    exam_id: { type: 'string', format: 'uuid' },
    paper: {
      type: 'object',
      required: ['paper_name', 'year', 'page_count'],
      properties: {
        paper_name: { type: 'string' },
        year: { type: 'integer', minimum: 1990 },
        page_count: { type: 'integer', minimum: 1 },
      },
    },
    extractor_target: { type: 'string', const: 'questions' },
    coord_system: { type: 'string', const: 'top_left_normalized' },
    expected_questions: {
      type: 'array',
      items: { $ref: '#/definitions/question' },
    },
  },
  definitions: {
    question: {
      type: 'object',
      required: ['question_number', 'question_text', 'regions'],
      properties: {
        question_number: { type: 'integer', minimum: 1 },
        question_text: { type: 'string', minLength: 1 },
        normalized_question_hash: {
          type: 'string',
          pattern: '^[a-f0-9]{64}$',
        },
        regions: {
          type: 'array',
          minItems: 1,
          items: { $ref: '#/definitions/region' },
        },
        notes: { type: 'string' },
      },
    },
    region: {
      type: 'object',
      required: ['page', 'bbox'],
      properties: {
        page: { type: 'integer', minimum: 1 },
        bbox: {
          type: 'array',
          minItems: 4,
          maxItems: 4,
          items: { type: 'number', minimum: 0, maximum: 1 },
          description:
            '[x_min, y_min, x_max, y_max], top-left origin, normalized [0..1]',
        },
        text_excerpt: { type: 'string' },
      },
    },
  },
  additionalProperties: false,
} as const;

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);
const _validate = ajv.compile(QUESTIONS_SCHEMA);

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export function validateFixture(doc: unknown): ValidationResult {
  const valid = _validate(doc) as boolean;
  const errors = valid
    ? []
    : (_validate.errors ?? []).map(
        (e) => `${e.instancePath || '(root)'} ${e.message ?? ''}`.trim(),
      );
  return { valid, errors };
}
