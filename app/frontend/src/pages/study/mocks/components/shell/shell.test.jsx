import React from 'react';
import { render, fireEvent, screen, act } from '@testing-library/react';
import QuestionPalette from './QuestionPalette';
import SectionTimer from './SectionTimer';
import SubmitConfirmDialog from './SubmitConfirmDialog';
import AntiCheatProvider from './AntiCheatProvider';

jest.useFakeTimers();

test('palette renders 100 questions', () => {
  const qs = Array.from({ length: 100 }, (_, i) => ({ id: `q${i}`, index: i }));
  const t0 = performance.now();
  render(<QuestionPalette questions={qs} statusMap={{}} currentIndex={0} onJump={()=>{}} />);
  const t1 = performance.now();
  expect(screen.getAllByRole('button').length).toBe(100);
  expect(t1 - t0).toBeLessThan(16);
});

test('timer clamps and expires once', () => {
  const onExpire = jest.fn();
  render(<SectionTimer expiresAt={new Date(Date.now()+1100).toISOString()} onExpire={onExpire} />);
  act(() => { jest.advanceTimersByTime(4000); });
  expect(onExpire).toHaveBeenCalledTimes(1);
});

test('submit dialog escape closes', () => {
  const onCancel = jest.fn();
  render(<SubmitConfirmDialog open summary={{total:1,answered:0,marked:0,not_visited:1,time_remaining_sec:1}} onConfirm={()=>{}} onCancel={onCancel} />);
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(onCancel).toHaveBeenCalled();
});

test('copy suppression scoped', () => {
  const onViolation = jest.fn();
  render(<><AntiCheatProvider blockCopy onViolation={onViolation}><div>inner</div></AntiCheatProvider><input aria-label='outside' /></>);
  fireEvent.copy(screen.getByText('inner'));
  expect(onViolation).toHaveBeenCalled();
});
