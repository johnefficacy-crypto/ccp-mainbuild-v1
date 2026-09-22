/**
 * P2 — the answer history surface.
 *
 * What these hold: an attempt is never replaced, the aspirant is told so
 * BEFORE they press Rewrite, and Rewrite starts a blank answer rather than
 * loading the old one into an editor.
 */
import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import MyAnswers, { attemptMeta } from "../MyAnswers";
import { api } from "../../../../lib/api";

jest.mock("../../../../lib/api", () => ({ api: { get: jest.fn() } }));

const ROW = {
  id: "a-2",
  status: "submitted",
  word_count: 260,
  time_spent_seconds: 1800,
  self_total: 9,
  answer_mode: "typed",
  has_pasted_text: false,
  submitted_at: "2026-02-10T10:00:00Z",
  started_at: "2026-02-10T09:00:00Z",
  question: {
    id: "q-a",
    excerpt: "Examine the idea of sovereignty in a globalised order.",
    breadcrumb: { trail: ["Political Science"], source: "2019 · P1 · Q5(b) · 15 marks" },
  },
};

const HANDWRITTEN = {
  ...ROW,
  id: "a-3",
  answer_mode: "handwritten",
  // NULL by design: nothing reads the images, so there is no count to print.
  word_count: null,
  page_count: 2,
  has_pasted_text: null,
  question: { ...ROW.question, id: "q-b", excerpt: "Discuss coalition politics in India." },
};

function hwPage(n) {
  return {
    id: `pg-${n}`,
    page_no: n,
    mime_type: "image/png",
    bytes: 2048,
    url: `https://storage.test/read/page_${n}.png`,
    url_expires_in: 900,
    url_error: null,
  };
}

const LIST = {
  items: [ROW, HANDWRITTEN],
  total: 2,
  has_more: false,
  facets: {
    subjects: [{ value: "Political Science", count: 2 }],
    papers: [{ paper_id: "p-2019", label: "2019 · P1", count: 2 }],
    themes: [],
    statuses: [{ value: "submitted", count: 2 }],
  },
};

function route(url) {
  if (url.includes("/attempts?")) return Promise.resolve(LIST);
  if (url.match(/\/attempts\/a-2$/)) {
    return Promise.resolve({
      attempt: { ...ROW, answer_text: "Sovereignty is contested because…" },
      can_rewrite: true,
    });
  }
  if (url.match(/\/attempts\/a-3$/)) {
    // The demo attempt's shape: submitted, handwritten, no text, real pages.
    return Promise.resolve({
      attempt: { ...HANDWRITTEN, answer_text: "" },
      pages: [hwPage(1), hwPage(2)],
      page_count: 2,
      url_ttl_seconds: 900,
      can_rewrite: true,
    });
  }
  if (url.match(/\/attempts\/a-3\/pages$/)) {
    return Promise.resolve({ pages: [hwPage(1), hwPage(2)] });
  }
  if (url.includes("/questions/q-b/attempts")) {
    return Promise.resolve({
      attempts: [
        { ...HANDWRITTEN, id: "a-4", answer_text: "", pages: [hwPage(1)] },
        { ...ROW, id: "a-5", question: HANDWRITTEN.question, answer_text: "Typed go." },
      ],
      count: 2,
      submitted_count: 2,
      url_ttl_seconds: 900,
    });
  }
  if (url.includes("/questions/q-a/attempts")) {
    return Promise.resolve({
      attempts: [
        { ...ROW, id: "a-1", self_total: 6, word_count: 180, answer_text: "First go." },
        { ...ROW, answer_text: "Second go." },
      ],
      count: 2,
      submitted_count: 2,
      self_total_first: 6,
      self_total_last: 9,
    });
  }
  return Promise.reject(new Error(`unrouted ${url}`));
}

beforeEach(() => {
  api.get.mockReset();
  api.get.mockImplementation(route);
});

test("lists every attempt with its breadcrumb and facts", async () => {
  render(<MyAnswers />);
  const rows = await screen.findAllByTestId("my-answers-row");
  expect(rows).toHaveLength(2);
  expect(rows[0]).toHaveTextContent("2019 · P1 · Q5(b) · 15 marks");
  expect(rows[0]).toHaveTextContent("260 words");
  expect(rows[0]).toHaveTextContent("9/12 self-score");
});

test("the retention rule is stated on the page, not hidden in help", async () => {
  render(<MyAnswers />);
  const note = await screen.findByTestId("my-answers-retention-note");
  expect(note).toHaveTextContent(/every answer you submit is kept/i);
  expect(note).toHaveTextContent(/one draft open per question/i);
});

