import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// One row per entity so each Edit/Retire button has a stable test id.
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
    {
      id: "sub-11111111", slug: "quant", name: "Quant",
      subject_group: "Mathematics", default_difficulty_level: null, is_active: true,
    },
  ],
  topics: [
    {
      id: "top-11111111", subject_id: "sub-11111111", slug: "algebra",
      name: "Algebra", level: "topic", parent_topic_id: null,
      default_difficulty_level: null, description: null, is_active: true,
    },
  ],
  "pyq-sources": [
    {
      id: "src-11111111", exam_id: "exam-11111111", source_type: "official",
      title: "Official 2024 Paper", source_url: null, trust_status: "pending",
      source_id: "ext-dedup-key-001",
    },
  ],
};

function mockEntityFromUrl(url) {
  const m = String(url).match(/exam-intelligence-cms\/([^?]+)/);
  return m ? m[1] : null;
}

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useSearchParams: () => [new URLSearchParams(), jest.fn()],
}))

jest.mock("../../../lib/supabase", () => ({
  __esModule: true,
  supabase: { auth: { getSession: jest.fn(), onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })) } },
}))
jest.mock("../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" }),
}))

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn(), del: jest.fn() },
  getApiErrorMessage: (e) => String(e?.message || e),
}));

jest.mock("../../../shared/ui/core", () => ({
  useToast: () => ({ success: jest.fn(), error: jest.fn(), info: jest.fn() }),
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

test("Edit button renders for each of the seven editable entities", async () => {
  renderWithClient();
  for (const [entity, rows] of [
    ["exam-families", mockListRows["exam-families"]],
    ["exams", mockListRows.exams],
    ["exam-cycles", mockListRows["exam-cycles"]],
    ["exam-phases", mockListRows["exam-phases"]],
    ["subjects", mockListRows.subjects],
    ["topics", mockListRows.topics],
    ["pyq-sources", mockListRows["pyq-sources"]],
  ]) {
    selectEntity(entity);
    expect(await screen.findByTestId(`cms-edit-${rows[0].id}`)).toBeTruthy();
  }
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
  // DateField wraps a native <input type="date">; its .value IDL attribute is
  // ISO (YYYY-MM-DD) regardless of the locale-specific display format, no TZ drift.
  expect(container.querySelector("#cms-edit-date-exam_start").value).toBe("2026-09-15");
});

test("diff-only: changing exam_start submits ONLY that key (+ reason), in YYYY-MM-DD", async () => {
  const { container } = renderWithClient();
  selectEntity("exam-cycles");
  fireEvent.click(await screen.findByTestId("cms-edit-cyc-11111111"));
  await screen.findByTestId("cms-edit-form");

  // Native date input IDL value is ISO (YYYY-MM-DD).
  fireEvent.change(container.querySelector("#cms-edit-date-exam_start"), {
    target: { value: "2026-09-20" },
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

test("Retire (exams): dialog collects reason, soft-deletes via DELETE with reason query", async () => {
  renderWithClient();
  selectEntity("exams");
  const btn = await screen.findByTestId("cms-retire-exam-11111111");
  expect(btn.textContent).toMatch("Retire");
  expect(btn.textContent).not.toMatch(/Delete/i);
  fireEvent.click(btn);

  // Dialog opens — no browser confirm/prompt.
  await screen.findByTestId("cms-retire-dialog");
  fireEvent.change(screen.getByTestId("cms-retire-reason"), {
    target: { value: "retiring this exam from the catalogue" },
  });
  fireEvent.click(screen.getByTestId("cms-retire"));

  await waitFor(() => expect(api.del).toHaveBeenCalled());
  const [url] = api.del.mock.calls[0];
  expect(url).toBe(
    "/api/admin/exam-intelligence-cms/exams/exam-11111111?reason=retiring%20this%20exam%20from%20the%20catalogue",
  );
});

test("Retire with a too-short reason does not call DELETE", async () => {
  renderWithClient();
  selectEntity("exams");
  fireEvent.click(await screen.findByTestId("cms-retire-exam-11111111"));

  // Dialog opens; submit without filling the reason field.
  await screen.findByTestId("cms-retire-dialog");
  fireEvent.click(screen.getByTestId("cms-retire"));

  await waitFor(() =>
    expect(screen.getByTestId("cms-retire-error").textContent).toMatch(/Retire reason must be ≥8 chars/),
  );
  expect(api.del).not.toHaveBeenCalled();
});

// ── Taxonomy edit tests ────────────────────────────────────────────────

test("subjects: Edit button renders and prefills name + subject_group", async () => {
  renderWithClient();
  selectEntity("subjects");
  fireEvent.click(await screen.findByTestId("cms-edit-sub-11111111"));
  await screen.findByTestId("cms-edit-form");
  expect(screen.getByTestId("cms-edit-field-name").value).toBe("Quant");
  expect(screen.getByTestId("cms-edit-field-subject_group").value).toBe("Mathematics");
});

test("subjects: PATCH sends only changed fields to /subjects/{id}", async () => {
  renderWithClient();
  selectEntity("subjects");
  fireEvent.click(await screen.findByTestId("cms-edit-sub-11111111"));
  await screen.findByTestId("cms-edit-form");

  fireEvent.change(screen.getByTestId("cms-edit-field-name"), {
    target: { value: "Quantitative Aptitude" },
  });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), {
    target: { value: "expand the subject name" },
  });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [url, body] = api.patch.mock.calls[0];
  expect(url).toBe("/api/admin/exam-intelligence-cms/subjects/sub-11111111");
  expect(body.payload).toEqual({ name: "Quantitative Aptitude" });
  expect(body.reason).toBe("expand the subject name");
});

test("topics: Edit button renders and prefills name + level", async () => {
  renderWithClient();
  selectEntity("topics");
  fireEvent.click(await screen.findByTestId("cms-edit-top-11111111"));
  await screen.findByTestId("cms-edit-form");
  expect(screen.getByTestId("cms-edit-field-name").value).toBe("Algebra");
  expect(screen.getByTestId("cms-edit-field-level").value).toBe("topic");
});

test("topics: PATCH sends only changed fields to /topics/{id}", async () => {
  renderWithClient();
  selectEntity("topics");
  fireEvent.click(await screen.findByTestId("cms-edit-top-11111111"));
  await screen.findByTestId("cms-edit-form");

  fireEvent.change(screen.getByTestId("cms-edit-field-name"), {
    target: { value: "Linear Algebra" },
  });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), {
    target: { value: "rename topic to be more specific" },
  });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [url, body] = api.patch.mock.calls[0];
  expect(url).toBe("/api/admin/exam-intelligence-cms/topics/top-11111111");
  expect(body.payload).toEqual({ name: "Linear Algebra" });
  expect(body.reason).toBe("rename topic to be more specific");
});

test("pyq-sources: Edit button renders and prefills title", async () => {
  renderWithClient();
  selectEntity("pyq-sources");
  fireEvent.click(await screen.findByTestId("cms-edit-src-11111111"));
  await screen.findByTestId("cms-edit-form");
  expect(screen.getByTestId("cms-edit-field-title").value).toBe("Official 2024 Paper");
});

test("pyq-sources: trust_status field is NOT rendered in the edit form", async () => {
  renderWithClient();
  selectEntity("pyq-sources");
  fireEvent.click(await screen.findByTestId("cms-edit-src-11111111"));
  await screen.findByTestId("cms-edit-form");
  expect(screen.queryByTestId("cms-edit-field-trust_status")).toBeNull();
});

test("pyq-sources: PATCH does not send trust_status even if row has it", async () => {
  renderWithClient();
  selectEntity("pyq-sources");
  fireEvent.click(await screen.findByTestId("cms-edit-src-11111111"));
  await screen.findByTestId("cms-edit-form");

  fireEvent.change(screen.getByTestId("cms-edit-field-title"), {
    target: { value: "Official 2024 Paper (revised)" },
  });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), {
    target: { value: "correct the paper title" },
  });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [url, body] = api.patch.mock.calls[0];
  expect(url).toBe("/api/admin/exam-intelligence-cms/pyq-sources/src-11111111");
  expect(body.payload).toEqual({ title: "Official 2024 Paper (revised)" });
  expect(body.payload).not.toHaveProperty("trust_status");
});

test("reviewable entities (exam-topic-coverage) have no Edit button", async () => {
  renderWithClient();
  selectEntity("exam-topic-coverage");
  // Table renders with rows column header but no actions column.
  await waitFor(() => expect(screen.queryByText("actions")).toBeNull());
});

// ── Identity / dedup-key fencing tests ────────────────────────────────

test("subjects: slug field is NOT rendered in the edit form", async () => {
  renderWithClient();
  selectEntity("subjects");
  fireEvent.click(await screen.findByTestId("cms-edit-sub-11111111"));
  await screen.findByTestId("cms-edit-form");
  expect(screen.queryByTestId("cms-edit-field-slug")).toBeNull();
});

test("subjects: PATCH does not include slug even if row has it", async () => {
  renderWithClient();
  selectEntity("subjects");
  fireEvent.click(await screen.findByTestId("cms-edit-sub-11111111"));
  await screen.findByTestId("cms-edit-form");

  fireEvent.change(screen.getByTestId("cms-edit-field-name"), {
    target: { value: "Quantitative Aptitude" },
  });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), {
    target: { value: "rename the subject" },
  });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [, body] = api.patch.mock.calls[0];
  expect(body.payload).not.toHaveProperty("slug");
  expect(body.payload).toEqual({ name: "Quantitative Aptitude" });
});

