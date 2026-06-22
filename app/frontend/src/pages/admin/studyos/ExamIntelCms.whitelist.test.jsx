import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// The page fetches the entity list on mount; stub the API so each test
// stays focused on which form / bulk-template fields the entity exposes.
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
  api: { get: jest.fn(() => Promise.resolve({ items: [], total: 0 })), post: jest.fn() },
  getApiErrorMessage: (e) => String(e),
}));

// eslint-disable-next-line global-require
const AdminExamIntelCms = require("./ExamIntelCms").default;

function renderWithClient(ui) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

function selectEntity(value) {
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value } });
}

async function bulkTemplateKeys(entity) {
  selectEntity(entity);
  fireEvent.click(screen.getByTestId("cms-toggle-bulk"));
  fireEvent.click(await screen.findByTestId("cms-bulk-template"));
  const rows = JSON.parse(screen.getByTestId("cms-bulk-rows").value);
  return Object.keys(rows[0]);
}

// Each entity's frontend ENTITY_CONFIG must now match the backend whitelist
// (admin_exam_intel_cms.py _DOC_FIELDS/_PAPER_FIELDS/_QUESTION_FIELDS/_POLICY_FIELDS)
// + the migration columns (031 / 032 / 056), which are the source of truth.

test("syllabus-documents: form + bulk template carry the whitelist columns", async () => {
  renderWithClient(<AdminExamIntelCms />);
  selectEntity("syllabus-documents");
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  for (const k of ["source_id", "published_at", "fetched_at", "content_hash", "metadata"]) {
    expect(await screen.findByTestId(`cms-field-${k}`)).toBeTruthy();
  }
  // content_hash is auto-computed → read-only, never submitted from the form.
  expect(screen.getByTestId("cms-field-content_hash").disabled).toBe(true);
  expect(screen.getByTestId("cms-field-metadata").tagName).toBe("TEXTAREA");

  const keys = await bulkTemplateKeys("syllabus-documents");
  expect(keys).toEqual(
    expect.arrayContaining(["source_id", "content_hash", "published_at", "fetched_at", "metadata"]),
  );
});

test("pyq-papers: form + bulk template carry exam_cycle_id, content_hash, metadata", async () => {
  renderWithClient(<AdminExamIntelCms />);
  selectEntity("pyq-papers");
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  for (const k of ["exam_cycle_id", "content_hash", "metadata"]) {
    expect(await screen.findByTestId(`cms-field-${k}`)).toBeTruthy();
  }
  expect(screen.getByTestId("cms-field-content_hash").disabled).toBe(true);

  const keys = await bulkTemplateKeys("pyq-papers");
  expect(keys).toEqual(expect.arrayContaining(["exam_cycle_id", "content_hash", "metadata"]));
});

test("pyq-questions: form + bulk template carry explanation_text, language, hash", async () => {
  renderWithClient(<AdminExamIntelCms />);
  selectEntity("pyq-questions");
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  for (const k of ["explanation_text", "language", "normalized_question_hash"]) {
    expect(await screen.findByTestId(`cms-field-${k}`)).toBeTruthy();
  }
  expect(screen.getByTestId("cms-field-explanation_text").tagName).toBe("TEXTAREA");
  // normalized_question_hash is server-derived from question_text → read-only.
  expect(screen.getByTestId("cms-field-normalized_question_hash").disabled).toBe(true);

  const keys = await bulkTemplateKeys("pyq-questions");
  expect(keys).toEqual(
    expect.arrayContaining(["explanation_text", "language", "normalized_question_hash"]),
  );
});

test("policy-updates: form + bulk template carry the full affects_* + evidence set", async () => {
  renderWithClient(<AdminExamIntelCms />);
  selectEntity("policy-updates");
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  const added = [
    "exam_cycle_id", "source_id", "claim_status",
    "affects_deadline", "affects_eligibility", "affects_documents", "affects_vacancy",
    "change_summary", "evidence", "published_at", "effective_from",
  ];
  for (const k of added) {
    expect(await screen.findByTestId(`cms-field-${k}`)).toBeTruthy();
  }
  // claim_status is a CHECK-backed dropdown (migration 056).
  const claim = screen.getByTestId("cms-field-claim_status");
  expect(claim.tagName).toBe("SELECT");
  const claimValues = Array.from(claim.querySelectorAll("option")).map((o) => o.value);
  expect(claimValues).toEqual(
    expect.arrayContaining(["unverified", "official_confirmed", "superseded"]),
  );

  const keys = await bulkTemplateKeys("policy-updates");
  expect(keys).toEqual(expect.arrayContaining(added));
});

test("pyq-sources: trust_status stays out of the create form (forced pending, no-op)", async () => {
  // Backend forces trust_status='pending' on create and exposes no review
  // queue; promotion is a PATCH-only / trust-UI concern, out of scope here.
  renderWithClient(<AdminExamIntelCms />);
  selectEntity("pyq-sources");
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  expect(await screen.findByTestId("cms-field-source_type")).toBeTruthy();
  expect(screen.queryByTestId("cms-field-trust_status")).toBeNull();

  await waitFor(() => expect(true).toBe(true));
});
