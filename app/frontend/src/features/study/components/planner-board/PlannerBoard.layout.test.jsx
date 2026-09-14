/**
 * PLAN-BUG-02 F6 — the palette must stay inside its container.
 *
 * jsdom does not lay out, so this asserts the CSS contract rather than pixels:
 * the grid track that holds the day scroller must be able to shrink, and the
 * scroller itself must be allowed to be narrower than its content. Those two
 * rules are the whole fix, and either one missing reproduces the overflow.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

const mockGet = jest.fn();

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...a) => mockGet(...a),
    post: jest.fn(),
    patch: jest.fn(),
    del: jest.fn(),
  },
}));

jest.mock("../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({ busy: false, run: async ({ action }) => ({ ok: true, data: await action() }) }),
}));

// eslint-disable-next-line import/first
import PlannerBoard from "./PlannerBoard";

const DAYS = [
  "2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17",
  "2026-09-18", "2026-09-19", "2026-09-20",
];

beforeEach(() => {
  jest.clearAllMocks();
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/plan/board") {
      return Promise.resolve({
        plan_id: "plan-1",
        today: DAYS[0],
        days: DAYS.map((d, i) => ({ date: d, label: i === 0 ? "Today" : d, tasks: [] })),
        max_tasks_per_day: 3,
        read_error: false,
      });
    }
    if (path === "/api/study/plan/candidates") {
      return Promise.resolve({
        items: Array.from({ length: 60 }, (_, i) => ({
          topic_id: `t-${i}`,
          topic: `A very long topic name that would push a container wide ${i}`,
          subject: "General Studies",
          comparable_priority: 50,
        })),
      });
    }
    return Promise.resolve({});
  });
});

test("the day scroller sits in a track that can shrink below its content", async () => {
  const { container } = render(<PlannerBoard />);
  await waitFor(() => expect(screen.getByLabelText(/^Today,/)).toBeInTheDocument());

  const grid = container.querySelector(".grid.gap-6");
  expect(grid).toBeTruthy();

  // A bare `1fr` track has `min-width: auto` and refuses to shrink below the
  // seven 210px columns inside it — the track grows, `overflow-x-auto` never
  // engages, and the palette column is pushed outside the container.
  expect(grid.className).toContain("lg:grid-cols-[minmax(0,1fr)_460px]");
  expect(grid.className).not.toMatch(/lg:grid-cols-\[1fr_/);
});

test("the scroller is allowed to be narrower than the columns it holds", async () => {
  const { container } = render(<PlannerBoard />);
  await waitFor(() => expect(screen.getByLabelText(/^Today,/)).toBeInTheDocument());

  const scroller = container.querySelector(".overflow-x-auto");
  expect(scroller).toBeTruthy();
  // Same rule one level down: a flex item's `min-width: auto` would otherwise
  // hold the scroller open to its content's full intrinsic width.
  expect(scroller.className).toContain("min-w-0");
});

test("the palette's own panes scroll rather than growing the panel", async () => {
  render(<PlannerBoard />);
  const tree = await screen.findByTestId("palette-tree");
  expect(tree.className).toContain("overflow-y-auto");
  expect(tree.className).toMatch(/max-h-\[\d+px\]/);
});
