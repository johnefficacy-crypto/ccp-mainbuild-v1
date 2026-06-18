/**
 * Wave 4.6 CL-1 — operator-chrome identifier hygiene.
 *
 * Across the in-scope surfaces (Registry table, ConsoleWorkQueue, Knowledge
 * Governance landing), operator-rendered text must contain no bare UUID, no
 * raw ISO-8601 timestamp, no "/api/" endpoint path, and no "§"; raw tokens must
 * render as human labels.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { humanizeToken, relativeDate } from "./operatorChrome";

jest.mock("../../../lib/api", () => ({ __esModule: true, api: { get: jest.fn() } }));
const { api } = require("../../../lib/api");

import ExamListTable from "./ExamListTable";
import ConsoleWorkQueue from "./ConsoleWorkQueue";
import AdminKnowledgeGovernance from "../../../pages/admin/KnowledgeGovernance";

const UUID = "3f9a1c2e-7b44-4d11-9aaa-0c2b9f8e1234";
const ISO = "2026-06-16T08:30:00+00:00";
const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const ISO_RE = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/;

function assertNoLeaks(text) {
  expect(text).not.toMatch(UUID_RE);
  expect(text).not.toMatch(ISO_RE);
  expect(text).not.toMatch(/\/api\//);
  expect(text).not.toContain("§");
}

// ── helpers ─────────────────────────────────────────────────────────────────

describe("operatorChrome helpers", () => {
  test("humanizeToken turns snake/dotted tokens into safe labels, never raw", () => {
    expect(humanizeToken("civil_services")).toBe("Civil services");
    expect(humanizeToken("exam_intel.cms.cycle.create")).toBe("Exam intel cms cycle create");
    expect(humanizeToken("civil_services")).not.toContain("_");
    expect(humanizeToken(null)).toBe("");
  });

  test("relativeDate never returns a raw ISO string", () => {
    expect(relativeDate(ISO)).not.toMatch(ISO_RE);
    expect(relativeDate(new Date(Date.now() - 3600_000).toISOString())).toMatch(/ago|just now/);
    expect(relativeDate(null)).toBe("—");
    expect(relativeDate("garbage")).toBe("—");
  });
});

// ── Registry table ──────────────────────────────────────────────────────────

test("ExamListTable: unmapped exam_type humanized; no id/iso/api/§ leaked", () => {
  const items = [{
    id: UUID, slug: "ssc-cgl", name: "SSC CGL", exam_type: "civil_services",
    syllabus_verified: 1, syllabus_pending: 0, verified_topic_count: 2,
    coverage_total: 3, high_yield_topic_count: 1, readiness_level: "ready",
    management_mode: "core", cadence: "annual",
  }];
  render(<MemoryRouter><ExamListTable items={items} total_count={1} /></MemoryRouter>);
  expect(screen.getByText("Civil services")).toBeInTheDocument(); // humanized, not "civil_services"
  const text = document.body.textContent;
  expect(text).not.toContain("civil_services");
  assertNoLeaks(text);
});

// ── ConsoleWorkQueue ─────────────────────────────────────────────────────────

test("ConsoleWorkQueue: unmapped status/flag/cadence humanized; no id/iso/api/§", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("/console/summary")) {
      return Promise.resolve({ blocked: 0, needs_action: 1, ready: 0, pending_review: 0, stale_review_queue: 0, total_count: 1 });
    }
    if (url.includes("/console/exams")) {
      return Promise.resolve({
        items: [{
          id: UUID, slug: "ssc-cgl", name: "SSC CGL", exam_type: "civil_services",
          management_mode: "core", cadence: "biennial", exam_family_id: null,
          organization_name: "SSC", status: "needs_review", flags: ["weird_flag"],
          blocker_count: 0, first_blocker_text: null, locked_coverage_count: 1,
          verified_pyq_count: 0, total_pyq_count: 3,
        }],
        count: 1, total_count: 1, has_next: false, limit: 25, offset: 0,
      });
    }
    return Promise.resolve({ items: [] }); // families
  });
  render(<MemoryRouter><ConsoleWorkQueue /></MemoryRouter>);
  await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
  const text = document.body.textContent;
  // unmapped tokens humanized, not raw snake_case
  expect(text).toContain("Needs review");
  expect(text).toContain("Weird flag");
  expect(text).toContain("Biennial");
  expect(text).toContain("Civil services");
  expect(text).not.toMatch(/needs_review|weird_flag/);
  assertNoLeaks(text);
});

// ── Knowledge Governance landing ─────────────────────────────────────────────

test("KnowledgeGovernance: audit event keys humanized + relative date; no raw token/iso/api/§", async () => {
  api.get.mockResolvedValue({
    recent_audit: [
      { action: "exam_intel.cms.cycle.create", target: "exam_cycle", actor: "ops@x", at: ISO, notes: null },
    ],
    kg: null,
  });
  render(<MemoryRouter><AdminKnowledgeGovernance /></MemoryRouter>);
  await waitFor(() => expect(screen.getByTestId("admin-kg-landing")).toBeTruthy());
  await waitFor(() => expect(document.body.textContent).toContain("Exam intel cms cycle create"));
  const text = document.body.textContent;
  expect(text).toContain("Exam cycle"); // target humanized
  expect(text).not.toContain("exam_intel.cms.cycle.create");
  expect(text).not.toContain("exam_cycle");
  assertNoLeaks(text);
});
