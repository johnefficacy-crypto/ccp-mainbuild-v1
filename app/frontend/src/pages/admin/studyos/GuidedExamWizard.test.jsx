import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  getApiErrorMessage: (e) => String(e?.message || e),
}));

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => jest.fn(),
}));

const { api } = require("../../../lib/api");
const GuidedExamWizard = require("./GuidedExamWizard").default;

const ORG_LIST = [
  { id: "org-aaa", name: "UPSC", short_name: "UPSC", type: "central", state: "" },
  { id: "org-bbb", name: "SSC", short_name: "SSC", type: "central", state: "" },
];

function setup() {
  return render(
    <MemoryRouter>
      <GuidedExamWizard />
    </MemoryRouter>
  );
}

beforeEach(() => {
  api.get.mockResolvedValue({ items: ORG_LIST });
  api.post.mockResolvedValue({ id: "org-new-1", row: { id: "exam-xxx" } });
});

// ── Slug utilities ────────────────────────────────────────────────────────────

const { slugify, cycleBoundSlug } = require("../../../lib/slugify");

describe("slugify util", () => {
  test("lowercases and replaces non-alphanumeric runs with hyphen", () => {
    expect(slugify("UPSC CSE")).toBe("upsc-cse");
    expect(slugify("  prelims 2025  ")).toBe("prelims-2025");
    expect(slugify("abc--def")).toBe("abc-def");
  });

  test("strips leading/trailing hyphens", () => {
    expect(slugify("-hello-")).toBe("hello");
  });
});

describe("cycleBoundSlug util", () => {
  test("suffixes base with year", () => {
    expect(cycleBoundSlug("prelims", "2025", "cycle name")).toBe("prelims-2025");
  });

  test("falls back to cycle_name when year is blank", () => {
    expect(cycleBoundSlug("prelims", "", "2026 cycle")).toBe("prelims-2026-cycle");
  });

  test("never emits bare-slug for cycle-bound (always has suffix)", () => {
    const result = cycleBoundSlug("prelims", "2025", "");
    expect(result).toMatch(/prelims-\d+/);
  });
});

// ── Step navigation ───────────────────────────────────────────────────────────

describe("step navigation", () => {
  test("renders Step 1 (org) initially", () => {
    setup();
    expect(screen.getByTestId("wizard-step-org")).toBeInTheDocument();
  });

  test("1→2: Next enabled after selecting org, advances to exam step", async () => {
    setup();
    await waitFor(() => expect(screen.getByTestId("org-list")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    expect(screen.getByTestId("wizard-next-1")).not.toBeDisabled();
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    expect(screen.getByTestId("wizard-step-exam")).toBeInTheDocument();
  });

  test("2→3: advances to cycle step after entering exam name", async () => {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "UPSC CSE" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    expect(screen.getByTestId("wizard-step-cycle")).toBeInTheDocument();
  });

  test("3→4: advances to phases step with name+year filled", async () => {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "UPSC CSE" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "CSE 2025" } });
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
    fireEvent.click(screen.getByTestId("wizard-next-3"));
    expect(screen.getByTestId("wizard-step-phases")).toBeInTheDocument();
  });

  test("4→5: advances to review step", async () => {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "UPSC CSE" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "CSE 2025" } });
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
    fireEvent.click(screen.getByTestId("wizard-next-3"));
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    expect(screen.getByTestId("wizard-step-review")).toBeInTheDocument();
  });

  test("Back button returns to previous step", async () => {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    expect(screen.getByTestId("wizard-step-exam")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("wizard-back-1"));
    expect(screen.getByTestId("wizard-step-org")).toBeInTheDocument();
  });
});

// ── Draft state retained across steps ────────────────────────────────────────

describe("draft state retained across steps", () => {
  test("exam name persists when navigating back and forward", async () => {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "My Exam" } });
    fireEvent.click(screen.getByTestId("wizard-back-1"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    expect(screen.getByTestId("exam-name")).toHaveValue("My Exam");
  });
});

// ── Nothing POSTs before Step 5 ───────────────────────────────────────────────

describe("no network calls before step 5", () => {
  test("navigating steps 1-4 fires no POST", async () => {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "UPSC CSE" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "CSE 2025" } });
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
    fireEvent.click(screen.getByTestId("wizard-next-3"));
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    expect(screen.getByTestId("wizard-step-review")).toBeInTheDocument();
    // No POST until "Create all" clicked
    expect(api.post).not.toHaveBeenCalled();
  });
});

// ── Step 1 org modes ──────────────────────────────────────────────────────────

describe("Step 1: org select-existing path", () => {
  test("shows org list, clicking org sets selected id", async () => {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    expect(screen.getByTestId("org-selected-id")).toHaveTextContent("org-aaa");
  });
});

