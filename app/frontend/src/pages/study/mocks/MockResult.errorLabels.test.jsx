import React from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import MockResult from "./MockResult";

jest.mock("../../../lib/api", () => ({ api: { get: jest.fn() } }));

// Capture what the error donut is asked to render so we can assert the labels
// were mapped (no raw classifier code reaches the chart/tooltip).
jest.mock("../components/reports/ErrorTypeDonut", () => ({
  __esModule: true,
  default: ({ data }) => (
    <div data-testid="donut-mock">{(data || []).map((d) => d.label).join("|")}</div>
  ),
}));

const RESULT = {
  score_percentage: 50,
  total_correct: 1,
  total_wrong: 2,
  time_used_sec: 120,
  section_breakdown: [],
};

const ANALYTICS = {
  response_classification: [
    { error_type: "silly_mistake" },
    { error_type: "silly_mistake" },
    { error_type: "time_pressure_unattempted" },
  ],
};

test("result Error tab renders mapped labels, never raw classifier codes", async () => {
  const { api } = require("../../../lib/api");
  api.get.mockImplementation((url) => {
    if (url.endsWith("/result")) return Promise.resolve(RESULT);
    if (url.endsWith("/analytics")) return Promise.resolve(ANALYTICS);
    return Promise.resolve({});
  });

  render(
    <MemoryRouter initialEntries={["/app/study/mocks/attempts/att1/result"]}>
      <Routes>
        <Route path="/app/study/mocks/attempts/:attemptId/result" element={<MockResult />} />
      </Routes>
    </MemoryRouter>,
  );

  await screen.findByTestId("result-page");
  fireEvent.click(screen.getByTestId("result-tab-error"));

  const donut = await screen.findByTestId("donut-mock");
  expect(donut).toHaveTextContent("Careless mistake");
  expect(donut).toHaveTextContent("Time pressure / not attempted");
  expect(donut).not.toHaveTextContent("silly_mistake");
  expect(donut).not.toHaveTextContent("time_pressure_unattempted");
});
