import PropTypes from "prop-types";
import React, { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../../lib/api";

/**
 * The pages of a handwritten attempt, shown back to the aspirant.
 *
 * WHAT THIS REPAIRS. "My answers" rendered `answer_text` and nothing else, so
 * a submitted handwritten attempt — one with a real page in storage — read
 * "This attempt has no text yet." The images were fetched, signed and
 * returned by the API, and then thrown away by the view.
 *
 * A handwritten attempt has NO word count and NO text by design: nothing reads
 * these images. Its pages are the answer, so this renders them as thumbnails
 * in page order, each opening full size.
 *
 * THE URLS EXPIRE. They are signed for fifteen minutes so a copied link is not
 * a permanent share of someone's answer, which means a tab left open outlives
 * them. Two different failures follow, and they are not the same message:
 *
 *   * an expired URL is recoverable — refetch once, silently, and the image
 *     loads;
 *   * an object that is not there is not — say so, on that page, and leave the
 *     other pages alone.
 *
 * So the first load failure on a page triggers one refresh; a second failure
 * on the same page is reported as missing.
 */

/** Refresh at 80% of the URL's life: before it expires, not after. */
export function refreshDelayMs(ttlSeconds) {
  const ttl = Number(ttlSeconds);
  if (!Number.isFinite(ttl) || ttl <= 0) return null;
  return Math.max(30, Math.floor(ttl * 0.8)) * 1000;
}

/** "3 pages", "1 page", "0 pages" — never "no text yet". */
export function pageCountLabel(count) {
  const n = Number(count) || 0;
  return `${n} ${n === 1 ? "page" : "pages"}`;
}

export default function AttemptPages({
  attemptId,
  pages: initial,
  ttlSeconds,
  emptyLabel,
}) {
  const [pages, setPages] = useState(initial || []);
  const [refreshing, setRefreshing] = useState(false);
  const [open, setOpen] = useState(null);
  // page id → how many times its image has failed to load. One is an expired
  // URL; two is an object that is not coming back.
  const misses = useRef({});

  useEffect(() => {
    setPages(initial || []);
    misses.current = {};
  }, [initial]);

  const refresh = useCallback(() => {
    if (!attemptId) return Promise.resolve();
    setRefreshing(true);
    return api
      .get(`/api/study/descriptive/attempts/${attemptId}/pages`)
      .then((d) => {
        if (Array.isArray(d?.pages)) setPages(d.pages);
      })
      .catch(() => {
        /* The previous URLs stay on screen; a failed refresh is not a reason
           to blank a page that may still be loading from the old one. */
      })
      .finally(() => setRefreshing(false));
  }, [attemptId]);

  // Re-sign before the URLs run out, so a tab left open on an answer keeps
  // showing it instead of turning into a wall of broken images.
  useEffect(() => {
    const delay = refreshDelayMs(ttlSeconds);
    if (!delay || !pages.length) return undefined;
    const timer = setTimeout(refresh, delay);
    return () => clearTimeout(timer);
  }, [ttlSeconds, pages, refresh]);

  const onImageError = useCallback(
    (page) => {
      const key = String(page.id);
      const seen = (misses.current[key] || 0) + 1;
      misses.current = { ...misses.current, [key]: seen };
      if (seen === 1) {
        refresh();
      } else {
        // Force the "missing" branch to render for this page alone.
        setPages((current) =>
          current.map((p) =>
            String(p.id) === key ? { ...p, url: null, url_error: "object_missing" } : p,
          ),
        );
      }
    },
    [refresh],
  );

  if (!pages.length) {
    return (
      <p className="text-[12.5px] text-clay-700" data-testid="attempt-pages-empty">
        {emptyLabel || `${pageCountLabel(0)} — nothing was uploaded for this answer.`}
      </p>
    );
  }

  return (
    <div data-testid="attempt-pages">
      <p className="num-mono text-[11px] text-clay-700" data-testid="attempt-pages-count">
        {pageCountLabel(pages.length)}
        {refreshing ? " · refreshing…" : ""}
      </p>

      <ul className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {pages.map((page) => (
          <li key={page.id} data-testid="attempt-page">
            {page.url ? (
              page.mime_type === "application/pdf" ? (
                <a
                  className="link-under block rounded-md border border-[#E7DECB] bg-[#FFFDF9] p-3 text-[12px]"
                  href={page.url}
                  target="_blank"
                  rel="noreferrer"
                  data-testid={`attempt-page-pdf-${page.page_no}`}
                >
                  Page {page.page_no} (PDF)
                </a>
              ) : (
                <button
                  type="button"
                  className="block w-full"
                  onClick={() => setOpen(page)}
                  data-testid={`attempt-page-open-${page.page_no}`}
                  aria-label={`Open page ${page.page_no} full size`}
                >
                  <img
                    className="w-full rounded-md border border-[#E7DECB]"
                    // Eight photos of A4 is several megabytes; below the fold
                    // they should cost nothing until they are scrolled to.
                    loading="lazy"
                    decoding="async"
                    src={page.url}
                    onError={() => onImageError(page)}
                    alt={`Page ${page.page_no} of this handwritten answer`}
                  />
                </button>
              )
            ) : (
              // PER PAGE, never for the whole attempt: one unreadable page
              // must not hide the seven that are fine.
              <p
                role="status"
                className="rounded-md border border-[#E7DECB] bg-[#FBF8F2] p-3 text-[11px] text-rose-700"
                data-testid={`attempt-page-error-${page.page_no}`}
              >
                {page.url_error === "object_missing"
                  ? `Page ${page.page_no} is missing from storage.`
                  : `Page ${page.page_no} can't be shown right now.`}{" "}
                <button
                  type="button"
                  className="link-under text-clay-700"
                  onClick={refresh}
                  data-testid={`attempt-page-retry-${page.page_no}`}
                >
                  Try again
                </button>
              </p>
            )}
          </li>
        ))}
      </ul>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal="true"
          aria-label={`Page ${open.page_no} full size`}
          onClick={() => setOpen(null)}
          data-testid="attempt-page-full"
        >
          <img
            className="max-h-full max-w-full rounded-md"
            src={open.url}
            alt={`Page ${open.page_no} of this handwritten answer, full size`}
          />
          <button
            type="button"
            className="absolute right-4 top-4 rounded-md bg-[#FFFDF9] px-3 py-1 text-[12px]"
            onClick={() => setOpen(null)}
            data-testid="attempt-page-full-close"
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}

AttemptPages.propTypes = {
  attemptId: PropTypes.string,
  pages: PropTypes.array,
  ttlSeconds: PropTypes.number,
  emptyLabel: PropTypes.string,
};