describe("Step 1: inline-create path", () => {
  test("creates org, shows created id, shows warnings non-blocking", async () => {
    api.post.mockResolvedValueOnce({
      id: "org-new-99",
      warnings: [{ existing_name: "UPSC Old", existing_id: "org-old-1" }],
    });
    setup();
    fireEvent.click(screen.getByTestId("org-mode-create"));
    fireEvent.change(screen.getByTestId("org-name"), { target: { value: "New UPSC" } });
    fireEvent.change(screen.getByTestId("org-short-name"), { target: { value: "NUPSC" } });
    fireEvent.change(screen.getByTestId("org-type"), { target: { value: "central" } });
    await act(async () => { fireEvent.click(screen.getByTestId("org-create-submit")); });
    await waitFor(() => expect(screen.getByTestId("org-created-id")).toHaveTextContent("org-new-99"));
    // Warnings shown but wizard not blocked — Next button still enabled
    expect(screen.getByTestId("org-warnings")).toBeInTheDocument();
    expect(screen.getByTestId("wizard-next-1")).not.toBeDisabled();
  });

  test("duplicate-block error is surfaced", async () => {
    api.post.mockRejectedValueOnce({ message: "duplicate org name" });
    setup();
    fireEvent.click(screen.getByTestId("org-mode-create"));
    fireEvent.change(screen.getByTestId("org-name"), { target: { value: "UPSC" } });
    fireEvent.change(screen.getByTestId("org-short-name"), { target: { value: "UPSC" } });
    fireEvent.change(screen.getByTestId("org-type"), { target: { value: "central" } });
    await act(async () => { fireEvent.click(screen.getByTestId("org-create-submit")); });
    await waitFor(() => expect(screen.getByTestId("org-error")).toHaveTextContent("duplicate org name"));
  });
});

// ── Step 2: exam fields ───────────────────────────────────────────────────────

describe("Step 2: exam fields", () => {
  async function goToExamStep() {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
  }

  test("conducting org id is bound (read-only field shows org id)", async () => {
    await goToExamStep();
    expect(screen.getByTestId("exam-org-id")).toHaveValue("org-aaa");
  });

  test("management_mode defaults to 'light'; null/blank coerced on advance", async () => {
    await goToExamStep();
    expect(screen.getByTestId("exam-management-mode")).toHaveValue("light");
    // Clear to blank and advance — should coerce to 'light'
    fireEvent.change(screen.getByTestId("exam-management-mode"), { target: { value: "" } });
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "Test Exam" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    // After coercion, going back shows 'light'
    fireEvent.click(screen.getByTestId("wizard-back-2"));
    expect(screen.getByTestId("exam-management-mode")).toHaveValue("light");
  });

  test("cadence defaults to 'unknown'; blank coerced on advance", async () => {
    await goToExamStep();
    expect(screen.getByTestId("exam-cadence")).toHaveValue("unknown");
  });
});

// ── Step 3: cycle ─────────────────────────────────────────────────────────────

describe("Step 3: cycle", () => {
  async function goToCycleStep() {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "UPSC CSE" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
  }

  test("year is required — Next disabled until year provided", async () => {
    await goToCycleStep();
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "CSE 2025" } });
    expect(screen.getByTestId("wizard-next-3")).toBeDisabled();
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
    expect(screen.getByTestId("wizard-next-3")).not.toBeDisabled();
  });
});

// ── Step 4: phases ────────────────────────────────────────────────────────────

