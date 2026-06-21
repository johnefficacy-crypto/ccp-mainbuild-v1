/**
 * OverviewPanel — UX-EI-3 (D1) regression tests.
 *
 * Asserts that:
 * 1. Duplicate exam identity fields (name, slug, type, family) are absent —
 *    they already live in SmartHeader and must not be duplicated here.
 * 2. Non-duplicate config fields (cadence, management_mode, is_active) are present.
 * 3. The readiness sections summary is still rendered (must NOT be removed).
 */
import React from "react";
import { render, screen } from "@testing-library/react";

jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: jest.fn(),
}));

const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const OverviewPanel = require("../OverviewPanel").default;

const BASE_EXAM = {
  id: "exam-uuid-1",
  name: "UPSC CSE",
  slug: "upsc-cse",
  exam_type: "civil_services",
  family: "UPSC",
  family_name: "UPSC",
  is_active: true,
  cadence: "annual",
  management_mode: "central",
};

const READINESS = {
  overall: { score_percent: 60, status: "partial" },
  sections: [
    {
      section: "setup",
      label: "Setup",
      status: "ready",
      weight: 1,
      blockers: [],
      note: "1 phase defined",
    },
    {
      section: "syllabus_mapper",
      label: "Syllabus Mapper",
      status: "partial",
      weight: 2,
      blockers: ["no topic-coverage rows"],
      note: "",
    },
  ],
};

function setup({ exam = BASE_EXAM, readiness = READINESS } = {}) {
  useExamWorkspace.mockReturnValue({ exam, readiness });
  return render(<OverviewPanel />);
}

// ── D1: Duplicate identity fields must be absent ──────────────────────────────

describe("OverviewPanel — UX-EI-3: no duplicate SmartHeader fields", () => {
  test("does NOT render exam name as a labelled field value", () => {
    setup();
    // SmartHeader renders the name; OverviewPanel must not also show it as a field.
    // We look for a <div class="field-val"> that contains the exact exam name.
    const vals = document.querySelectorAll(".field-val");
    const nameVals = Array.from(vals).filter(el => el.textContent.trim() === "UPSC CSE");
    expect(nameVals).toHaveLength(0);
  });

  test("does NOT render slug as a labelled field value", () => {
    setup();
    const vals = document.querySelectorAll(".field-val");
    const slugVals = Array.from(vals).filter(el => el.textContent.trim() === "upsc-cse");
    expect(slugVals).toHaveLength(0);
  });

  test("does NOT render exam type as a labelled field value", () => {
    setup();
    const vals = document.querySelectorAll(".field-val");
    const typeVals = Array.from(vals).filter(el =>
      el.textContent.trim() === "civil_services"
    );
    expect(typeVals).toHaveLength(0);
  });

  test("does NOT render family name as a labelled field value", () => {
    setup();
    const vals = document.querySelectorAll(".field-val");
    const familyVals = Array.from(vals).filter(el => el.textContent.trim() === "UPSC");
    expect(familyVals).toHaveLength(0);
  });
});

// ── Non-duplicate fields must be present ──────────────────────────────────────

describe("OverviewPanel — non-duplicate fields are shown", () => {
  test("shows cadence field", () => {
    setup();
    expect(screen.getByTestId("overview-cadence").textContent).toBe("annual");
  });

  test("shows management_mode field", () => {
    setup();
    expect(screen.getByTestId("overview-management-mode").textContent).toBe("central");
  });

  test("shows is_active as Yes/No", () => {
    setup();
    expect(screen.getByTestId("overview-is-active").textContent).toBe("Yes");
  });

  test("shows is_active=false as No", () => {
    setup({ exam: { ...BASE_EXAM, is_active: false } });
    expect(screen.getByTestId("overview-is-active").textContent).toBe("No");
  });

  test("shows — for null cadence", () => {
    setup({ exam: { ...BASE_EXAM, cadence: null } });
    expect(screen.getByTestId("overview-cadence").textContent).toBe("—");
  });
});

// ── Readiness sections must still be present ──────────────────────────────────

describe("OverviewPanel — readiness sections are NOT removed", () => {
  test("renders the readiness summary card", () => {
    setup();
    expect(screen.getByTestId("overview-readiness-card")).toBeTruthy();
  });

  test("renders per-section rows for each readiness section", () => {
    setup();
    expect(screen.getByTestId("overview-section-setup")).toBeTruthy();
    expect(screen.getByTestId("overview-section-syllabus_mapper")).toBeTruthy();
  });

  test("shows section labels in the readiness summary", () => {
    setup();
    expect(screen.getByText("Setup")).toBeTruthy();
    expect(screen.getByText("Syllabus Mapper")).toBeTruthy();
  });

  test("shows blocker text for a blocked section", () => {
    setup();
    expect(screen.getByText(/no topic-coverage rows/i)).toBeTruthy();
  });

  test("renders readiness data-testid container", () => {
    setup();
    expect(screen.getByTestId("overview-readiness-sections")).toBeTruthy();
  });
});
