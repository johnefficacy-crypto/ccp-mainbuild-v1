import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";

import TopicPalette from "./TopicPalette";

const DAYS = [
  { date: "2026-09-14", label: "Mon" },
  { date: "2026-09-15", label: "Tue" },
];

function topic(over) {
  return {
    topic_id: "t1",
    topic: "Percentage",
    subject_id: "s1",
    subject: "Quantitative Aptitude",
    parent_topic_id: "m1",
    parent_topic: "Quantitative methods",
    selection_kind: "compulsory",
    comparable_priority: 87.5,
    exam_priority_score: 9.2,
    predictability_band: null,
    scheduled_date: null,
    ...over,
  };
}

/** Two subjects, one of them the user's optional, each with a macro topic. */
const ITEMS = [
  topic({ topic_id: "quant-1", topic: "Percentage" }),
  topic({ topic_id: "quant-2", topic: "Ratio and proportion" }),
  topic({
    topic_id: "quant-3",
    topic: "Data interpretation",
    parent_topic_id: "m2",
    parent_topic: "Data",
  }),
  topic({
    topic_id: "psir-1",
    topic: "Balance of power",
    subject_id: "s2",
    subject: "PSIR Paper-1",
    parent_topic_id: "m3",
    parent_topic: "International relations",
    selection_kind: "elective",
    predictability_band: "near_certain",
  }),
];

function renderPalette(items = ITEMS, props = {}) {
  return render(
    <TopicPalette items={items} days={DAYS} onAdd={() => {}} {...props} />,
  );
}

const cardIds = () =>
  screen.queryAllByTestId("palette-topic").map((el) => el.getAttribute("data-topic-id"));

// ── 1. the search defect, first ────────────────────────────────────────────

test("search finds topics outside the selected subject and says where they are", () => {
  renderPalette();
  // Opens on the first compulsory subject, so PSIR is not in view.
  expect(cardIds()).not.toContain("psir-1");

  fireEvent.change(screen.getByLabelText("Search topics"), {
    target: { value: "balance" },
  });

  expect(cardIds()).toEqual(["psir-1"]);
  const card = screen.getByTestId("palette-topic");
  expect(card.textContent).toMatch(/PSIR Paper-1 › International relations/);
});

test("clearing the query restores the tree selection", () => {
  renderPalette();
  const search = screen.getByLabelText("Search topics");

  fireEvent.change(search, { target: { value: "balance" } });
  expect(cardIds()).toEqual(["psir-1"]);

  fireEvent.change(search, { target: { value: "" } });
  expect(cardIds()).toEqual(["quant-1", "quant-2", "quant-3"]);
});

test("a search with no match says so and leaves the tree alone", () => {
  renderPalette();
  fireEvent.change(screen.getByLabelText("Search topics"), {
    target: { value: "zzz" },
  });

  expect(cardIds()).toEqual([]);
  expect(screen.getByText("No topic matches that search.")).toBeTruthy();
});

// ── 2. tree selection ──────────────────────────────────────────────────────

test("selecting a macro topic filters the cards and names the position", () => {
  renderPalette();

  fireEvent.click(screen.getByRole("button", { name: /Data/ }));

  expect(cardIds()).toEqual(["quant-3"]);
  expect(screen.getByTestId("palette-breadcrumb").textContent).toBe(
    "Quantitative Aptitude › Data",
  );
});

test("selecting a subject shows every topic in it, macro children included", () => {
  renderPalette();

  fireEvent.click(screen.getByRole("button", { name: /PSIR Paper-1/ }));

  expect(cardIds()).toEqual(["psir-1"]);
  expect(screen.getByTestId("palette-breadcrumb").textContent).toBe("PSIR Paper-1");
});

// ── 3. the band ────────────────────────────────────────────────────────────

test("a topic with no band renders no pill at all", () => {
  renderPalette();
  const card = screen.getAllByTestId("palette-topic")[0];

  expect(within(card).queryByTestId("recurrence-pill")).toBeNull();
});

