import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  getApiErrorMessage: (e) => String(e?.message || e),
}));

const mockNavigate = jest.fn();

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
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
  mockNavigate.mockClear();
  api.get.mockResolvedValue({ items: ORG_LIST });
  // default happy-path: org create → exam → cycle
  api.post
    .mockResolvedValueOnce({ id: "org-new-1" })             // org
    .mockResolvedValueOnce({ row: { id: "exam-xxx" } })     // exam
    .mockResolvedValueOnce({ row: { id: "cycle-yyy" } });   // cycle
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
    expect(cycleBoundSlug("prelims", "2025", "")).toMatch(/prelims-\d+/);
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

  test("1→2 create mode: Next enabled after name+short_name+type filled", () => {
    setup();
    fireEvent.click(screen.getByTestId("org-mode-create"));
    expect(screen.getByTestId("wizard-next-1")).toBeDisabled();
    fireEvent.change(screen.getByTestId("org-name"), { target: { value: "New Org" } });
    fireEvent.change(screen.getByTestId("org-short-name"), { target: { value: "NO" } });
    fireEvent.change(screen.getByTestId("org-type"), { target: { value: "central" } });
    expect(screen.getByTestId("wizard-next-1")).not.toBeDisabled();
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
  test("create-mode: navigating steps 1–4 fires zero api.post calls", () => {
    setup();
    fireEvent.click(screen.getByTestId("org-mode-create"));
    fireEvent.change(screen.getByTestId("org-name"), { target: { value: "New Org" } });
    fireEvent.change(screen.getByTestId("org-short-name"), { target: { value: "NO" } });
    fireEvent.change(screen.getByTestId("org-type"), { target: { value: "central" } });
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "Test Exam" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "Cycle 2025" } });
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
    fireEvent.click(screen.getByTestId("wizard-next-3"));
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    expect(screen.getByTestId("wizard-step-review")).toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
  });

  test("select-mode: navigating steps 1–4 fires zero api.post calls", async () => {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "Test Exam" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "Cycle 2025" } });
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
    fireEvent.click(screen.getByTestId("wizard-next-3"));
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    expect(screen.getByTestId("wizard-step-review")).toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
  });
});

// ── Step 1 org select mode ────────────────────────────────────────────────────

