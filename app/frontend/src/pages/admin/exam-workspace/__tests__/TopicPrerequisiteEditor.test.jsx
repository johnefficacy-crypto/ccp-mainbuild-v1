import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import ToastProvider from "../../../../shared/ui/ToastProvider";

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn(), del: jest.fn() },
  getApiErrorMessage: (e) => (e && e.message) || "error",
}));

const { api } = require("../../../../lib/api");
const TopicPrerequisiteEditor = require("../syllabus-mapper/TopicPrerequisiteEditor").default;

const TOPIC = { id: "t2", name: "Ratios" };
const CANDIDATES = [
  { id: "t1", name: "Percentages" },
  { id: "t2", name: "Ratios" },
  { id: "t3", name: "Interest" },
];

function edges(list) {
  return { items: list, total: list.length };
}

function renderEditor(props) {
  return render(
    <ToastProvider>
      <TopicPrerequisiteEditor examId="E1" topic={TOPIC} candidateTopics={CANDIDATES} {...props} />
    </ToastProvider>,
  );
}

const CANDIDATE_RESULT = {
  items: [{ id: "t1", subject_id: "s1", name: "Percentages" }, { id: "t3", subject_id: "s2", name: "Interest" }],
  total: 2,
};

function routeGet(url) {
  if (url.includes("/candidate-topics")) return Promise.resolve(CANDIDATE_RESULT);
  return Promise.resolve(edges([]));
}

beforeEach(() => {
  api.get.mockReset(); api.post.mockReset(); api.del.mockReset(); api.patch.mockReset();
  api.get.mockImplementation(routeGet);
  api.post.mockResolvedValue({ ok: true });
  api.del.mockResolvedValue({ ok: true });
  api.patch.mockResolvedValue({ ok: true });
});

test("manage can add a prerequisite (posts draft with reason)", async () => {
  renderEditor({ canManage: true, canReview: false });
  await waitFor(() => expect(screen.getByTestId("tpe-add-toggle")).toBeInTheDocument());
  fireEvent.click(screen.getByTestId("tpe-add-toggle"));
  // Candidate options are fetched across all exam subjects.
  await waitFor(() => expect(screen.getByTestId("tpe-prereq-select").querySelectorAll("option").length).toBeGreaterThan(1));
  fireEvent.change(screen.getByTestId("tpe-prereq-select"), { target: { value: "t1" } });
  fireEvent.change(screen.getByTestId("tpe-reason"), { target: { value: "t2 needs t1 first" } });
  fireEvent.click(screen.getByTestId("tpe-add-save"));
  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [url, body] = api.post.mock.calls[0];
  expect(url).toContain("/topic-prerequisites?exam_id=E1");
  expect(body.payload).toMatchObject({ topic_id: "t2", prerequisite_topic_id: "t1", relation_type: "requires" });
  expect(body.reason).toBe("t2 needs t1 first");
});

test("draft edge shows manage Submit/Delete; no review controls for a manager", async () => {
  api.get.mockResolvedValue(edges([
    { id: "e1", topic_id: "t2", prerequisite_topic_id: "t1", relation_type: "requires", strength: 1.0, reviewer_status: "draft" },
  ]));
  renderEditor({ canManage: true, canReview: false });
  expect(await screen.findByTestId("tpe-edge-e1")).toBeInTheDocument();
  expect(screen.getByTestId("tpe-submit-e1")).toBeInTheDocument();
  expect(screen.getByTestId("tpe-delete-e1")).toBeInTheDocument();
  expect(screen.queryByTestId("tpe-approve-e1")).toBeNull();
});

test("review sees Approve/Reject on pending_review and no manage add", async () => {
  api.get.mockResolvedValue(edges([
    { id: "e1", topic_id: "t2", prerequisite_topic_id: "t1", relation_type: "requires", strength: 1.0, reviewer_status: "pending_review" },
  ]));
  renderEditor({ canManage: false, canReview: true });
  expect(await screen.findByTestId("tpe-approve-e1")).toBeInTheDocument();
  expect(screen.getByTestId("tpe-reject-e1")).toBeInTheDocument();
  expect(screen.queryByTestId("tpe-add-toggle")).toBeNull();
  fireEvent.click(screen.getByTestId("tpe-approve-e1"));
  await waitFor(() => expect(api.post).toHaveBeenCalled());
  expect(api.post.mock.calls[0][0]).toContain("/review?exam_id=E1");
  expect(api.post.mock.calls[0][1].target_status).toBe("reviewed");
});

