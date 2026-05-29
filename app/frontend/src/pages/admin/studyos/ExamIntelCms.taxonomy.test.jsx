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

const SUBJECTS = [{ id: "s1", slug: "quant", name: "Quantitative Aptitude" }];
const TOPICS = [{ id: "tp1", slug: "algebra", name: "Algebra", level: "topic", subject_id: "s1" }];

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AdminExamIntelCms />
    </QueryClientProvider>,
  );
}

function selectEntity(value) {
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value } });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));
}

async function pickRef(fieldKey, optionId) {
  fireEvent.focus(screen.getByTestId(`cms-field-${fieldKey}`));
  const opt = await screen.findByTestId(`cms-field-${fieldKey}-option-${optionId}`);
  fireEvent.mouseDown(opt);
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
});


test("1. subject create → list refresh shows the new row", async () => {
  const store = [];
  api.get.mockImplementation((url) => {
    if (url.includes("/subjects")) return Promise.resolve({ items: store, total: store.length });
    return Promise.resolve({ items: [], total: 0 });
  });
  api.post.mockImplementation((url, body) => {
    if (url.endsWith("/subjects")) {
      store.push({ id: "subj-1", ...body.payload });
      return Promise.resolve({ ok: true, audit_id: "a1", row: store[store.length - 1] });
    }
    return Promise.resolve({ ok: true, audit_id: "a1" });
  });

  renderPage();
  selectEntity("subjects");
  fireEvent.change(await screen.findByTestId("cms-field-slug"), { target: { value: "english" } });
  fireEvent.change(screen.getByTestId("cms-field-name"), { target: { value: "English" } });
  fireEvent.change(screen.getByTestId("cms-reason"), { target: { value: "seeding english subject" } });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  // After create the list reloads and the new slug shows in the table.
  expect(await screen.findByText("english")).toBeTruthy();
});


test("2. topic create under subject + parent submits both ids", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("/topic-aliases") || url.includes("/topic-prerequisites")) return Promise.resolve({ items: [], total: 0 });
    if (url.includes("/subjects")) return Promise.resolve({ items: SUBJECTS, total: 1 });
    if (url.includes("/topics")) return Promise.resolve({ items: TOPICS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
  api.post.mockResolvedValue({ ok: true, audit_id: "a1", row: { id: "new" } });

  renderPage();
  selectEntity("topics");
  await pickRef("subject_id", "s1");
  await pickRef("parent_topic_id", "tp1");
  fireEvent.change(screen.getByTestId("cms-field-slug"), { target: { value: "linear-equations" } });
  fireEvent.change(screen.getByTestId("cms-field-name"), { target: { value: "Linear Equations" } });
  fireEvent.change(screen.getByTestId("cms-reason"), { target: { value: "topic under algebra" } });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    expect.stringContaining("/topics"),
    expect.anything(),
  ));
  const [, body] = api.post.mock.calls.find(([u]) => u.endsWith("/topics"));
  expect(body.payload.subject_id).toBe("s1");
  expect(body.payload.parent_topic_id).toBe("tp1");
});


test("3. microtopic without a parent is blocked with a validation message", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("/topic-aliases") || url.includes("/topic-prerequisites")) return Promise.resolve({ items: [], total: 0 });
    if (url.includes("/subjects")) return Promise.resolve({ items: SUBJECTS, total: 1 });
    if (url.includes("/topics")) return Promise.resolve({ items: TOPICS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
  api.post.mockResolvedValue({ ok: true, audit_id: "a1" });

  renderPage();
  selectEntity("topics");
  await pickRef("subject_id", "s1");
  fireEvent.change(screen.getByTestId("cms-field-level"), { target: { value: "microtopic" } });
  fireEvent.change(screen.getByTestId("cms-field-slug"), { target: { value: "simple-interest" } });
  fireEvent.change(screen.getByTestId("cms-field-name"), { target: { value: "Simple Interest" } });
  fireEvent.change(screen.getByTestId("cms-reason"), { target: { value: "orphan microtopic attempt" } });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  expect(await screen.findByText(/must have a parent topic/i)).toBeTruthy();
  // No create POST was issued.
  expect(api.post.mock.calls.some(([u]) => u.endsWith("/topics"))).toBe(false);
});


test("4. alias create attaches to the selected topic and omits the scope field", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("/topic-aliases")) return Promise.resolve({ items: [], total: 0 });
    if (url.includes("/subjects")) return Promise.resolve({ items: SUBJECTS, total: 1 });
    if (url.includes("/topics")) return Promise.resolve({ items: TOPICS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
  api.post.mockResolvedValue({ ok: true, audit_id: "a1", row: { id: "al-1" } });

  renderPage();
  selectEntity("topic-aliases");
  await pickRef("topic_id", "tp1");
  fireEvent.change(screen.getByTestId("cms-field-alias"), { target: { value: "Algebra (alt)" } });
  fireEvent.change(screen.getByTestId("cms-reason"), { target: { value: "adding an alias row" } });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    expect.stringContaining("/topic-aliases"),
    expect.anything(),
  ));
  const [, body] = api.post.mock.calls.find(([u]) => u.endsWith("/topic-aliases"));
  expect(body.payload.topic_id).toBe("tp1");
  expect(body.payload.alias).toBe("Algebra (alt)");
  // The uiOnly subject_id scope picker must never be submitted.
  expect("subject_id" in body.payload).toBe(false);
});


test("5. prerequisite topic pickers refetch scoped to the chosen subject", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("/topic-prerequisites")) return Promise.resolve({ items: [], total: 0 });
    if (url.includes("/subjects")) return Promise.resolve({ items: SUBJECTS, total: 1 });
    if (url.includes("/topics")) return Promise.resolve({ items: TOPICS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });

  renderPage();
  selectEntity("topic-prerequisites");
  await pickRef("subject_id", "s1");

  // Both topic pickers refetch their list filtered to the chosen subject.
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/topics?")),
  );
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("subject_id=s1"));
});
