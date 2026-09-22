/**
 * The answer structure beside a submitted answer.
 *
 * Pins: no affordance before submit (the server refuses too); an honest "no
 * structure yet"; ticks save to the attempt and roll back on failure; the same
 * panel works beside a handwritten attempt's pages; My answers and Progress
 * show points covered only when there is something to show.
 */
import React from "react";
import { fireEvent, render, screen, waitFor, act } from "@testing-library/react";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPatch = jest.fn();
const mockPut = jest.fn();

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...a) => mockGet(...a),
    post: (...a) => mockPost(...a),
    patch: (...a) => mockPatch(...a),
    put: (...a) => mockPut(...a),
    del: jest.fn(),
  },
}));

// eslint-disable-next-line import/first
import AnswerStructurePanel from "../AnswerStructurePanel";
// eslint-disable-next-line import/first
import QuestionScreen from "../QuestionScreen";
// eslint-disable-next-line import/first
import { AttemptDetail, attemptMeta } from "../MyAnswers";

const STRUCTURE = {
  id: "s-1",
  version: 2,
  directive: "Critically examine",
  demand: "Weigh both sides of the Governor's role.",
  intro_angles: ["Define the office."],
  body_points: [
    { id: "p1", point: "Constitutional position", why: "Textual basis first.", evidence_type: "Articles", example: null, thinker: null, sub_points: [] },
    { id: "p2", point: "Friction points", why: null, evidence_type: "Recent judgments", example: null, thinker: null, sub_points: ["Assent delays"] },
    { id: "p3", point: "Reforms", why: null, evidence_type: null, example: null, thinker: null, sub_points: [] },
    { id: "p4", point: "Commission recommendations", why: null, evidence_type: null, example: null, thinker: null, sub_points: [] },
  ],
  dimensions: ["Federal"],
  examples: [],
  conclusion_angles: ["Balanced verdict."],
  pitfalls: ["Only criticism."],
  word_budget: { total: 250, intro: 40, body: 170, conclusion: 40, basis: "word_limit" },
  sources_note: null,
};

beforeEach(() => {
  mockGet.mockReset();
  mockPost.mockReset();
  mockPatch.mockReset();
  mockPut.mockReset();
});

function wireStructure(over = {}) {
  mockGet.mockImplementation((url) => {
    if (url.endsWith("/structure")) {
      return Promise.resolve({
        attempt_id: "att-1",
        structure: STRUCTURE,
        covered_point_ids: [],
        points_covered_pct: null,
        ticks_from_older_version: false,
        ...over,
      });
    }
    return Promise.resolve({ items: [] });
  });
}

test("renders demand, directive, budget, checklist, angles and pitfalls", async () => {
  wireStructure();
  render(<AnswerStructurePanel attemptId="att-1" />);
  await screen.findByTestId("answer-structure-panel");
  expect(screen.getByTestId("answer-structure-directive")).toHaveTextContent("Critically examine");
  expect(screen.getByTestId("answer-structure-directive")).toHaveTextContent("Weigh both sides");
  expect(screen.getByTestId("answer-structure-budget")).toHaveTextContent("about 250 words");
  expect(screen.getByTestId("answer-structure-intro")).toHaveTextContent("Define the office.");
  expect(screen.getByTestId("answer-structure-conclusion")).toHaveTextContent("Balanced verdict.");
  expect(screen.getByTestId("answer-structure-pitfalls")).toHaveTextContent("Only criticism.");
  expect(screen.getAllByRole("checkbox")).toHaveLength(4);
  expect(screen.getByTestId("answer-structure-covered")).toHaveTextContent("0 of 4 points covered");
});

test("says so plainly when there is no verified structure", async () => {
  wireStructure({ structure: null });
  render(<AnswerStructurePanel attemptId="att-1" />);
  expect(await screen.findByTestId("answer-structure-none")).toHaveTextContent(
    "doesn't have a reviewed answer structure yet",
  );
  expect(screen.queryByRole("checkbox")).toBeNull();
});

test("a tick is saved on the attempt against the structure version", async () => {
  wireStructure();
  mockPut.mockResolvedValue({ covered_point_ids: ["p2"], points_covered_pct: 25 });
  render(<AnswerStructurePanel attemptId="att-1" />);
  fireEvent.click(await screen.findByTestId("answer-structure-tick-p2"));
  await waitFor(() =>
    expect(mockPut).toHaveBeenCalledWith("/api/study/descriptive/attempts/att-1/coverage", {
      structure_version: 2,
      covered_point_ids: ["p2"],
    }),
  );
  await waitFor(() =>
    expect(screen.getByTestId("answer-structure-covered")).toHaveTextContent("1 of 4 points covered (25%)"),
  );
  expect(screen.getByTestId("answer-structure-tick-p2")).toBeChecked();
});

