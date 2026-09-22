import React from "react";
import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const mockGet = jest.fn();
jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: (...args) => mockGet(...args) },
}));

import SyllabusRoadmap, { Sparkline, SyllabusRoadmapView } from "../SyllabusRoadmap";

const EXAM = "11111111-1111-1111-1111-111111111111";

const THRESHOLDS = { weak_below: 41, mastered_at: 82, min_attempts: 3, revise_after_days: 9 };

const FIXTURE = {
  exam_id: EXAM,
  generated_at: "2026-09-22T12:00:00+00:00",
  thresholds: THRESHOLDS,
  subjects: [
    {
      subject_id: "sub-1",
      name: "Reasoning",
      rollup: { not_started: 1, studied: 1, mastered: 1, weak_count: 1, revise_count: 1, pct_mastered: 33.3 },
      macros: [
        {
          topic_id: "m-1", name: "Puzzles", state: "mastered", score: 88.4, attempts: 4,
          last_practiced: "2026-09-01T00:00:00+00:00", weak: false, revise: true,
          history: [{ at: "2026-08-01", score: 60 }, { at: "2026-09-01", score: 88.4 }],
          completed_tasks: 2,
          micros: [
            { topic_id: "u-1", name: "Seating", state: "studied", completed_tasks: 1,
              is_high_yield: true, predictability_band: "high" },
          ],
        },
        {
          topic_id: "m-2", name: "Syllogism", state: "studied", score: 35, attempts: 3,
          last_practiced: null, weak: true, revise: false, history: [], completed_tasks: 0, micros: [],
        },
        {
          topic_id: "m-3", name: "Coding", state: "not_started", score: null, attempts: 0,
          last_practiced: null, weak: false, revise: false, history: [], completed_tasks: 0, micros: [],
        },
      ],
    },
  ],
};

function renderIt(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

function apiError(status) {
  const e = new Error(`http ${status}`);
  e.status = status;
  return e;
}

beforeEach(() => mockGet.mockReset());

test("renders state chips, badges and legend from the payload", () => {
  renderIt(<SyllabusRoadmapView data={FIXTURE} />);
  // Legend uses the response's thresholds, not constants.
  const legend = screen.getByTestId("roadmap-legend").textContent;
  expect(legend).toContain("82+");
  expect(legend).toContain("3+ attempts");
  expect(legend).toContain("below 41");
  expect(legend).toContain("more than 9 days");

  fireEvent.click(screen.getByRole("button", { name: /Reasoning/ }));
  const chips = screen.getAllByTestId("roadmap-state-chip").map((c) => c.textContent);
  expect(chips).toEqual(expect.arrayContaining(["✓Mastered", "◐Studied", "○Not started"]));
  expect(screen.getAllByTestId("roadmap-weak-badge")).toHaveLength(1);
  expect(screen.getAllByTestId("roadmap-revise-badge")).toHaveLength(1);
  expect(screen.queryByTestId("roadmap-empty")).toBeNull();

  // Expanding a macro shows its micros with the high-yield marker.
  fireEvent.click(screen.getByRole("button", { name: /Puzzles/ }));
  expect(screen.getByTestId("roadmap-micro-row").textContent).toContain("Seating");
  expect(screen.getByTestId("roadmap-high-yield")).toBeTruthy();
  for (const link of screen.getAllByTestId("roadmap-schedule-link")) {
    expect(link.getAttribute("href")).toBe("/app/study/plan");
  }
});

test("empty roadmap shows the practice line and all not_started", () => {
  const empty = {
    ...FIXTURE,
    subjects: [{ ...FIXTURE.subjects[0], macros: [FIXTURE.subjects[0].macros[2]] }],
  };
  renderIt(<SyllabusRoadmapView data={empty} />);
  expect(screen.getByTestId("roadmap-empty").textContent).toMatch(/fill this in/);
});

test("sparkline absent when history is empty", () => {
  const { container } = render(<Sparkline points={[]} />);
  expect(container.firstChild).toBeNull();
  render(<Sparkline points={[{ score: 50 }, { score: 70 }]} />);
  expect(screen.getByTestId("roadmap-sparkline")).toBeTruthy();
});

test("loads the primary exam's roadmap", async () => {
  mockGet.mockImplementation((path) =>
    path === "/api/study/target-exam"
      ? Promise.resolve({ selected_exam: { id: EXAM } })
      : Promise.resolve(FIXTURE),
  );
  renderIt(<SyllabusRoadmap />);
  expect(screen.getByRole("status").textContent).toMatch(/Loading/);
  await waitFor(() => expect(screen.getByTestId("roadmap-legend")).toBeTruthy());
  expect(mockGet).toHaveBeenCalledWith(`/api/study/progress/roadmap?exam_id=${EXAM}`);
});

test("503 shows an error with a working retry", async () => {
  let calls = 0;
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/target-exam") return Promise.resolve({ selected_exam: { id: EXAM } });
    calls += 1;
    return calls === 1 ? Promise.reject(apiError(503)) : Promise.resolve(FIXTURE);
  });
  renderIt(<SyllabusRoadmap />);
  await waitFor(() => expect(screen.getByTestId("roadmap-error")).toBeTruthy());
  fireEvent.click(screen.getByTestId("roadmap-retry"));
  await waitFor(() => expect(screen.getByTestId("roadmap-legend")).toBeTruthy());
  expect(calls).toBe(2);
});

test("409 shows the exam-not-ready message, not an error", async () => {
  mockGet.mockImplementation((path) =>
    path === "/api/study/target-exam"
      ? Promise.resolve({ selected_exam: { id: EXAM } })
      : Promise.reject(apiError(409)),
  );
  renderIt(<SyllabusRoadmap />);
  await waitFor(() => expect(screen.getByTestId("roadmap-not-ready")).toBeTruthy());
  expect(screen.queryByTestId("roadmap-error")).toBeNull();
  expect(screen.queryByTestId("roadmap-retry")).toBeNull();
});

test("no primary exam points to the Plan page", async () => {
  mockGet.mockResolvedValue({ selected_exam: null });
  renderIt(<SyllabusRoadmap />);
  await waitFor(() => expect(screen.getByTestId("roadmap-no-exam")).toBeTruthy());
  expect(mockGet).toHaveBeenCalledTimes(1);
});
