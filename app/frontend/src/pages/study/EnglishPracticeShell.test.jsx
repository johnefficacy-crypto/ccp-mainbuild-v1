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

// The REAL GET /sessions/{id} shape: { session, units } — the writing_sessions
// row (no embedded prompt) + units. (Prompt/version enrichment is a deferred
// backend resume-endpoint item.)
function session(units) {
  return { session: { id: "S1", mode: "learning", status: "active" }, units };
}

describe("EnglishPracticeShell", () => {
  afterEach(() => jest.clearAllMocks());

  test("renders a sentence builder for a not-started unit (real API shape)", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        session([{ id: "u1", unit_number: 1, status: "not_started", unit_constraints: {} }]),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByTestId("english-practice-shell")).toBeInTheDocument();
    expect(screen.getByTestId("sentence-builder")).toBeInTheDocument();
  });

  test("submitting calls submitUnit with session, unit number and CAS version 1", async () => {
    const submitUnit = jest.fn().mockResolvedValue({ ok: true, data: { version_number: 1, evaluation: {} } });
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        session([{ id: "u1", unit_number: 1, status: "not_started", unit_constraints: {} }]),
      ),
      submitUnit,
      busy: false,
    });
    renderShell();
    await screen.findByTestId("sentence-builder");
    fireEvent.change(screen.getByTestId("sentence-input"), { target: { value: "She is a diligent student." } });
    fireEvent.click(screen.getByTestId("sentence-submit"));
    await waitFor(() => expect(submitUnit).toHaveBeenCalledWith("S1", 1, "She is a diligent student.", 1));
  });

  test("rewrite_required renders a direct rewrite editor (no reopen 409)", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        session([{ id: "u1", unit_number: 1, status: "rewrite_required", unit_constraints: {} }]),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByTestId("rewrite-editor")).toBeInTheDocument();
    expect(screen.queryByTestId("unit-1-reopen")).not.toBeInTheDocument();
  });

  test("shows a pending message while a unit is being evaluated", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        session([{ id: "u1", unit_number: 1, status: "evaluation_pending", unit_constraints: {} }]),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByTestId("unit-1-pending")).toBeInTheDocument();
  });

  test("renders an empty state when the session has no units", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(session([])),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByTestId("ewp-empty")).toBeInTheDocument();
  });

  test("renders an error state with retry when the session cannot load", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockRejectedValue(new Error("boom")),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByText("Practice session unavailable")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });
});
