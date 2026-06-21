/**
 * Targeted label-semantics tests for Mocks.jsx (§17 frontend label fix).
 *
 * Acceptance:
 * - Self-logged mocks show "Self-reported error patterns" + user-entered footer.
 * - Self-logged subtitle: "based on the values you entered" (not "extracted").
 * - Platform subtitle: "derived from your platform-scored attempt".
 * - Platform mocks show "Error patterns" with no self-reported copy.
 * - Average stat is scoped: "Average across N logged mocks" (0/1/many).
 */
import React from "react";
import { act, render, screen } from "@testing-library/react";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPatch = jest.fn();

jest.mock("../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
    patch: (...args) => mockPatch(...args),
  },
}));

jest.mock("../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({ run: jest.fn() }),
}));

jest.mock("react-router-dom", () => ({
  useNavigate: () => jest.fn(),
}));

import Mocks from "../study/Mocks";

const SELF_LOGGED_ITEM = {
  id: "mock-sl-1",
  name: "SSC CGL Mock 3",
  exam_slug: "ssc-cgl-2026",
  score: 153,
  max_score: 200,
  percentage: 76.5,
  review_state: "unreviewed",
  trust_level: "self_reported",
  source_type: "manual_log",
  attempted_at: "2026-06-10T10:00:00Z",
};

const PLATFORM_ITEM = {
  id: "mock-pa-1",
  name: "IBPS PO Prelims Mock 1",
  exam_slug: "ibps-po-xv",
  score: 58,
  max_score: 100,
  percentage: 58,
  review_state: "unreviewed",
  trust_level: "platform_verified",
  source_type: "platform_attempt",
  attempted_at: "2026-06-11T10:00:00Z",
};

const SELF_LOGGED_ANALYSIS = {
  mock: { ...SELF_LOGGED_ITEM },
  review_state: "unreviewed",
  subject_breakdown: [],
  error_patterns: { concept: 3, time: 2, guess: 1 },
  correction_tasks: [],
};

const PLATFORM_ANALYSIS = {
  mock: { ...PLATFORM_ITEM },
  review_state: "unreviewed",
  subject_breakdown: [],
  error_patterns: { concept: 5, misread: 2 },
  correction_tasks: [],
};

function primeApi({ item, analysis }) {
  mockGet.mockReset();
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/mocks")
      return Promise.resolve({ items: [item], trend: [] });
    if (path === `/api/study/mocks/${item.id}/analysis`)
      return Promise.resolve(analysis);
    if (path === "/api/recruitments")
      return Promise.resolve({ items: [] });
    return Promise.resolve({});
  });
}

afterEach(() => {
  mockGet.mockReset();
  mockPost.mockReset();
  mockPatch.mockReset();
});

// ── self-logged label tests ────────────────────────────────────────────────

test("self-logged mock: error patterns section uses 'Self-reported error patterns' heading", async () => {
  primeApi({ item: SELF_LOGGED_ITEM, analysis: SELF_LOGGED_ANALYSIS });
  await act(async () => { render(<Mocks />); });
  await screen.findByTestId("self-reported-banner");

  expect(document.body.textContent).toContain("Self-reported error patterns");
});

test("self-logged mock: subtitle says 'based on the values you entered'", async () => {
  primeApi({ item: SELF_LOGGED_ITEM, analysis: SELF_LOGGED_ANALYSIS });
  await act(async () => { render(<Mocks />); });
  await screen.findByTestId("self-reported-banner");

  expect(document.body.textContent).toContain("based on the values you entered");
});

test("self-logged mock: subtitle does NOT say 'extracted from your logged answer sheet'", async () => {
  primeApi({ item: SELF_LOGGED_ITEM, analysis: SELF_LOGGED_ANALYSIS });
  await act(async () => { render(<Mocks />); });
  await screen.findByTestId("self-reported-banner");

  expect(document.body.textContent).not.toContain("extracted from your logged answer sheet");
});

test("self-logged mock: subtitle does NOT say 'derived from your platform-scored attempt'", async () => {
  primeApi({ item: SELF_LOGGED_ITEM, analysis: SELF_LOGGED_ANALYSIS });
  await act(async () => { render(<Mocks />); });
  await screen.findByTestId("self-reported-banner");

  expect(document.body.textContent).not.toContain("derived from your platform-scored attempt");
});

