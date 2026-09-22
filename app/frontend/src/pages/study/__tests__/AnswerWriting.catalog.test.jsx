/**
 * The catalogue request the Answer Writing page actually sends.
 *
 * THE BUG. The Essay tab encoded itself as `paper_number=99`. The endpoint
 * validated `1 <= paper_number <= 10` and answered 422, and the page rendered
 * "The question catalogue is unavailable right now. Reload the page." — which
 * sent the aspirant to reload a page that would fail again the same way.
 *
 * So these assert the REQUEST SHAPE against the vocabulary the backend
 * publishes (`app.study_os.descriptive.PAPER_SLOT_CODES`), not against what
 * this component happens to send today.
 */
import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";

import AnswerWriting from "../AnswerWriting";
import { api, getApiErrorMessage } from "../../../lib/api";

jest.mock("../../../lib/api", () => ({
  api: { get: jest.fn() },
  getApiErrorMessage: jest.fn((e) => e?.message || ""),
}));

//: The backend's slot vocabulary, verbatim. A code added on one side and not
//: the other is exactly the failure this file exists for.
const PAPER_SLOT_CODES = ["GS1", "GS2", "GS3", "GS4", "ESSAY", "P1", "P2"];

const GS = "General Studies";

const GS_SLOTS = [
  { slot: "GS1", paper_number: 1, label: "GS1", question_count: 218, attempted_count: 0 },
  { slot: "GS2", paper_number: 2, label: "GS2", question_count: 220, attempted_count: 0 },
  { slot: "GS3", paper_number: 3, label: "GS3", question_count: 223, attempted_count: 0 },
  { slot: "GS4", paper_number: 4, label: "GS4", question_count: 212, attempted_count: 0 },
  { slot: "ESSAY", paper_number: 99, label: "Essay", question_count: 84, attempted_count: 0 },
];

function catalog(over = {}) {
  return {
    exam_id: "exam-1",
    subject: GS,
    subject_short: "GS",
    paper: null,
    paper_number: null,
    syllabus_supported: true,
    subjects: [{ subject: GS, question_count: 957 }],
    paper_slots: GS_SLOTS,
    papers: [],
    themes: [],
    theme_papers: [],
    years: [{ year: 2025, question_count: 20, attempted_count: 0, paper_ids: ["p"] }],
    total_questions: 957,
    ...over,
  };
}

/** Every catalogue URL the page has requested, newest last. */
function catalogUrls() {
  return api.get.mock.calls
    .map(([url]) => String(url))
    .filter((url) => url.includes("/descriptive/catalog"));
}

function params(url) {
  return new URLSearchParams(String(url).split("?")[1] || "");
}

function renderPage(search) {
  return render(
    <MemoryRouter initialEntries={[`/app/study/answer-writing${search}`]}>
      <Routes>
        <Route path="/app/study/answer-writing" element={<AnswerWriting />} />
      </Routes>
    </MemoryRouter>,
  );
}

