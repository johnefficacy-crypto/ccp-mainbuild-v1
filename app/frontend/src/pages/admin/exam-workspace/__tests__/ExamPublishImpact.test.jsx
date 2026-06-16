/**
 * Tests for Wave 4.6D — ExamPublishImpact (read-only console Publish surface).
 *
 * Covers: the four framing sections + mock-impact + evidence drill composed
 * from the correct reads; View 7 via /mock-readiness with no %; excluded rows
 * with reviewer_status/notes + the PYQ papers→questions join; no percentage
 * anywhere; evidence drill; per-section resilience; the negative guards
 * (no recruitment publish_impact, no get_plan_impact); and context reuse
 * (readiness from context is not refetched).
 */
import React from "react";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";

jest.mock("../../../../lib/api", () => ({ __esModule: true, api: { get: jest.fn(), patch: jest.fn() } }));
jest.mock("../../../../lib/supabase", () => ({
  __esModule: true,
  supabase: { auth: { getSession: jest.fn(), onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })) } },
}));
jest.mock("../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: { id: "a1", role: "admin", permissions: [] } }),
}));

// Controlled console context (exam + readiness). ReviewActivatePanel reads the
// same module, so it gets readiness from here too.
let mockCtx;
jest.mock("../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: () => mockCtx,
  ExamWorkspaceProvider: ({ children }) => children,
}));

const { api } = require("../../../../lib/api");
const ExamPublishImpact = require("../ExamPublishImpact").default;

const EXAM = { id: "exam-1", slug: "ssc-cgl", name: "SSC CGL" };
const READINESS = {
  topic_coverage: { total: 10, reviewed: 3, pending: 4, draft: 1, locked: 2, high_yield: 1 },
  sections: [],
  overall: { status: "partial", score_percent: 40, ready_to_activate: false, blockers: [] },
};

const SUMMARY = {
  available: true,
  topics: [{ topic_id: "t1", topic_name: "Percentage", exam_priority_score: 88 }],
  verified_pyq_counts: { t1: 5, t2: 3 },
  verified_syllabus_mentions: 7,
  competition_series: [{ year: 2025 }, { year: 2024 }],
};
const OFFICIAL = { items: [{ id: "u1", title: "Exam date moved", affects_plan: true, affects_deadline: true }] };
const LOCKED_COMP = { items: [{ id: "c1" }] };
const COVERAGE = {
  items: [
    { id: "cov-locked", reviewer_status: "locked", topic_id: "t1" },
    { id: "cov-rev", reviewer_status: "reviewed", topic_id: "t2", review_notes: "needs an admin-reviewed source" },
    { id: "cov-pend", reviewer_status: "pending_review", topic_id: "t3" },
    { id: "cov-rej", reviewer_status: "rejected", topic_id: "t4", reviewer_notes: "off-syllabus" },
  ],
};
const SYLLABUS = {
  items: [
    { id: "s1", reviewer_status: "pending", topic_id: "ts1" },
    { id: "s2", reviewer_status: "verified", topic_id: "ts2" },
  ],
};
const PAPERS = { items: [{ id: "p1", paper_code: "2025-GS-I" }] };
const MOCK = {
  exam_id: "exam-1",
  exam_phase_id: null,
  thresholds: { min_per_section: 30, min_locked_coverage: 1 },
  summary: { ready: 1, thin_bank: 0, blocked: 1 },
  phases: [
    { exam_phase_id: "ph1", phase_name: "Prelims", readiness_verdict: { summary: { ready: 1, thin_bank: 0, blocked: 0 } } },
    { exam_phase_id: "ph2", phase_name: "Mains", readiness_verdict: { summary: { ready: 0, thin_bank: 0, blocked: 1 } } },
  ],
  skipped: [],
};

function routeGet(url, overrides = {}) {
  if (overrides[url] !== undefined) return overrides[url];
  if (url.includes("/api/exam-intelligence/exams/")) return Promise.resolve(SUMMARY);
  if (url.includes("/policy-updates")) return Promise.resolve(OFFICIAL);
  if (url.includes("/competition-metrics")) return Promise.resolve(LOCKED_COMP);
  if (url.includes("/exam-topic-coverage")) return Promise.resolve(COVERAGE);
  if (url.includes("/syllabus-topic-mentions")) return Promise.resolve(SYLLABUS);
  if (url.includes("/pyq-papers")) return Promise.resolve(PAPERS);
  if (url.includes("/pyq-questions")) {
    // q1 surfaces under both pending and needs_correction → must dedupe to one.
    if (url.includes("reviewer_status=pending")) {
      return Promise.resolve({ items: [{ id: "q1", question_number: 5, reviewer_status: "pending" }] });
    }
    if (url.includes("reviewer_status=needs_correction")) {
      return Promise.resolve({ items: [
        { id: "q1", question_number: 5, reviewer_status: "needs_correction" },
        { id: "q2", question_number: 6, reviewer_status: "needs_correction" },
      ] });
    }
    if (url.includes("reviewer_status=rejected")) return Promise.resolve({ items: [] });
    return Promise.resolve({ items: [] });
  }
  if (url.includes("/mock-readiness")) return Promise.resolve(MOCK);
  if (url.includes("/api/evidence/")) return Promise.resolve({ row: { reviewer_status: "rejected", source_url: "https://gov.in/x", confidence_score: 0.86 }, trust: { status: "rejected", confidence_score: 0.86 } });
  return Promise.resolve({});
}