test("topics: slug field is NOT rendered in the edit form", async () => {
  renderWithClient();
  selectEntity("topics");
  fireEvent.click(await screen.findByTestId("cms-edit-top-11111111"));
  await screen.findByTestId("cms-edit-form");
  expect(screen.queryByTestId("cms-edit-field-slug")).toBeNull();
});

test("topics: PATCH does not include slug even if row has it", async () => {
  renderWithClient();
  selectEntity("topics");
  fireEvent.click(await screen.findByTestId("cms-edit-top-11111111"));
  await screen.findByTestId("cms-edit-form");

  fireEvent.change(screen.getByTestId("cms-edit-field-name"), {
    target: { value: "Linear Algebra" },
  });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), {
    target: { value: "rename topic" },
  });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [, body] = api.patch.mock.calls[0];
  expect(body.payload).not.toHaveProperty("slug");
  expect(body.payload).toEqual({ name: "Linear Algebra" });
});

test("topics: level, subject_id, parent_topic_id ARE rendered (not over-fenced)", async () => {
  renderWithClient();
  selectEntity("topics");
  fireEvent.click(await screen.findByTestId("cms-edit-top-11111111"));
  await screen.findByTestId("cms-edit-form");
  // level and subject_id must be present — legitimate re-parenting use case.
  expect(screen.getByTestId("cms-edit-field-level")).toBeTruthy();
  expect(screen.getByTestId("cms-edit-field-subject_id")).toBeTruthy();
  expect(screen.getByTestId("cms-edit-field-parent_topic_id")).toBeTruthy();
});