test("locked edge offers Reopen to reviewer (prompts for notes)", async () => {
  api.get.mockResolvedValue(edges([
    { id: "e1", topic_id: "t2", prerequisite_topic_id: "t1", relation_type: "requires", strength: 1.0, reviewer_status: "locked" },
  ]));
  const promptSpy = jest.spyOn(window, "prompt").mockReturnValue("needs a fix");
  try {
    renderEditor({ canManage: true, canReview: true });
    fireEvent.click(await screen.findByTestId("tpe-reopen-e1"));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(api.post.mock.calls[0][1]).toMatchObject({ target_status: "reviewed", review_notes: "needs a fix" });
  } finally {
    promptSpy.mockRestore();
  }
});

test("manage can edit an editable edge (PATCH relation/strength)", async () => {
  api.get.mockResolvedValue(edges([
    { id: "e1", topic_id: "t2", prerequisite_topic_id: "t1", relation_type: "requires", strength: 1.0, reviewer_status: "draft" },
  ]));
  api.patch.mockResolvedValue({ ok: true });
  renderEditor({ canManage: true, canReview: false });
  fireEvent.click(await screen.findByTestId("tpe-edit-e1"));
  fireEvent.change(screen.getByTestId("tpe-edit-relation"), { target: { value: "recommended_before" } });
  fireEvent.change(screen.getByTestId("tpe-edit-reason"), { target: { value: "soften the edge" } });
  fireEvent.click(screen.getByTestId("tpe-edit-save"));
  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [url, body] = api.patch.mock.calls[0];
  expect(url).toContain("/topic-prerequisites/e1?exam_id=E1");
  expect(body.payload).toMatchObject({ relation_type: "recommended_before" });
});

test("incoming edge is shown with a dependent marker", async () => {
  api.get.mockResolvedValue(edges([
    { id: "e2", topic_id: "t3", prerequisite_topic_id: "t2", relation_type: "requires", strength: 1.0, reviewer_status: "locked" },
  ]));
  renderEditor({ canManage: true, canReview: false });
  const row = await screen.findByTestId("tpe-edge-e2");
  expect(row).toHaveTextContent("dependent");
});

test("candidate picker fetches across subjects and search sends q", async () => {
  renderEditor({ canManage: true, canReview: false });
  fireEvent.click(await screen.findByTestId("tpe-add-toggle"));
  await waitFor(() => expect(api.get.mock.calls.some(([u]) => u.includes("/candidate-topics"))).toBe(true));
  fireEvent.change(screen.getByTestId("tpe-cand-search"), { target: { value: "inter" } });
  await waitFor(() => expect(api.get.mock.calls.some(([u]) => u.includes("/candidate-topics") && u.includes("q=inter"))).toBe(true));
});

test("edge list Next advances the offset", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("/candidate-topics")) return Promise.resolve(CANDIDATE_RESULT);
    return Promise.resolve({ items: [
      { id: "e1", topic_id: "t2", prerequisite_topic_id: "t1", relation_type: "requires", strength: 1.0, reviewer_status: "locked" },
    ], total: 60 });
  });
  renderEditor({ canManage: true, canReview: false });
  await waitFor(() => expect(screen.getByTestId("tpe-next")).not.toBeDisabled());
  expect(screen.getByTestId("tpe-prev")).toBeDisabled();
  fireEvent.click(screen.getByTestId("tpe-next"));
  await waitFor(() => expect(api.get.mock.calls.some(([u]) => u.includes("/topic-prerequisites") && u.includes("offset=50"))).toBe(true));
});

test("a failed load shows an error and blocks adding", async () => {
  api.get.mockRejectedValue(new Error("500"));
  renderEditor({ canManage: true, canReview: false });
  expect(await screen.findByTestId("tpe-error")).toBeInTheDocument();
  expect(screen.getByTestId("tpe-add-toggle")).toBeDisabled();
});
