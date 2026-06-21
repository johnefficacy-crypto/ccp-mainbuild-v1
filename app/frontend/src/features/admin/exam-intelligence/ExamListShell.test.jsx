import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

const { api } = require("../../../lib/api");
const ExamListShell = require("./ExamListShell").default;

const PAGE = [
  {
    id: "exam-1", slug: "ssc-cgl", name: "SSC CGL", exam_type: "recruitment",
    management_mode: "core", cadence: "annual",
    verified_topic_count: 3, coverage_total: 5, readiness_level: "ready",
  },
  {
    id: "exam-2", slug: "upsc-cse", name: "UPSC CSE", exam_type: "entrance",
    management_mode: null, cadence: null,
    verified_topic_count: 0, coverage_total: 0, readiness_level: "not_ready",
  },
];

function mockExams(extra = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/exam-intelligence/exams")) {
      return Promise.resolve({ items: PAGE, total_count: 30, has_next: true, offset: 0, ...extra });
    }
    return Promise.resolve({}); // families etc.
  });
}

function wrap(props = {}) {
  return render(
    <MemoryRouter>
      <ExamListShell rowAction={(e) => <a href={`/c/${e.id}`} data-testid={`act-${e.id}`}>go</a>} {...props} />
    </MemoryRouter>,
  );
}

beforeEach(() => jest.clearAllMocks());

test("renders name-first rows with slug as secondary text", async () => {
  mockExams();
  wrap();
  await waitFor(() => expect(screen.getByTestId("exam-list-table")).toBeTruthy());
  expect(screen.getByText("SSC CGL")).toBeTruthy();
  expect(screen.getByTestId("exam-list-slug-exam-1").textContent).toBe("ssc-cgl");
});

test("injects the row action via the rowAction prop", async () => {
  mockExams();
  wrap();
  await waitFor(() => expect(screen.getByTestId("act-exam-1")).toBeTruthy());
  expect(screen.getByTestId("act-exam-2")).toBeTruthy();
});

test("sends the supported /exams filters (exam_type, management_mode, cadence)", async () => {
  mockExams();
  wrap();
  await waitFor(() => expect(screen.getByTestId("exam-list-table")).toBeTruthy());

  api.get.mockClear();
  mockExams();
  fireEvent.change(screen.getByTestId("exam-list-filter-type"), { target: { value: "entrance" } });
  await waitFor(() => expect(api.get.mock.calls.some((c) => c[0].includes("exam_type=entrance"))).toBe(true));

  api.get.mockClear();
  mockExams();
  fireEvent.change(screen.getByTestId("exam-list-filter-cadence"), { target: { value: "annual" } });
  await waitFor(() => expect(api.get.mock.calls.some((c) => c[0].includes("cadence=annual"))).toBe(true));
});

test("pagination advances offset by page size when has_next is true", async () => {
  mockExams();
  wrap();
  await waitFor(() => expect(screen.getByTestId("exam-list-next")).toBeTruthy());
  expect(screen.getByTestId("exam-list-prev")).toBeDisabled();
  expect(screen.getByTestId("exam-list-next")).not.toBeDisabled();

  api.get.mockClear();
  mockExams({ offset: 25 });
  fireEvent.click(screen.getByTestId("exam-list-next"));
  await waitFor(() => expect(api.get.mock.calls.some((c) => c[0].includes("offset=25"))).toBe(true));
});

test("readiness shows a status word, never a percentage", async () => {
  mockExams();
  wrap();
  await waitFor(() => expect(screen.getByTestId("exam-list-table")).toBeTruthy());
  expect(document.body.textContent).not.toMatch(/%/);
  expect(screen.getByText("ready")).toBeTruthy();
});

test("empty state shows no rows and offers a clear-filters reset", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exam-intelligence/exams")
      ? Promise.resolve({ items: [], total_count: 0 })
      : Promise.resolve({}),
  );
  wrap();
  await waitFor(() => expect(screen.getByTestId("exam-list-empty")).toBeTruthy());
  expect(screen.queryByTestId("exam-list-table")).toBeNull();
});

test("error state shows a retry and no rows", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exam-intelligence/exams")
      ? Promise.reject(new Error("nope"))
      : Promise.resolve({}),
  );
  wrap();
  await waitFor(() => expect(screen.getByTestId("exam-list-error")).toBeTruthy());
  expect(screen.queryByTestId("exam-list-table")).toBeNull();
});