test("pyq-sources: source_id field is NOT rendered in the edit form", async () => {
  renderWithClient();
  selectEntity("pyq-sources");
  fireEvent.click(await screen.findByTestId("cms-edit-src-11111111"));
  await screen.findByTestId("cms-edit-form");
  expect(screen.queryByTestId("cms-edit-field-source_id")).toBeNull();
});

test("pyq-sources: PATCH does not include source_id", async () => {
  renderWithClient();
  selectEntity("pyq-sources");
  fireEvent.click(await screen.findByTestId("cms-edit-src-11111111"));
  await screen.findByTestId("cms-edit-form");

  fireEvent.change(screen.getByTestId("cms-edit-field-title"), {
    target: { value: "Official 2024 Paper (revised)" },
  });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), {
    target: { value: "correct the title" },
  });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [, body] = api.patch.mock.calls[0];
  expect(body.payload).not.toHaveProperty("source_id");
  expect(body.payload).not.toHaveProperty("trust_status");
});

test("pyq-sources: exam_id IS rendered (not over-fenced)", async () => {
  renderWithClient();
  selectEntity("pyq-sources");
  fireEvent.click(await screen.findByTestId("cms-edit-src-11111111"));
  await screen.findByTestId("cms-edit-form");
  expect(screen.getByTestId("cms-edit-field-exam_id")).toBeTruthy();
});