test("a handwritten attempt shows its badge and no word count", async () => {
  render(<MyAnswers />);
  const rows = await screen.findAllByTestId("my-answers-row");
  expect(rows[1]).toHaveTextContent("Handwritten");
  // Nothing has read the pages, so a count would be a measurement nobody made.
  expect(rows[1]).not.toHaveTextContent("0 words");
  expect(rows[1]).not.toHaveTextContent("words");
});

test("the pasted badge appears only when paste was actually measured", async () => {
  render(<MyAnswers />);
  const rows = await screen.findAllByTestId("my-answers-row");
  expect(rows[0]).not.toHaveTextContent(/pasted/i);   // measured, clean
  expect(rows[1]).not.toHaveTextContent(/pasted/i);   // never measured

  api.get.mockImplementation((url) =>
    url.includes("/attempts?")
      ? Promise.resolve({ ...LIST, items: [{ ...ROW, has_pasted_text: true }], total: 1 })
      : route(url),
  );
  render(<MyAnswers />);
  await waitFor(() =>
    expect(screen.getAllByTestId("my-answers-row").at(-1)).toHaveTextContent(
      /contains pasted text/i,
    ),
  );
});

test("a filter re-reads the history with that filter applied", async () => {
  render(<MyAnswers />);
  await screen.findAllByTestId("my-answers-row");
  fireEvent.change(screen.getByTestId("my-answers-filter-paper"), {
    target: { value: "p-2019" },
  });
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("paper_id=p-2019")),
  );
});

test("filter options come from the aspirant's own history", async () => {
  render(<MyAnswers />);
  const select = await screen.findByTestId("my-answers-filter-subject");
  expect(within(select).getByText("Political Science (2)")).toBeInTheDocument();
});

test("opening an attempt shows the full answer read-only", async () => {
  render(<MyAnswers />);
  const rows = await screen.findAllByTestId("my-answers-row");
  fireEvent.click(rows[0]);
  expect(await screen.findByTestId("my-answers-detail-text")).toHaveTextContent(
    "Sovereignty is contested because…",
  );
  // No editor: the history is a record, not a workspace.
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});

test("rewrite hands back the question id and never the old text", async () => {
  const onRewrite = jest.fn();
  render(<MyAnswers onRewrite={onRewrite} />);
  const rows = await screen.findAllByTestId("my-answers-row");
  fireEvent.click(rows[0]);
  fireEvent.click(await screen.findByTestId("my-answers-rewrite"));

  expect(onRewrite).toHaveBeenCalledWith("q-a");
  expect(onRewrite).toHaveBeenCalledTimes(1);
  // The whole contract in one assertion: the answer text is not an argument,
  // so there is nothing for a caller to prefill an editor with.
  expect(onRewrite.mock.calls[0]).toHaveLength(1);
});

test("the detail says the old answer survives a rewrite", async () => {
  render(<MyAnswers />);
  fireEvent.click((await screen.findAllByTestId("my-answers-row"))[0]);
  expect(
    await screen.findByText(/rewriting starts a blank answer/i),
  ).toBeInTheDocument();
});

test("compare shows the attempts side by side, oldest first", async () => {
  render(<MyAnswers />);
  fireEvent.click((await screen.findAllByTestId("my-answers-row"))[0]);
  fireEvent.click(await screen.findByTestId("my-answers-compare"));

  const columns = await screen.findAllByTestId("my-answers-compare-column");
  expect(columns).toHaveLength(2);
  expect(columns[0]).toHaveTextContent("First go.");
  expect(columns[1]).toHaveTextContent("Second go.");
  expect(columns[0]).toHaveTextContent("Attempt 1");
});

test("compare states the self-score movement in words", async () => {
  render(<MyAnswers />);
  fireEvent.click((await screen.findAllByTestId("my-answers-row"))[0]);
  fireEvent.click(await screen.findByTestId("my-answers-compare"));
  expect(await screen.findByTestId("my-answers-compare-delta")).toHaveTextContent(
    "Self-score went from 6/12 to 9/12 — up 3.",
  );
});

test("a single attempt gets no movement line at all", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/questions/q-a/attempts")
      ? Promise.resolve({
          attempts: [{ ...ROW, answer_text: "Only go." }],
          count: 1,
          submitted_count: 1,
          self_total_first: 9,
          self_total_last: 9,
        })
      : route(url),
  );
  render(<MyAnswers />);
  fireEvent.click((await screen.findAllByTestId("my-answers-row"))[0]);
  fireEvent.click(await screen.findByTestId("my-answers-compare"));
  await screen.findAllByTestId("my-answers-compare-column");
  // "+0" would read as a judgement rather than as an absence.
  expect(screen.queryByTestId("my-answers-compare-delta")).not.toBeInTheDocument();
});

