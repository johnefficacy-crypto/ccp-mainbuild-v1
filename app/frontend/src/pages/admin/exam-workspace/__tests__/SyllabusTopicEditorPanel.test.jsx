import React from "react";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import ToastProvider from "../../../../shared/ui/ToastProvider";

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn(), del: jest.fn() },
  getApiErrorMessage: (e) => (e && e.message) || "error",
}));

let mockAuthUser = { role: "admin", permissions: ["exam_intelligence.manage"] };
jest.mock("../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: mockAuthUser }),
}));

const { api } = require("../../../../lib/api");
const SyllabusTopicEditorPanel = require("../syllabus-mapper/SyllabusTopicEditorPanel").default;
const { TOPIC_LEVELS } = require("../../studyos/editors/TopicEditorForm");

test("contract parity: shared TOPIC_LEVELS matches the backend _TOPIC_LEVELS", () => {
  // Mirrors admin_exam_intel_cms._TOPIC_LEVELS / admin_exam_intel_manage.
  expect(TOPIC_LEVELS).toEqual(["topic", "microtopic", "concept"]);
});

const SUBJECTS = { items: [{ id: "s1", name: "Quant" }, { id: "s2", name: "Reasoning" }], total: 2 };
const TOPICS = { items: [
  { id: "t1", subject_id: "s1", slug: "percentages", name: "Percentages", level: "topic" },
  { id: "t2", subject_id: "s1", slug: "ratios", name: "Ratios", level: "topic" },
], total: 2 };

function routeGet(url) {
  if (url.includes("/subjects")) return Promise.resolve(SUBJECTS);
  if (url.includes("/topics")) return Promise.resolve(TOPICS);
  if (url.includes("/topic-aliases")) return Promise.resolve({ items: [], total: 0 });
  return Promise.resolve({ items: [] });
}

function renderPanel() {
  return render(
    <ToastProvider>
      <SyllabusTopicEditorPanel examId="E1" />
    </ToastProvider>,
  );
}

beforeEach(() => {
  mockAuthUser = { role: "admin", permissions: ["exam_intelligence.manage"] };
  api.get.mockReset();
  api.post.mockReset();
  api.patch.mockReset();
  api.del.mockReset();
  api.get.mockImplementation(routeGet);
  api.post.mockResolvedValue({ ok: true });
  api.patch.mockResolvedValue({ ok: true });
  api.del.mockResolvedValue({ ok: true });
});

test("renders nothing without exam_intelligence.manage", () => {
  mockAuthUser = { role: "admin", permissions: [] };
  const { container } = renderPanel();
  expect(container.querySelector('[data-testid="syllabus-topic-editor"]')).toBeNull();
});

test("super_admin without token still sees the editor", async () => {
  mockAuthUser = { role: "super_admin", permissions: [] };
  renderPanel();
  expect(await screen.findByTestId("syllabus-topic-editor")).toBeInTheDocument();
});

test("review-only operator sees the panel + Prereqs but not manage controls", async () => {
  mockAuthUser = { role: "admin", permissions: ["exam_intelligence.review"] };
  renderPanel();
  expect(await screen.findByTestId("syllabus-topic-editor")).toBeInTheDocument();
  await screen.findByTestId("ste-topic-t1");
  expect(screen.getByTestId("ste-prereqs-t1")).toBeInTheDocument();
  // manage-only controls are absent for a review-only operator
  expect(screen.queryByTestId("ste-new-topic")).toBeNull();
  expect(screen.queryByTestId("ste-edit-t1")).toBeNull();
  expect(screen.queryByTestId("ste-delete-t1")).toBeNull();
});

test("Prereqs button opens the prerequisite editor", async () => {
  renderPanel();
  await screen.findByTestId("ste-topic-t1");
  fireEvent.click(screen.getByTestId("ste-prereqs-t1"));
  expect(await screen.findByTestId("tpe-editor")).toBeInTheDocument();
});

test("resolves subjects and lists topics for the first subject", async () => {
  renderPanel();
  await waitFor(() => expect(screen.getByTestId("ste-subject-select")).not.toBeDisabled());
  expect(await screen.findByTestId("ste-topic-t1")).toHaveTextContent("Percentages");
  const topicCall = api.get.mock.calls.find(([u]) => u.includes("/topics?"));
  expect(topicCall[0]).toContain("exam_id=E1");
  expect(topicCall[0]).toContain("subject_id=s1");
  expect(topicCall[0]).toContain("offset=0");
});

test("empty coverage shows empty-subjects state, no global fallback", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/subjects") ? Promise.resolve({ items: [], total: 0 }) : routeGet(url),
  );
  renderPanel();
  expect(await screen.findByTestId("ste-empty-subjects")).toBeInTheDocument();
  expect(api.get.mock.calls.some(([u]) => u.includes("/topics?"))).toBe(false);
});

test("scope error blocks writes and shows an alert", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/subjects") ? Promise.reject(new Error("boom")) : routeGet(url),
  );
  renderPanel();
  expect(await screen.findByTestId("ste-scope-error")).toBeInTheDocument();
  expect(screen.getByTestId("ste-new-topic")).toBeDisabled();
});

