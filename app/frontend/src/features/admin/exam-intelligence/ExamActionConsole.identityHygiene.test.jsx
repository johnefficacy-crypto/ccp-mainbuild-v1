import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import ExamActionConsole from "./ExamActionConsole";

jest.mock("../../../lib/api", () => ({ __esModule: true, api: { get: jest.fn() } }));
const { api } = require("../../../lib/api");

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

const FIXTURE = {
  exam: { id: UUID, name: null, slug: null, organization_name: null, family_name: null },
  activation_verdict: {
    status: "needs_action",
    headline: "Backend headline text",
    reasons: ["zzz_unmapped_reason"],
  },
  mock_readiness: { status: "thin_bank", detail: "Backend mock detail" },
  action_queue: [{
    id: "a1",
    severity: "action",
    area: "pyq",
    title: "Backend title",
    why: "Backend why",
    cta_label: "Open workspace",
    cta_route: `/admin/exam-intelligence/workspace/${UUID}`,
    entity_kind: "exam_topic_coverage",
    entity_id: null,
    evidence_refs: [],
    status: "open",
  }],
  activation_checks: [{
    area: "pyq",
    gate: "advisory",
    state: "needs_action",
    detail: "Backend detail",
    reasons: ["zzz_unmapped_reason"],
    evidence_refs: [],
  }],
  stages: [
    { id: "setup", label: "Setup", areas: ["setup", "documents"] },
    { id: "evidence", label: "Evidence", areas: ["syllabus", "topic_coverage", "pyq"] },
    { id: "review", label: "Review", areas: ["updates", "competition", "mock_readiness"] },
    { id: "activation", label: "Activation", areas: ["publish"] },
  ],
  evidence_refs: [],
  generated_at: ISO,
};

beforeEach(() => {
  api.get.mockReset();
});

test("ExamActionConsole humanizes reachable reason fallbacks without leaking identifiers", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes(`/console/exams/${UUID}`)) return Promise.resolve(FIXTURE);
    return Promise.reject(new Error(`unexpected url ${url}`));
  });

  render(<MemoryRouter><ExamActionConsole examId={UUID} /></MemoryRouter>);

  await waitFor(() => expect(screen.getByTestId("exam-action-console")).toBeInTheDocument());

  expect(screen.getByTestId("action-console-name")).toHaveTextContent(/^Unnamed exam$/);

  const text = document.body.textContent;
  expect(text).toContain("Unnamed exam");
  expect(text).toContain("Zzz unmapped reason");
  expect(text).toContain("PYQ");
  expect(text).toContain("Advisory");
  expect(text).toContain("Needs action");

  expect(text).toContain("Backend headline text");
  expect(text).toContain("Backend title");
  expect(text).toContain("Backend why");
  expect(text).toContain("Backend detail");
  expect(text).toContain("Backend mock detail");

  expect(text).not.toMatch(/zzz_unmapped_reason/);
  assertNoLeaks(text);
});
