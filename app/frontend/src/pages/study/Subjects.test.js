import React from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const mockGet = jest.fn();
const mockPost = jest.fn();
jest.mock("../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
  },
}));

// env.js throws at module load without REACT_APP_BACKEND_URL; useApiCollection
// pulls ENABLE_DEMO_DATA from it. Stub so the suite is hermetic.
jest.mock("../../shared/config/env", () => ({
  __esModule: true,
  ENABLE_DEMO_DATA: false,
  BACKEND_URL: "http://test.local",
  API_TIMEOUT_MS: 15000,
}));

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => {
  const actual = jest.requireActual("react-router-dom");
  return { __esModule: true, ...actual, useNavigate: () => mockNavigate };
});

// Radar chart is heavy (recharts) and irrelevant to this page's behavior.
jest.mock("./components/reports", () => ({
  __esModule: true,
  TopicRadarChart: () => null,
}));

import ToastProvider from "../../shared/ui/ToastProvider";
import Subjects from "./Subjects";

function renderPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <Subjects />
      </ToastProvider>
    </MemoryRouter>,
  );
}

const SUBJECTS = [
  {
    subject_id: "sub-english",
    subject: "English",
    progress: 62,
    trend: "up",
    weak_count: 3,
    locked_topics: 8,
    practice: {
      available: true,
      modes: [
        {
          type: "english_writing",
          label: "Sentence practice",
          target_topic_id: null,
          route_type: "server_launch",
          launch_mode: "english_writing",
        },
        {
          type: "error_lab",
          label: "Error Lab",
          target_topic_id: null,
          route_type: "client_route",
          route: "/app/study/error-lab",
        },
      ],
    },
  },
  {
    subject_id: "sub-quant",
    subject: "Quantitative Aptitude",
    progress: 40,
    trend: "flat",
    weak_count: 5,
    locked_topics: 12,
    practice: { available: false, modes: [] },
  },
  {
    subject_id: "sub-ga",
    subject: "General Awareness",
    progress: 0,
    trend: "flat",
    weak_count: 0,
    locked_topics: 4,
    practice: {
      available: true,
      modes: [
        {
          type: "weekly_current_affairs",
          label: "Weekly current affairs",
          target_topic_id: null,
          route_type: "server_launch",
          launch_mode: "weekly_current_affairs",
        },
      ],
    },
  },
];

beforeEach(() => {
  mockGet.mockReset();
  mockPost.mockReset();
  mockNavigate.mockReset();
});

test("renders subject cards from the mocked /api/study/subjects", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  renderPage();

  expect(screen.getByTestId("subjects-page")).toBeTruthy();
  await waitFor(() => expect(screen.getByText("English")).toBeTruthy());
  expect(screen.getByText("Quantitative Aptitude")).toBeTruthy();
  // Mastery summary line preserved.
  expect(screen.getByText(/62% mastery · 3 weak · 8 topics/)).toBeTruthy();
});

test("a server_launch button POSTs the launch endpoint and navigates to the returned route", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  mockPost.mockResolvedValue({ kind: "english_writing", route: "/app/study/practice/english/abc" });
  renderPage();

  const btn = await screen.findByTestId("practice-sub-english-english_writing");
  fireEvent.click(btn);

  await waitFor(() =>
    expect(mockPost).toHaveBeenCalledWith(
      "/api/study/subjects/sub-english/practice/start",
      { mode: "english_writing", topic_id: null },
    ),
  );
  await waitFor(() =>
    expect(mockNavigate).toHaveBeenCalledWith("/app/study/practice/english/abc"),
  );
});

test("client_route mode renders a link (no POST)", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  renderPage();

  const link = await screen.findByTestId("practice-sub-english-error_lab");
  expect(link.tagName.toLowerCase()).toBe("a");
  expect(link.getAttribute("href")).toBe("/app/study/error-lab");
});

test("a subject with practice.available=false shows the calm no-practice copy", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  renderPage();

  await waitFor(() => expect(screen.getByText("Quantitative Aptitude")).toBeTruthy());
  expect(screen.getByTestId("practice-sub-quant-none").textContent).toMatch(
    /No verified practice set yet/,
  );
});

test("weekly current-affairs launch navigates to the returned CA attempt route", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  mockPost.mockResolvedValue({
    kind: "current_affairs",
    outcome: "ready",
    route: "/app/study/current-affairs/attempts/ca-1",
  });
  renderPage();

  const btn = await screen.findByTestId("practice-sub-ga-weekly_current_affairs");
  fireEvent.click(btn);

  await waitFor(() =>
    expect(mockPost).toHaveBeenCalledWith(
      "/api/study/subjects/sub-ga/practice/start",
      { mode: "weekly_current_affairs", topic_id: null },
    ),
  );
  await waitFor(() =>
    expect(mockNavigate).toHaveBeenCalledWith("/app/study/current-affairs/attempts/ca-1"),
  );
});

test("weekly current-affairs no_bundle outcome shows a calm note and does not navigate", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  // no_bundle is returned as a 200 body with an outcome and NO route.
  mockPost.mockResolvedValue({ kind: "current_affairs", outcome: "no_bundle" });
  renderPage();

  const btn = await screen.findByTestId("practice-sub-ga-weekly_current_affairs");
  fireEvent.click(btn);

  await waitFor(() =>
    expect(screen.getByTestId("practice-sub-ga-notice").textContent).toMatch(
      /No current-affairs set is published/,
    ),
  );
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("a 409 on launch shows an inline notice and does not navigate", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  const err = new Error("no_eligible_prompt");
  err.status = 409;
  mockPost.mockRejectedValue(err);
  renderPage();

  const btn = await screen.findByTestId("practice-sub-english-english_writing");
  fireEvent.click(btn);

  await waitFor(() =>
    expect(screen.getByTestId("practice-sub-english-notice").textContent).toMatch(
      /No verified practice set yet/,
    ),
  );
  expect(mockNavigate).not.toHaveBeenCalled();
});