describe("Step 1: org select-existing path", () => {
  test("shows org list, clicking org sets selected id", async () => {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    expect(screen.getByTestId("org-selected-id")).toHaveTextContent("org-aaa");
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
    fireEvent.change(screen.getByTestId("exam-management-mode"), { target: { value: "" } });
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "Test Exam" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.click(screen.getByTestId("wizard-back-2"));
    expect(screen.getByTestId("exam-management-mode")).toHaveValue("light");
  });

  test("cadence defaults to 'unknown'", async () => {
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

  test("date inputs have type=date", async () => {
    await goToCycleStep();
    expect(screen.getByTestId("cycle-notification_date")).toHaveAttribute("type", "date");
    expect(screen.getByTestId("cycle-exam_start")).toHaveAttribute("type", "date");
  });
});

// ── Step 4: phases ────────────────────────────────────────────────────────────

describe("Step 4: phases", () => {
  async function goToPhaseStep(cycleName = "CSE 2025", year = "2025") {
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "UPSC CSE" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: cycleName } });
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: year } });
    fireEvent.click(screen.getByTestId("wizard-next-3"));
  }

  test("zero phases: Next (Review) enabled immediately", async () => {
    await goToPhaseStep();
    expect(screen.getByTestId("wizard-next-4")).not.toBeDisabled();
  });

  test("blank phase_name blocks Next", async () => {
    await goToPhaseStep();
    fireEvent.click(screen.getByTestId("add-phase"));
    // Name is empty — Next should be disabled
    expect(screen.getByTestId("wizard-next-4")).toBeDisabled();
    expect(screen.getByTestId("phase-errors")).toBeInTheDocument();
  });

  test("base_slug auto-derives from phase_name when left blank", async () => {
    await goToPhaseStep();
    fireEvent.click(screen.getByTestId("add-phase"));
    const rowId = screen.getAllByTestId(/^phase-row-/)[0]
      .getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-name-${rowId}`), { target: { value: "Prelims" } });
    // base_slug input is empty — placeholder shows derived slug
    expect(screen.getByTestId(`phase-base-slug-${rowId}`)).toHaveAttribute("placeholder", "prelims");
    // cb-slug preview uses derived slug
    await waitFor(() => {
      expect(screen.getByTestId(`phase-cb-slug-preview-${rowId}`)).toHaveTextContent("prelims-2025");
    });
    // Next should now be enabled
    expect(screen.getByTestId("wizard-next-4")).not.toBeDisabled();
  });

  test("duplicate base_slug across rows blocks Next and shows error", async () => {
    await goToPhaseStep();
    fireEvent.click(screen.getByTestId("add-phase"));
    fireEvent.click(screen.getByTestId("add-phase"));
    const rows = screen.getAllByTestId(/^phase-row-/);
    const id1 = rows[0].getAttribute("data-testid").replace("phase-row-", "");
    const id2 = rows[1].getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-name-${id1}`), { target: { value: "Prelims" } });
    fireEvent.change(screen.getByTestId(`phase-name-${id2}`), { target: { value: "Prelims" } });
    expect(screen.getByTestId("wizard-next-4")).toBeDisabled();
    expect(screen.getByTestId("phase-errors")).toHaveTextContent("Duplicate base slug");
  });

  test("unique slugs unblock Next", async () => {
    await goToPhaseStep();
    fireEvent.click(screen.getByTestId("add-phase"));
    fireEvent.click(screen.getByTestId("add-phase"));
    const rows = screen.getAllByTestId(/^phase-row-/);
    const id1 = rows[0].getAttribute("data-testid").replace("phase-row-", "");
    const id2 = rows[1].getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-name-${id1}`), { target: { value: "Prelims" } });
    fireEvent.change(screen.getByTestId(`phase-name-${id2}`), { target: { value: "Mains" } });
    expect(screen.getByTestId("wizard-next-4")).not.toBeDisabled();
  });

  test("cb-slug preview = slugify(base+year)", async () => {
    await goToPhaseStep("CSE 2025", "2025");
    fireEvent.click(screen.getByTestId("add-phase"));
    const rowId = screen.getAllByTestId(/^phase-row-/)[0]
      .getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-name-${rowId}`), { target: { value: "Prelims" } });
    fireEvent.change(screen.getByTestId(`phase-base-slug-${rowId}`), { target: { value: "prelims" } });
    await waitFor(() => {
      expect(screen.getByTestId(`phase-cb-slug-preview-${rowId}`)).toHaveTextContent("prelims-2025");
    });
  });

  test("toggle ON 'also template' emits bare slug template (cycle=null)", async () => {
    await goToPhaseStep();
    fireEvent.click(screen.getByTestId("add-phase"));
    const rowId = screen.getAllByTestId(/^phase-row-/)[0]
      .getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-name-${rowId}`), { target: { value: "Prelims" } });
    const toggle = screen.getByTestId(`phase-template-toggle-${rowId}`).querySelector("input");
    fireEvent.click(toggle);
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    await waitFor(() => {
      expect(screen.getByTestId("review-template-phases")).toHaveTextContent("prelims");
    });
    expect(screen.getByTestId("review-cb-phases")).toHaveTextContent("prelims-2025");
  });

  test("wizard never emits bare-slug cycle-bound phase", async () => {
    await goToPhaseStep();
    fireEvent.click(screen.getByTestId("add-phase"));
    const rowId = screen.getAllByTestId(/^phase-row-/)[0]
      .getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-name-${rowId}`), { target: { value: "Prelims" } });
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    const cbSection = screen.getByTestId("review-cb-phases");
    expect(cbSection).not.toHaveTextContent(/slug: prelims(?!-)/);
    expect(cbSection).toHaveTextContent("prelims-2025");
  });
});

