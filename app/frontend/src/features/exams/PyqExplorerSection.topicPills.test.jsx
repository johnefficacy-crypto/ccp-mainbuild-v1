import React from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import ToastProvider from "../../shared/ui/ToastProvider";

jest.mock("react-router-dom", () => ({ useNavigate: () => jest.fn() }));
jest.mock("../../lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() } }));
const { api } = require("../../lib/api");
const PyqExplorerSection = require("./PyqExplorerSection").default;

const PAPER_ID = "44444444-4444-4444-4444-444444444444";

// One verified question row; topic_tags/topic_names are index-paired exactly as
// the /pyqs endpoint returns them.
const questionRow = (overrides = {}) => ({
  id: "q1",
  paper_id: PAPER_ID,
  paper_year: 2024,
  subject_name: "General Studies I",
  question_text: "A question",
  options: [],
  ...overrides,
});

const payloadWith = (overrides) => ({ exam_id: "e1", total: 1, items: [questionRow(overrides)] });

const renderExplorer = () =>
  render(
    <ToastProvider>
      <PyqExplorerSection examSlug="upsc-cse" />
    </ToastProvider>
  );

// The question cards live inside the collapsible Browse section.
async function openBrowseAndGetCard() {
  renderExplorer();
  fireEvent.click(await screen.findByTestId("pyq-browse-toggle"));
  return within(await screen.findByTestId("pyq-question-card"));
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
});

test("renders exactly one topic pill for a question with a single topic tag", async () => {
  api.get.mockResolvedValue(
    payloadWith({ topic_tags: [{ topic_id: "t1" }], topic_names: ["Ancient India"] })
  );
  const card = await openBrowseAndGetCard();

  const pills = card.getAllByTestId("pyq-topic-pill");
  expect(pills).toHaveLength(1);
  expect(pills[0]).toHaveTextContent("Ancient India");
  // Topic uses pill-amber so it is visually distinct from the pill-sage subject.
  expect(pills[0]).toHaveClass("pill-amber");
  expect(card.getByText("General Studies I")).toHaveClass("pill-sage");
});

test("renders no topic pill when the question has zero topic tags", async () => {
  api.get.mockResolvedValue(payloadWith({ topic_tags: [], topic_names: [] }));
  const card = await openBrowseAndGetCard();

  expect(card.queryAllByTestId("pyq-topic-pill")).toHaveLength(0);
  // Card itself still renders normally.
  expect(card.getByText("A question")).toBeInTheDocument();
});

test("renders no topic pill and does not crash when topic fields are missing entirely", async () => {
  api.get.mockResolvedValue(payloadWith({})); // no topic_tags / topic_names keys
  const card = await openBrowseAndGetCard();

  expect(card.queryAllByTestId("pyq-topic-pill")).toHaveLength(0);
});

test("renders one pill per tag, index-paired, for a multi-topic question", async () => {
  api.get.mockResolvedValue(
    payloadWith({
      topic_tags: [{ topic_id: "t1" }, { topic_id: "t2" }],
      topic_names: ["Ancient India", "Medieval India"],
    })
  );
  const card = await openBrowseAndGetCard();

  const pills = card.getAllByTestId("pyq-topic-pill");
  expect(pills.map((p) => p.textContent)).toEqual(["Ancient India", "Medieval India"]);
});

test("renders only cleanly-resolved pairs on a names/tags length mismatch (no 'undefined')", async () => {
  api.get.mockResolvedValue(
    payloadWith({
      topic_tags: [{ topic_id: "t1" }, { topic_id: "t2" }],
      topic_names: ["Only One"], // shorter than tags — second pair can't resolve
    })
  );
  const card = await openBrowseAndGetCard();

  const pills = card.getAllByTestId("pyq-topic-pill");
  expect(pills).toHaveLength(1);
  expect(pills[0]).toHaveTextContent("Only One");
  expect(card.queryByText(/undefined/i)).toBeNull();
});