test("an empty history explains itself rather than showing a blank list", async () => {
  api.get.mockResolvedValue({ items: [], total: 0, has_more: false, facets: {} });
  render(<MyAnswers />);
  expect(await screen.findByText(/no answers yet/i)).toBeInTheDocument();
});

test("a read failure says so instead of showing an empty history", async () => {
  api.get.mockRejectedValue(new Error("boom"));
  render(<MyAnswers />);
  expect(await screen.findByRole("status")).toHaveTextContent(/couldn't load your answers/i);
});

describe("attemptMeta", () => {
  test("omits the word count for a handwritten attempt", () => {
    expect(attemptMeta(HANDWRITTEN).join(" · ")).not.toMatch(/words/);
  });

  test("omits a self-score that was never given", () => {
    expect(attemptMeta({ ...ROW, self_total: null }).join(" · ")).not.toMatch(/self-score/);
  });

  test("omits a time that was never spent", () => {
    expect(attemptMeta({ ...ROW, time_spent_seconds: 0 }).join(" · ")).not.toMatch(/min/);
  });
});


// ── the handwritten attempt IS its pages ──────────────────────────────────
//
// THE DEMO BUG. 69689f58-…, answer_mode='handwritten', submitted, one row in
// descriptive_attempt_pages and the object present in storage, opened reading
// "This attempt has no text yet" with nothing rendered.

test("opening a handwritten attempt renders its pages, not 'no text yet'", async () => {
  render(<MyAnswers />);
  const rows = await screen.findAllByTestId("my-answers-row");
  fireEvent.click(within(rows[1]).getByText(/coalition politics/));

  const pages = await screen.findByTestId("attempt-pages");
  expect(within(pages).getAllByRole("img")).toHaveLength(2);
  expect(screen.queryByText(/no text yet/i)).not.toBeInTheDocument();
  expect(screen.queryByTestId("my-answers-detail-text")).not.toBeInTheDocument();
});

test("a handwritten attempt states its page count", async () => {
  render(<MyAnswers />);
  const rows = await screen.findAllByTestId("my-answers-row");
  fireEvent.click(within(rows[1]).getByText(/coalition politics/));

  expect(await screen.findByTestId("attempt-pages-count")).toHaveTextContent("2 pages");
});

test("a handwritten attempt can still be rewritten and compared", async () => {
  render(<MyAnswers />);
  const rows = await screen.findAllByTestId("my-answers-row");
  fireEvent.click(within(rows[1]).getByText(/coalition politics/));

  expect(await screen.findByTestId("my-answers-rewrite")).toBeInTheDocument();
  expect(screen.getByTestId("my-answers-compare")).toBeInTheDocument();
});

test("a typed attempt still shows its text", async () => {
  render(<MyAnswers />);
  const rows = await screen.findAllByTestId("my-answers-row");
  fireEvent.click(within(rows[0]).getByText(/sovereignty/i));

  expect(await screen.findByTestId("my-answers-detail-text")).toHaveTextContent(
    "Sovereignty is contested because…",
  );
  expect(screen.queryByTestId("attempt-pages")).not.toBeInTheDocument();
});

test("comparing puts a handwritten attempt's pages beside a typed one's text", async () => {
  render(<MyAnswers />);
  const rows = await screen.findAllByTestId("my-answers-row");
  fireEvent.click(within(rows[1]).getByText(/coalition politics/));
  fireEvent.click(await screen.findByTestId("my-answers-compare"));

  const columns = await screen.findAllByTestId("my-answers-compare-column");
  expect(within(columns[0]).getByTestId("attempt-pages")).toBeInTheDocument();
  expect(within(columns[1]).getByText("Typed go.")).toBeInTheDocument();
});

describe("attemptMeta, handwritten", () => {
  test("reads its pages where a typed attempt reads its words", () => {
    expect(attemptMeta(HANDWRITTEN).join(" · ")).toMatch(/2 pages/);
    expect(attemptMeta(HANDWRITTEN).join(" · ")).not.toMatch(/words/);
  });

  test("a draft with nothing uploaded says 0 pages rather than nothing", () => {
    // Silence here read as a typed attempt, so an aspirant could not tell a
    // handwritten draft waiting for its photos from one never started.
    const line = attemptMeta({ ...HANDWRITTEN, page_count: 0, status: "draft" }).join(" · ");
    expect(line).toMatch(/0 pages/);
  });

  test("one page is singular", () => {
    expect(attemptMeta({ ...HANDWRITTEN, page_count: 1 }).join(" · ")).toMatch(/1 page\b/);
  });
});
