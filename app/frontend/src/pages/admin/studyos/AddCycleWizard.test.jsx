import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

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
const AddCycleWizard = require("./AddCycleWizard").default;

const EXAM_ID = "exam-test-1";

const EXISTING_CYCLES = [
  { id: "cyc-1", cycle_name: "Main", year: 2024, exam_id: EXAM_ID },
];

const TEMPLATE_PHASES = [
  { id: "ph-tmpl-1", phase_name: "Prelims", phase_slug: "prelims", exam_cycle_id: null, exam_id: EXAM_ID },
  { id: "ph-tmpl-2", phase_name: "Mains", phase_slug: "mains", exam_cycle_id: null, exam_id: EXAM_ID },
];

const BOUND_PHASES = [
  { id: "ph-bound-1", phase_name: "Prelims 2024", phase_slug: "prelims-2024", exam_cycle_id: "cyc-1", exam_id: EXAM_ID },
];

function setup({ cycles = EXISTING_CYCLES, phases = [...TEMPLATE_PHASES, ...BOUND_PHASES] } = {}) {
  api.get
    .mockResolvedValueOnce({ items: cycles })
    .mockResolvedValueOnce({ items: phases });

  return render(
    <MemoryRouter initialEntries={[`/admin/exam-intelligence/exams/${EXAM_ID}/add-cycle`]}>
      <Routes>
        <Route path="/admin/exam-intelligence/exams/:exam_id/add-cycle" element={<AddCycleWizard />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
});

// ── Initial load ──────────────────────────────────────────────────────────────

describe("initial load", () => {
  test("shows loading state initially", () => {
    api.get.mockReturnValue(new Promise(() => {}));
    api.get.mockReturnValueOnce(new Promise(() => {})).mockReturnValueOnce(new Promise(() => {}));
    render(
      <MemoryRouter initialEntries={[`/admin/exam-intelligence/exams/${EXAM_ID}/add-cycle`]}>
        <Routes>
          <Route path="/admin/exam-intelligence/exams/:exam_id/add-cycle" element={<AddCycleWizard />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByTestId("add-cycle-wizard")).toBeInTheDocument();
  });

  test("renders Step 1 after load", async () => {
    setup();
    await waitFor(() => expect(screen.getByTestId("add-cycle-step-cycle")).toBeInTheDocument());
  });

  test("shows load error when fetch fails", async () => {
    api.get.mockRejectedValueOnce(new Error("Network error")).mockRejectedValueOnce(new Error("Network error"));
    render(
      <MemoryRouter initialEntries={[`/admin/exam-intelligence/exams/${EXAM_ID}/add-cycle`]}>
        <Routes>
          <Route path="/admin/exam-intelligence/exams/:exam_id/add-cycle" element={<AddCycleWizard />} />
        </Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  test("makes exactly 2 GET calls (cycles + phases) and ZERO POST before Review", async () => {
    setup();
    await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
    expect(api.get).toHaveBeenCalledTimes(2);
    expect(api.post).not.toHaveBeenCalled();
  });
});

// ── Step 1: Cycle ─────────────────────────────────────────────────────────────

describe("Step 1 — Cycle", () => {
  test("Next button disabled when cycle_name or year is empty", async () => {
    setup();
    await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
    const btn = screen.getByTestId("ac-next-1");
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByTestId("ac-cycle-name"), { target: { value: "Main" } });
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2025" } });
    expect(btn).not.toBeDisabled();
  });

  test("no POST before reaching Review step", async () => {
    setup();
    await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
    fireEvent.change(screen.getByTestId("ac-cycle-name"), { target: { value: "Main" } });
    fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2025" } });
    fireEvent.click(screen.getByTestId("ac-next-1"));
    expect(api.post).not.toHaveBeenCalled();
  });
});

// ── Dup-year guard ────────────────────────────────────────────────────────────

describe("dup-year guard", () => {
  test("exact (year, cycle_name) match shows block — Next stays disabled", async () => {
    setup();
    await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
    fireEvent.change(screen.getByTestId("ac-cycle-name"), { target: { value: "Main" } });
    fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2024" } });
    expect(screen.getByTestId("ac-dup-block")).toBeInTheDocument();
    expect(screen.getByTestId("ac-next-1")).toBeDisabled();
  });

  test("year-only match (different name) shows warn — blocked until confirmed", async () => {
    setup();
    await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
    fireEvent.change(screen.getByTestId("ac-cycle-name"), { target: { value: "Supplementary" } });
    fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2024" } });
    expect(screen.getByTestId("ac-dup-warn")).toBeInTheDocument();
    expect(screen.getByTestId("ac-next-1")).toBeDisabled();
    fireEvent.click(screen.getByTestId("ac-dup-confirm"));
    expect(screen.getByTestId("ac-dup-confirmed")).toBeInTheDocument();
    expect(screen.getByTestId("ac-next-1")).not.toBeDisabled();
  });

  test("changing year after confirmation resets confirmation flag", async () => {
    setup();
    await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
    fireEvent.change(screen.getByTestId("ac-cycle-name"), { target: { value: "Supplementary" } });
    fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2024" } });
    fireEvent.click(screen.getByTestId("ac-dup-confirm"));
    expect(screen.getByTestId("ac-dup-confirmed")).toBeInTheDocument();
    // Change year → resets confirmation
    fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2025" } });
    expect(screen.queryByTestId("ac-dup-confirmed")).not.toBeInTheDocument();
  });
});

// ── Step 2: Phases — template picker ─────────────────────────────────────────

async function goToPhases() {
  setup();
  await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
  fireEvent.change(screen.getByTestId("ac-cycle-name"), { target: { value: "Main" } });
  fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2025" } });
  fireEvent.click(screen.getByTestId("ac-next-1"));
  await waitFor(() => screen.getByTestId("add-cycle-step-phases"));
}

describe("Step 2 — Phases: template picker", () => {
  test("only template phases (exam_cycle_id=null) appear in picker", async () => {
    await goToPhases();
    expect(screen.getByTestId("ac-template-list")).toBeInTheDocument();
    // Only 2 templates (ph-tmpl-1 and ph-tmpl-2), not the bound phase
    expect(screen.getByTestId("ac-template-check-ph-tmpl-1")).toBeInTheDocument();
    expect(screen.getByTestId("ac-template-check-ph-tmpl-2")).toBeInTheDocument();
    expect(screen.queryByTestId("ac-template-check-ph-bound-1")).not.toBeInTheDocument();
  });

  test("selecting template shows cycle-bound slug", async () => {
    await goToPhases();
    fireEvent.click(screen.getByTestId("ac-template-check-ph-tmpl-1"));
    // cycleBoundSlug("prelims", "2025", "Main") = "prelims-2025"
    expect(screen.getByTestId("ac-template-cb-slug-ph-tmpl-1")).toHaveTextContent("prelims-2025");
  });

  test("can advance without selecting any templates (zero phases is valid)", async () => {
    await goToPhases();
    expect(screen.getByTestId("ac-next-2")).not.toBeDisabled();
  });
});

// ── Step 2: Phases — new phases ───────────────────────────────────────────────

describe("Step 2 — Phases: new phases", () => {
  test("adding new phase with empty name blocks advance", async () => {
    await goToPhases();
    fireEvent.click(screen.getByTestId("ac-add-phase"));
    expect(screen.getByTestId("ac-next-2")).toBeDisabled();
  });

  test("filling phase name unblocks advance", async () => {
    await goToPhases();
    fireEvent.click(screen.getByTestId("ac-add-phase"));
    const inputs = screen.getAllByTestId(/^ac-phase-name-/);
    fireEvent.change(inputs[0], { target: { value: "Interview" } });
    expect(screen.getByTestId("ac-next-2")).not.toBeDisabled();
  });

  test("auto-derives slug from phase_name when base_slug blank", async () => {
    await goToPhases();
    fireEvent.click(screen.getByTestId("ac-add-phase"));
    const inputs = screen.getAllByTestId(/^ac-phase-name-/);
    fireEvent.change(inputs[0], { target: { value: "Physical Test" } });
    const cbSlugs = screen.getAllByTestId(/^ac-phase-cb-slug-/);
    // cycleBoundSlug("physical-test", "2025", "Main") = "physical-test-2025"
    expect(cbSlugs[0]).toHaveTextContent("physical-test-2025");
  });

  test("intra-set duplicate base_slug shows error and blocks advance", async () => {
    await goToPhases();
    // Add two phases with same effective slug
    fireEvent.click(screen.getByTestId("ac-add-phase"));
    fireEvent.click(screen.getByTestId("ac-add-phase"));
    const names = screen.getAllByTestId(/^ac-phase-name-/);
    fireEvent.change(names[0], { target: { value: "Prelims" } });
    fireEvent.change(names[1], { target: { value: "Prelims" } });
    await waitFor(() => expect(screen.getByTestId("ac-phase-errors")).toBeInTheDocument());
    expect(screen.getByTestId("ac-next-2")).toBeDisabled();
  });

  test("existing-phase collision (same year cycle) shows error", async () => {
    // ph-bound-1 has slug prelims-2024 for cyc-1 (year 2024).
    // Adding a template phase "prelims" for year 2024 → cb slug "prelims-2024" → collision.
    setup({ cycles: EXISTING_CYCLES, phases: [...TEMPLATE_PHASES, ...BOUND_PHASES] });
    await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
    fireEvent.change(screen.getByTestId("ac-cycle-name"), { target: { value: "Supplementary" } });
    fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2024" } });
    fireEvent.click(screen.getByTestId("ac-dup-confirm"));
    fireEvent.click(screen.getByTestId("ac-next-1"));
    await waitFor(() => screen.getByTestId("add-cycle-step-phases"));
    // Select "prelims" template → its cb slug = "prelims-2024" which already exists
    fireEvent.click(screen.getByTestId("ac-template-check-ph-tmpl-1"));
    await waitFor(() => expect(screen.getByTestId("ac-phase-errors")).toBeInTheDocument());
    expect(screen.getByTestId("ac-next-2")).toBeDisabled();
  });

  test("createTemplate toggle shown on new phases", async () => {
    await goToPhases();
    fireEvent.click(screen.getByTestId("ac-add-phase"));
    const toggles = screen.getAllByTestId(/^ac-phase-template-toggle-/);
    expect(toggles.length).toBeGreaterThan(0);
  });
});

// ── Step 3: Review & Create ───────────────────────────────────────────────────

async function goToReview({ withTemplate = false, withNewPhase = false } = {}) {
  setup();
  await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
  fireEvent.change(screen.getByTestId("ac-cycle-name"), { target: { value: "Main" } });
  fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2025" } });
  fireEvent.click(screen.getByTestId("ac-next-1"));
  await waitFor(() => screen.getByTestId("add-cycle-step-phases"));
  if (withTemplate) {
    fireEvent.click(screen.getByTestId("ac-template-check-ph-tmpl-1"));
  }
  if (withNewPhase) {
    fireEvent.click(screen.getByTestId("ac-add-phase"));
    const names = screen.getAllByTestId(/^ac-phase-name-/);
    fireEvent.change(names[names.length - 1], { target: { value: "Interview" } });
  }
  fireEvent.click(screen.getByTestId("ac-next-2"));
  await waitFor(() => screen.getByTestId("add-cycle-step-review"));
}

describe("Step 3 — Review & Create: no POST before clicking Create", () => {
  test("no api.post before Create is clicked", async () => {
    await goToReview();
    expect(api.post).not.toHaveBeenCalled();
  });
});

describe("Step 3 — Review & Create: happy path (cycle only)", () => {
  test("cycle POST succeeds, shows success banner", async () => {
    api.post.mockResolvedValueOnce({ row: { id: "cyc-new" } });
    await goToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("ac-create")); });
    await waitFor(() => expect(screen.getByTestId("ac-create-success")).toBeInTheDocument());
    expect(api.post).toHaveBeenCalledTimes(1);
    expect(api.post.mock.calls[0][1]).toMatchObject({
      reason: "add cycle wizard create",
      payload: expect.objectContaining({ exam_id: EXAM_ID, cycle_name: "Main", year: 2025 }),
    });
  });
});

describe("Step 3 — Review & Create: template clone", () => {
  test("cloned template → cycle-bound slug in POST", async () => {
    api.post
      .mockResolvedValueOnce({ row: { id: "cyc-new" } })
      .mockResolvedValueOnce({ row: { id: "ph-new-1" } });
    await goToReview({ withTemplate: true });
    await act(async () => { fireEvent.click(screen.getByTestId("ac-create")); });
    await waitFor(() => expect(screen.getByTestId("ac-create-success")).toBeInTheDocument());
    const phasePosts = api.post.mock.calls.filter((c) => String(c[0]).includes("exam-phases"));
    expect(phasePosts).toHaveLength(1);
    // phase_slug should be "prelims-2025"
    expect(phasePosts[0][1].payload.phase_slug).toBe("prelims-2025");
    expect(phasePosts[0][1].payload.exam_cycle_id).toBe("cyc-new");
  });
});

describe("Step 3 — Review & Create: createTemplate flag", () => {
  test("new phase with createTemplate=true triggers template POST before cb POST", async () => {
    api.post
      .mockResolvedValueOnce({ row: { id: "cyc-new" } })
      .mockResolvedValueOnce({ row: { id: "ph-tmpl-new" } })  // template
      .mockResolvedValueOnce({ row: { id: "ph-cb-new" } });   // cycle-bound

    setup();
    await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
    fireEvent.change(screen.getByTestId("ac-cycle-name"), { target: { value: "Main" } });
    fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2025" } });
    fireEvent.click(screen.getByTestId("ac-next-1"));
    await waitFor(() => screen.getByTestId("add-cycle-step-phases"));
    fireEvent.click(screen.getByTestId("ac-add-phase"));
    const names = screen.getAllByTestId(/^ac-phase-name-/);
    fireEvent.change(names[0], { target: { value: "Interview" } });
    const toggles = screen.getAllByTestId(/^ac-phase-template-toggle-/);
    fireEvent.click(toggles[0].querySelector("input[type=checkbox]"));
    fireEvent.click(screen.getByTestId("ac-next-2"));
    await waitFor(() => screen.getByTestId("add-cycle-step-review"));

    await act(async () => { fireEvent.click(screen.getByTestId("ac-create")); });
    await waitFor(() => expect(screen.getByTestId("ac-create-success")).toBeInTheDocument());

    // 3 POSTs: cycle, template (exam_cycle_id=null), cycle-bound
    expect(api.post).toHaveBeenCalledTimes(3);
    const [, tmplCall, cbCall] = api.post.mock.calls;
    expect(tmplCall[1].payload.exam_cycle_id).toBeNull();
    expect(tmplCall[1].payload.phase_slug).toBe("interview");
    expect(cbCall[1].payload.exam_cycle_id).toBe("cyc-new");
    expect(cbCall[1].payload.phase_slug).toBe("interview-2025");
  });
});

// ── Resume on failure ─────────────────────────────────────────────────────────

describe("resume on failure", () => {
  test("cycle POST fails — Create button becomes Resume, cycle not re-posted on retry", async () => {
    const cycleFail = new Error("duplicate key");
    api.post.mockRejectedValueOnce(cycleFail);
    await goToReview({ withTemplate: true });
    await act(async () => { fireEvent.click(screen.getByTestId("ac-create")); });
    await waitFor(() => expect(screen.getByTestId("ac-create")).toHaveTextContent("Resume creation"));
    expect(api.post).toHaveBeenCalledTimes(1);
  });

  test("cycle succeeds, phase fails — resume re-posts only the failed phase", async () => {
    api.post
      .mockResolvedValueOnce({ row: { id: "cyc-new" } })
      .mockRejectedValueOnce(new Error("phase fail"));

    await goToReview({ withTemplate: true });
    await act(async () => { fireEvent.click(screen.getByTestId("ac-create")); });
    await waitFor(() => expect(screen.getByTestId("ac-create")).toHaveTextContent("Resume creation"));
    expect(api.post).toHaveBeenCalledTimes(2);

    // Now retry — cycle already stored, should only POST the phase
    api.post.mockResolvedValueOnce({ row: { id: "ph-new" } });
    await act(async () => { fireEvent.click(screen.getByTestId("ac-create")); });
    await waitFor(() => expect(screen.getByTestId("ac-create-success")).toBeInTheDocument());
    // On resume, only 1 more POST (the phase), cycle not re-posted
    expect(api.post).toHaveBeenCalledTimes(3);
    const lastCall = api.post.mock.calls[2];
    expect(lastCall[0]).toContain("exam-phases");
  });
});

// ── ISO dates ─────────────────────────────────────────────────────────────────

describe("ISO dates", () => {
  test("date fields sent as ISO strings when filled", async () => {
    api.post.mockResolvedValueOnce({ row: { id: "cyc-new" } });
    setup();
    await waitFor(() => screen.getByTestId("add-cycle-step-cycle"));
    fireEvent.change(screen.getByTestId("ac-cycle-name"), { target: { value: "Main" } });
    fireEvent.change(screen.getByTestId("ac-cycle-year"), { target: { value: "2025" } });
    fireEvent.change(screen.getByTestId("ac-cycle-exam_start"), { target: { value: "2025-05-01" } });
    fireEvent.click(screen.getByTestId("ac-next-1"));
    await waitFor(() => screen.getByTestId("add-cycle-step-phases"));
    fireEvent.click(screen.getByTestId("ac-next-2"));
    await waitFor(() => screen.getByTestId("add-cycle-step-review"));
    await act(async () => { fireEvent.click(screen.getByTestId("ac-create")); });
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(api.post.mock.calls[0][1].payload.exam_start).toBe("2025-05-01");
  });

  test("empty date fields omitted (not sent as empty string)", async () => {
    api.post.mockResolvedValueOnce({ row: { id: "cyc-new" } });
    await goToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("ac-create")); });
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const payload = api.post.mock.calls[0][1].payload;
    expect(payload.exam_start).toBeUndefined();
    expect(payload.notification_date).toBeUndefined();
  });
});

// ── Reset ─────────────────────────────────────────────────────────────────────

describe("reset", () => {
  test("Add another cycle button resets to Step 1", async () => {
    api.post.mockResolvedValueOnce({ row: { id: "cyc-new" } });
    await goToReview();
    await act(async () => { fireEvent.click(screen.getByTestId("ac-create")); });
    await waitFor(() => expect(screen.getByTestId("ac-create-success")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("ac-reset"));
    await waitFor(() => expect(screen.getByTestId("add-cycle-step-cycle")).toBeInTheDocument());
  });
});
