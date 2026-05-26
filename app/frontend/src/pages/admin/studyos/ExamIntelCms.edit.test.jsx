import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// One row per entity so each Edit/Deactivate button has a stable test id.
const mockListRows = {
  "exam-families": [
    { id: "fam-11111111", slug: "ssc", name: "SSC", description: "old desc", is_active: true },
  ],
  exams: [
    {
      id: "exam-11111111", slug: "ssc-cgl", name: "SSC CGL",
      exam_family_id: "fam-11111111", exam_type: "recruitment",
      description: null, is_active: true,
    },
  ],
  "exam-cycles": [
    {
      id: "cyc-11111111", exam_id: "exam-11111111", year: 2026,
      cycle_name: "UPSC CSE 2026", status: "active",
      notification_date: null, application_start: null, application_end: null,
      exam_start: "2026-09-15", exam_end: null, source_url: null,
    },
  ],
  "exam-phases": [
    {
      id: "ph-11111111", exam_id: "exam-11111111", phase_name: "Prelims",
      phase_slug: "prelims", exam_cycle_id: null, phase_order: 1, mode: null,
      duration_mins: null, total_questions: null, total_marks: null, status: "active",
    },
  ],
  subjects: [
    { id: "sub-11111111", slug: "quant", name: "Quant", subject_group: null, is_active: true },
  ],
};

function mockEntityFromUrl(url) {
  const m = String(url).match(/exam-intelligence-cms\/([^?]+)/);
  return m ? m[1] : null;
}

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn(), del: jest.fn() },
  getApiErrorMessage: (e) => String(e?.message || e),
}));

// eslint-disable-next-line global-require
const { api } = require("../../../lib/api");
// eslint-disable-next-line global-require
const AdminExamIntelCms = require("./ExamIntelCms").default;

// CRA's jest preset sets resetMocks:true, which wipes mock implementations
// before every test — so (re)install them here, after that reset runs.
beforeEach(() => {
  api.get.mockImplementation((url) => {
    const ent = mockEntityFromUrl(url);
    const items = mockListRows[ent] || [];
    return Promise.resolve({ items, total: items.length });
  });
  api.post.mockResolvedValue({ audit_id: "aud-create" });
  api.patch.mockResolvedValue({ audit_id: "aud-edit-1" });
  api.del.mockResolvedValue({ audit_id: "aud-del-1" });
});

function renderWithClient() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AdminExamIntelCms />
    </QueryClientProvider>,
  );
}

function selectEntity(value) {
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value } });
}

afterEach(() => {
  jest.clearAllMocks();
});

test("Edit button renders for each of the four editable entities", async () => {
  renderWithClient();
  for (const [entity, rows] of [
    ["exam-families", mockListRows["exam-families"]],
    ["exams", mockListRows.exams],
    ["exam-cycles", mockListRows["exam-cycles"]],
    ["exam-phases", mockListRows["exam-phases"]],
  ]) {
    selectEntity(entity);
    expect(await screen.findByTestId(`cms-edit-${rows[0].id}`)).toBeTruthy();
  }
});

test("non-editable entity (subjects) shows no Edit button or actions column", async () => {
  renderWithClient();
  selectEntity("subjects");
  // Row renders…
  await waitFor(() => expect(screen.getByText("quant")).toBeTruthy());
  // …but no Edit affordance and no actions header.
  expect(screen.queryByTestId("cms-edit-sub-11111111")).toBeNull();
  expect(screen.queryByText("actions")).toBeNull();
});

test("clicking Edit pre-fills fields from the row", async () => {
  const { container } = renderWithClient();
  selectEntity("exam-cycles");
  fireEvent.click(await screen.findByTestId("cms-edit-cyc-11111111"));

  await screen.findByTestId("cms-edit-form");
  // Text field prefilled.
  expect(screen.getByTestId("cms-edit-field-cycle_name").value).toBe("UPSC CSE 2026");
  // int field prefilled.
  expect(screen.getByTestId("cms-edit-field-year").value).toBe("2026");
  // enum select prefilled.
  expect(screen.getByTestId("cms-edit-field-status").value).toBe("active");
  // DateField prefills from the YYYY-MM-DD value, displayed dd-mm-yyyy, no TZ drift.
  expect(container.querySelector("#cms-edit-date-exam_start").value).toBe("15-09-2026");
});

