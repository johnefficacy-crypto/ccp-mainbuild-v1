import React from "react";
import { render, screen } from "@testing-library/react";

import TopicPalette from "./TopicPalette";

/**
 * COV-DIM-01: the recurrence band is the one signal on a coverage row that
 * means the same thing across subjects — a percentile within the topic's own
 * subject-paper — where the raw priority does not (a derived optional row tops
 * out near 15, an authored one starts at 60).
 */
const DAYS = [{ date: "2026-09-14", label: "Mon" }];

function item(overrides) {
  return {
    topic_id: "t1",
    topic: "Balance of power",
    subject: "PSIR Paper-1",
    exam_priority_score: 9,
    predictability_band: null,
    ...overrides,
  };
}

function renderPalette(items) {
  render(<TopicPalette items={items} days={DAYS} onAdd={() => {}} />);
}

test("renders the band as plain words, not the stored enum", () => {
  renderPalette([item({ predictability_band: "near_certain" })]);

  const row = screen.getByTestId("palette-topic");
  expect(row.textContent).toMatch(/recurrence Near-certain/);
  expect(row.textContent).not.toMatch(/near_certain/);
});

test("each band has a label", () => {
  renderPalette([
    item({ topic_id: "a", predictability_band: "near_certain" }),
    item({ topic_id: "b", predictability_band: "likely" }),
    item({ topic_id: "c", predictability_band: "occasional" }),
    item({ topic_id: "d", predictability_band: "rare" }),
  ]);

  const text = screen.getAllByTestId("palette-topic").map((r) => r.textContent);
  expect(text[0]).toMatch(/Near-certain/);
  expect(text[1]).toMatch(/Likely/);
  expect(text[2]).toMatch(/Occasional/);
  expect(text[3]).toMatch(/Rare/);
});

test("a topic with no year evidence shows no band rather than a default", () => {
  renderPalette([item({ predictability_band: null })]);

  const row = screen.getByTestId("palette-topic");
  expect(row.textContent).not.toMatch(/recurrence/i);
  // The rest of the row is unchanged.
  expect(row.textContent).toMatch(/PSIR Paper-1/);
});

test("an unrecognised band is not rendered", () => {
  // The propType rejects it too; silence that expected warning so the
  // assertion below is what this test reports on.
  const warn = jest.spyOn(console, "error").mockImplementation(() => {});
  try {
    renderPalette([item({ predictability_band: "sometimes" })]);
    expect(screen.getByTestId("palette-topic").textContent).not.toMatch(
      /recurrence/i,
    );
  } finally {
    warn.mockRestore();
  }
});

test("shows the standing the server ranked by, not a zero", () => {
  // D16: the palette used to read a key the payload never carried, so every
  // row rendered "priority 0".
  renderPalette([item({ exam_priority_score: 30, comparable_priority: 87 })]);

  expect(screen.getByTestId("palette-topic").textContent).toMatch(
    /priority 87/,
  );
});

test("falls back to the raw priority when no standing is attached", () => {
  renderPalette([item({ exam_priority_score: 30, comparable_priority: undefined })]);

  expect(screen.getByTestId("palette-topic").textContent).toMatch(
    /priority 30/,
  );
});
