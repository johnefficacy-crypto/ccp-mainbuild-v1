import React from "react";
import { render, screen } from "@testing-library/react";

// Mock ExamWorkspaceContext so we don't need the full provider fetch chain
jest.mock("../../ExamWorkspaceContext", () => ({
  useExamWorkspace: jest.fn(),
}));

// Mock ExamIntelGlossary to avoid CSS-in-JS / pill class issues in jsdom
jest.mock("../../../../../features/admin/exam-intelligence/ExamIntelGlossary", () => ({
  LifecycleLegend: () => null,
  EXAM_PURPOSE_LABELS: { recruitment: { label: "Recruitment exam" } },
  BUSINESS_PRIORITY_LABELS: { core: { label: "Core" } },
}));

const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const OverviewPanel = require("../OverviewPanel").default;

const BASE_EXAM = {
  id: "exam-1",
  name: "SSC CGL",
  slug: "ssc-cgl",
  exam_type: "recruitment",
  management_mode: "core",
  cadence: "annual",
  is_active: true,
};

const BASE_READINESS = {
  overall: { status: "partial", score_percent: 42, ready_to_activate: false },
  sections: [
    { section: "setup", label: "Setup", status: "ready", score_percent: 100, weight: 2, blockers: [], counts: {}, metrics: { phase_count: 1 } },
    { section: "documents", label: "Documents", status: "partial", score_percent: 50, weight: 1, blockers: [], counts: {}, metrics: { total: 2, extracted: 1, pending: 1, failed: 0 } },
    { section: "syllabus_mapper", label: "Syllabus Mapper", status: "partial", score_percent: 50, weight: 2, blockers: [], counts: {}, metrics: {} },
    { section: "pyq_workbench", label: "PYQ Workbench", status: "ready", score_percent: 100, weight: 3, blockers: [], counts: {}, metrics: { papers: 2, questions_total: 40, questions_verified: 40, questions_locked: 20, options_total: 160, topic_tags_total: 80 } },
    { section: "updates", label: "Updates", status: "empty", score_percent: 0, weight: 1, blockers: [], counts: {}, metrics: { total: 0, pending: 0, verified: 0, stale: 0, rejected: 0 } },
    { section: "competition", label: "Competition", status: "empty", score_percent: 0, weight: 1, blockers: [], counts: {}, metrics: { present_for_cycle: false, reviewer_status: null, breakdown: { draft: 0, reviewed: 0, locked: 0 } } },
    { section: "review_activate", label: "Review & Activate", status: "partial", score_percent: 0, weight: 0, blockers: [], counts: {}, metrics: {} },
  ],
  topic_coverage: { total: 10, draft: 2, pending: 1, reviewed: 3, locked: 4, high_yield: 2 },
};

function setup(overrides = {}) {
  useExamWorkspace.mockReturnValue({
    exam: BASE_EXAM,
    cycle: null,
    cycles: [],
    phases: [{ id: "ph-1" }],
    readiness: BASE_READINESS,
    organization: null,
    family: null,
    ...overrides,
  });
  return render(<OverviewPanel />);
}

describe("OverviewPanel", () => {
  afterEach(() => jest.clearAllMocks());

  test("renders overview-panel root", () => {
    setup();
    expect(screen.getByTestId("overview-panel")).toBeTruthy();
  });

  test("org shows — when organization is null", () => {
    setup({ organization: null });
    expect(screen.getByTestId("overview-org").textContent).toBe("—");
  });

  test("org shows name when organization provided", () => {
    setup({ organization: { id: "org-1", name: "UPSC Board", type: "central", trust_tier: "verified" } });
    expect(screen.getByTestId("overview-org").textContent).toBe("UPSC Board");
  });

  test("org falls back to exam.organization_name when organization is null", () => {
    setup({
      exam: { ...BASE_EXAM, organization_name: "Fallback Org" },
      organization: null,
    });
    expect(screen.getByTestId("overview-org").textContent).toBe("Fallback Org");
  });

  test("family shows — when family is null", () => {
    setup({ family: null });
    expect(screen.getByTestId("overview-family").textContent).toBe("—");
  });

  test("family shows name when family provided", () => {
    setup({ family: { id: "fam-1", name: "Civil Services" } });
    expect(screen.getByTestId("overview-family").textContent).toBe("Civil Services");
  });

  test("family falls back to exam.family_name when family is null", () => {
    setup({
      exam: { ...BASE_EXAM, family_name: "Fallback Family" },
      family: null,
    });
    expect(screen.getByTestId("overview-family").textContent).toBe("Fallback Family");
  });

  test("topic coverage section renders total count", () => {
    setup();
    expect(screen.getByTestId("overview-section-topic-coverage")).toBeTruthy();
    expect(screen.getByTestId("overview-section-topic-coverage").textContent).toContain("10");
  });

  test("pyq workbench section renders options_total and topic_tags_total", () => {
    setup();
    const pyqSection = screen.getByTestId("overview-section-pyq");
    expect(pyqSection.textContent).toContain("160"); // options_total
    expect(pyqSection.textContent).toContain("80");  // topic_tags_total
  });
});
