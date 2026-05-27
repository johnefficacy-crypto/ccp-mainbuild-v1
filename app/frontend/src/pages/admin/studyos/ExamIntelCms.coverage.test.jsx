import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// The page fetches the entity list on mount; stub the API so the test
// stays focused on which form fields the coverage entity renders.
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

test("exam-topic-coverage create form renders the real schema fields, not the stale ones", async () => {
  renderWithClient(<AdminExamIntelCms />);

  // Switch to the coverage entity (changing entity resets the create form).
  fireEvent.change(screen.getByTestId("cms-entity-select"), {
    target: { value: "exam-topic-coverage" },
  });
  // Open the create form.
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  // Real migration-030 columns are present.
  expect(await screen.findByTestId("cms-field-exam_priority_score")).toBeTruthy();
  expect(screen.getByTestId("cms-field-coverage_depth")).toBeTruthy();
  expect(screen.getByTestId("cms-field-confidence_score")).toBeTruthy();
  expect(screen.getByTestId("cms-field-source_basis")).toBeTruthy();
  expect(screen.getByTestId("cms-field-reviewer_status")).toBeTruthy();
  expect(screen.getByTestId("cms-field-review_notes")).toBeTruthy();
  expect(screen.getByTestId("cms-field-metadata")).toBeTruthy();

  // Stale fields are gone.
  expect(screen.queryByTestId("cms-field-priority")).toBeNull();
  expect(screen.queryByTestId("cms-field-is_active")).toBeNull();

  // Enum fields render as <select> dropdowns sourced from the CHECK lists.
  const depth = screen.getByTestId("cms-field-coverage_depth");
  expect(depth.tagName).toBe("SELECT");
  const depthValues = Array.from(depth.querySelectorAll("option")).map((o) => o.value);
  expect(depthValues).toEqual(
    expect.arrayContaining(["unknown", "none", "mentioned", "light", "normal", "deep", "core"]),
  );

  // Score fields are numeric with step/min/max bounds.
  const score = screen.getByTestId("cms-field-exam_priority_score");
  expect(score.getAttribute("type")).toBe("number");
  expect(score.getAttribute("min")).toBe("0");
  expect(score.getAttribute("max")).toBe("100");

  // metadata is a free-form JSON textarea.
  expect(screen.getByTestId("cms-field-metadata").tagName).toBe("TEXTAREA");

  await waitFor(() => expect(true).toBe(true));
});
