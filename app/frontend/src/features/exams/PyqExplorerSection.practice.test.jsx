import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ToastProvider from "../../shared/ui/ToastProvider";

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({ useNavigate: () => mockNavigate }));
// The whole api module is stubbed (requireActual would construct the real
// Supabase client). Two separate claims, two separate tests:
//   * that getApiErrorMessage maps {detail, code} to the human text lives in
//     src/lib/api.error.test.js, against the real formatter;
//   * that this component RENDERS whatever that helper returns is what this
//     file proves, so the stub just echoes the body back.
jest.mock("../../lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn() },
  getApiErrorMessage: (e) =>
    (e && e.detail && e.detail.detail) || (e && e.message) || "",
}));
const { api } = require("../../lib/api");
const PyqExplorerSection = require("./PyqExplorerSection").default;

const EXAM_ID = "11111111-1111-1111-1111-111111111111";
const PAPER_ID = "44444444-4444-4444-4444-444444444444";

const listPayload = {
  exam_id: EXAM_ID,
  total: 1,
  items: [
    { id: "q1", paper_id: PAPER_ID, paper_year: 2024, question_text: "A question", options: [] },
  ],
};

// The practice CTA mutates through the shared useApiAction runner, which uses the
// toast context — render inside a real ToastProvider so the governed path runs.
const renderExplorer = (props = {}) =>
  render(
    <ToastProvider>
      <PyqExplorerSection examSlug="upsc-cse" {...props} />
    </ToastProvider>
  );

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  mockNavigate.mockReset();
  api.get.mockResolvedValue(listPayload);
});

test("starts paper practice through useApiAction and navigates to the attempt shell", async () => {
  api.post.mockResolvedValue({ outcome: "ready", attempt_id: "att-1" });
  renderExplorer();

  // Practice-this-paper lives in the collapsible Browse section.
  fireEvent.click(await screen.findByTestId("pyq-browse-toggle"));
  fireEvent.click(await screen.findByTestId("pyq-practice-paper-btn"));

  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith("/api/study/mocks/practice/start", {
      mode: "paper",
      target_id: PAPER_ID,
      exam_id: EXAM_ID,
    })
  );
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/app/study/mocks/attempts/att-1"));
});

test("shows a graceful inline message on 409 without navigating", async () => {
  // No structured body — the fallback sentence still applies.
  const err = new Error();
  err.status = 409;
  api.post.mockRejectedValue(err);
  renderExplorer();

  // Practice-this-paper lives in the collapsible Browse section.
  fireEvent.click(await screen.findByTestId("pyq-browse-toggle"));
  fireEvent.click(await screen.findByTestId("pyq-practice-paper-btn"));

  const banner = await screen.findByTestId("pyq-practice-error");
  expect(banner.textContent).toMatch(/isn't available for practice yet/i);
  expect(mockNavigate).not.toHaveBeenCalled();
});

test.each([
  [
    "descriptive_paper",
    "Descriptive paper — answer-writing practice not available yet.",
  ],
  [
    "thematic_not_paper",
    "This is a topic-wise collection, not a paper. Paper practice isn't available.",
  ],
])("surfaces the backend's specific 409 reason (%s)", async (code, detail) => {
  // A descriptive UPSC Mains optional paper can NEVER become practice-ready, so
  // the old "its questions need to be verified and projected" sentence was an
  // instruction to wait for something that will not happen. The backend now
  // says which of the three reasons applies; the UI must show that text.
  const err = new Error("conflict");
  err.status = 409;
  err.detail = { detail, code };
  api.post.mockRejectedValue(err);
  renderExplorer();

  fireEvent.click(await screen.findByTestId("pyq-browse-toggle"));
  fireEvent.click(await screen.findByTestId("pyq-practice-paper-btn"));

  const banner = await screen.findByTestId("pyq-practice-error");
  expect(banner.textContent).toContain(detail);
  expect(banner.textContent).not.toMatch(/need to be verified and projected/i);
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("disables the practice button while the useApiAction run is in flight", async () => {
  let resolvePost;
  api.post.mockReturnValue(
    new Promise((res) => {
      resolvePost = res;
    })
  );
  renderExplorer();

  fireEvent.click(await screen.findByTestId("pyq-browse-toggle"));
  const btn = await screen.findByTestId("pyq-practice-paper-btn");
  fireEvent.click(btn);

  await waitFor(() => expect(screen.getByTestId("pyq-practice-paper-btn")).toBeDisabled());
  expect(screen.getByTestId("pyq-practice-paper-btn").textContent).toMatch(/Starting/i);

  await act(async () => {
    resolvePost({ outcome: "ready", attempt_id: "att-1" });
  });
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/app/study/mocks/attempts/att-1"));
});

test("no practice button when a row has no paper_id", async () => {
  api.get.mockResolvedValue({ exam_id: EXAM_ID, total: 1, items: [{ id: "q2", paper_year: 2024, question_text: "No paper", options: [] }] });
  renderExplorer();

  fireEvent.click(await screen.findByTestId("pyq-browse-toggle"));
  await screen.findByTestId("pyq-question-card");
  expect(screen.queryByTestId("pyq-practice-paper-btn")).toBeNull();
});
