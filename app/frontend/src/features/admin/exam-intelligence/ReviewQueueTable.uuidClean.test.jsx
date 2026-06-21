/**
 * ReviewQueueTable — UX-EI-1 (I1) regression tests.
 *
 * Asserts that raw UUIDs are never rendered as visible text in the
 * Row id column. The fix replaces {r.id} with humanizeToken(r.id),
 * which produces "#<first-8-chars>" for UUID-shaped values.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

jest.mock("./ExamEvidenceDrawer", () => ({
  __esModule: true,
  default: () => <div data-testid="evidence-drawer-stub" />,
}));

const ReviewQueueTable = require("./ReviewQueueTable").default;

const UUID_ID = "a4cad004-401a-3632-a000-000000000001";
const UUID_ID_2 = "b8f3e001-dead-beef-cafe-123456789abc";

const ROWS = [
  {
    id: UUID_ID,
    reviewer_status: "pending",
    confidence_score: 0.75,
    question_type: "MCQ",
  },
  {
    id: UUID_ID_2,
    reviewer_status: "verified",
    confidence_score: 0.9,
    question_type: "MCQ",
  },
];

describe("ReviewQueueTable — UX-EI-1: no raw UUIDs in Row id column", () => {
  test("does NOT render the full raw UUID as visible text", () => {
    render(
      <ReviewQueueTable
        items={ROWS}
        kind="pyq_question"
        onReview={() => {}}
        busyRowId={null}
      />,
    );
    // Full UUIDs must not appear as text content
    expect(screen.queryByText(UUID_ID)).toBeNull();
    expect(screen.queryByText(UUID_ID_2)).toBeNull();
  });

  test("renders humanized short prefix (#<first-8-chars>) instead of UUID", () => {
    render(
      <ReviewQueueTable
        items={ROWS}
        kind="pyq_question"
        onReview={() => {}}
        busyRowId={null}
      />,
    );
    // humanizeToken("#a4cad004") — first 8 hex chars
    expect(screen.getByText("#a4cad004")).toBeTruthy();
    expect(screen.getByText("#b8f3e001")).toBeTruthy();
  });

  test("expand button still has correct data-testid using full id", () => {
    render(
      <ReviewQueueTable
        items={[ROWS[0]]}
        kind="pyq_question"
        onReview={() => {}}
        busyRowId={null}
      />,
    );
    // data-testid uses full ID for programmatic targeting; only visible text is short
    expect(screen.getByTestId(`exam-intel-review-${UUID_ID}-expand`)).toBeTruthy();
  });

  test("non-UUID short ids pass through unchanged", () => {
    const shortRow = {
      id: "mention-42",
      normalized_text: "Some text",
      mention_type: "topic",
      reviewer_status: "pending",
      confidence_score: 0.8,
    };
    render(
      <ReviewQueueTable
        items={[shortRow]}
        kind="syllabus_topic_mention"
        onReview={() => {}}
        busyRowId={null}
      />,
    );
    // Non-UUID IDs are returned as-is by humanizeToken
    expect(screen.getByText("mention-42")).toBeTruthy();
  });
});
