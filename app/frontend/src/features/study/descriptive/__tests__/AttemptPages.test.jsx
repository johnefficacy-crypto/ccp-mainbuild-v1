/**
 * Handwritten pages, shown back in "My answers".
 *
 * THE BUG. A submitted handwritten attempt with a real object in storage read
 * "This attempt has no text yet." and rendered nothing. The API returned the
 * pages, signed; the view dropped them and fell through to the typed empty
 * state.
 *
 * These hold the three things that make images safe to render here: they are
 * in page order and lazy, an expiring URL recovers by itself, and a page that
 * is genuinely gone says so on that page alone.
 */
import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import AttemptPages, { pageCountLabel, refreshDelayMs } from "../AttemptPages";
import { api } from "../../../../lib/api";

jest.mock("../../../../lib/api", () => ({ api: { get: jest.fn() } }));

const ATTEMPT = "69689f58-9835-4b4c-95da-7d6d64382ea2";

function page(n, over = {}) {
  return {
    id: `pg-${n}`,
    page_no: n,
    mime_type: "image/png",
    bytes: 2048,
    url: `https://storage.test/read/page_${n}.png?sig=v1`,
    url_expires_in: 900,
    url_error: null,
    ...over,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  api.get.mockResolvedValue({ pages: [page(1), page(2)] });
});

// ── 1. the pages are the answer ───────────────────────────────────────────

test("the pages render as thumbnails in page order", () => {
  render(<AttemptPages attemptId={ATTEMPT} pages={[page(1), page(2), page(3)]} />);
  const imgs = screen.getAllByRole("img");
  expect(imgs).toHaveLength(3);
  expect(imgs.map((i) => i.getAttribute("alt"))).toEqual([
    "Page 1 of this handwritten answer",
    "Page 2 of this handwritten answer",
    "Page 3 of this handwritten answer",
  ]);
});

test("the page count is stated, never 'no text yet'", () => {
  render(<AttemptPages attemptId={ATTEMPT} pages={[page(1), page(2)]} />);
  expect(screen.getByTestId("attempt-pages-count")).toHaveTextContent("2 pages");
  expect(screen.queryByText(/no text yet/i)).not.toBeInTheDocument();
});

test("eight photos of A4 do not all load at once", () => {
  render(<AttemptPages attemptId={ATTEMPT} pages={[page(1), page(2)]} />);
  screen.getAllByRole("img").forEach((img) => {
    expect(img).toHaveAttribute("loading", "lazy");
  });
});

test("a thumbnail opens full size and closes again", () => {
  render(<AttemptPages attemptId={ATTEMPT} pages={[page(1), page(2)]} />);
  fireEvent.click(screen.getByTestId("attempt-page-open-2"));

  const full = screen.getByTestId("attempt-page-full");
  expect(full).toHaveAttribute("aria-modal", "true");
  expect(
    screen.getByAltText("Page 2 of this handwritten answer, full size"),
  ).toBeInTheDocument();

  fireEvent.click(screen.getByTestId("attempt-page-full-close"));
  expect(screen.queryByTestId("attempt-page-full")).not.toBeInTheDocument();
});