function setApi(router) {
  api.get.mockImplementation((url) => router(url));
}

beforeEach(() => {
  jest.clearAllMocks();
  mockCtx = { exam: EXAM, readiness: READINESS, readiness_loading: false, refetchReadiness: jest.fn(), variant: "console" };
  setApi(routeGet);
});

function renderPanel() {
  return render(<ExamPublishImpact onGotoTab={jest.fn()} />);
}

// ── 1 ──────────────────────────────────────────────────────────────────────
test("renders the four framing sections + mock-impact, composed from the correct reads", async () => {
  renderPanel();
  await waitFor(() => screen.getByTestId("exam-publish-impact"));

  expect(screen.getByTestId("impact-reaches-aspirants")).toBeTruthy();
  expect(screen.getByTestId("impact-planner-consumes")).toBeTruthy();
  expect(screen.getByTestId("impact-excluded")).toBeTruthy();
  expect(screen.getByTestId("impact-mock")).toBeTruthy();
  expect(screen.getByTestId("impact-review-activate")).toBeTruthy();

  const urls = api.get.mock.calls.map((c) => c[0]);
  expect(urls.some((u) => u.startsWith("/api/exam-intelligence/exams/ssc-cgl"))).toBe(true);
  expect(urls.some((u) => u.includes("/exam-topic-coverage?exam_id=exam-1"))).toBe(true);
  expect(urls.some((u) => u.includes("/syllabus-topic-mentions?exam_id=exam-1"))).toBe(true);
  expect(urls.some((u) => u.includes("/pyq-papers?exam_id=exam-1"))).toBe(true);
  expect(urls.some((u) => u.includes("/policy-updates?exam_id=exam-1"))).toBe(true);
  expect(urls.some((u) => u.includes("/exam-intelligence/competition-metrics?exam_id=exam-1") && u.includes("status=locked"))).toBe(true);
  expect(urls.some((u) => u.includes("/exams/exam-1/mock-readiness"))).toBe(true);
});

// ── 2 ──────────────────────────────────────────────────────────────────────
test("View 7 uses /mock-readiness and renders per-phase ready/thin_bank/blocked; no %", async () => {
  renderPanel();
  await waitFor(() => screen.getByTestId("mock-summary"));
  expect(api.get.mock.calls.some((c) => c[0].includes("/mock-readiness"))).toBe(true);

  const phaseRows = screen.getAllByTestId("mock-phase-row");
  expect(phaseRows).toHaveLength(2);
  expect(screen.getAllByTestId("mock-phase-verdict")[0].textContent).toContain("ready 1");
  expect(screen.getByTestId("impact-mock").textContent).not.toContain("%");
});

// ── 3 ──────────────────────────────────────────────────────────────────────
test("excluded section shows reviewed-not-locked + pending/rejected with reasons; PYQ via papers→questions", async () => {
  renderPanel();
  // locked is NOT excluded → 3 of the 4 coverage rows surface here.
  await waitFor(() => expect(screen.getAllByTestId("excluded-coverage-row")).toHaveLength(3));
  expect(screen.getByText(/needs an admin-reviewed source/)).toBeTruthy();
  expect(screen.getByText("off-syllabus")).toBeTruthy();

  // PYQ resolved through the papers→questions join.
  const pyqCalls = api.get.mock.calls.map((c) => c[0]);
  expect(pyqCalls.some((u) => u.includes("/pyq-papers?exam_id=exam-1"))).toBe(true);
  await waitFor(() => expect(screen.getAllByTestId("excluded-pyq-row").length).toBeGreaterThan(0));
  expect(api.get.mock.calls.some((c) => c[0].includes("/pyq-questions?pyq_paper_id=p1"))).toBe(true);
  // syllabus excluded = the non-verified mention only.
  expect(screen.getAllByTestId("excluded-syllabus-row")).toHaveLength(1);
});

// ── 4 ──────────────────────────────────────────────────────────────────────
test("no percentage anywhere; priority renders as a glossary band", async () => {
  renderPanel();
  await waitFor(() => screen.getByTestId("reaches-priority-band"));
  // exam_priority_score 88 → ">80 Critical" band label, not "88%".
  expect(screen.getByTestId("reaches-priority-band").textContent).toMatch(/Critical/);
  expect(screen.getByTestId("exam-publish-impact").textContent).not.toContain("%");
});

