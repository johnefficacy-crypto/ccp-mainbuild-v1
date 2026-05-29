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
const DOCS = [{ id: "doc1", title: "SSC CGL Syllabus", document_type: "syllabus_pdf" }];
const TOPICS = [{ id: "t1", name: "Percentages", level: "topic", slug: "percentages" }];

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
  api.post.mockResolvedValue({ ok: true, audit_id: "a1", row: { id: "m1" } });
  api.get.mockImplementation((url) => {
    if (url.includes("/syllabus-documents")) return Promise.resolve({ items: DOCS, total: 1 });
    if (url.includes("/syllabus-topic-mentions")) return Promise.resolve({ items: [], total: 0 });
    if (url.includes("/exams")) return Promise.resolve({ items: EXAMS, total: 1 });
    if (url.includes("/subjects")) return Promise.resolve({ items: [{ id: "s1", name: "Quant", slug: "quant" }], total: 1 });
    if (url.includes("/topics")) return Promise.resolve({ items: TOPICS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
});


test("create form shows the trust notice and a mention_type dropdown", async () => {
  renderPage();
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "syllabus-topic-mentions" } });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  const notice = await screen.findByTestId("cms-create-notice");
  expect(notice.textContent).toMatch(/pending/i);
  expect(notice.textContent).toMatch(/review/i);

  const mt = screen.getByTestId("cms-field-mention_type");
  expect(mt.tagName).toBe("SELECT");
  const opts = Array.from(mt.querySelectorAll("option")).map((o) => o.value);
  expect(opts).toEqual(expect.arrayContaining(["explicit", "implied", "parent_topic_only", "derived"]));
});


test("submits the selected document + topic ids and never sends reviewer_status", async () => {
  renderPage();
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "syllabus-topic-mentions" } });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  await pickRef("exam_id", "e1");
  await pickRef("syllabus_document_id", "doc1");
  await pickRef("topic_id", "t1");
  fireEvent.change(screen.getByTestId("cms-field-raw_text"), { target: { value: "Percentages" } });
  fireEvent.change(screen.getByTestId("cms-reason"), { target: { value: "seeding a syllabus mention" } });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    expect.stringContaining("/syllabus-topic-mentions"),
    expect.anything(),
  ));
  const [, body] = api.post.mock.calls.find(([u]) => u.endsWith("/syllabus-topic-mentions"));
  expect(body.payload.syllabus_document_id).toBe("doc1");
  expect(body.payload.exam_id).toBe("e1");
  expect(body.payload.topic_id).toBe("t1");
  // Status is the backend's job (forced pending); the form never sends it.
  expect("reviewer_status" in body.payload).toBe(false);
  // The ui-only subject scope picker is not submitted either.
  expect("subject_id" in body.payload).toBe(false);
});


test("document picker is scoped to the chosen exam", async () => {
  renderPage();
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "syllabus-topic-mentions" } });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  await pickRef("exam_id", "e1");
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/syllabus-documents?")),
  );
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("exam_id=e1"));
});