test("a PDF page opens in a new tab rather than rendering as an image", () => {
  render(
    <AttemptPages attemptId={ATTEMPT} pages={[page(1, { mime_type: "application/pdf" })]} />,
  );
  const link = screen.getByTestId("attempt-page-pdf-1");
  expect(link).toHaveAttribute("target", "_blank");
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("no pages says zero pages, in the caller's words", () => {
  render(
    <AttemptPages attemptId={ATTEMPT} pages={[]} emptyLabel="0 pages — waiting." />,
  );
  expect(screen.getByTestId("attempt-pages-empty")).toHaveTextContent("0 pages — waiting.");
});

// ── 2. an expiring URL recovers by itself ─────────────────────────────────

test("an image that fails once is retried with a freshly signed URL", async () => {
  // A tab left open outlives a 15-minute signature. The first failure is
  // assumed to be that, and is fixed silently.
  api.get.mockResolvedValue({ pages: [page(1, { url: "https://storage.test/read/page_1.png?sig=v2" })] });
  render(<AttemptPages attemptId={ATTEMPT} pages={[page(1)]} />);

  fireEvent.error(screen.getByRole("img"));

  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(
      `/api/study/descriptive/attempts/${ATTEMPT}/pages`,
    ),
  );
  await waitFor(() =>
    expect(screen.getByRole("img")).toHaveAttribute("src", expect.stringContaining("sig=v2")),
  );
  expect(screen.queryByTestId("attempt-page-error-1")).not.toBeInTheDocument();
});

test("the URLs are re-signed before they expire, not after", async () => {
  jest.useFakeTimers();
  try {
    render(<AttemptPages attemptId={ATTEMPT} pages={[page(1)]} ttlSeconds={900} />);
    expect(api.get).not.toHaveBeenCalled();
    // Async act so the refresh's own state updates settle inside it, rather
    // than landing after the test and warning.
    await act(async () => {
      jest.advanceTimersByTime(refreshDelayMs(900));
    });
    expect(api.get).toHaveBeenCalledTimes(1);
  } finally {
    jest.useRealTimers();
  }
});

test("the refresh is early enough to be useful and never a busy loop", () => {
  expect(refreshDelayMs(900)).toBe(720_000);
  expect(refreshDelayMs(900)).toBeLessThan(900_000);
  // A tiny or absent TTL must not schedule a tight timer.
  expect(refreshDelayMs(1)).toBe(30_000);
  expect(refreshDelayMs(0)).toBeNull();
  expect(refreshDelayMs(undefined)).toBeNull();
});

// ── 3. a page that is genuinely gone says so, alone ───────────────────────

test("a page that fails twice is reported missing, and the others still show", async () => {
  api.get.mockResolvedValue({ pages: [page(1), page(2)] });
  render(<AttemptPages attemptId={ATTEMPT} pages={[page(1), page(2)]} />);

  const second = () => screen.getAllByRole("img")[1];
  fireEvent.error(second());                       // expiry, refetched
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  await act(async () => {
    fireEvent.error(second());                     // still gone
  });

  expect(await screen.findByTestId("attempt-page-error-2")).toHaveTextContent(
    "Page 2 is missing from storage.",
  );
  // Page 1 is untouched: one broken page is not a broken attempt.
  expect(screen.getByAltText("Page 1 of this handwritten answer")).toBeInTheDocument();
});

test("a page the server could not sign says so, with its own retry", async () => {
  render(
    <AttemptPages
      attemptId={ATTEMPT}
      pages={[page(1), page(2, { url: null, url_error: "url_unavailable", url_expires_in: null })]}
    />,
  );
  const message = screen.getByTestId("attempt-page-error-2");
  expect(message).toHaveTextContent("Page 2 can't be shown right now.");
  expect(message).toHaveAttribute("role", "status");

  await act(async () => {
    fireEvent.click(screen.getByTestId("attempt-page-retry-2"));
  });
  expect(api.get).toHaveBeenCalledWith(
    `/api/study/descriptive/attempts/${ATTEMPT}/pages`,
  );
});

test("a failed refresh leaves the pages that were on screen alone", async () => {
  api.get.mockRejectedValue(new Error("network"));
  render(<AttemptPages attemptId={ATTEMPT} pages={[page(1)]} />);

  fireEvent.error(screen.getByRole("img"));
  await waitFor(() => expect(api.get).toHaveBeenCalled());

  // Still one page, not an empty state: a failed re-sign is not evidence the
  // answer is gone.
  expect(screen.getByTestId("attempt-pages-count")).toHaveTextContent("1 page");
});

// ── 4. the label ──────────────────────────────────────────────────────────

test("the page count reads as a sentence at every size", () => {
  expect(pageCountLabel(0)).toBe("0 pages");
  expect(pageCountLabel(1)).toBe("1 page");
  expect(pageCountLabel(8)).toBe("8 pages");
  expect(pageCountLabel(null)).toBe("0 pages");
});
