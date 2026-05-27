import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  getApiErrorMessage: (e) => String(e),
}));

// eslint-disable-next-line global-require
const { api } = require("../../../lib/api");
// eslint-disable-next-line global-require
const AdminExamIntelCms = require("./ExamIntelCms").default;

const EXAMS = [{ id: "e1", name: "SSC CGL", slug: "ssc-cgl" }];
const PAPERS = [{ id: "p1", paper_code: "CGL-2024-T1", year: 2024 }];
const QUESTIONS = [{ id: "q1", question_text: "What is 10% of 200?", question_number: 1 }];
const SUBJECTS = [{ id: "s1", name: "Quant", slug: "quant" }];
const TOPICS = [{ id: "t1", name: "Percentages", level: "topic", slug: "pct" }];

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AdminExamIntelCms />
    </QueryClientProvider>,
  );
}

async function pickRef(fieldKey, optionId) {
  fireEvent.focus(screen.getByTestId(`cms-field-${fieldKey}`));
  fireEvent.mouseDown(await screen.findByTestId(`cms-field-${fieldKey}-option-${optionId}`));
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.post.mockResolvedValue({ ok: true, audit_id: "a1", row: { id: "tag1" } });
  api.get.mockImplementation((url) => {
    // Specific-first so /pyq-question-topic-tags and /pyq-questions don't collide.
    if (url.includes("/pyq-question-topic-tags")) return Promise.resolve({ items: [], total: 0 });
    if (url.includes("/pyq-questions")) return Promise.resolve({ items: QUESTIONS, total: 1 });
    if (url.includes("/pyq-papers")) return Promise.resolve({ items: PAPERS, total: 1 });
    if (url.includes("/exams")) return Promise.resolve({ items: EXAMS, total: 1 });
    if (url.includes("/subjects")) return Promise.resolve({ items: SUBJECTS, total: 1 });
    if (url.includes("/topics")) return Promise.resolve({ items: TOPICS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
});

function openTags() {
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "pyq-question-topic-tags" } });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));
}


test("shows trust notice and tag_role dropdown", async () => {
  renderPage();
  openTags();
  const notice = await screen.findByTestId("cms-create-notice");
  expect(notice.textContent).toMatch(/pending/i);
  const role = screen.getByTestId("cms-field-tag_role");
  expect(role.tagName).toBe("SELECT");
  const opts = Array.from(role.querySelectorAll("option")).map((o) => o.value);
  expect(opts).toEqual(expect.arrayContaining(["primary", "secondary", "trap", "calculation_layer"]));
});


test("cascade: choosing exam → paper refetches papers, then question list filters by paper", async () => {
  renderPage();
  openTags();

  await pickRef("exam_id", "e1");
  await waitFor(() => expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/pyq-papers?")));
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("exam_id=e1"));

  await pickRef("pyq_paper_id", "p1");
  await waitFor(() => expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/pyq-questions?")));
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("pyq_paper_id=p1"));
});


test("submits question_id + topic_id and never the ui-only scope fields or reviewer_status", async () => {
  renderPage();
  openTags();

  await pickRef("exam_id", "e1");
  await pickRef("pyq_paper_id", "p1");
  await pickRef("question_id", "q1");
  await pickRef("subject_id", "s1");
  await pickRef("topic_id", "t1");
  fireEvent.change(screen.getByTestId("cms-reason"), { target: { value: "tagging q1 to percentages" } });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    expect.stringContaining("/pyq-question-topic-tags"),
    expect.anything(),
  ));
  const [, body] = api.post.mock.calls.find(([u]) => u.endsWith("/pyq-question-topic-tags"));
  expect(body.payload.question_id).toBe("q1");
  expect(body.payload.topic_id).toBe("t1");
  for (const k of ["exam_id", "pyq_paper_id", "subject_id", "reviewer_status"]) {
    expect(k in body.payload).toBe(false);
  }
});
