/**
 * I6 — identifier hygiene regression for ExamIntelCms (defects I3 + I5).
 *
 * Guards:
 * - Raw UUID row IDs must not appear verbatim in table cells.
 * - Raw UUID FK columns (exam_id, subject_id, topic_id, etc.) must not
 *   appear verbatim in table cells.
 * - Non-UUID values (slugs, names, statuses) still render in readable form.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Full UUID used as both the row id and FK values to verify leakage.
const UUID = "550e8400-e29b-41d4-a716-446655440000";
const UUID2 = "660f9500-f30c-52e5-b827-557766551111";
const UUID_PREFIX = "550e8400"; // first 8 hex chars — what should appear after truncation

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
    // Return a minimal fixture that exercises UUID columns for the entity.
    if (url.includes("exam-families")) {
      return Promise.resolve({
        items: [{ id: UUID, slug: "upsc", name: "UPSC", is_active: true, created_at: null }],
        total: 1,
      });
    }
    if (url.includes("exam-cycles")) {
      return Promise.resolve({
        items: [
          {
            id: UUID,
            exam_id: UUID2,        // FK UUID — must not appear raw
            year: 2026,
            cycle_name: "CSE 2026",
            status: "active",
          },
        ],
        total: 1,
      });
    }
    if (url.includes("/topics?")) {
      return Promise.resolve({
        items: [
          {
            id: UUID,
            subject_id: UUID2,     // FK UUID — must not appear raw
            slug: "polity",
            name: "Polity",
            level: "topic",
            is_active: true,
          },
        ],
        total: 1,
      });
    }
    return Promise.resolve({ items: [], total: 0 });
  });
  api.post.mockResolvedValue({ audit_id: "aud-1" });
  api.patch.mockResolvedValue({ audit_id: "aud-2" });
  api.del.mockResolvedValue({ audit_id: "aud-3" });
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

// ── I3: row id column ──────────────────────────────────────────────────────

test("I3: row id is truncated — full UUID not shown in exam-families table", async () => {
  renderWithClient();
  // default entity is exam-families
  await waitFor(() => expect(screen.queryByText("UPSC")).toBeTruthy());

  // Full UUID must NOT appear anywhere in the document.
  expect(document.body.textContent).not.toContain(UUID);
  // Truncated prefix + ellipsis must appear instead.
  expect(document.body.textContent).toContain(`${UUID_PREFIX}…`);
});

// ── I3: FK UUID columns ────────────────────────────────────────────────────

test("I3: exam_id FK column is truncated — full UUID not shown in exam-cycles table", async () => {
  renderWithClient();
  selectEntity("exam-cycles");
  await waitFor(() => expect(screen.queryByText("CSE 2026")).toBeTruthy());

  // Full UUID2 (the exam_id value) must not appear raw.
  expect(document.body.textContent).not.toContain(UUID2);
  // UUID prefix for UUID2.
  expect(document.body.textContent).toContain("660f9500…");
});

// ── I5: subject_id FK column in topics ────────────────────────────────────

test("I5: subject_id FK column is truncated — full UUID not shown in topics table", async () => {
  renderWithClient();
  selectEntity("topics");
  // Wait for the row name to appear (name column = "Polity")
  await waitFor(() => expect(screen.queryAllByText("Polity").length).toBeGreaterThan(0));

  // Full UUID2 (the subject_id value) must not appear raw.
  expect(document.body.textContent).not.toContain(UUID2);
  // UUID prefix for UUID2 must appear (truncated form).
  expect(document.body.textContent).toContain("660f9500…");
});

// ── Non-UUID values still render ───────────────────────────────────────────

test("non-UUID slug and name values still render legibly", async () => {
  renderWithClient();
  // exam-families: slug="upsc", name="UPSC"
  // Non-UUID values pass through renderCellValue unchanged (no capitalisation).
  await waitFor(() => expect(screen.queryByText("UPSC")).toBeTruthy());
  // Slug "upsc" is a non-UUID 4-char string — should appear as raw value "upsc".
  expect(document.body.textContent).toContain("upsc");
});
