/**
 * M4 — subjects entity: exam-family-scoped filtering.
 *
 * Subjects has no direct exam_family_id column; the backend resolves family
 * membership via exam_topic_coverage -> topics -> subject_id
 * (admin_exam_intel_cms._subject_ids_for_exam_family). This test covers the
 * frontend filter control: it renders only for ENTITY_FAMILY_SCOPE entities
 * (currently just subjects), populates from /exam-families, and sends
 * exam_family_id on the subjects list request when a family is selected.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

let mockSearchParamsRaw = {};
const mockSetSearchParams = jest.fn();

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useSearchParams: () => {
    const sp = new URLSearchParams(mockSearchParamsRaw);
    return [sp, mockSetSearchParams];
  },
}));

jest.mock("../../../../lib/supabase", () => ({
  __esModule: true,
  supabase: {
    auth: {
      getSession: jest.fn(),
      onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })),
    },
  },
}));

jest.mock("../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" }),
}));

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn(), del: jest.fn() },
  getApiErrorMessage: (e) => e?.message || "error",
}));

jest.mock("../../../../features/admin/shared/CmsRefField", () => ({
  __esModule: true,
  default: ({ testId }) => <input data-testid={testId} defaultValue="" />,
}));

jest.mock("../../../../shared/ui/heavy", () => ({
  DateField: () => null,
}));

jest.mock("../ExamIntelDocuments", () => ({
  __esModule: true,
  default: () => <div data-testid="documents-panel" />,
}));

const { api } = require("../../../../lib/api");
const ExamIntelCms = require("../ExamIntelCms").default;

const FAMILIES = [
  { id: "fam-1", name: "SSC" },
  { id: "fam-2", name: "UPSC" },
];

function setupDefaultMocks() {
  api.get.mockImplementation((url) => {
    if (url.includes("/exam-families")) return Promise.resolve({ items: FAMILIES, total: FAMILIES.length });
    if (url.includes("/admin/organizations")) return Promise.resolve({ items: [] });
    return Promise.resolve({ items: [], total: 0 });
  });
}

function renderCms() {
  return render(<ExamIntelCms />);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockSetSearchParams.mockClear();
  mockSearchParamsRaw = {};
  setupDefaultMocks();
});

test("exam-family filter is NOT rendered for the default entity (exam-families)", async () => {
  renderCms();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.queryByTestId("cms-family-filter")).toBeNull();
});

test("exam-family filter IS rendered for subjects and lists families", async () => {
  renderCms();
  fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: "subjects" } });
  const select = await screen.findByTestId("cms-family-filter");
  await waitFor(() => {
    const options = Array.from(select.options).map((o) => o.textContent);
    return options.includes("SSC") && options.includes("UPSC");
  });
  const optionLabels = Array.from(select.options).map((o) => o.textContent);
  expect(optionLabels).toContain("SSC");
  expect(optionLabels).toContain("UPSC");
});

test("selecting a family sends exam_family_id on the subjects list request", async () => {
  renderCms();
  fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: "subjects" } });
  const select = await screen.findByTestId("cms-family-filter");
  api.get.mockClear();
  fireEvent.change(select, { target: { value: "fam-1" } });
  await waitFor(() => {
    return api.get.mock.calls.some(([url]) => url.includes("/subjects") && url.includes("exam_family_id=fam-1"));
  });
  expect(
    api.get.mock.calls.some(([url]) => url.includes("/subjects") && url.includes("exam_family_id=fam-1")),
  ).toBe(true);
});

test("family filter resets and disappears when switching to a non-scoped entity", async () => {
  renderCms();
  fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: "subjects" } });
  const select = await screen.findByTestId("cms-family-filter");
  fireEvent.change(select, { target: { value: "fam-1" } });
  expect(select.value).toBe("fam-1");
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "topics" } });
  await waitFor(() => expect(screen.queryByTestId("cms-family-filter")).toBeNull());
});

test("'All families' selection sends no exam_family_id param", async () => {
  renderCms();
  fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: "subjects" } });
  const select = await screen.findByTestId("cms-family-filter");
  fireEvent.change(select, { target: { value: "fam-1" } });
  await waitFor(() => api.get.mock.calls.some(([url]) => url.includes("exam_family_id=fam-1")));
  api.get.mockClear();
  fireEvent.change(select, { target: { value: "" } });
  await waitFor(() => api.get.mock.calls.some(([url]) => url.includes("/subjects")));
  expect(api.get.mock.calls.some(([url]) => url.includes("exam_family_id="))).toBe(false);
});
