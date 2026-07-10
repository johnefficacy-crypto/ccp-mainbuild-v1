import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

jest.mock("react-router-dom", () => ({ useNavigate: () => jest.fn() }));
jest.mock("../../lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() } }));
const { api } = require("../../lib/api");
const PyqExplorerSection = require("./PyqExplorerSection").default;

const SUMMARY = {
  exam_id: "e1",
  verified_only: true,
  totals: { papers: 2, questions: 3, projected_practice_ready: 2 },
  by_year: [
    { year: 2024, questions: 2, papers: 1 },
    { year: 2023, questions: 1, papers: 1 },
  ],
  by_phase: [{ phase_slug: "prelims", phase_name: "Prelims", questions: 3 }],
  by_subject: [{ subject_id: "s1", subject_name: "General Studies", questions: 3 }],
  by_difficulty: [
    { difficulty: "medium", questions: 2 },
    { difficulty: "hard", questions: 1 },
  ],
  papers: [
    { paper_id: "p1", year: 2024, phase_slug: "prelims", phase_name: "Prelims", subject_id: "s1", subject_name: "General Studies", question_count: 2, practice_ready_count: 2, practice_enabled: true },
    { paper_id: "p2", year: 2023, phase_slug: "prelims", phase_name: "Prelims", subject_id: "s1", subject_name: "General Studies", question_count: 1, practice_ready_count: 0, practice_enabled: false },
  ],
};

const LIST = {
  exam_id: "e1",
  total: 1,
  items: [
    {
      id: "q1",
      paper_id: "p1",
      paper_year: 2024,
      phase_name: "Prelims",
      subject_id: "s1",
      subject_name: "General Studies",
      difficulty: "medium",
      question_number: 1,
      question_text: "Q1",
      options: [],
      topic_tags: [{ topic_id: "t1" }],
      topic_names: ["Polity"],
    },
  ],
};

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.get.mockImplementation((url) => {
    if (url.includes("/pyq-summary")) return Promise.resolve(SUMMARY);
    if (url.includes("/pyqs")) return Promise.resolve(LIST);
    return Promise.resolve({});
  });
});

test("defaults to the intelligence overview + paper practice cards, not a raw question feed", async () => {
  render(<PyqExplorerSection examSlug="upsc-cse" examName="UPSC CSE" />);
  expect(await screen.findByTestId("pyq-summary-charts")).toBeTruthy();
  expect(screen.getByTestId("pyq-paper-cards")).toBeTruthy();
  // Browse is collapsed by default — no 20-question feed up front.
  expect(screen.queryByTestId("pyq-question-card")).toBeNull();
  // Distribution blocks are present.
  expect(screen.getByTestId("summary-by-year")).toBeTruthy();
  expect(screen.getByTestId("summary-by-phase")).toBeTruthy();
  expect(screen.getByTestId("summary-by-subject")).toBeTruthy();
  expect(screen.getByTestId("summary-by-difficulty")).toBeTruthy();
});

test("shows one paper card per paper and offers practice only for practice-ready papers", async () => {
  render(<PyqExplorerSection examSlug="upsc-cse" examName="UPSC CSE" />);
  await screen.findByTestId("pyq-paper-cards");
  expect(screen.getAllByTestId("pyq-paper-card")).toHaveLength(2);
  // p1 is practice_enabled → one Practice button; p2 is not → a not-ready notice.
  expect(screen.getAllByTestId("pyq-paper-practice-btn")).toHaveLength(1);
  expect(screen.getByTestId("pyq-paper-not-ready")).toBeTruthy();
});

test("browse is opt-in: initial render hits /pyq-summary but never /pyqs until Browse opens", async () => {
  render(<PyqExplorerSection examSlug="upsc-cse" examName="UPSC CSE" />);
  await screen.findByTestId("pyq-summary-charts");
  // The hub default must not fetch the raw question feed for any reason
  // (topic options included) before the learner opens Browse.
  const urls = () => api.get.mock.calls.map((c) => c[0]);
  expect(urls().some((u) => u.includes("/pyq-summary"))).toBe(true);
  expect(urls().some((u) => u.includes("/pyqs"))).toBe(false);

  fireEvent.click(screen.getByTestId("pyq-browse-toggle"));
  await screen.findByTestId("pyq-browse");
  expect(api.get.mock.calls.some((c) => c[0].includes("/pyqs"))).toBe(true);
});

test("learner filters are Year/Phase/Subject/Topic/Difficulty — Source/Trust is gone", async () => {
  render(<PyqExplorerSection examSlug="upsc-cse" examName="UPSC CSE" />);
  await screen.findByTestId("pyq-summary-charts");
  expect(screen.queryByText("Source / Trust")).toBeNull();

  fireEvent.click(screen.getByTestId("pyq-browse-toggle"));
  await screen.findByTestId("pyq-browse");
  ["Year", "Phase", "Subject", "Topic", "Difficulty"].forEach((label) => {
    expect(screen.getByText(label)).toBeTruthy();
  });
  expect(screen.queryByText("Source / Trust")).toBeNull();
});