function route(handler) {
  api.get.mockImplementation((url) => {
    if (url.includes("/target-exam")) {
      return Promise.resolve({ selected_exam: { id: "exam-1" }, user_id: "u1" });
    }
    return handler(url);
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  getApiErrorMessage.mockImplementation((e) => e?.message || "");
  route(() => Promise.resolve(catalog()));
});

// ── 1. the request shape matches the backend's schema ─────────────────────

test("the Essay tab asks for a slot the backend accepts, never a magic number", async () => {
  renderPage(`?subject=${encodeURIComponent(GS)}&paper=ESSAY`);
  await waitFor(() => expect(catalogUrls().length).toBeGreaterThan(0));

  const q = params(catalogUrls().at(-1));
  expect(q.get("paper")).toBe("ESSAY");
  expect(PAPER_SLOT_CODES).toContain(q.get("paper"));
  // The number the backend refused is not sent at all.
  expect(q.get("paper_number")).toBeNull();
});

test.each(PAPER_SLOT_CODES)("the %s tab sends that exact slot code", async (slot) => {
  renderPage(`?subject=${encodeURIComponent(GS)}&paper=${slot}`);
  await waitFor(() => expect(catalogUrls().length).toBeGreaterThan(0));
  expect(params(catalogUrls().at(-1)).get("paper")).toBe(slot);
});

test("a link still carrying the old paper_number is rewritten to its slot", async () => {
  renderPage(`?subject=${encodeURIComponent(GS)}&paper_number=99`);

  // The first read may still carry the legacy number — the backend resolves it
  // — but once the catalogue can name the slot, the URL and every read after
  // it say `paper=ESSAY`.
  await waitFor(() => {
    const q = params(catalogUrls().at(-1));
    expect(q.get("paper")).toBe("ESSAY");
    expect(q.get("paper_number")).toBeNull();
  });
});

test("the legacy number is not sent alongside the slot", async () => {
  renderPage(`?subject=${encodeURIComponent(GS)}&paper=GS3&paper_number=3`);
  await waitFor(() => expect(catalogUrls().length).toBeGreaterThan(0));
  const q = params(catalogUrls().at(-1));
  expect(q.get("paper")).toBe("GS3");
  expect(q.get("paper_number")).toBeNull();
});

// ── 2. a 4xx is an error state, not a blank screen ────────────────────────

test("a 422 says what the server said instead of 'reload the page'", async () => {
  const err = Object.assign(new Error("ESSAY is not a paper of Anthropology."), {
    status: 422,
  });
  route((url) =>
    url.includes("/descriptive/catalog") ? Promise.reject(err) : Promise.resolve({}),
  );

  renderPage(`?subject=${encodeURIComponent(GS)}&paper=ESSAY`);

  const message = await screen.findByText("ESSAY is not a paper of Anthropology.");
  expect(message).toHaveAttribute("role", "status");
  // Not the blank catalogue, and not the 5xx line.
  expect(screen.queryByTestId("descriptive-catalog")).not.toBeInTheDocument();
  expect(screen.queryByText(/unavailable right now/)).not.toBeInTheDocument();
});

test("a 400 with no message still says something an aspirant can act on", async () => {
  getApiErrorMessage.mockReturnValue("");
  route((url) =>
    url.includes("/descriptive/catalog")
      ? Promise.reject(Object.assign(new Error(""), { status: 400 }))
      : Promise.resolve({}),
  );

  renderPage(`?subject=${encodeURIComponent(GS)}&paper=GS1`);
  expect(await screen.findByText(/isn't one this subject has/)).toBeInTheDocument();
});

test("a 500 keeps the reload line, because reloading may actually help", async () => {
  route((url) =>
    url.includes("/descriptive/catalog")
      ? Promise.reject(Object.assign(new Error("boom"), { status: 500 }))
      : Promise.resolve({}),
  );

  renderPage(`?subject=${encodeURIComponent(GS)}&paper=GS1`);
  expect(await screen.findByText(/unavailable right now/)).toBeInTheDocument();
});

// ── 3. a slow response never overwrites a newer one ───────────────────────

test("a catalogue that lands after a newer one is ignored", async () => {
  // Demo: the catalogue took 12-15s, so the read for the tab the aspirant left
  // could land after the read for the tab they moved to, and the screen
  // settled on the wrong one.
  let releaseFirst;
  const first = new Promise((resolve) => {
    releaseFirst = () => resolve(catalog({ paper: "GS1", total_questions: 111 }));
  });

  route((url) =>
    url.includes("/descriptive/catalog")
      ? (params(url).get("paper") === "GS1"
          ? first
          : Promise.resolve(catalog({ paper: "GS4", total_questions: 222 })))
      : Promise.resolve({}),
  );

  // A real navigation within ONE mounted page — `initialEntries` only applies
  // on mount, and remounting would reset the very guard under test.
  function SwitchTab() {
    const navigate = useNavigate();
    return (
      <button
        type="button"
        onClick={() =>
          navigate(`/app/study/answer-writing?subject=${encodeURIComponent(GS)}&paper=GS4`)
        }
      >
        go GS4
      </button>
    );
  }

  render(
    <MemoryRouter
      initialEntries={[`/app/study/answer-writing?subject=${encodeURIComponent(GS)}&paper=GS1`]}
    >
      <SwitchTab />
      <Routes>
        <Route path="/app/study/answer-writing" element={<AnswerWriting />} />
      </Routes>
    </MemoryRouter>,
  );

  await waitFor(() => expect(catalogUrls().length).toBeGreaterThan(0));
  fireEvent.click(screen.getByText("go GS4"));

  expect(await screen.findByText("222 questions in this subject")).toBeInTheDocument();
  releaseFirst();
  await act(async () => {});
  // The stale 111 never reaches the screen.
  expect(screen.getByText("222 questions in this subject")).toBeInTheDocument();
  expect(screen.queryByText("111 questions in this subject")).not.toBeInTheDocument();
});

// ── 4. Essay has no syllabus, and the surface says which ──────────────────

test("the Essay tab says it has no syllabus rather than showing an empty tree", async () => {
  route((url) =>
    url.includes("/descriptive/catalog")
      ? Promise.resolve(catalog({ paper: "ESSAY", syllabus_supported: false, themes: [] }))
      : Promise.resolve({}),
  );

  renderPage(`?subject=${encodeURIComponent(GS)}&paper=ESSAY`);
  expect(
    await screen.findByTestId("descriptive-syllabus-unsupported"),
  ).toHaveTextContent("The Essay paper has no syllabus to browse. Pick a year instead.");
  expect(screen.queryByTestId("descriptive-syllabus-empty")).not.toBeInTheDocument();
});

// ── 5. the header names no subject ────────────────────────────────────────

test("the header does not tell a General Studies aspirant they are in an optional", async () => {
  renderPage(`?subject=${encodeURIComponent(GS)}`);
  await waitFor(() => expect(catalogUrls().length).toBeGreaterThan(0));
  expect(screen.queryByText(/from your optional/)).not.toBeInTheDocument();
  expect(screen.getByText(/Past questions from your papers/)).toBeInTheDocument();
});
