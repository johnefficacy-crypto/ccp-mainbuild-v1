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
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
  getApiErrorMessage: (e) => String(e),
}));

jest.mock("../../../shared/ui/core", () => ({
  useToast: () => ({ success: jest.fn(), error: jest.fn(), info: jest.fn() }),
}));

// eslint-disable-next-line global-require
const { api } = require("../../../lib/api");
// eslint-disable-next-line global-require
const AdminExamIntelCms = require("./ExamIntelCms").default;

beforeEach(() => {
  api.get.mockResolvedValue({ items: [], total: 0 });
  api.post.mockResolvedValue({ audit_id: "aud-1" });
});

function renderWithClient(ui) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

test("exam-cycles create: a date picked/typed via DateField submits as ISO", async () => {
  const { container } = renderWithClient(<AdminExamIntelCms />);

  fireEvent.change(screen.getByTestId("cms-entity-select"), {
    target: { value: "exam-cycles" },
  });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  // The date field renders a DateField (text input shows dd-mm-yyyy).
  const examStart = await waitFor(() => {
    const el = container.querySelector("#cms-date-exam_start");
    if (!el) throw new Error("date input not mounted yet");
    return el;
  });
  fireEvent.change(examStart, { target: { value: "15-06-2027" } });

  fireEvent.change(screen.getByTestId("cms-reason"), {
    target: { value: "adding a new exam cycle" },
  });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [, body] = api.post.mock.calls[0];
  expect(body.payload.exam_start).toBe("2027-06-15");
});