test("previously saved ticks come back checked", async () => {
  wireStructure({ covered_point_ids: ["p1", "p3"] });
  render(<AnswerStructurePanel attemptId="att-1" />);
  expect(await screen.findByTestId("answer-structure-tick-p1")).toBeChecked();
  expect(screen.getByTestId("answer-structure-tick-p3")).toBeChecked();
  expect(screen.getByTestId("answer-structure-tick-p2")).not.toBeChecked();
  expect(screen.getByTestId("answer-structure-covered")).toHaveTextContent("2 of 4 points covered (50%)");
});

test("a failed save rolls the tick back and says so", async () => {
  wireStructure();
  mockPut.mockRejectedValue({ status: 503 });
  render(<AnswerStructurePanel attemptId="att-1" />);
  fireEvent.click(await screen.findByTestId("answer-structure-tick-p1"));
  expect(await screen.findByTestId("answer-structure-save-error")).toHaveTextContent("Couldn't save");
  expect(screen.getByTestId("answer-structure-tick-p1")).not.toBeChecked();
});

// ── QuestionScreen: hidden before submit ────────────────────────────────────

const QUESTION = { id: "q-1", text: "Examine the Governor's role.", breadcrumb: { trail: [] } };

test("no compare affordance while the answer is still a draft", async () => {
  mockPost.mockResolvedValue({ id: "att-1", pyq_question_id: "q-1", status: "draft", answer_text: "", answer_mode: "typed" });
  mockGet.mockResolvedValue({ items: [] });
  render(<QuestionScreen question={QUESTION} />);
  await screen.findByTestId("descriptive-question-screen");
  expect(screen.queryByTestId("descriptive-compare-structure")).toBeNull();
  expect(screen.queryByTestId("answer-structure-panel")).toBeNull();
  expect(mockGet.mock.calls.some(([u]) => String(u).endsWith("/structure"))).toBe(false);
});

test("after submit, the structure opens beside the answer", async () => {
  mockPost.mockResolvedValue({
    id: "att-1", pyq_question_id: "q-1", status: "submitted", answer_text: "My answer",
    answer_mode: "typed", word_count: 2, self_total: 8,
  });
  wireStructure();
  render(<QuestionScreen question={QUESTION} />);
  const btn = await screen.findByTestId("descriptive-compare-structure");
  await act(async () => { fireEvent.click(btn); });
  expect(await screen.findByTestId("answer-structure-panel")).toBeInTheDocument();
  expect(screen.getByTestId("descriptive-answer-area").className).toContain("lg:grid-cols-2");
});

// ── My answers: handwritten attempts too ────────────────────────────────────

test("a handwritten attempt's pages sit beside the structure in My answers", async () => {
  mockGet.mockImplementation((url) => {
    if (url.endsWith("/structure")) {
      return Promise.resolve({ attempt_id: "att-9", structure: STRUCTURE, covered_point_ids: ["p1"] });
    }
    return Promise.resolve({
      attempt: { id: "att-9", status: "submitted", answer_mode: "handwritten", answer_text: "" },
      pages: [{ id: "pg-1", page_no: 1, url: "https://storage.test/p1.jpg", mime_type: "image/jpeg" }],
      page_count: 1,
      url_ttl_seconds: 900,
      can_rewrite: true,
    });
  });
  mockPut.mockResolvedValue({ covered_point_ids: ["p1", "p4"] });
  render(<AttemptDetail attemptId="att-9" questionId="q-1" />);
  fireEvent.click(await screen.findByTestId("my-answers-compare-structure"));
  expect(await screen.findByTestId("answer-structure-panel")).toBeInTheDocument();
  expect(screen.getByTestId("answer-structure-tick-p1")).toBeChecked();
  fireEvent.click(screen.getByTestId("answer-structure-tick-p4"));
  await waitFor(() =>
    expect(mockPut).toHaveBeenCalledWith("/api/study/descriptive/attempts/att-9/coverage", {
      structure_version: 2,
      covered_point_ids: ["p1", "p4"],
    }),
  );
});

test("a draft in My answers offers no structure", async () => {
  mockGet.mockResolvedValue({
    attempt: { id: "att-3", status: "draft", answer_mode: "typed", answer_text: "wip" },
    pages: [],
    can_rewrite: true,
  });
  render(<AttemptDetail attemptId="att-3" questionId="q-1" />);
  await screen.findByTestId("my-answers-detail-text");
  expect(screen.queryByTestId("my-answers-compare-structure")).toBeNull();
});

test("the history row shows points covered only once ticked", () => {
  expect(attemptMeta({ answer_mode: "typed", word_count: 200, points_covered_pct: 60 })).toContain(
    "60% points covered",
  );
  expect(attemptMeta({ answer_mode: "typed", word_count: 200, points_covered_pct: null }).join(" ")).not.toContain(
    "points covered",
  );
});
