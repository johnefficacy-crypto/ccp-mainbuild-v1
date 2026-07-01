import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import EnglishPracticeShell from "./EnglishPracticeShell";
import useEnglishPracticeSession from "../../features/study/english-practice/useEnglishPracticeSession";

// Factory mock so the real hook (which imports lib/api → env) is never loaded.
jest.mock("../../features/study/english-practice/useEnglishPracticeSession", () => ({
  __esModule: true,
  default: jest.fn(),
}));

function renderShell() {
  return render(
    <MemoryRouter initialEntries={["/app/study/practice/english/S1"]}>
      <Routes>
        <Route path="/app/study/practice/english/:sessionId" element={<EnglishPracticeShell />} />
      </Routes>
    </MemoryRouter>,
  );
}

const NOT_STARTED_SESSION = {
  session: { mode: "learning", prompt: { prompt_text: "Write one sentence using 'diligent'.", min_words: 5 } },
  units: [{ id: "u1", unit_number: 1, status: "not_started", unit_constraints: {} }],
};

describe("EnglishPracticeShell", () => {
  afterEach(() => jest.clearAllMocks());

  test("renders the prompt and a sentence builder for a not-started unit", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(NOT_STARTED_SESSION),
      submitUnit: jest.fn(),
      reopenUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByTestId("english-practice-shell")).toBeInTheDocument();
    // The prompt shows in both the header and the builder.
    expect(screen.getAllByText("Write one sentence using 'diligent'.").length).toBeGreaterThan(0);
    expect(screen.getByTestId("sentence-builder")).toBeInTheDocument();
  });

  test("submitting a unit calls submitUnit with the session, unit number and version 1", async () => {
    const submitUnit = jest.fn().mockResolvedValue({ ok: true, data: { version_number: 1, evaluation: {} } });
    const fetchSession = jest.fn().mockResolvedValue(NOT_STARTED_SESSION);
    useEnglishPracticeSession.mockReturnValue({ fetchSession, submitUnit, reopenUnit: jest.fn(), busy: false });

    renderShell();
    await screen.findByTestId("sentence-builder");
    fireEvent.change(screen.getByTestId("sentence-input"), { target: { value: "She is a diligent student today." } });
    fireEvent.click(screen.getByTestId("sentence-submit"));

    await waitFor(() =>
      expect(submitUnit).toHaveBeenCalledWith("S1", 1, "She is a diligent student today.", 1),
    );
  });

  test("shows a pending message while a unit is being evaluated", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue({
        session: { mode: "learning", prompt: {} },
        units: [{ id: "u1", unit_number: 1, status: "evaluation_pending", unit_constraints: {} }],
      }),
      submitUnit: jest.fn(),
      reopenUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByTestId("unit-1-pending")).toBeInTheDocument();
  });

  test("renders an error state with retry when the session cannot load", async () => {
    const fetchSession = jest.fn().mockRejectedValue(new Error("boom"));
    useEnglishPracticeSession.mockReturnValue({ fetchSession, submitUnit: jest.fn(), reopenUnit: jest.fn(), busy: false });
    renderShell();
    expect(await screen.findByText("Practice session unavailable")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });
});
