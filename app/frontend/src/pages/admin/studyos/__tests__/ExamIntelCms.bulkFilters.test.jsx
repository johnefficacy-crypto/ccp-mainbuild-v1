/**
 * Advanced Import / Repair — extra CMS filters (exam_type, management_mode,
 * cadence incl. 'biannual', is_active, organization) and bulk select / bulk
 * update / bulk retire against the filtered result set.
 */
import React from "react";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";

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

const EXAMS = [
  { id: "exam-1", name: "Exam One", exam_type: "recruitment", management_mode: "light", cadence: "annual", is_active: true, created_at: "2026-01-01" },
  { id: "exam-2", name: "Exam Two", exam_type: "recruitment", management_mode: "light", cadence: "annual", is_active: true, created_at: "2026-01-02" },
];
const ORGS = [{ id: "org-1", name: "UPSC" }];

function setupDefaultMocks() {
  api.get.mockImplementation((url) => {
    if (url.includes("/admin/organizations")) return Promise.resolve({ items: ORGS });
    if (url.includes("/exams")) return Promise.resolve({ items: EXAMS, total: EXAMS.length });
    return Promise.resolve({ items: [], total: 0 });
  });
}

function renderCms() {
  return render(<ExamIntelCms />);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockSetSearchParams.mockClear();
  mockSearchParamsRaw = { entity: "exams" };
  setupDefaultMocks();
});

test("cadence field/filter offers biannual for exams that run twice a year", async () => {
  renderCms();
  const filterSelect = await screen.findByTestId("cms-filter-cadence");
  const optionValues = Array.from(filterSelect.options).map((o) => o.value);
  expect(optionValues).toContain("biannual");

  fireEvent.click(screen.getByTestId("cms-toggle-create"));
  const fieldSelect = await screen.findByTestId("cms-field-cadence");
  expect(Array.from(fieldSelect.options).map((o) => o.value)).toContain("biannual");
});

test("extra filters (exam_type, management_mode, cadence, is_active, organization) send matching query params", async () => {
  renderCms();
  await screen.findByTestId("cms-filter-exam_type");
  api.get.mockClear();

  fireEvent.change(screen.getByTestId("cms-filter-cadence"), { target: { value: "biannual" } });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith(expect.stringContaining("cadence=biannual")));

  api.get.mockClear();
  fireEvent.change(screen.getByTestId("cms-filter-is_active"), { target: { value: "false" } });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith(expect.stringContaining("is_active=false")));

  api.get.mockClear();
  fireEvent.change(screen.getByTestId("cms-filter-conducting_organization_id"), { target: { value: "org-1" } });
  await waitFor(() => expect(api.get).toHaveBeenCalledWith(expect.stringContaining("conducting_organization_id=org-1")));
});

test("exams name search sends a `q` param (ilike on name)", async () => {
  renderCms();
  const searchInput = await screen.findByTestId("cms-search-input");
  api.get.mockClear();
  fireEvent.change(searchInput, { target: { value: "ssc" } });
  // search is debounced (300ms) then fires load with the `q` param
  await waitFor(
    () => expect(api.get).toHaveBeenCalledWith(expect.stringContaining("q=ssc")),
    { timeout: 1000 },
  );
});

test("row checkboxes drive a selected count and enable bulk edit / retire", async () => {
  renderCms();
  await screen.findByTestId(`cms-select-row-${EXAMS[0].id}`);
  expect(screen.getByTestId("cms-bulk-selected-count")).toHaveTextContent("0 selected");

  fireEvent.click(screen.getByTestId(`cms-select-row-${EXAMS[0].id}`));
  fireEvent.click(screen.getByTestId(`cms-select-row-${EXAMS[1].id}`));
  expect(screen.getByTestId("cms-bulk-selected-count")).toHaveTextContent("2 selected");
  expect(screen.getByTestId("cms-bulk-edit-toggle")).not.toBeDisabled();
  expect(screen.getByTestId("cms-bulk-retire-toggle")).not.toBeDisabled();
});