test("diff-only: changing exam_start submits ONLY that key (+ reason), in YYYY-MM-DD", async () => {
  const { container } = renderWithClient();
  selectEntity("exam-cycles");
  fireEvent.click(await screen.findByTestId("cms-edit-cyc-11111111"));
  await screen.findByTestId("cms-edit-form");

  fireEvent.change(container.querySelector("#cms-edit-date-exam_start"), {
    target: { value: "20-09-2026" },
  });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), {
    target: { value: "shift exam_start to the confirmed date" },
  });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [url, body] = api.patch.mock.calls[0];
  expect(url).toBe("/api/admin/exam-intelligence-cms/exam-cycles/cyc-11111111");
  // Timezone-correct date-only string, not a full ISO timestamp.
  expect(body.payload.exam_start).toBe("2026-09-20");
  // Only the changed key — nothing the admin didn't touch.
  expect(Object.keys(body.payload)).toEqual(["exam_start"]);
  expect(body.reason).toBe("shift exam_start to the confirmed date");
});

test("reason < 8 chars blocks submit (no PATCH, error shown)", async () => {
  renderWithClient();
  selectEntity("exam-cycles");
  fireEvent.click(await screen.findByTestId("cms-edit-cyc-11111111"));
  await screen.findByTestId("cms-edit-form");

  fireEvent.change(screen.getByTestId("cms-edit-field-cycle_name"), {
    target: { value: "UPSC CSE 2026 Revised" },
  });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), { target: { value: "short" } });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  expect((await screen.findByTestId("cms-edit-error")).textContent).toMatch(/Reason must be ≥8 chars/);
  expect(api.patch).not.toHaveBeenCalled();
});

test("clearing a NOT NULL field is blocked with a field-level error", async () => {
  // cycle_name is NOT NULL — clearing it must not submit a null.
  renderWithClient();
  selectEntity("exam-cycles");
  fireEvent.click(await screen.findByTestId("cms-edit-cyc-11111111"));
  await screen.findByTestId("cms-edit-form");

  fireEvent.change(screen.getByTestId("cms-edit-field-cycle_name"), { target: { value: "" } });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), {
    target: { value: "trying to clear the cycle name" },
  });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  expect((await screen.findByTestId("cms-edit-error")).textContent).toMatch(/cycle_name cannot be empty/);
  expect(api.patch).not.toHaveBeenCalled();
});

test("successful PATCH closes the form and reloads the list", async () => {
  renderWithClient();
  selectEntity("exam-cycles");
  fireEvent.click(await screen.findByTestId("cms-edit-cyc-11111111"));
  await screen.findByTestId("cms-edit-form");

  const getCallsBefore = api.get.mock.calls.length;
  fireEvent.change(screen.getByTestId("cms-edit-field-cycle_name"), {
    target: { value: "UPSC CSE 2026 Revised" },
  });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), {
    target: { value: "rename the cycle for clarity" },
  });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  // Form closes…
  await waitFor(() => expect(screen.queryByTestId("cms-edit-form")).toBeNull());
  // …success status shows the audit id…
  expect(screen.getByRole("status").textContent).toMatch(/Updated\. audit_id=aud-edit-1/);
  // …and the list reloaded.
  expect(api.get.mock.calls.length).toBeGreaterThan(getCallsBefore);
});

test("Deactivate (exams): confirm + reason required, soft-deletes via DELETE with reason query", async () => {
  const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
  const promptSpy = jest.spyOn(window, "prompt").mockReturnValue("retiring this exam from the catalogue");
  try {
    renderWithClient();
    selectEntity("exams");
    const btn = await screen.findByTestId("cms-deactivate-exam-11111111");
    // Never labelled "Delete".
    expect(btn.textContent).toMatch("Deactivate");
    expect(btn.textContent).not.toMatch(/Delete/i);
    fireEvent.click(btn);

    await waitFor(() => expect(api.del).toHaveBeenCalled());
    expect(confirmSpy).toHaveBeenCalled();
    const [url] = api.del.mock.calls[0];
    expect(url).toBe(
      "/api/admin/exam-intelligence-cms/exams/exam-11111111?reason=retiring%20this%20exam%20from%20the%20catalogue",
    );
  } finally {
    confirmSpy.mockRestore();
    promptSpy.mockRestore();
  }
});

test("Deactivate with a too-short reason does not call DELETE", async () => {
  const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
  const promptSpy = jest.spyOn(window, "prompt").mockReturnValue("short");
  try {
    renderWithClient();
    selectEntity("exams");
    fireEvent.click(await screen.findByTestId("cms-deactivate-exam-11111111"));
    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toMatch(/Deactivate reason must be ≥8 chars/),
    );
    expect(api.del).not.toHaveBeenCalled();
  } finally {
    confirmSpy.mockRestore();
    promptSpy.mockRestore();
  }
});