// ── Step 5: sequential create POSTs ──────────────────────────────────────────

async function fillSelectAndGoToReview({ withPhase = false } = {}) {
  await waitFor(() => screen.getByTestId("org-list"));
  fireEvent.click(screen.getByTestId("org-select-org-aaa"));
  fireEvent.click(screen.getByTestId("wizard-next-1"));
  fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "UPSC CSE" } });
  fireEvent.click(screen.getByTestId("wizard-next-2"));
  fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "CSE 2025" } });
  fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
  fireEvent.click(screen.getByTestId("wizard-next-3"));
  if (withPhase) {
    fireEvent.click(screen.getByTestId("add-phase"));
    const rowId = screen.getAllByTestId(/^phase-row-/)[0]
      .getAttribute("data-testid").replace("phase-row-", "");
    fireEvent.change(screen.getByTestId(`phase-name-${rowId}`), { target: { value: "Prelims" } });
  }
  fireEvent.click(screen.getByTestId("wizard-next-4"));
}

async function fillCreateAndGoToReview() {
  fireEvent.click(screen.getByTestId("org-mode-create"));
  fireEvent.change(screen.getByTestId("org-name"), { target: { value: "New Org" } });
  fireEvent.change(screen.getByTestId("org-short-name"), { target: { value: "NO" } });
  fireEvent.change(screen.getByTestId("org-type"), { target: { value: "central" } });
  fireEvent.click(screen.getByTestId("wizard-next-1"));
  fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "Test Exam" } });
  fireEvent.click(screen.getByTestId("wizard-next-2"));
  fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "Cycle 2025" } });
  fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
  fireEvent.click(screen.getByTestId("wizard-next-3"));
  fireEvent.click(screen.getByTestId("wizard-next-4"));
}

describe("Step 5: create mode — org POSTed first", () => {
  test("posts org → exam → cycle in order; exam uses org id from POST", async () => {
    api.post
      .mockReset()
      .mockResolvedValueOnce({ id: "org-created-111" })          // org
      .mockResolvedValueOnce({ row: { id: "exam-222" } })        // exam
      .mockResolvedValueOnce({ row: { id: "cycle-333" } });      // cycle
    setup();
    await fillCreateAndGoToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());
    const calls = api.post.mock.calls;
    expect(calls[0][0]).toContain("/organizations");
    expect(calls[1][0]).toContain("/exams");
    expect(calls[2][0]).toContain("/exam-cycles");
    // Exam payload uses the org id from the org POST
    expect(calls[1][1].payload.conducting_organization_id).toBe("org-created-111");
  });

  test("no duplicate org POST on resume after exam failure", async () => {
    api.post
      .mockReset()
      .mockResolvedValueOnce({ id: "org-created-111" })           // org ok
      .mockRejectedValueOnce({ message: "exam error" });          // exam fails
    setup();
    await fillCreateAndGoToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("wizard-create")).toHaveTextContent("Resume creation"));

    // Resume: only exam and cycle re-attempted, NOT org
    api.post
      .mockResolvedValueOnce({ row: { id: "exam-222" } })
      .mockResolvedValueOnce({ row: { id: "cycle-333" } });
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());

    const orgPosts = api.post.mock.calls.filter((c) => c[0].includes("/organizations"));
    expect(orgPosts).toHaveLength(1); // posted exactly once
  });
});

describe("Step 5: select-existing org — no org POST", () => {
  test("fires exam → cycle only; conducting_organization_id = selected org id", async () => {
    api.post
      .mockReset()
      .mockResolvedValueOnce({ row: { id: "exam-created" } })
      .mockResolvedValueOnce({ row: { id: "cycle-created" } });
    setup();
    await fillSelectAndGoToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());
    const calls = api.post.mock.calls;
    expect(calls.every((c) => !c[0].includes("/organizations"))).toBe(true);
    expect(calls[0][0]).toContain("/exams");
    expect(calls[0][1].payload.conducting_organization_id).toBe("org-aaa");
  });
});