test("self-logged mock: footer says counts are user-entered, not system-inferred", async () => {
  primeApi({ item: SELF_LOGGED_ITEM, analysis: SELF_LOGGED_ANALYSIS });
  await act(async () => { render(<Mocks />); });
  await screen.findByTestId("self-reported-banner");

  expect(document.body.textContent).toContain("user-entered, not system-inferred");
  expect(document.body.textContent).not.toContain("pattern weighted in next plan");
});

test("self-logged mock: footer does not imply platform inferred guesswork/misread/time-pressure", async () => {
  primeApi({ item: SELF_LOGGED_ITEM, analysis: SELF_LOGGED_ANALYSIS });
  await act(async () => { render(<Mocks />); });
  await screen.findByTestId("self-reported-banner");

  const text = document.body.textContent || "";
  expect(text).not.toMatch(/\d+ wrong answers tagged/);
});

// ── platform-attempt label tests ───────────────────────────────────────────

test("platform-attempt mock: subtitle says 'derived from your platform-scored attempt'", async () => {
  primeApi({ item: PLATFORM_ITEM, analysis: PLATFORM_ANALYSIS });
  await act(async () => { render(<Mocks />); });
  await screen.findByTestId("mock-analysis");

  expect(document.body.textContent).toContain("derived from your platform-scored attempt");
});

test("platform-attempt mock: subtitle does NOT say 'extracted from your logged answer sheet'", async () => {
  primeApi({ item: PLATFORM_ITEM, analysis: PLATFORM_ANALYSIS });
  await act(async () => { render(<Mocks />); });
  await screen.findByTestId("mock-analysis");

  expect(document.body.textContent).not.toContain("extracted from your logged answer sheet");
});

test("platform-attempt mock: error patterns section uses 'Error patterns' heading (no self-reported copy)", async () => {
  primeApi({ item: PLATFORM_ITEM, analysis: PLATFORM_ANALYSIS });
  await act(async () => { render(<Mocks />); });
  await screen.findByTestId("mock-analysis");

  expect(document.body.textContent).not.toContain("Self-reported error patterns");
  expect(document.body.textContent).not.toContain("user-entered, not system-inferred");
});

test("platform-attempt mock: footer uses tagged-answers copy", async () => {
  primeApi({ item: PLATFORM_ITEM, analysis: PLATFORM_ANALYSIS });
  await act(async () => { render(<Mocks />); });
  await screen.findByTestId("mock-analysis");

  expect(document.body.textContent).toContain("pattern weighted in next plan");
});

// ── average stat scoping ──────────────────────────────────────────────────

test("average stat shows 0 logged mocks when list is empty", async () => {
  mockGet.mockReset();
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/mocks") return Promise.resolve({ items: [], trend: [] });
    if (path === "/api/recruitments") return Promise.resolve({ items: [] });
    return Promise.resolve({});
  });
  await act(async () => { render(<Mocks />); });

  expect(document.body.textContent).toContain("Average across 0 logged mocks");
});

test("average stat is labeled 'Average across N logged mocks' (plural)", async () => {
  primeApi({ item: SELF_LOGGED_ITEM, analysis: SELF_LOGGED_ANALYSIS });
  await act(async () => { render(<Mocks />); });

  expect(document.body.textContent).toContain("Average across 1 logged mock");
});

test("average stat uses singular 'mock' for exactly 1 item", async () => {
  primeApi({ item: SELF_LOGGED_ITEM, analysis: SELF_LOGGED_ANALYSIS });
  await act(async () => { render(<Mocks />); });

  const text = document.body.textContent || "";
  expect(text).not.toContain("Average across 1 logged mocks");
  expect(text).toContain("Average across 1 logged mock");
});

test("average stat uses plural 'mocks' for multiple items", async () => {
  const SECOND_ITEM = { ...SELF_LOGGED_ITEM, id: "mock-sl-2", name: "SSC CGL Mock 4" };
  mockGet.mockReset();
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/mocks")
      return Promise.resolve({ items: [SELF_LOGGED_ITEM, SECOND_ITEM], trend: [] });
    if (path === "/api/recruitments") return Promise.resolve({ items: [] });
    return Promise.resolve({});
  });
  await act(async () => { render(<Mocks />); });

  expect(document.body.textContent).toContain("Average across 2 logged mocks");
});

test("average stat label does not say 'Average score'", async () => {
  primeApi({ item: SELF_LOGGED_ITEM, analysis: SELF_LOGGED_ANALYSIS });
  await act(async () => { render(<Mocks />); });

  expect(document.body.textContent).not.toContain("Average score");
});