test("bulk edit selected rows posts entity/ids/patch to /bulk-update", async () => {
  api.post.mockResolvedValue({ ok: true, ok_count: 2, error_count: 0, total: 2, audit_id: "a1", results: [] });
  renderCms();
  await screen.findByTestId(`cms-select-row-${EXAMS[0].id}`);
  fireEvent.click(screen.getByTestId(`cms-select-row-${EXAMS[0].id}`));
  fireEvent.click(screen.getByTestId(`cms-select-row-${EXAMS[1].id}`));

  fireEvent.click(screen.getByTestId("cms-bulk-edit-toggle"));
  fireEvent.change(await screen.findByTestId("cms-bulk-edit-field-select"), { target: { value: "cadence" } });
  fireEvent.change(await screen.findByTestId("cms-bulk-edit-field-cadence"), { target: { value: "biannual" } });
  fireEvent.change(screen.getByTestId("cms-bulk-edit-reason"), { target: { value: "reclassify both exams" } });
  fireEvent.click(screen.getByTestId("cms-bulk-edit-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    "/api/admin/exam-intelligence-cms/bulk-update",
    expect.objectContaining({
      entity: "exams",
      ids: expect.arrayContaining(["exam-1", "exam-2"]),
      patch: { cadence: "biannual" },
    }),
  ));
});

test("retire selected rows posts entity/ids to /bulk-deactivate", async () => {
  api.post.mockResolvedValue({ ok: true, ok_count: 2, error_count: 0, total: 2, audit_id: "a2", results: [] });
  renderCms();
  await screen.findByTestId(`cms-select-row-${EXAMS[0].id}`);
  fireEvent.click(screen.getByTestId(`cms-select-row-${EXAMS[0].id}`));
  fireEvent.click(screen.getByTestId(`cms-select-row-${EXAMS[1].id}`));

  fireEvent.click(screen.getByTestId("cms-bulk-retire-toggle"));
  const dialog = await screen.findByTestId("cms-bulk-retire-dialog");
  fireEvent.change(within(dialog).getByTestId("cms-bulk-retire-reason"), { target: { value: "duplicate exams, retiring both" } });
  fireEvent.click(within(dialog).getByTestId("cms-bulk-retire-confirm"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    "/api/admin/exam-intelligence-cms/bulk-deactivate",
    expect.objectContaining({ entity: "exams", ids: expect.arrayContaining(["exam-1", "exam-2"]) }),
  ));
});

test("bulk edit field picker excludes identity + reference/scope fields (backend rejects them)", async () => {
  renderCms();
  await screen.findByTestId(`cms-select-row-${EXAMS[0].id}`);
  fireEvent.click(screen.getByTestId(`cms-select-row-${EXAMS[0].id}`));
  fireEvent.click(screen.getByTestId("cms-bulk-edit-toggle"));
  const fieldSelect = await screen.findByTestId("cms-bulk-edit-field-select");
  const optionValues = Array.from(fieldSelect.options).map((o) => o.value);
  // identity column
  expect(optionValues).not.toContain("name");
  // reference FKs — bulk_update has no existence check, so these are single-row-only
  expect(optionValues).not.toContain("exam_family_id");
  expect(optionValues).not.toContain("conducting_organization_id");
  // a legitimate scalar/enum IS offered
  expect(optionValues).toContain("cadence");
  expect(optionValues).toContain("management_mode");
});

test("bulk toolbar is not shown for entities without bulk-update/bulk-deactivate backend support", async () => {
  renderCms();
  await screen.findByTestId("cms-bulk-toolbar");

  // pyq-papers is lifecycle-owned (trust_status via the review queue) and is
  // not in EDITABLE_ENTITIES, so it must not offer row selection / bulk actions.
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "pyq-papers" } });
  await waitFor(() => expect(screen.queryByTestId("cms-bulk-toolbar")).toBeNull());
});

test("selection resets to zero when switching entities", async () => {
  renderCms();
  await screen.findByTestId(`cms-select-row-${EXAMS[0].id}`);
  fireEvent.click(screen.getByTestId(`cms-select-row-${EXAMS[0].id}`));
  expect(screen.getByTestId("cms-bulk-selected-count")).toHaveTextContent("1 selected");

  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exam-families" } });
  await waitFor(() => expect(screen.getByTestId("cms-bulk-selected-count")).toHaveTextContent("0 selected"));
});
