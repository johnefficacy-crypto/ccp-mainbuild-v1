import PropTypes from "prop-types";
import React, { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../../lib/api";

/**
 * Handwritten answers: photograph the pages you wrote.
 *
 * WHY THIS MODE EXISTS. The Mains answer an aspirant will actually write is
 * handwritten, under time, on paper. Typing-only practice trains a different
 * skill — it removes the handwriting speed that is half of what the paper
 * tests, and it makes the word count feel free.
 *
 * NOTHING READS THESE IMAGES. No OCR, no AI evaluation. They are the
 * aspirant's own record, shown back to them beside the same rubric a typed
 * answer gets. A handwritten attempt therefore has no word count at all —
 * printing 0 would say they wrote nothing.
 *
 * `capture="environment"` on the input is what opens the rear camera on a
 * phone instead of the file browser. On a desktop it is ignored and the
 * control is an ordinary file picker.
 */

export const ACCEPTED = "image/jpeg,image/png,image/heic,image/heif,application/pdf";
export const MAX_BYTES = 10 * 1024 * 1024;
export const MAX_PAGES = 8;

/** Why this file cannot be uploaded, or null. Mirrors the server's checks. */
export function rejectReason(file, { pageCount = 0, replacing = false } = {}) {
  if (!file) return "Pick a page to upload.";
  const types = ACCEPTED.split(",");
  if (!types.includes(file.type)) {
    return "Upload a photo or PDF — JPG, PNG, HEIC or PDF.";
  }
  if (!file.size) return "That file is empty.";
  if (file.size > MAX_BYTES) {
    return `Each page must be under ${MAX_BYTES / (1024 * 1024)} MB.`;
  }
  if (!replacing && pageCount >= MAX_PAGES) {
    return `An answer can have at most ${MAX_PAGES} pages.`;
  }
  return null;
}

export default function HandwrittenPages({ attemptId, readOnly, onModeChange }) {
  const [pages, setPages] = useState([]);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);

  const load = useCallback(() => {
    if (!attemptId) return;
    api
      .get(`/api/study/descriptive/attempts/${attemptId}/pages`)
      .then((d) => {
        setPages(Array.isArray(d?.pages) ? d.pages : []);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, [attemptId]);

  useEffect(load, [load]);

  const upload = useCallback(
    async (file, pageNo) => {
      const replacing = pages.some((p) => p.page_no === pageNo);
      const reason = rejectReason(file, { pageCount: pages.length, replacing });
      if (reason) {
        setError(reason);
        return;
      }
      setError("");
      setBusy(true);
      try {
        const ticket = await api.post(
          `/api/study/descriptive/attempts/${attemptId}/pages`,
          { page_no: pageNo, mime_type: file.type, size_bytes: file.size },
        );
        // The bytes go straight to storage on the signed URL. They never pass
        // through the API, which is what keeps a 10 MB photo off the request
        // path the rest of the surface shares.
        const res = await fetch(ticket.upload_url, {
          method: "PUT",
          headers: { "Content-Type": file.type },
          body: file,
        });
        if (!res.ok) throw new Error(`upload failed: ${res.status}`);
        load();
        if (onModeChange) onModeChange("handwritten");
      } catch (err) {
        setError("That page didn't upload. Try again.");
      } finally {
        setBusy(false);
      }
    },
    [attemptId, pages, load, onModeChange],
  );

  const remove = useCallback(
    async (pageNo) => {
      setBusy(true);
      setError("");
      try {
        const out = await api.del(
          `/api/study/descriptive/attempts/${attemptId}/pages/${pageNo}`,
        );
        load();
        if (out?.remaining === 0 && onModeChange) onModeChange("typed");
      } catch (err) {
        setError("Couldn't remove that page.");
      } finally {
        setBusy(false);
      }
    },
    [attemptId, load, onModeChange],
  );

  const nextPage = pages.length
    ? Math.max(...pages.map((p) => p.page_no)) + 1
    : 1;

  return (
    <section className="soft-card rounded-2xl p-4" data-testid="handwritten-pages">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-heading text-[16px]">Your pages</h3>
        <span className="num-mono text-[11px] text-clay-700">
          {pages.length} of {MAX_PAGES}
        </span>
      </div>

      <p className="mt-1 text-[12px] text-clay-700">
        Photograph each side as you finish it. Nothing reads these images — they
        are here so you can mark your own answer against the rubric, the same
        rubric a typed answer gets.
      </p>

      {state === "error" && (
        <p role="status" className="mt-3 text-[12px] text-rose-700">
          Couldn&apos;t load your pages. Reload the page.
        </p>
      )}

      {error && (
        <p role="status" className="mt-3 text-[12px] text-rose-700" data-testid="handwritten-error">
          {error}
        </p>
      )}

      <ul className="mt-3 grid gap-3 sm:grid-cols-2">
        {pages.map((page) => (
          <li
            key={page.id}
            className="rounded-lg border border-[#E7DECB] bg-[#FBF8F2] p-3"
            data-testid="handwritten-page"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="num-mono text-[11px] text-clay-700">
                Page {page.page_no}
              </span>
              {!readOnly && (
                <button
                  type="button"
                  className="link-under text-[11px] text-clay-700"
                  onClick={() => remove(page.page_no)}
                  disabled={busy}
                  data-testid={`handwritten-remove-${page.page_no}`}
                >
                  Remove
                </button>
              )}
            </div>
            {page.url ? (
              page.mime_type === "application/pdf" ? (
                <a
                  className="link-under mt-2 block text-[12px]"
                  href={page.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open page {page.page_no} (PDF)
                </a>
              ) : (
                <img
                  className="mt-2 w-full rounded-md border border-[#E7DECB]"
                  src={page.url}
                  alt={`Page ${page.page_no} of your handwritten answer`}
                />
              )
            ) : (
              // One unreadable page must not take down the view of the other
              // seven, so it says so and the rest still render.
              <p className="mt-2 text-[11px] text-clay-700">
                This page can&apos;t be shown right now.
              </p>
            )}
          </li>
        ))}
      </ul>

      {!readOnly && (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            capture="environment"
            className="text-[12px]"
            disabled={busy || pages.length >= MAX_PAGES}
            onChange={(e) => {
              const file = e.target.files && e.target.files[0];
              if (file) upload(file, nextPage);
              e.target.value = "";
            }}
            data-testid="handwritten-input"
            aria-label={`Add page ${nextPage} of your handwritten answer`}
          />
          {pages.length >= MAX_PAGES && (
            <span className="text-[11px] text-clay-700">
              That&apos;s the maximum. Remove a page to add another.
            </span>
          )}
        </div>
      )}
    </section>
  );
}

HandwrittenPages.propTypes = {
  attemptId: PropTypes.string,
  readOnly: PropTypes.bool,
  onModeChange: PropTypes.func,
};
