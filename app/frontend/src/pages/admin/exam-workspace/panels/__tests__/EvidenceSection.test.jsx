/**
 * Tests for EvidenceSection (D05 document-evidence registration + trust review, PR-4).
 *
 * Covers:
 * - load: coverage summary + registered-evidence table render
 * - register flow (manage): POST /evidence with a role via useApiAction
 * - verify (review): POST /evidence/{id}/review decision=verified
 * - reject (review): inline reason → POST review decision=rejected
 * - permission gating: manage sees Register but not Verify; review sees Verify but not Register
 * - picker filters out upload-incomplete (placeholder) assets
 * - empty state when no evidence registered
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { ToastProvider } from "../../../../../shared/ui/core";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  getApiErrorMessage: (e) => (e && e.message) || "error",
}));

jest.mock("../../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: jest.fn(),
}));

const { api } = require("../../../../../lib/api");
const { useAuth } = require("../../../../../lib/authContext");
const EvidenceSection = require("../EvidenceSection").default;

const EV = {
  id: "ev-1",
  document_asset_id: "doc-1",
  source_registry_id: "src-1",
  source_authoritative: true,
  trust_status: "pending",
  document: { title: "SSC CGL Syllabus", document_kind: "syllabus", status: "processed" },
  extraction_status: "succeeded",
  roles: [{ id: "r-1", evidence_kind: "syllabus" }],
};

const COVERAGE = { applicable: true, complete: false, unclassified_phases: 0,
  unmet_requirements: [{ scope: "phase", evidence_kind: "exam_pattern", phase_kind: "objective_written" }] };

const ASSETS = [
  { id: "doc-1", title: "SSC CGL Syllabus", document_kind: "syllabus", status: "processed", content_hash: "abc" },
  { id: "doc-2", title: "Placeholder", document_kind: "syllabus", status: "uploaded", content_hash: "pending:x" },
];

function mockGet({ evidence = [EV], coverage = COVERAGE, assets = ASSETS } = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/evidence/coverage")) return Promise.resolve(coverage);
    if (url.includes("/evidence/sources")) return Promise.resolve({ items: [{ id: "src-1", source_name: "SSC Official", is_authoritative: true }] });
    if (url.includes("/documents")) return Promise.resolve({ items: assets });
    if (url.includes("/evidence")) return Promise.resolve({ items: evidence, total: evidence.length });
    return Promise.resolve({ items: [] });
  });
}

function setUser({ manage = true, review = true, superAdmin = false } = {}) {
  const permissions = [];
  if (manage) permissions.push("exam_intelligence.manage");
  if (review) permissions.push("exam_intelligence.review");
  useAuth.mockReturnValue({ user: { role: superAdmin ? "super_admin" : "admin", permissions } });
}

async function renderSection(props = {}) {
  let utils;
  await act(async () => {
    utils = render(
      <ToastProvider>
        <EvidenceSection examId="e1" cycleId="cA" phases={[{ id: "pA", phase_name: "Tier I" }]} {...props} />
      </ToastProvider>,
    );
  });
  return utils;
}

beforeEach(() => { jest.clearAllMocks(); setUser(); });

test("renders coverage summary and evidence row", async () => {
  mockGet();
  await renderSection();
  expect(await screen.findByTestId("ev-coverage")).toBeInTheDocument();
  expect(screen.getByTestId("ev-coverage-incomplete")).toHaveTextContent("1 unmet");
  expect(screen.getByTestId("ev-row-ev-1")).toBeInTheDocument();
  expect(screen.getByTestId("ev-trust-pending")).toBeInTheDocument();
  expect(screen.getByTestId("ev-src-ok-ev-1")).toBeInTheDocument();
});

test("empty state when nothing registered", async () => {
  mockGet({ evidence: [] });
  await renderSection();
  expect(await screen.findByTestId("ev-empty")).toBeInTheDocument();
});

test("register flow posts evidence with a role and filters placeholder assets", async () => {
  mockGet();
  api.post.mockResolvedValue({ ok: true, evidence: { id: "ev-2" } });
  await renderSection();
  fireEvent.click(await screen.findByTestId("ev-toggle-register"));
  await screen.findByTestId("ev-register-form");
  // Placeholder (uploaded / pending hash) asset must not be offered.
  const options = Array.from(screen.getByTestId("ev-asset-select").querySelectorAll("option")).map((o) => o.value);
  expect(options).toContain("doc-1");
  expect(options).not.toContain("doc-2");
  fireEvent.change(screen.getByTestId("ev-asset-select"), { target: { value: "doc-1" } });
  fireEvent.change(screen.getByTestId("ev-kind-select"), { target: { value: "exam_pattern" } });
  fireEvent.change(screen.getByTestId("ev-reason"), { target: { value: "official pattern doc" } });
  await act(async () => { fireEvent.click(screen.getByTestId("ev-register-submit")); });
  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [url, body] = api.post.mock.calls[0];
  expect(url).toBe("/api/admin/exam-intelligence-cms/evidence");
  expect(body.document_asset_id).toBe("doc-1");
  expect(body.roles[0].evidence_kind).toBe("exam_pattern");
  expect(body.reason).toBe("official pattern doc");
});

test("verify posts a verified review decision", async () => {
  mockGet();
  api.post.mockResolvedValue({ ok: true });
  await renderSection();
  await screen.findByTestId("ev-row-ev-1");
  await act(async () => { fireEvent.click(screen.getByTestId("ev-verify-ev-1")); });
  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    "/api/admin/exam-intelligence-cms/evidence/ev-1/review",
    expect.objectContaining({ decision: "verified" }),
  ));
});

test("reject requires a reason then posts rejected decision", async () => {
  mockGet();
  api.post.mockResolvedValue({ ok: true });
  await renderSection();
  await screen.findByTestId("ev-row-ev-1");
  fireEvent.click(screen.getByTestId("ev-reject-ev-1"));
  fireEvent.change(await screen.findByTestId("ev-reason-input-ev-1"), { target: { value: "wrong year uploaded" } });
  await act(async () => { fireEvent.click(screen.getByTestId("ev-reason-confirm-ev-1")); });
  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    "/api/admin/exam-intelligence-cms/evidence/ev-1/review",
    expect.objectContaining({ decision: "rejected", reason: "wrong year uploaded" }),
  ));
});

test("manage-only operator sees Register but not Verify", async () => {
  setUser({ manage: true, review: false });
  mockGet();
  await renderSection();
  await screen.findByTestId("ev-row-ev-1");
  expect(screen.getByTestId("ev-toggle-register")).toBeInTheDocument();
  expect(screen.queryByTestId("ev-verify-ev-1")).not.toBeInTheDocument();
  expect(screen.getByTestId("ev-review-na-ev-1")).toBeInTheDocument();
});

test("review-only operator sees Verify but not Register", async () => {
  setUser({ manage: false, review: true });
  mockGet();
  await renderSection();
  await screen.findByTestId("ev-row-ev-1");
  expect(screen.queryByTestId("ev-toggle-register")).not.toBeInTheDocument();
  expect(screen.getByTestId("ev-verify-ev-1")).toBeInTheDocument();
});