describe("Step 4: phases", () => {
  async function goToPhaseStep(cycleYear = "2025", cycleName = "CSE 2025") {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "UPSC CSE" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: cycleName } });
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: cycleYear } });
    fireEvent.click(screen.getByTestId("wizard-next-3"));
  }

  test("adds a phase row and shows cb-slug preview = slugify(base+year)", async () => {
    await goToPhaseStep("2025", "CSE 2025");
    fireEvent.click(screen.getByTestId("add-phase"));
    const rows = screen.getAllByTestId(/^phase-row-/);
    expect(rows).toHaveLength(1);
    const rowId = rows[0].getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-base-slug-${rowId}`), { target: { value: "prelims" } });
    await waitFor(() => {
      const preview = screen.getByTestId(`phase-cb-slug-preview-${rowId}`);
      expect(preview).toHaveTextContent("prelims-2025");
    });
  });

  test("toggle ON 'also template' emits bare slug template (cycle=null)", async () => {
    await goToPhaseStep("2025", "CSE 2025");
    fireEvent.click(screen.getByTestId("add-phase"));
    const rowId = screen.getAllByTestId(/^phase-row-/)[0]
      .getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-base-slug-${rowId}`), { target: { value: "prelims" } });
    fireEvent.change(screen.getByTestId(`phase-name-${rowId}`), { target: { value: "Prelims" } });
    // Check the template toggle checkbox
    const toggle = screen.getByTestId(`phase-template-toggle-${rowId}`).querySelector("input");
    fireEvent.click(toggle);
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    // Review should show template phases section with bare slug
    await waitFor(() => {
      expect(screen.getByTestId("review-template-phases")).toHaveTextContent("prelims");
    });
    // And cycle-bound slug for cb row (not bare)
    expect(screen.getByTestId("review-cb-phases")).toHaveTextContent("prelims-2025");
  });

  test("wizard never emits bare-slug cycle-bound phase (cb slug always has suffix)", async () => {
    await goToPhaseStep("2025", "CSE 2025");
    fireEvent.click(screen.getByTestId("add-phase"));
    const rowId = screen.getAllByTestId(/^phase-row-/)[0]
      .getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-base-slug-${rowId}`), { target: { value: "prelims" } });
    fireEvent.change(screen.getByTestId(`phase-name-${rowId}`), { target: { value: "Prelims" } });
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    const cbSection = screen.getByTestId("review-cb-phases");
    // cb slug must not be bare "prelims" — must be "prelims-2025"
    expect(cbSection).not.toHaveTextContent(/slug: prelims(?!-)/);
    expect(cbSection).toHaveTextContent("prelims-2025");
  });
});

// ── Step 5: create sequence ───────────────────────────────────────────────────

async function fillAndGoToReview({ withPhase = false, cycleName = "CSE 2025", year = "2025" } = {}) {
  await waitFor(() => screen.getByTestId("org-list"));
  fireEvent.click(screen.getByTestId("org-select-org-aaa"));
  fireEvent.click(screen.getByTestId("wizard-next-1"));
  fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "UPSC CSE" } });
  fireEvent.click(screen.getByTestId("wizard-next-2"));
  fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: cycleName } });
  fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: year } });
  fireEvent.click(screen.getByTestId("wizard-next-3"));
  if (withPhase) {
    fireEvent.click(screen.getByTestId("add-phase"));
    const rowId = screen.getAllByTestId(/^phase-row-/)[0]
      .getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-name-${rowId}`), { target: { value: "Prelims" } });
    fireEvent.change(screen.getByTestId(`phase-base-slug-${rowId}`), { target: { value: "prelims" } });
  }
  fireEvent.click(screen.getByTestId("wizard-next-4"));
}

describe("Step 5: sequential create POSTs", () => {
  test("fires exam → cycle POSTs in order (existing org skips org POST)", async () => {
    api.post
      .mockResolvedValueOnce({ row: { id: "exam-created" } })   // exam
      .mockResolvedValueOnce({ row: { id: "cycle-created" } }); // cycle
    setup();
    await fillAndGoToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());
    const calls = api.post.mock.calls;
    expect(calls[0][0]).toMatch(/\/exams$/);
    expect(calls[1][0]).toMatch(/\/exam-cycles$/);
    // No org POST (select mode)
    expect(calls.every((c) => !c[0].includes("/organizations"))).toBe(true);
  });

  test("phases posted after cycle — cb phase has exam_cycle_id set", async () => {
    api.post
      .mockResolvedValueOnce({ row: { id: "exam-111" } })
      .mockResolvedValueOnce({ row: { id: "cycle-222" } })
      .mockResolvedValueOnce({ row: { id: "phase-333" } });
    setup();
    await fillAndGoToReview({ withPhase: true });
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());
    const phasePosts = api.post.mock.calls.filter((c) => c[0].includes("/exam-phases"));
    expect(phasePosts).toHaveLength(1);
    expect(phasePosts[0][1].payload.exam_cycle_id).toBe("cycle-222");
    expect(phasePosts[0][1].payload.phase_slug).toBe("prelims-2025");
  });

  test("mid-failure keeps created IDs; resume re-posts only remainder", async () => {
    api.post
      .mockResolvedValueOnce({ row: { id: "exam-111" } })    // exam ok
      .mockRejectedValueOnce({ message: "cycle server error" }); // cycle fails
    setup();
    await fillAndGoToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("wizard-create")).toHaveTextContent("Resume creation"));

    // Now fix: next call succeeds
    api.post.mockResolvedValueOnce({ row: { id: "cycle-222" } });
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());

    // Exam was NOT posted again on resume
    const examCalls = api.post.mock.calls.filter((c) => c[0].includes("/exams"));
    expect(examCalls).toHaveLength(1);
  });

  test("review labels distinguish template vs cycle-bound groups", async () => {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "Test Exam" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "Test Cycle" } });
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
    fireEvent.click(screen.getByTestId("wizard-next-3"));
    fireEvent.click(screen.getByTestId("add-phase"));
    const rowId = screen.getAllByTestId(/^phase-row-/)[0]
      .getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-name-${rowId}`), { target: { value: "Prelims" } });
    fireEvent.change(screen.getByTestId(`phase-base-slug-${rowId}`), { target: { value: "prelims" } });
    const toggle = screen.getByTestId(`phase-template-toggle-${rowId}`).querySelector("input");
    fireEvent.click(toggle);
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    expect(screen.getByTestId("review-template-phases")).toBeInTheDocument();
    expect(screen.getByTestId("review-cb-phases")).toBeInTheDocument();
  });
});
