/**
 * P3 — handwritten pages.
 *
 * Nothing here reads an image. What these hold is that the client's limits
 * match the server's, that a page is uploaded straight to storage rather than
 * through the API, and that the surface never claims a word count for an
 * answer nobody has read.
 */
import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import HandwrittenPages, { ACCEPTED, MAX_BYTES, MAX_PAGES, rejectReason } from "../HandwrittenPages";
import { api } from "../../../../lib/api";

jest.mock("../../../../lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn(), del: jest.fn() },
}));

const ATTEMPT = "attempt-1";

function file(name, type, size) {
  const f = new File(["x"], name, { type });
  Object.defineProperty(f, "size", { value: size });
  return f;
}

const PAGES = {
  attempt_id: ATTEMPT,
  answer_mode: "handwritten",
  pages: [
    { id: "p1", page_no: 1, mime_type: "image/jpeg", bytes: 2048,
      url: "https://storage.test/read/a/1?ttl=900" },
    { id: "p2", page_no: 2, mime_type: "application/pdf", bytes: 4096,
      url: "https://storage.test/read/a/2?ttl=900" },
  ],
  max_pages: MAX_PAGES,
};

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.del.mockReset();
  api.get.mockResolvedValue(PAGES);
  api.post.mockResolvedValue({
    page: { id: "p3", page_no: 3 },
    upload_url: "https://storage.test/upload/a/3",
    upload_token: "tok",
  });
  api.del.mockResolvedValue({ deleted: 1, remaining: 1 });
  global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200 });
});

test("shows each uploaded page and says nothing reads them", async () => {
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  expect(await screen.findAllByTestId("handwritten-page")).toHaveLength(2);
  expect(screen.getByText(/nothing reads these images/i)).toBeInTheDocument();
  expect(screen.getByText(/the same rubric a typed answer gets/i)).toBeInTheDocument();
});

test("an image page renders as an image with a real alt", async () => {
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  const img = await screen.findByAltText("Page 1 of your handwritten answer");
  expect(img).toHaveAttribute("src", PAGES.pages[0].url);
});

test("a PDF page is a link rather than a broken image", async () => {
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  expect(await screen.findByText(/open page 2 \(pdf\)/i)).toHaveAttribute(
    "href",
    PAGES.pages[1].url,
  );
});

test("a page whose URL could not be signed says so and the others still render", async () => {
  api.get.mockResolvedValue({
    ...PAGES,
    pages: [{ ...PAGES.pages[0], url: null }, PAGES.pages[1]],
  });
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  expect(await screen.findByText(/can't be shown right now/i)).toBeInTheDocument();
  expect(screen.getByText(/open page 2 \(pdf\)/i)).toBeInTheDocument();
});

test("the file input opens the rear camera on a phone", async () => {
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  const input = await screen.findByTestId("handwritten-input");
  expect(input).toHaveAttribute("capture", "environment");
  expect(input).toHaveAttribute("accept", ACCEPTED);
});

test("uploading sends the bytes to storage, not through the API", async () => {
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  const input = await screen.findByTestId("handwritten-input");
  const page = file("page3.jpg", "image/jpeg", 2048);
  fireEvent.change(input, { target: { files: [page] } });

  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  expect(api.post).toHaveBeenCalledWith(
    `/api/study/descriptive/attempts/${ATTEMPT}/pages`,
    { page_no: 3, mime_type: "image/jpeg", size_bytes: 2048 },
  );
  const [url, init] = global.fetch.mock.calls[0];
  expect(url).toBe("https://storage.test/upload/a/3");
  expect(init.method).toBe("PUT");
  expect(init.body).toBe(page);
});

test("the next page number continues the sequence", async () => {
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  const input = await screen.findByTestId("handwritten-input");
  fireEvent.change(input, { target: { files: [file("p.jpg", "image/jpeg", 10)] } });
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith(expect.any(String),
      expect.objectContaining({ page_no: 3 })),
  );
});

test("an oversized page is refused in the browser before any request", async () => {
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  const input = await screen.findByTestId("handwritten-input");
  fireEvent.change(input, {
    target: { files: [file("huge.jpg", "image/jpeg", MAX_BYTES + 1)] },
  });
  expect(await screen.findByTestId("handwritten-error")).toHaveTextContent(
    /under 10 MB/i,
  );
  expect(api.post).not.toHaveBeenCalled();
});

test("an unsupported type is refused before any request", async () => {
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  const input = await screen.findByTestId("handwritten-input");
  fireEvent.change(input, { target: { files: [file("a.mp4", "video/mp4", 100)] } });
  expect(await screen.findByTestId("handwritten-error")).toHaveTextContent(
    /photo or PDF/i,
  );
  expect(api.post).not.toHaveBeenCalled();
});

test("a failed storage PUT says so rather than showing a phantom page", async () => {
  global.fetch.mockResolvedValue({ ok: false, status: 403 });
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  fireEvent.change(await screen.findByTestId("handwritten-input"), {
    target: { files: [file("p.jpg", "image/jpeg", 10)] },
  });
  expect(await screen.findByTestId("handwritten-error")).toHaveTextContent(
    /didn't upload/i,
  );
});

test("removing a page calls delete and reports the mode back when the last goes", async () => {
  api.del.mockResolvedValue({ deleted: 1, remaining: 0 });
  const onModeChange = jest.fn();
  render(<HandwrittenPages attemptId={ATTEMPT} onModeChange={onModeChange} />);
  fireEvent.click(await screen.findByTestId("handwritten-remove-1"));

  await waitFor(() =>
    expect(api.del).toHaveBeenCalledWith(
      `/api/study/descriptive/attempts/${ATTEMPT}/pages/1`,
    ),
  );
  await waitFor(() => expect(onModeChange).toHaveBeenCalledWith("typed"));
});

test("a submitted attempt offers no upload and no remove", async () => {
  render(<HandwrittenPages attemptId={ATTEMPT} readOnly />);
  await screen.findAllByTestId("handwritten-page");
  expect(screen.queryByTestId("handwritten-input")).not.toBeInTheDocument();
  expect(screen.queryByTestId("handwritten-remove-1")).not.toBeInTheDocument();
});

test("at the page ceiling the input is disabled and says why", async () => {
  api.get.mockResolvedValue({
    ...PAGES,
    pages: Array.from({ length: MAX_PAGES }, (_, i) => ({
      id: `p${i}`, page_no: i + 1, mime_type: "image/jpeg", bytes: 10, url: "u",
    })),
  });
  render(<HandwrittenPages attemptId={ATTEMPT} />);
  expect(await screen.findByTestId("handwritten-input")).toBeDisabled();
  expect(screen.getByText(/that's the maximum/i)).toBeInTheDocument();
});

describe("rejectReason mirrors the server's limits", () => {
  test("accepts every type the server accepts", () => {
    ACCEPTED.split(",").forEach((type) => {
      expect(rejectReason(file("a", type, 1000))).toBeNull();
    });
  });

  test("refuses a ninth page but not a replacement of an existing one", () => {
    const f = file("a.jpg", "image/jpeg", 1000);
    expect(rejectReason(f, { pageCount: MAX_PAGES })).toMatch(/at most 8 pages/);
    expect(rejectReason(f, { pageCount: MAX_PAGES, replacing: true })).toBeNull();
  });

  test("refuses an empty file", () => {
    expect(rejectReason(file("a.jpg", "image/jpeg", 0))).toMatch(/empty/);
  });

  test("refuses nothing at all", () => {
    expect(rejectReason(null)).toMatch(/pick a page/i);
  });
});