// ── 5 ──────────────────────────────────────────────────────────────────────
test("evidence drill calls GET /api/evidence/{kind}/{id}", async () => {
  renderPanel();
  await waitFor(() => screen.getByTestId("evidence-toggle-cov-rev"));
  await act(async () => { fireEvent.click(screen.getByTestId("evidence-toggle-cov-rev")); });
  await waitFor(() =>
    expect(api.get.mock.calls.some((c) => c[0] === "/api/evidence/exam_topic_coverage/cov-rev")).toBe(true),
  );
  expect(screen.getByTestId("evidence-trace-cov-rev")).toBeTruthy();
});

// ── 6 ──────────────────────────────────────────────────────────────────────
test("resilience: one failing read shows that section's error; the rest still render", async () => {
  setApi((url) => {
    if (url.includes("/mock-readiness")) return Promise.reject(new Error("mock read boom"));
    return routeGet(url);
  });
  renderPanel();
  await waitFor(() => screen.getByTestId("mock-error"));
  // The other sections still rendered.
  expect(screen.getByTestId("impact-reaches-aspirants")).toBeTruthy();
  expect(screen.getByTestId("reaches-locked-topics").textContent).toBe("1");
  expect(screen.getByTestId("impact-excluded")).toBeTruthy();
});

// ── 7 ──────────────────────────────────────────────────────────────────────
test("negative guards: never calls recruitment publish_impact or get_plan_impact", async () => {
  renderPanel();
  await waitFor(() => screen.getByTestId("exam-publish-impact"));
  await waitFor(() => screen.getByTestId("mock-summary"));
  const urls = api.get.mock.calls.map((c) => c[0]);
  expect(urls.some((u) => u.includes("/publish-impact"))).toBe(false);
  expect(urls.some((u) => u.includes("/plan-impact"))).toBe(false);
  expect(urls.some((u) => u.includes("/recruitments/"))).toBe(false);
});

// ── 9 ──────────────────────────────────────────────────────────────────────
test("context reuse: readiness from context is not refetched", async () => {
  renderPanel();
  await waitFor(() => screen.getByTestId("excluded-tc-snapshot"));
  // The topic_coverage snapshot comes from context, rendered without a fetch.
  expect(screen.getByTestId("excluded-tc-snapshot").textContent).toContain("reviewed 3");
  const urls = api.get.mock.calls.map((c) => c[0]);
  expect(urls.some((u) => u.includes("/workspace/") && u.includes("/readiness"))).toBe(false);
});

// ── 4.6D.1 Fix 1 ────────────────────────────────────────────────────────────
test("locked competition reads EI /competition-metrics?status=locked, not the CMS path", async () => {
  renderPanel();
  await waitFor(() => screen.getByTestId("exam-publish-impact"));
  const urls = api.get.mock.calls.map((c) => c[0]);
  expect(urls.some((u) =>
    u.includes("/api/admin/exam-intelligence/competition-metrics?exam_id=exam-1") && u.includes("status=locked"),
  )).toBe(true);
  // The flag-gated CMS write-surface endpoint must NOT be used for this read.
  expect(urls.some((u) => u.includes("/exam-competition-metrics"))).toBe(false);
});

// ── 4.6D.1 Fix 2 ────────────────────────────────────────────────────────────
test("excluded PYQ fetches pending + needs_correction + rejected and dedupes by id", async () => {
  renderPanel();
  await waitFor(() => expect(screen.getAllByTestId("excluded-pyq-row").length).toBeGreaterThan(0));
  const urls = api.get.mock.calls.map((c) => c[0]);
  ["pending", "needs_correction", "rejected"].forEach((st) => {
    expect(urls.some((u) => u.includes("/pyq-questions?pyq_paper_id=p1") && u.includes(`reviewer_status=${st}`))).toBe(true);
  });
  // q1 surfaced under both pending and needs_correction → appears once; q2 once.
  expect(screen.getAllByTestId("excluded-pyq-row")).toHaveLength(2);
});

// ── 4.6D.1 Fix 3 ────────────────────────────────────────────────────────────
test("no % regression; evidence trace does not mount the shared ExamEvidenceDrawer", async () => {
  renderPanel();
  await waitFor(() => screen.getByTestId("evidence-toggle-cov-rev"));
  // Open the evidence trace (drill returns a row carrying a confidence_score).
  await act(async () => { fireEvent.click(screen.getByTestId("evidence-toggle-cov-rev")); });
  await waitFor(() => screen.getByTestId("evidence-trace-cov-rev"));
  // The shared drawer (which renders a ConfidencePill %) is never mounted.
  expect(screen.queryByTestId("exam-evidence-drawer-cov-rev")).toBeNull();
  expect(screen.getByTestId("exam-publish-impact").textContent).not.toContain("%");
});
