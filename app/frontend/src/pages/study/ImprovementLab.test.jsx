import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

import ImprovementLab from "./ImprovementLab";
import useErrorLab from "../../features/study/english-practice/useErrorLab";
import useStrategyFeed from "../../features/study/improvement-lab/useStrategyFeed";

// Factory mocks so the real hooks (which import lib/api → env) are never loaded.
jest.mock("../../features/study/english-practice/useErrorLab", () => ({
  __esModule: true,
  default: jest.fn(),
}));
jest.mock("../../features/study/improvement-lab/useStrategyFeed", () => ({
  __esModule: true,
  default: jest.fn(),
}));

beforeEach(() => {
  // Quant/Reasoning feeds default to empty so the shell assertions stay stable.
  useStrategyFeed.mockReturnValue({ items: [], status: "empty", refresh: jest.fn() });
});

afterEach(() => jest.clearAllMocks());

test("renders the renamed page with all three independent sections", () => {
  useErrorLab.mockReturnValue({ groups: [], status: "empty", refresh: jest.fn() });
  render(<ImprovementLab />);

  expect(screen.getByTestId("improvement-lab")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Improvement Lab" })).toBeInTheDocument();

  // Three independent sections present.
  expect(screen.getByTestId("improvement-lab-english")).toBeInTheDocument();
  expect(screen.getByTestId("improvement-lab-quant")).toBeInTheDocument();
  expect(screen.getByTestId("improvement-lab-reasoning")).toBeInTheDocument();

  // Learner-facing section titles per the design lock.
  expect(screen.getByText("My Writing Errors")).toBeInTheDocument();
  expect(screen.getByText("Methods & Shortcuts")).toBeInTheDocument();
  expect(screen.getByText("Approaches & Patterns")).toBeInTheDocument();
});

test("each section owns its state — English empty does not hide Quant/Reasoning", () => {
  useErrorLab.mockReturnValue({ groups: [], status: "empty", refresh: jest.fn() });
  render(<ImprovementLab />);

  expect(screen.getByTestId("english-empty")).toBeInTheDocument();
  expect(screen.getByTestId("improvement-lab-quant-empty")).toBeInTheDocument();
  expect(screen.getByTestId("improvement-lab-reasoning-empty")).toBeInTheDocument();
});

test("a failure in one section does not hide the others", () => {
  // Force the English section to throw during render.
  useErrorLab.mockImplementation(() => {
    throw new Error("boom");
  });
  const spy = jest.spyOn(console, "error").mockImplementation(() => {});

  render(<ImprovementLab />);

  // English degraded to its local error card…
  expect(screen.getByText("My Writing Errors unavailable")).toBeInTheDocument();
  // …while the sibling sections still render.
  expect(screen.getByTestId("improvement-lab-quant")).toBeInTheDocument();
  expect(screen.getByTestId("improvement-lab-reasoning")).toBeInTheDocument();

  spy.mockRestore();
});
