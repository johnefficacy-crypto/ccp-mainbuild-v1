/**
 * P5 — progress.
 *
 * Nothing here is machine-scored: every number is the aspirant's own rubric
 * judgement and their own clock. What these hold is that the surface never
 * invents a target — ~87% of the corpus has no marks and most questions have
 * no word limit — and never calls a topic weak off too few answers.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

import Progress, { comparisonLine, minutes } from "../Progress";
import { api } from "../../../../lib/api";

jest.mock("../../../../lib/api", () => ({ api: { get: jest.fn() } }));

const FULL_WEEK = {
  week: "2026-03-09",
  submitted: 4,
  avg_self_total: 8.5,
  avg_words: 300,
  avg_word_limit: 250,
  words_sample: 3,
  avg_seconds: 1200,
  avg_target_seconds: 1080,
  time_sample: 2,
  rubric: {},
};

const BARE_WEEK = {
  week: "2026-03-02",
  submitted: 2,
  avg_self_total: null,
  avg_words: null,
  avg_word_limit: null,
  words_sample: 0,
  avg_seconds: null,
  avg_target_seconds: null,
  time_sample: 0,
  rubric: {},
};

const DATA = {
  weeks: [BARE_WEEK, FULL_WEEK],
  window_weeks: 8,
  submitted_total: 6,
  streak_weeks: 2,
  rubric: {
    structure: 1.8, relevance: 1.6, coverage: 1.4,
    examples: 0.5, conclusion: 1.2, within_limit: null,
  },
  weakest_dimensions: ["examples"],
  strongest_topics: [{ topic: "Federalism", attempts: 4, avg_self_total: 10.5 }],
  weakest_topics: [{ topic: "Judiciary", attempts: 3, avg_self_total: 5.0 }],
  min_attempts_per_topic: 3,
  topics_below_threshold: 2,
};

beforeEach(() => {
  api.get.mockReset();
  api.get.mockResolvedValue(DATA);
});

test("reports the total and the streak in words", async () => {
  render(<Progress />);
  expect(await screen.findByTestId("progress-total")).toHaveTextContent(
    "6 answers written",
  );
  expect(screen.getByTestId("progress-streak")).toHaveTextContent(
    "2 weeks in a row",
  );
});

test("no streak says how to start one rather than showing a zero", async () => {
  api.get.mockResolvedValue({ ...DATA, streak_weeks: 0 });
  render(<Progress />);
  expect(await screen.findByTestId("progress-streak")).toHaveTextContent(
    /one answer this week starts it/i,
  );
});

test("a week states its comparison AND its sample size", async () => {
  render(<Progress />);
  const lines = await screen.findAllByTestId("progress-week-comparison");
  // Without the sample, eight answers and one answer look the same.
  expect(lines[0]).toHaveTextContent("300 words against a 250-word limit (3 answers)");
  expect(lines[0]).toHaveTextContent("20 min against 18 min (2 answers)");
});

test("a week with nothing comparable says so instead of showing zeroes", async () => {
  render(<Progress />);
  const weeks = await screen.findAllByTestId("progress-week");
  expect(weeks[0]).toHaveTextContent(/nothing to compare/i);
  expect(weeks[0]).not.toHaveTextContent("0 min");
  expect(weeks[0]).not.toHaveTextContent("0 words");
});

test("every rubric criterion gets a row, scored or not", async () => {
  render(<Progress />);
  const rows = await screen.findAllByTestId("progress-rubric-row");
  expect(rows).toHaveLength(6);
  expect(rows[5]).toHaveTextContent("Within limit");
  // "not scored" rather than 0/2 — nobody judged it.
  expect(rows[5]).toHaveTextContent("not scored");
  expect(rows[0]).toHaveTextContent("1.8/2");
});

test("the weakest criterion is named in a sentence", async () => {
  render(<Progress />);
  expect(await screen.findByTestId("progress-weakest")).toHaveTextContent(
    "Your lowest-scoring criterion is examples.",
  );
});

test("a tie for weakest names both", async () => {
  api.get.mockResolvedValue({ ...DATA, weakest_dimensions: ["conclusion", "examples"] });
  render(<Progress />);
  expect(await screen.findByTestId("progress-weakest")).toHaveTextContent(
    "Your lowest-scoring criteria are conclusion and examples.",
  );
});

test("topics are ranked at both ends", async () => {
  render(<Progress />);
  expect(await screen.findByTestId("progress-topic-strong")).toHaveTextContent(
    "Federalism — 10.5/12 over 4",
  );
  expect(screen.getByTestId("progress-topic-weak")).toHaveTextContent(
    "Judiciary — 5/12 over 3",
  );
});

test("too few answers per topic explains the threshold rather than showing a list", async () => {
  api.get.mockResolvedValue({
    ...DATA, strongest_topics: [], weakest_topics: [], topics_below_threshold: 2,
  });
  render(<Progress />);
  const note = await screen.findByTestId("progress-topics-empty");
  expect(note).toHaveTextContent("No topic has 3 answers yet");
  expect(note).toHaveTextContent("2 topics are close");
  expect(note).toHaveTextContent(/too little to call a topic strong or weak/i);
});

test("nothing written yet invites the first answer", async () => {
  api.get.mockResolvedValue({ weeks: [], submitted_total: 0, streak_weeks: 0,
                              rubric: {}, strongest_topics: [], weakest_topics: [],
                              min_attempts_per_topic: 3, topics_below_threshold: 0 });
  render(<Progress />);
  expect(await screen.findByText(/nothing to measure yet/i)).toBeInTheDocument();
});

test("a read failure says so instead of showing zero progress", async () => {
  api.get.mockRejectedValue(new Error("boom"));
  render(<Progress />);
  expect(
    await screen.findByText(/couldn't load your progress/i),
  ).toHaveAttribute("role", "status");
});

describe("comparisonLine", () => {
  test("is absent when nothing in the week had a target", () => {
    expect(comparisonLine(BARE_WEEK)).toBeNull();
  });

  test("reports only the half that has a sample", () => {
    const line = comparisonLine({ ...FULL_WEEK, time_sample: 0 });
    expect(line).toMatch(/words/);
    expect(line).not.toMatch(/min/);
  });

  test("uses the singular for one answer", () => {
    expect(comparisonLine({ ...BARE_WEEK, words_sample: 1, avg_words: 200,
                            avg_word_limit: 250 })).toMatch(/\(1 answer\)/);
  });
});

describe("minutes", () => {
  test("is absent for nothing spent", () => {
    expect(minutes(0)).toBeNull();
    expect(minutes(null)).toBeNull();
  });

  test("rounds to whole minutes", () => {
    expect(minutes(1080)).toBe("18 min");
    expect(minutes(100)).toBe("2 min");
  });
});
