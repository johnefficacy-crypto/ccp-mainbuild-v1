import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const mockExamRow = {
  id: "exam-11111111",
  slug: "ssc-cgl",
  name: "SSC CGL",
  exam_family_id: "fam-11111111",
  exam_type: "recruitment",
  management_mode: "core",
  cadence: "annual",
  description: null,
  is_active: true,
};

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

// eslint-disable-next-line global-require
const { api } = require("../../../lib/api");
// eslint-disable-next-line global-require
const AdminExamIntelCms = require("./ExamIntelCms").default;

beforeEach(() => {
  api.get.mockImplementation((url) => {
    if (String(url).includes("exam-intelligence-cms/exams")) {
      return Promise.resolve({ items: [mockExamRow], total: 1 });
    }
    return Promise.resolve({ items: [], total: 0 });
  });
  api.post.mockResolvedValue({ ok: true, audit_id: "aud-create" });
  api.patch.mockResolvedValue({ ok: true, audit_id: "aud-edit" });
});

afterEach(() => {
  jest.clearAllMocks();
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

// ─── Create form ───────────────────────────────────────────────────────────

test("exam create form renders management_mode select with default light", async () => {
  renderWithClient();
  selectEntity("exams");
  fireEvent.click(await screen.findByText(/New row/i));

  const select = await screen.findByTestId("cms-field-management_mode");
  expect(select.tagName).toBe("SELECT");
  expect(select.value).toBe("light");
  const options = Array.from(select.options).map((o) => o.value);
  expect(options).toEqual(expect.arrayContaining(["core", "light", "index_only", "archive"]));
});

test("exam create form renders cadence select with default unknown", async () => {
  renderWithClient();
  selectEntity("exams");
  fireEvent.click(await screen.findByText(/New row/i));

  const select = await screen.findByTestId("cms-field-cadence");
  expect(select.tagName).toBe("SELECT");
  expect(select.value).toBe("unknown");
  const options = Array.from(select.options).map((o) => o.value);
  expect(options).toEqual(
    expect.arrayContaining(["annual", "recurring", "irregular", "one_off", "unknown"]),
  );
});

// ─── Edit form ─────────────────────────────────────────────────────────────

test("exam edit form pre-fills management_mode and cadence from the row", async () => {
  renderWithClient();
  selectEntity("exams");
  fireEvent.click(await screen.findByTestId("cms-edit-exam-11111111"));
  await screen.findByTestId("cms-edit-form");

  expect(screen.getByTestId("cms-edit-field-management_mode").value).toBe("core");
  expect(screen.getByTestId("cms-edit-field-cadence").value).toBe("annual");
});

test("edit form shows row value not create default when row carries management_mode", async () => {
  // Regression: the create default ('light') must not bleed into the edit form when the
  // row already has a different value ('core'). This test uses the mock as-returned by
  // the fixed list endpoint (management_mode/cadence present in items).
  renderWithClient();
  selectEntity("exams");
  fireEvent.click(await screen.findByTestId("cms-edit-exam-11111111"));
  await screen.findByTestId("cms-edit-form");

  // 'core' row should show 'core', not the create default 'light'.
  expect(screen.getByTestId("cms-edit-field-management_mode").value).toBe("core");
  // 'annual' row should show 'annual', not the create default 'unknown'.
  expect(screen.getByTestId("cms-edit-field-cadence").value).toBe("annual");
});

test("exam edit form allows changing management_mode and submits only the diff", async () => {
  renderWithClient();
  selectEntity("exams");
  fireEvent.click(await screen.findByTestId("cms-edit-exam-11111111"));
  await screen.findByTestId("cms-edit-form");

  fireEvent.change(screen.getByTestId("cms-edit-field-management_mode"), {
    target: { value: "light" },
  });
  fireEvent.change(screen.getByTestId("cms-edit-reason"), {
    target: { value: "downgrading to light management" },
  });
  fireEvent.click(screen.getByTestId("cms-edit-submit"));

  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [url, body] = api.patch.mock.calls[0];
  expect(url).toContain("exams/exam-11111111");
  expect(body.payload.management_mode).toBe("light");
  expect(body.payload).not.toHaveProperty("cadence");
});
