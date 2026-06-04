/**
 * Tests for ExamIntelCms exam form:
 * - conducting_organization_id org select is rendered
 * - slug field is NOT present
 * - submitted payload omits slug
 * - conducting_organization_id is included when selected
 *
 * Note: this repo's CRA setup has no @testing-library/jest-dom; assertions use
 * plain Jest matchers (queryBy*-null, toBeTruthy, etc.) only.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

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
  default: () => null,
}));

const { api } = require("../../../../lib/api");
const ExamIntelCms = require("../ExamIntelCms").default;

beforeEach(() => {
  jest.clearAllMocks();
  // Both CMS entity lists and the org list use api.get; return appropriate shapes
  api.get.mockImplementation((url) => {
    if (url.includes("/admin/organizations")) {
      return Promise.resolve({ items: [{ id: "org-1", name: "RPSC", type: "state_psc", state: "rajasthan" }] });
    }
    return Promise.resolve({ items: [] });
  });
});

// Navigate to exams entity and open create form
async function openExamCreate() {
  render(<ExamIntelCms />);
  const select = await screen.findByTestId("cms-entity-select");
  fireEvent.change(select, { target: { value: "exams" } });
  const createBtn = await screen.findByTestId("cms-toggle-create");
  fireEvent.click(createBtn);
}

// ─── slug field is gone ───────────────────────────────────────────────────────

test("exam create form does NOT have a slug input", async () => {
  await openExamCreate();
  expect(screen.queryByTestId("cms-field-slug")).toBeNull();
});

// ─── org select is present ────────────────────────────────────────────────────

test("exam create form has conducting_organization_id field", async () => {
  await openExamCreate();
  expect(screen.queryByTestId("cms-field-conducting_organization_id")).toBeTruthy();
});

// ─── submitted payload omits slug ────────────────────────────────────────────

test("exam create payload omits slug", async () => {
  api.post.mockResolvedValueOnce({
    ok: true,
    audit_id: "a1",
    row: { id: "e1", name: "RPSC RAS", slug: "rajasthan-rpsc-ras" },
  });

  await openExamCreate();

  fireEvent.change(screen.getByTestId("cms-field-name"), { target: { value: "RPSC RAS" } });
  fireEvent.change(screen.getByTestId("cms-reason"), {
    target: { value: "adding rpsc ras exam for rajasthan" },
  });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const body = api.post.mock.calls[0][1];
  expect(body.payload.slug).toBeUndefined();
});

// ─── org id included in payload when selected ────────────────────────────────

test("exam create payload includes conducting_organization_id when selected", async () => {
  api.post.mockResolvedValueOnce({ ok: true, audit_id: "a1", row: { id: "e1" } });

  await openExamCreate();

  fireEvent.change(screen.getByTestId("cms-field-name"), { target: { value: "Test Exam" } });
  fireEvent.change(screen.getByTestId("cms-field-conducting_organization_id"), {
    target: { value: "org-1" },
  });
  fireEvent.change(screen.getByTestId("cms-reason"), {
    target: { value: "adding test exam with org link" },
  });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const body = api.post.mock.calls[0][1];
  expect(body.payload.conducting_organization_id).toBe("org-1");
});
