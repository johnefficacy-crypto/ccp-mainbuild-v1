import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { api } from "../../../lib/api";

// PyqTagsSidebar — "Real questions on this theme": verified essay-paper PYQs
// tagged to the selected theme, read-only (GET /api/essay-pyq-tags?theme_id=).
// The 100 imported tags are still pending verification, so an EMPTY result is
// the normal, expected state today — it renders a calm "not yet available"
// note, never a broken-looking blank area.
export default function PyqTagsSidebar({ themeId }) {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | ready | error

  useEffect(() => {
    let live = true;
    if (!themeId) return undefined;
    setStatus("loading");
    api
      .get(`/api/essay-pyq-tags?theme_id=${encodeURIComponent(themeId)}`)
      .then((res) => {
        if (!live) return;
        setItems(Array.isArray(res?.items) ? res.items : []);
        setStatus("ready");
      })
      .catch(() => { if (live) setStatus("error"); });
    return () => { live = false; };
  }, [themeId]);

  return (
    <aside
      className="rounded border p-3 text-left w-full"
      data-testid="essay-pyq-tags"
      aria-label="Real questions on this theme"
    >
      <div className="text-xs font-semibold text-slate-700 mb-2">
        Real questions on this theme
      </div>

      {status === "loading" ? (
        <p className="text-xs text-slate-500" data-testid="essay-pyq-tags-loading" role="status">
          Loading…
        </p>
      ) : status === "error" ? (
        <p className="text-xs text-clay-700" data-testid="essay-pyq-tags-error" role="alert">
          Couldn&apos;t load past questions.
        </p>
      ) : items.length === 0 ? (
        <p className="text-xs text-slate-500" data-testid="essay-pyq-tags-empty">
          No verified past-paper questions are tagged to this theme yet. They&apos;ll
          appear here once tagging is verified.
        </p>
      ) : (
        <ul className="space-y-2" data-testid="essay-pyq-tags-list">
          {items.map((t) => (
            <li key={t.id} className="text-xs text-slate-700" data-testid={`essay-pyq-tag-${t.id}`}>
              <span className="num-mono text-slate-400">{t.year ?? "—"}</span>{" "}
              {t.question_text || "(untitled question)"}
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

PyqTagsSidebar.propTypes = {
  themeId: PropTypes.string.isRequired,
};