test("a topic with a band renders it as words", () => {
  renderPalette();
  fireEvent.click(screen.getByRole("button", { name: /PSIR Paper-1/ }));

  const pill = screen.getByTestId("recurrence-pill");
  expect(pill.textContent).toBe("Asked near-certain");
  expect(pill.textContent).not.toMatch(/near_certain/);
});

// ── 4. the priority number is gone ─────────────────────────────────────────

test("no element renders comparable_priority", () => {
  const { container } = renderPalette();

  expect(container.textContent).not.toMatch(/87/);
  expect(container.textContent).not.toMatch(/priority/i);
});

// ── 5. scheduled topics ────────────────────────────────────────────────────

test("a scheduled topic stays listed, dimmed, showing its day", () => {
  renderPalette([
    topic({ topic_id: "quant-1", scheduled_date: "2026-09-15" }),
    topic({ topic_id: "quant-2", topic: "Ratio and proportion" }),
  ]);

  expect(cardIds()).toEqual(["quant-1", "quant-2"]);
  const [scheduled] = screen.getAllByTestId("palette-topic");
  expect(scheduled.getAttribute("data-scheduled")).toBe("true");
  expect(scheduled.className).toMatch(/opacity-60/);
  expect(within(scheduled).getByTestId("palette-scheduled").textContent).toBe(
    "On your board — Tue",
  );
  // No second way to add what is already there.
  expect(within(scheduled).queryByRole("button", { name: "Add" })).toBeNull();
});

// ── 6. elective scoping ────────────────────────────────────────────────────

test("the chosen optional has its own heading and unchosen ones appear nowhere", () => {
  renderPalette();

  expect(screen.getByText("Compulsory papers")).toBeTruthy();
  expect(screen.getByText("Your optional")).toBeTruthy();
  // The payload is already elective-scoped, so an unchosen optional is absent
  // from it — and therefore absent from the tree.
  expect(screen.queryByText(/Anthropology/)).toBeNull();
});

// ── 7. keyboard ────────────────────────────────────────────────────────────

test("every tree node and card action is a focusable control", () => {
  renderPalette();
  fireEvent.click(screen.getByRole("button", { name: /PSIR Paper-1/ }));

  const nodes = [
    ...screen.getAllByTestId("tree-subject"),
    ...screen.getAllByTestId("tree-macro"),
  ];
  expect(nodes.length).toBeGreaterThan(1);
  nodes.forEach((n) => expect(n.tagName).toBe("BUTTON"));

  const card = screen.getByTestId("palette-topic");
  expect(within(card).getByRole("combobox")).toBeTruthy();
  expect(within(card).getByRole("button", { name: "Add" })).toBeTruthy();
  // The day picker is labelled for a screen reader.
  expect(within(card).getByLabelText("Day for Balance of power")).toBeTruthy();
});

test("the selected node is marked for assistive tech", () => {
  renderPalette();
  const [first] = screen.getAllByTestId("tree-subject");

  expect(first.getAttribute("aria-current")).toBe("true");
});

// ── adding ─────────────────────────────────────────────────────────────────

test("Add hands the topic and the chosen day to the caller", () => {
  const onAdd = jest.fn();
  renderPalette(ITEMS, { onAdd });

  const card = screen.getAllByTestId("palette-topic")[0];
  fireEvent.change(within(card).getByRole("combobox"), {
    target: { value: "2026-09-15" },
  });
  fireEvent.click(within(card).getByRole("button", { name: "Add" }));

  expect(onAdd).toHaveBeenCalledTimes(1);
  expect(onAdd.mock.calls[0][0].topic_id).toBe("quant-1");
  expect(onAdd.mock.calls[0][1]).toBe("2026-09-15");
});

test("an empty payload says so without breaking the panes", () => {
  renderPalette([]);

  expect(
    screen.getByText("Every verified topic is already on your board."),
  ).toBeTruthy();
  expect(cardIds()).toEqual([]);
});
