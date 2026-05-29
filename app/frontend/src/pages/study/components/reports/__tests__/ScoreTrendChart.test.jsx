import { render, screen } from '@testing-library/react';
import ScoreTrendChart from '../ScoreTrendChart';

beforeAll(() => {
  global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
});

test('renders heading and summary', () => {
  render(<ScoreTrendChart data={[{ attempt_id: 'a1', score_pct: 72, attempt_label: 'A1' }]} />);
  expect(screen.getByText('Score Trend')).toBeTruthy();
  expect(screen.getByText('Trend across attempts')).toBeTruthy();
});