describe("Step 5: exam payload — management_mode / cadence coercion", () => {
  // Helper: reach exam step via select-org path, apply overrides, then proceed to review
  async function goToReviewWithExamFields(examFieldOverrides = {}) {
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    // Apply any field overrides before advancing
    for (const [testId, value] of Object.entries(examFieldOverrides)) {
      fireEvent.change(screen.getByTestId(testId), { target: { value } });
    }
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "Test Exam" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "CSE 2025" } });
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
    fireEvent.click(screen.getByTestId("wizard-next-3"));
    fireEvent.click(screen.getByTestId("wizard-next-4"));
  }

  test("Test A — blank management_mode and cadence coerce to light/unknown in exam POST", async () => {
    api.post
      .mockReset()
      .mockResolvedValueOnce({ row: { id: "exam-111" } })
      .mockResolvedValueOnce({ row: { id: "cycle-222" } });
    setup();
    // Force both fields to blank — coercion must fire in handleNext and/or payload build
    await goToReviewWithExamFields({
      "exam-management-mode": "",
      "exam-cadence": "",
    });
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());
    const examPost = api.post.mock.calls.find((c) => c[0].includes("/exams"));
    expect(examPost[1].payload.management_mode).toBe("light");
    expect(examPost[1].payload.cadence).toBe("unknown");
  });

  test("Test B — explicit management_mode/cadence pass through unchanged", async () => {
    api.post
      .mockReset()
      .mockResolvedValueOnce({ row: { id: "exam-111" } })
      .mockResolvedValueOnce({ row: { id: "cycle-222" } });
    setup();
    await goToReviewWithExamFields({
      "exam-management-mode": "core",
      "exam-cadence": "annual",
    });
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());
    const examPost = api.post.mock.calls.find((c) => c[0].includes("/exams"));
    expect(examPost[1].payload.management_mode).toBe("core");
    expect(examPost[1].payload.cadence).toBe("annual");
  });
});

describe("Step 5: phases", () => {
  test("cb phase has exam_cycle_id set; slug uses derived name slug", async () => {
    api.post
      .mockReset()
      .mockResolvedValueOnce({ row: { id: "exam-111" } })
      .mockResolvedValueOnce({ row: { id: "cycle-222" } })
      .mockResolvedValueOnce({ row: { id: "phase-333" } });
    setup();
    await fillSelectAndGoToReview({ withPhase: true });
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());
    const phasePosts = api.post.mock.calls.filter((c) => c[0].includes("/exam-phases"));
    expect(phasePosts).toHaveLength(1);
    expect(phasePosts[0][1].payload.exam_cycle_id).toBe("cycle-222");
    // Derived slug from name "Prelims" → "prelims", cb → "prelims-2025"
    expect(phasePosts[0][1].payload.phase_slug).toBe("prelims-2025");
  });
});

describe("Step 5: mid-failure resume", () => {
  test("keeps created IDs; resume re-posts only remainder", async () => {
    api.post
      .mockReset()
      .mockResolvedValueOnce({ row: { id: "exam-111" } })
      .mockRejectedValueOnce({ message: "cycle server error" });
    setup();
    await fillSelectAndGoToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("wizard-create")).toHaveTextContent("Resume creation"));

    api.post.mockResolvedValueOnce({ row: { id: "cycle-222" } });
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());

    const examCalls = api.post.mock.calls.filter((c) => c[0].includes("/exams"));
    expect(examCalls).toHaveLength(1); // not double-posted
  });
});

