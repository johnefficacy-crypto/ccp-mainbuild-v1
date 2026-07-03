/**
 * Tests for EvidenceSection (D05 document-evidence registration + trust review, PR-4).
 *
 * Covers:
 * - load: coverage summary + registered-evidence table render
 * - register flow: POST /evidence with a role, then reload
 * - verify: POST /evidence/{id}/review decision=verified
 * - reject: inline reason → POST review decision=rejected
 * - empty state when no evidence registered
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  getApiErrorMessage: (e) => (e && e.message) || "error",
}));

const { api } = require("../../../../../lib/api");
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

function mockGet({ evidence = [EV], coverage = COVERAGE } = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/evidence/coverage")) return Promise.resolve(coverage);
    if (url.includes("/evidence/sources")) return Promise.resolve({ items: [{ id: "src-1", source_name: "SSC Official", is_authoritative: true }] });
    if (url.includes("/documents")) return Promise.resolve({ items: [{ id: "doc-1", title: "SSC CGL Syllabus", document_kind: "syllabus", status: "processed" }] });
    if (url.includes("/evidence")) return Promise.resolve({ items: evidence, total: evidence.length });
    return Promise.resolve({ items: [] });
  });
}

async function renderSection(props = {}) {
  let utils;
  await act(async () => {
    utils = render(<EvidenceSection examId="e1" cycleId="cA" phases={[{ id: "pA", phase_name: "Tier I" }]} {...props} />);
  });
  return utils;
}

beforeEach(() => { jest.clearAllMocks(); });

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

test("register flow posts evidence with a role", async () => {
  mockGet();
  api.post.mockResolvedValue({ ok: true, evidence: { id: "ev-2" } });
  await renderSection();
  fireEvent.click(await screen.findByTestId("ev-toggle-register"));
  const form = await screen.findByTestId("ev-register-form");
  expect(form).toBeInTheDocument();
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
