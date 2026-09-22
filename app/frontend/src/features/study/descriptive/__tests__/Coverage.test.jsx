/**
 * P4 — coverage.
 *
 * The number an aspirant needs is "how much of it have I answered", and it has
 * to be readable as a fraction. These hold the two ways a coverage surface
 * usually lies: a bare percentage that hides the size of what is left, and a
 * 0.0 average that reads as "everything scored zero".
 */
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import Coverage, { scoreLine } from "../Coverage";
import { api } from "../../../../lib/api";

jest.mock("../../../../lib/api", () => ({ api: { get: jest.fn() } }));

const DATA = {
  exam_id: "exam-1",
  totals: { available: 1351, attempted: 18, unattempted: 1333,
            avg_self_score: 7.5, subjects: 1 },
  subjects: [
    {
      subject: "Political Science",
      available: 1351,
      attempted: 18,
      avg_self_score: 7.5,
      scored_attempts: 20,
      groups: [
        {
          label: "P1 · Political Theory", source: "syllabus",
          available: 40, attempted: 3, avg_self_score: 8.0, scored_attempts: 3,
          unattempted: [{ id: "q-9", excerpt: "Examine sovereignty.",
                          paper_id: "p-2019", marks: 15 }],
          unattempted_total: 37,
        },
        {
          label: "2013 · P1", source: "paper",
          available: 20, attempted: 20, avg_self_score: null, scored_attempts: 0,
          unattempted: [], unattempted_total: 0,
        },
      ],
    },
  ],
};

beforeEach(() => {
  api.get.mockReset();
  api.get.mockResolvedValue(DATA);
});

test("the headline is a fraction, not a percentage", async () => {
  render(<Coverage examId="exam-1" />);
  expect(await screen.findByTestId("coverage-total")).toHaveTextContent(
    "18 of 1351 written",
  );
  // A bare "1%" would hide how much is left, which is the number that decides
  // what to write tonight.
  expect(screen.queryByText(/^1%$/)).not.toBeInTheDocument();
});

test("it says how many are still waiting", async () => {
  render(<Coverage examId="exam-1" />);
  expect(await screen.findByText(/1333 still waiting/)).toBeInTheDocument();
});

test("each group reports its own fraction and average", async () => {
  render(<Coverage examId="exam-1" />);
  const groups = await screen.findAllByTestId("coverage-group");
  expect(groups[0]).toHaveTextContent("P1 · Political Theory");
  expect(groups[0]).toHaveTextContent("3 of 40 written");
  expect(groups[0]).toHaveTextContent("8/12 average over 3 answers");
});

test("a group with no scores shows no average rather than a zero", async () => {
  render(<Coverage examId="exam-1" />);
  const groups = await screen.findAllByTestId("coverage-group");
  expect(groups[1]).toHaveTextContent("20 of 20 written");
  expect(groups[1]).not.toHaveTextContent(/average/);
  expect(groups[1]).not.toHaveTextContent("0/12");
});

test("expanding a group lists what is not yet attempted and how many more", async () => {
  render(<Coverage examId="exam-1" />);
  fireEvent.click((await screen.findAllByTestId("coverage-group"))[0]);
  const panel = await screen.findByTestId("coverage-unattempted");
  expect(panel).toHaveTextContent("showing 1 of 37");
  expect(screen.getByTestId("coverage-unattempted-row")).toHaveTextContent(
    "Examine sovereignty.",
  );
});

test("a fully written group says so instead of showing an empty list", async () => {
  render(<Coverage examId="exam-1" />);
  fireEvent.click((await screen.findAllByTestId("coverage-group"))[1]);
  expect(
    await screen.findByText(/every question in this group is written/i),
  ).toBeInTheDocument();
});

test("picking an unattempted question hands it back to the caller", async () => {
  const onPick = jest.fn();
  render(<Coverage examId="exam-1" onPickQuestion={onPick} />);
  fireEvent.click((await screen.findAllByTestId("coverage-group"))[0]);
  fireEvent.click(await screen.findByTestId("coverage-unattempted-row"));
  expect(onPick).toHaveBeenCalledWith(
    expect.objectContaining({ id: "q-9", paper_id: "p-2019" }),
  );
});

test("no exam asks for one rather than showing an empty report", () => {
  render(<Coverage examId="" />);
  expect(screen.getByText(/pick your target exam/i)).toBeInTheDocument();
  expect(api.get).not.toHaveBeenCalled();
});

test("a read failure says so instead of showing zero coverage", async () => {
  api.get.mockRejectedValue(new Error("boom"));
  render(<Coverage examId="exam-1" />);
  // findByRole("status") would settle on the LOADING status first, which is
  // also a live region; the error is what this test is about.
  expect(
    await screen.findByText(/couldn't load your coverage/i),
  ).toHaveAttribute("role", "status");
});

test("an exam with no descriptive questions explains itself", async () => {
  api.get.mockResolvedValue({ exam_id: "e", subjects: [], totals: {} });
  render(<Coverage examId="exam-1" />);
  expect(await screen.findByText(/nothing to cover yet/i)).toBeInTheDocument();
});

describe("scoreLine", () => {
  test("is absent when nothing has been scored", () => {
    expect(scoreLine({ avg_self_score: null, scored_attempts: 0 })).toBeNull();
    expect(scoreLine({ scored_attempts: 0 })).toBeNull();
  });

  test("says 0 when 0 was actually scored", () => {
    // A real zero is a real judgement and must not be hidden with the absent
    // case — that is the whole reason null and 0 are kept apart.
    expect(scoreLine({ avg_self_score: 0, scored_attempts: 2 })).toBe(
      "0/12 average over 2 answers",
    );
  });

  test("uses the singular for one answer", () => {
    expect(scoreLine({ avg_self_score: 9, scored_attempts: 1 })).toBe(
      "9/12 average over 1 answer",
    );
  });
});
