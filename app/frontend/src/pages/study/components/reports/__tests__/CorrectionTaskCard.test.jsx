import { render, screen } from '@testing-library/react';

import CorrectionTaskCard from '../CorrectionTaskCard';

// Mirrors a CorrectionTaskDraft as serialized by the backend (Decimal/UUID as strings).
const validTask = {
  user_id: 'u-1',
  topic_id: 'topic-quant',
  microtopic_id: null,
  task_type: 'concept_review',
  priority: 1,
  reason: 'concept_review due to 5 attempted with 40% accuracy',
  evidence: {
    accuracy_pct: '40',
    error_types: ['concept_gap'],
    related_question_ids: ['q1', 'q2'],
  },
  estimated_minutes: 30,
  source_attempt_id: '00000000-0000-0000-0000-000000000000',
};

test('renders a CorrectionTaskDraft using schema fields', () => {
  render(<CorrectionTaskCard task={validTask} />);
  expect(screen.getByText('Concept Review')).toBeTruthy();
  expect(screen.getByText(validTask.reason)).toBeTruthy();
  expect(screen.getByText('P1')).toBeTruthy();
  expect(screen.getByText('~30 min')).toBeTruthy();
  expect(screen.getByText('concept_gap')).toBeTruthy();
});

test('renders nothing when task is missing', () => {
  const { container } = render(<CorrectionTaskCard task={null} />);
  expect(container.firstChild).toBeNull();
});

test('PropTypes accept a valid draft and reject a schema mismatch', () => {
  const errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

  render(<CorrectionTaskCard task={validTask} />);
  expect(errSpy).not.toHaveBeenCalled();

  // priority is required int per the contract; a string must trip PropTypes.
  render(<CorrectionTaskCard task={{ ...validTask, priority: 'high' }} />);
  expect(errSpy).toHaveBeenCalled();
  const allOutput = errSpy.mock.calls.map((args) => args.join(' ')).join('\n');
  expect(allOutput).toContain('priority');

  errSpy.mockRestore();
});
