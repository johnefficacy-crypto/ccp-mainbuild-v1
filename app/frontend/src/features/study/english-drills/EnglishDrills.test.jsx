import React from "react";
import { act, fireEvent, render, screen, within } from "@testing-library/react";

import EnglishDrills from "./EnglishDrills";
import { STORAGE_KEY } from "./drillEngine";

jest.mock("./drillSound", () => ({ playVerdict: jest.fn(), shake: jest.fn() }));
const sound = require("./drillSound");

beforeEach(() => {
  window.localStorage.clear();
  window.scrollTo = jest.fn();
  jest.clearAllMocks();
});

const fb = () => screen.getByTestId("ed-feedback");

test("overview lists nine modules and the daily-mix terms", () => {
  render(<EnglishDrills />);
  expect(screen.getByText("The English section, drilled daily.")).toBeInTheDocument();
  expect(screen.getAllByTestId(/^ed-module-/)).toHaveLength(9);
  expect(screen.getByText("12 questions, 10 minutes, every type.")).toBeInTheDocument();
  expect(screen.getByTestId("ed-xp")).toHaveTextContent("0");
});

test("wrong error-detection pick buzzes, shakes, states the rule and costs 3 XP", () => {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ xp: 20 }));
  render(<EnglishDrills />);
  fireEvent.click(screen.getByTestId("ed-module-err"));
  fireEvent.click(screen.getByTestId("ed-err-1")); // answer is part A (0)
  expect(sound.playVerdict).toHaveBeenCalledWith(false);
  expect(sound.shake).toHaveBeenCalled();
  expect(fb()).toHaveTextContent("Not quite");
  expect(fb()).toHaveTextContent("“One of my friend” should be “One of my friends”");
  expect(screen.getByTestId("ed-rule")).toHaveTextContent("“One of” is always followed by a plural noun.");
  expect(screen.getByText("One of my friends has gone to Delhi for an interview.")).toBeInTheDocument();
  expect(screen.getByTestId("ed-xp")).toHaveTextContent("17");
  expect(JSON.parse(window.localStorage.getItem(STORAGE_KEY)).stats.err).toEqual({ a: 1, c: 0 });
});

test("correct vocab answer earns 10 XP; a hint strikes two options and halves the reward", () => {
  render(<EnglishDrills />);
  fireEvent.click(screen.getByTestId("ed-module-voc"));
  expect(screen.getByTestId("ed-voc-word")).toHaveTextContent("Ephemeral");
  fireEvent.click(screen.getByTestId("ed-opt-1"));
  expect(sound.playVerdict).toHaveBeenCalledWith(true);
  expect(fb()).toHaveTextContent("Correct — Transient");
  expect(screen.getByTestId("ed-xp")).toHaveTextContent("10");

  fireEvent.click(screen.getByText("Next →"));
  fireEvent.click(screen.getByText("Hint · −2 XP"));
  expect(screen.getByTestId("ed-xp")).toHaveTextContent("8");
  const struck = [0, 1, 2, 3].filter((k) => screen.getByTestId(`ed-opt-${k}`).style.textDecoration === "line-through");
  expect(struck).toHaveLength(2);
  expect(struck).not.toContain(0);
  fireEvent.click(screen.getByTestId("ed-opt-0"));
  expect(screen.getByTestId("ed-xp")).toHaveTextContent("13");
});

test("parajumble: tap two rows to swap, check reports parts in place, reveal shows the answer", () => {
  render(<EnglishDrills />);
  fireEvent.click(screen.getByTestId("ed-module-pj"));
  expect(screen.getByTestId("ed-pj-code")).toHaveTextContent("P Q R S");
  fireEvent.click(screen.getByTestId("ed-pj-row-0"));
  fireEvent.click(screen.getByTestId("ed-pj-row-1"));
  expect(screen.getByTestId("ed-pj-code")).toHaveTextContent("Q P R S");
  fireEvent.click(screen.getByText("Check"));
  expect(fb()).toHaveTextContent("Not in order");
  expect(sound.playVerdict).toHaveBeenCalledWith(false);
  fireEvent.click(screen.getByText("Reveal answer"));
  expect(fb()).toHaveTextContent("Answer: Q S P R");
});

test("parajumble drag-and-drop reorders rows", () => {
  render(<EnglishDrills />);
  fireEvent.click(screen.getByTestId("ed-module-pj"));
  const dt = { setData: jest.fn(), effectAllowed: "" };
  fireEvent.dragStart(screen.getByTestId("ed-pj-row-3"), { dataTransfer: dt });
  fireEvent.dragOver(screen.getByTestId("ed-pj-row-0"), { dataTransfer: dt });
  fireEvent.drop(screen.getByTestId("ed-pj-row-0"), { dataTransfer: dt });
  expect(screen.getByTestId("ed-pj-code")).toHaveTextContent("S P Q R");
});

test("sentence construction builds from the word bank and checks", () => {
  render(<EnglishDrills />);
  fireEvent.click(screen.getByTestId("ed-module-sc"));
  // t: approved the policy has new government the → "The government has approved the new policy."
  [1, 5, 3, 0, 6, 4, 2].forEach((i) => fireEvent.click(screen.getByTestId(`ed-bank-${i}`)));
  fireEvent.click(screen.getByText("Check"));
  expect(fb()).toHaveTextContent("Well built");
});

test("parts-of-speech tagging requires every word, then marks corrections", () => {
  render(<EnglishDrills />);
  fireEvent.click(screen.getByTestId("ed-module-pos"));
  fireEvent.click(screen.getByText("Check"));
  expect(fb()).toHaveTextContent("Tag every word first");
  for (let k = 0; k < 9; k += 1) fireEvent.click(screen.getByTestId(`ed-word-${k}`)); // all Noun
  fireEvent.click(screen.getByText("Check"));
  expect(fb()).toHaveTextContent("2 of 9 correct");
  expect(screen.getByTestId("ed-word-0")).toHaveTextContent("N → DET");
});

test("cloze: fill each blank, then check", () => {
  render(<EnglishDrills />);
  fireEvent.click(screen.getByTestId("ed-module-cloze"));
  ["than", "regularly", "wise", "reveal"].forEach((w) => fireEvent.click(screen.getByRole("button", { name: w })));
  fireEvent.click(screen.getByText("Check"));
  expect(fb()).toHaveTextContent("All 4 blanks correct");
});

test("daily mix runs a timer, ends on a result sheet with every row marked", () => {
  jest.useFakeTimers();
  try {
    render(<EnglishDrills mixSize={4} mixMinutes={3} />);
    fireEvent.click(screen.getByText("Start today’s mix →"));
    expect(screen.getByText(/Daily mix · question 1 of 4/)).toBeInTheDocument();
    expect(screen.getByTestId("ed-timer")).toHaveTextContent("03:00");
    act(() => {
      jest.advanceTimersByTime(181000);
    });
    const result = screen.getByTestId("ed-result");
    expect(within(result).getByText("of 4 correct")).toBeInTheDocument();
    expect(within(result).getAllByText("— Skipped")).toHaveLength(4);
  } finally {
    jest.useRealTimers();
  }
});

test("sound toggle silences the buzzer", () => {
  render(<EnglishDrills />);
  fireEvent.click(screen.getByText("♪ Sound on"));
  fireEvent.click(screen.getByTestId("ed-module-ce"));
  fireEvent.click(screen.getByTestId("ed-ce-0")); // "I am having two brothers." contains an error
  expect(fb()).toHaveTextContent("Not quite");
  expect(sound.playVerdict).not.toHaveBeenCalled();
});