test("search sends q after debounce; level filter sends level", async () => {
  jest.useFakeTimers();
  try {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId("ste-search")).toBeInTheDocument());
    fireEvent.change(screen.getByTestId("ste-search"), { target: { value: "perc" } });
    act(() => { jest.advanceTimersByTime(350); });
    await waitFor(() => expect(api.get.mock.calls.some(([u]) => u.includes("q=perc"))).toBe(true));
    fireEvent.change(screen.getByTestId("ste-level-filter"), { target: { value: "microtopic" } });
    await waitFor(() => expect(api.get.mock.calls.some(([u]) => u.includes("level=microtopic"))).toBe(true));
  } finally {
    jest.useRealTimers();
  }
});

test("pagination: Next enabled when total exceeds page, advances offset; Prev resets", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("/subjects")) return Promise.resolve(SUBJECTS);
    if (url.includes("/topics")) return Promise.resolve({ items: TOPICS.items, total: 60 });
    return Promise.resolve({ items: [] });
  });
  renderPanel();
  await waitFor(() => expect(screen.getByTestId("ste-next")).not.toBeDisabled());
  expect(screen.getByTestId("ste-prev")).toBeDisabled();
  fireEvent.click(screen.getByTestId("ste-next"));
  await waitFor(() => expect(api.get.mock.calls.some(([u]) => u.includes("offset=50"))).toBe(true));
  expect(screen.getByTestId("ste-prev")).not.toBeDisabled();
});

test("creating a topic posts to the manage endpoint with a reason", async () => {
  renderPanel();
  await waitFor(() => expect(screen.getByTestId("ste-new-topic")).not.toBeDisabled());
  fireEvent.click(screen.getByTestId("ste-new-topic"));
  fireEvent.change(screen.getByTestId("ste-form-name"), { target: { value: "Profit" } });
  fireEvent.change(screen.getByTestId("ste-form-slug"), { target: { value: "profit" } });
  fireEvent.change(screen.getByTestId("ste-form-reason"), { target: { value: "add operational topic" } });
  fireEvent.click(screen.getByTestId("ste-form-save"));
  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [url, body] = api.post.mock.calls[0];
  expect(url).toContain("/admin/exam-intelligence-manage/topics?exam_id=E1");
  expect(body.reason).toBe("add operational topic");
  expect(body.payload.subject_id).toBe("s1");
});

test("short reason is rejected client-side (no POST)", async () => {
  renderPanel();
  await waitFor(() => expect(screen.getByTestId("ste-new-topic")).not.toBeDisabled());
  fireEvent.click(screen.getByTestId("ste-new-topic"));
  fireEvent.change(screen.getByTestId("ste-form-name"), { target: { value: "X" } });
  fireEvent.change(screen.getByTestId("ste-form-slug"), { target: { value: "x" } });
  fireEvent.change(screen.getByTestId("ste-form-reason"), { target: { value: "short" } });
  fireEvent.click(screen.getByTestId("ste-form-save"));
  await waitFor(() => expect(screen.getByTestId("ste-form")).toBeInTheDocument());
  expect(api.post).not.toHaveBeenCalled();
});

test("a failed topic fetch blocks writes (no silent empty state)", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("/subjects")) return Promise.resolve(SUBJECTS);
    if (url.includes("/topics")) return Promise.reject(new Error("500"));
    return Promise.resolve({ items: [] });
  });
  renderPanel();
  await waitFor(() => expect(screen.getByTestId("ste-subject-select")).not.toBeDisabled());
  await waitFor(() => expect(screen.getByTestId("ste-new-topic")).toBeDisabled());
});

test("switching Edit targets does not carry stale field values", async () => {
  renderPanel();
  await screen.findByTestId("ste-topic-t1");
  fireEvent.click(screen.getByTestId("ste-edit-t1"));
  expect(screen.getByTestId("ste-form-name")).toHaveValue("Percentages");
  // Cancel then edit a different topic; the form must show t2's values, not t1's.
  fireEvent.click(screen.getByTestId("ste-edit-t2"));
  await waitFor(() => expect(screen.getByTestId("ste-form-name")).toHaveValue("Ratios"));
});

test("mutations run through useApiAction (busy state disables save)", async () => {
  let resolvePost;
  api.post.mockImplementation(() => new Promise((res) => { resolvePost = res; }));
  renderPanel();
  await waitFor(() => expect(screen.getByTestId("ste-new-topic")).not.toBeDisabled());
  fireEvent.click(screen.getByTestId("ste-new-topic"));
  fireEvent.change(screen.getByTestId("ste-form-name"), { target: { value: "Profit" } });
  fireEvent.change(screen.getByTestId("ste-form-slug"), { target: { value: "profit" } });
  fireEvent.change(screen.getByTestId("ste-form-reason"), { target: { value: "add operational topic" } });
  fireEvent.click(screen.getByTestId("ste-form-save"));
  await waitFor(() => expect(screen.getByTestId("ste-form-save")).toBeDisabled());
  expect(screen.getByTestId("ste-form-save")).toHaveTextContent("Saving…");
  await act(async () => { resolvePost({ ok: true }); });
});
