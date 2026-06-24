import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

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
  api: { get: jest.fn(), post: jest.fn(() => Promise.resolve({ audit_id: "audit-1" })) },
  getApiErrorMessage: (e) => String(e),
}));

// eslint-disable-next-line global-require
const { api } = require("../../../lib/api");
// eslint-disable-next-line global-require
const AdminExamIntelCms = require("./ExamIntelCms").default;

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AdminExamIntelCms />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.post.mockResolvedValue({ audit_id: "audit-1" });
  api.get.mockImplementation((url) => {
    if (url.includes("/exams?")) {
      return Promise.resolve({
        items: [{ id: "exam-uuid-1", name: "SSC CGL", slug: "ssc-cgl" }],
        total: 1,
      });
    }
    return Promise.resolve({ items: [], total: 0 });
  });
});

test("submits the selected UUID, not the human-readable label", async () => {
  renderPage();

  fireEvent.change(screen.getByTestId("cms-entity-select"), {
    target: { value: "exam-cycles" },
  });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  // The exam_id field is now a searchable picker.
  fireEvent.focus(screen.getByTestId("cms-field-exam_id"));
  const option = await screen.findByTestId("cms-field-exam_id-option-exam-uuid-1");
  fireEvent.mouseDown(option);

  // The selection chip shows the readable label, not the raw id.
  expect(screen.getByTestId("cms-field-exam_id-selected").textContent).toContain("SSC CGL");

  fireEvent.change(screen.getByTestId("cms-field-year"), { target: { value: "2024" } });
  fireEvent.change(screen.getByTestId("cms-field-cycle_name"), { target: { value: "CGL 2024" } });
  fireEvent.change(screen.getByTestId("cms-reason"), {
    target: { value: "seeding a cycle row for the picker test" },
  });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [, body] = api.post.mock.calls[0];
  // The UUID is submitted — never the label.
  expect(body.payload.exam_id).toBe("exam-uuid-1");
  expect(JSON.stringify(body.payload)).not.toContain("SSC CGL");
});

test("an out-of-scope raw-UUID FK (topic_id) stays a plain text input", async () => {
  renderPage();

  fireEvent.change(screen.getByTestId("cms-entity-select"), {
    target: { value: "exam-topic-coverage" },
  });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  const topic = await screen.findByTestId("cms-field-topic_id");
  // Not converted to a picker: it is a bare <input>, with no selection chip.
  expect(topic.tagName).toBe("INPUT");
  expect(screen.queryByTestId("cms-field-topic_id-selected")).toBeNull();

  // It still accepts a raw UUID as before.
  fireEvent.change(topic, { target: { value: "11111111-1111-1111-1111-111111111111" } });
  expect(topic.value).toBe("11111111-1111-1111-1111-111111111111");
});
