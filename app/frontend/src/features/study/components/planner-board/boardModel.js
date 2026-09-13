/**
 * Pure board-state helpers for the drag-and-drop planner.
 *
 * Kept free of React so the move arithmetic — the part that has to be exactly
 * right, and the part a failed write has to undo — is testable on its own and
 * cannot drift between the pointer path and the keyboard path. Both call
 * `applyMove`; there is one implementation of "what the board looks like after
 * this move", not two.
 */

/** Deep-enough clone of the board so an optimistic update never mutates state. */
export function cloneBoard(board) {
  if (!board) return board;
  return {
    ...board,
    days: (board.days || []).map((d) => ({ ...d, tasks: [...(d.tasks || [])] })),
  };
}

export function findTask(board, taskId) {
  for (const day of board?.days || []) {
    const index = (day.tasks || []).findIndex((t) => t.id === taskId);
    if (index !== -1) return { day, index, task: day.tasks[index] };
  }
  return null;
}

/**
 * Move one card to `toDate` at `toIndex`, returning a new board.
 *
 * The moved card is marked `placed_by_user` immediately because that is what
 * the server does: arranging a card is the user claiming it from the planner.
 * Showing it any other way would mean the badge flickers from "Planner" to
 * "Yours" a round-trip later, which reads as a bug.
 */
export function applyMove(board, taskId, toDate, toIndex) {
  const next = cloneBoard(board);
  const found = findTask(next, taskId);
  if (!found) return next;

  const target = next.days.find((d) => d.date === toDate);
  if (!target) return next;

  found.day.tasks.splice(found.index, 1);
  const moved = {
    ...found.task,
    scheduled_date: toDate,
    source: "user",
    placed_by_user: true,
  };
  const index = Math.max(0, Math.min(toIndex ?? target.tasks.length, target.tasks.length));
  target.tasks.splice(index, 0, moved);
  return next;
}

export function removeTask(board, taskId) {
  const next = cloneBoard(board);
  const found = findTask(next, taskId);
  if (found) found.day.tasks.splice(found.index, 1);
  return next;
}

export function insertCard(board, card, toDate, toIndex) {
  const next = cloneBoard(board);
  const target = next.days.find((d) => d.date === toDate);
  if (!target) return next;
  const index = Math.max(0, Math.min(toIndex ?? target.tasks.length, target.tasks.length));
  target.tasks.splice(index, 0, card);
  return next;
}

/**
 * Where a keyboard move lands after one arrow press.
 *
 * Up/Down walk positions inside the day; Left/Right walk days, entering the
 * neighbour at the same position (clamped). Returns null when the key is not a
 * move, so the caller can let the event through.
 */
export function nextKeyboardPlacement(board, { date, index }, key) {
  const days = board?.days || [];
  const dayIndex = days.findIndex((d) => d.date === date);
  if (dayIndex === -1) return null;
  const count = (days[dayIndex].tasks || []).length;

  if (key === "ArrowUp") return { date, index: Math.max(0, index - 1) };
  if (key === "ArrowDown") return { date, index: Math.min(count - 1, index + 1) };
  if (key === "ArrowLeft" || key === "ArrowRight") {
    const step = key === "ArrowLeft" ? -1 : 1;
    const nextDay = days[dayIndex + step];
    if (!nextDay) return null;
    const nextCount = (nextDay.tasks || []).length;
    return { date: nextDay.date, index: Math.min(index, nextCount) };
  }
  return null;
}

/** Plain-language position announcement for the live region. */
export function describePlacement(board, taskId) {
  const found = findTask(board, taskId);
  if (!found) return "";
  const total = found.day.tasks.length;
  return `${found.task.topic || found.task.title}, ${found.day.label}, position ${
    found.index + 1
  } of ${total}.`;
}