describe("Step 5: org Step-5 failure (create mode)", () => {
  test("surfaces error, exam/cycle NOT posted; retry re-posts org only", async () => {
    api.post
      .mockReset()
      .mockRejectedValueOnce({ message: "duplicate org name" });
    setup();
    await fillCreateAndGoToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("log-org")).toHaveTextContent("✗"));
    // Exam and cycle must NOT have been posted
    expect(api.post.mock.calls.filter((c) => c[0].includes("/exams"))).toHaveLength(0);
    expect(api.post.mock.calls.filter((c) => c[0].includes("/exam-cycles"))).toHaveLength(0);
    // Resume button shown
    expect(screen.getByTestId("wizard-create")).toHaveTextContent("Resume creation");

    // Retry — org now succeeds
    api.post
      .mockResolvedValueOnce({ id: "org-retry-1" })
      .mockResolvedValueOnce({ row: { id: "exam-222" } })
      .mockResolvedValueOnce({ row: { id: "cycle-333" } });
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());
    const orgPosts = api.post.mock.calls.filter((c) => c[0].includes("/organizations"));
    expect(orgPosts).toHaveLength(2); // first failed, second retry
  });
});

describe("GuidedExamWizard workspace handoff and cycle source URL", () => {
  test("GuidedExamWizard success CTA navigates to workspace setup tab", async () => {
    api.post
      .mockReset()
      .mockResolvedValueOnce({ row: { id: "exam-created" } })
      .mockResolvedValueOnce({ row: { id: "cycle-created" } });
    setup();
    await fillSelectAndGoToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /open exam workspace/i }));

    expect(mockNavigate).toHaveBeenCalledWith("/admin/exam-intelligence/workspace/exam-created?tab=setup");
  });


});

describe("Step 5: cycle date payload", () => {
  test("filled dates submitted as ISO strings; empty dates omitted", async () => {
    api.post
      .mockReset()
      .mockResolvedValueOnce({ row: { id: "exam-111" } })
      .mockResolvedValueOnce({ row: { id: "cycle-222" } });
    setup();
    await waitFor(() => screen.getByTestId("org-list"));
    fireEvent.click(screen.getByTestId("org-select-org-aaa"));
    fireEvent.click(screen.getByTestId("wizard-next-1"));
    fireEvent.change(screen.getByTestId("exam-name"), { target: { value: "UPSC CSE" } });
    fireEvent.click(screen.getByTestId("wizard-next-2"));
    fireEvent.change(screen.getByTestId("cycle-name"), { target: { value: "CSE 2025" } });
    fireEvent.change(screen.getByTestId("cycle-year"), { target: { value: "2025" } });
    fireEvent.change(screen.getByTestId("cycle-exam_start"), { target: { value: "2025-09-15" } });
    // Leave all other dates empty
    fireEvent.click(screen.getByTestId("wizard-next-3"));
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    await act(async () => { fireEvent.click(screen.getByTestId("wizard-create")); });
    await waitFor(() => expect(screen.getByTestId("create-success")).toBeInTheDocument());
    const cyclePosts = api.post.mock.calls.filter((c) => c[0].includes("/exam-cycles"));
    const payload = cyclePosts[0][1].payload;
    expect(payload.exam_start).toBe("2025-09-15");
    // Empty dates must be omitted (undefined)
    expect(payload.notification_date).toBeUndefined();
    expect(payload.application_start).toBeUndefined();
    expect(payload.exam_end).toBeUndefined();
  });
});

describe("Step 5: review labels template vs cycle-bound", () => {
  test("distinguishes template and cycle-bound groups", async () => {
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
    const toggle = screen.getByTestId(`phase-template-toggle-${rowId}`).querySelector("input");
    fireEvent.click(toggle);
    fireEvent.click(screen.getByTestId("wizard-next-4"));
    expect(screen.getByTestId("review-template-phases")).toBeInTheDocument();
    expect(screen.getByTestId("review-cb-phases")).toBeInTheDocument();
  });
});
