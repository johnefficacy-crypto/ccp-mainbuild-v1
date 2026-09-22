import React from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ResourcesScreen from "./ResourcesScreen";

// CA-RES-01 — the lane filter.
//
// Every lane compared r.category, but the API returned no such field and two of
// the lanes ("Official", "Community") are source-trust views, not categories.
// Result: every lane except "All" rendered empty. These cover both halves.

const ITEMS = [
  {
    id: "r1", title: "Weekly current-affairs digest", type: "current_affairs_digest",
    category: "current_affairs", exam: "all", subject: "General",
    sourceTrust: "official", sourceUrl: "https://example.test/ca", size: "link",
    upvotes: 5, status: "approved",
  },
  {
    id: "r2", title: "Polity notes", type: "notes",
    category: "study_material", exam: "all", subject: "Polity",
    sourceTrust: "community", sourceUrl: "https://example.test/notes", size: "link",
    upvotes: 3, status: "approved",
  },
  {
    id: "r3", title: "Prelims 2024 paper", type: "pyq_paper",
    category: "pyq", exam: "all", subject: "General",
    sourceTrust: "official", sourceUrl: "https://example.test/pyq", size: "link",
    upvotes: 1, status: "approved",
  },
];

const mockApiGet = jest.fn();

jest.mock("../../lib/api", () => ({
  api: {
    get: (...args) => mockApiGet(...args),
    post: jest.fn().mockResolvedValue({}),
  },
}));

jest.mock("../../lib/authContext", () => ({
  useAuth: () => ({ user: { id: "u1", goal_exams: [] } }),
}));

// env.js throws without REACT_APP_BACKEND_URL, which the CI frontend job does
// not set. Mocked so the lane behaviour is tested without a backend URL, and
// with demo data off so only the API items above are rendered.
jest.mock("../../shared/config/env", () => ({
  ENABLE_DEMO_DATA: false,
  BACKEND_URL: "http://backend.test",
}));

function renderScreen() {
  return render(
    <MemoryRouter>
      <ResourcesScreen />
    </MemoryRouter>,
  );
}

async function titlesAfterLane(lane) {
  fireEvent.click(screen.getByTestId(`res-lane-${lane}`));
  await waitFor(() => screen.getByTestId("resources-page"));
  return ITEMS.filter((i) => screen.queryByText(i.title)).map((i) => i.title);
}

beforeEach(() => {
  mockApiGet.mockReset();
  mockApiGet.mockResolvedValue({ items: ITEMS });
});

test("category lanes show only their own resources", async () => {
  renderScreen();
  await waitFor(() => screen.getByText("Weekly current-affairs digest"));

  expect(await titlesAfterLane("current_affairs")).toEqual(["Weekly current-affairs digest"]);
  expect(await titlesAfterLane("study_material")).toEqual(["Polity notes"]);
  expect(await titlesAfterLane("pyq")).toEqual(["Prelims 2024 paper"]);
});

test("official and community lanes filter on source trust, not category", async () => {
  renderScreen();
  await waitFor(() => screen.getByText("Weekly current-affairs digest"));

  // Both of these were permanently empty before the fix.
  expect(await titlesAfterLane("official")).toEqual([
    "Weekly current-affairs digest",
    "Prelims 2024 paper",
  ]);
  expect(await titlesAfterLane("community")).toEqual(["Polity notes"]);
});

test("the all lane shows everything", async () => {
  renderScreen();
  await waitFor(() => screen.getByText("Weekly current-affairs digest"));
  expect(await titlesAfterLane("all")).toEqual(ITEMS.map((i) => i.title));
});

test("an empty lane renders nothing rather than falling back to all", async () => {
  renderScreen();
  await waitFor(() => screen.getByText("Weekly current-affairs digest"));
  expect(await titlesAfterLane("practice")).toEqual([]);
});

test("lane is never sent to the API, which has no lane parameter", async () => {
  renderScreen();
  await waitFor(() => expect(mockApiGet).toHaveBeenCalled());

  fireEvent.click(screen.getByTestId("res-lane-current_affairs"));
  await waitFor(() => screen.getByTestId("resources-page"));

  for (const [url] of mockApiGet.mock.calls) {
    expect(url).not.toContain("lane=");
  }
});
