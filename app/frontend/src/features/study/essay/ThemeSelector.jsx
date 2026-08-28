import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { api } from "../../../lib/api";

// ThemeSelector — entry point before the canvas loads.
//
// DEFERRED (see PR body): there is no aspirant-facing essay-themes list
// endpoint yet — only the admin CMS route (gated behind exam_intelligence.cms).
// This component reads from the natural future endpoint GET /api/essay-themes
// and is forward-compatible: the moment that route lands, the picker lights up.
// Until then the fetch fails and we fall back to a clear "not available yet"
// note PLUS a manual theme-id entry, so the fully-wired canvas is still
// exercisable against a real theme_id today (the canvas itself is NOT stubbed).
//
// Only `active` themes are selectable; `reserved` themes are shown but
// disabled (not yet opened for aspirant brainstorming).
export default function ThemeSelector({ onPick }) {
  const [status, setStatus] = useState("loading"); // loading | ready | unavailable
  const [themes, setThemes] = useState([]);
  const [manual, setManual] = useState("");

  useEffect(() => {
    let live = true;
    api
      .get("/api/essay-themes")
      .then((res) => {
        if (!live) return;
        const items = Array.isArray(res?.items) ? res.items : [];
        setThemes(items);
        setStatus("ready");
      })
      .catch(() => { if (live) setStatus("unavailable"); });
    return () => { live = false; };
  }, []);

  return (
    <section className="space-y-4" data-testid="essay-theme-selector">
      <h1 className="font-heading text-2xl">Essay Idea Canvas</h1>
      <p className="text-sm text-slate-600">
        Pick an essay theme to open its idea canvas — six thematic lenses, a
        helper rail, and your own draggable stickies.
      </p>

      {status === "loading" ? (
        <p className="text-sm text-slate-500" role="status" data-testid="theme-loading">
          Loading themes…
        </p>
      ) : status === "ready" && themes.length > 0 ? (
        <ul className="grid gap-2 sm:grid-cols-2" data-testid="theme-list">
          {themes.map((t) => {
            const selectable = t.status === "active";
            return (
              <li key={t.id}>
                <button
                  type="button"
                  disabled={!selectable}
                  onClick={() => onPick(t.id, t.theme_name)}
                  data-testid={`theme-option-${t.id}`}
                  className={
                    "w-full rounded border p-3 text-left text-sm " +
                    (selectable
                      ? "hover:border-slate-400"
                      : "cursor-not-allowed opacity-50")
                  }
                >
                  <div className="font-medium">{t.theme_name || t.theme_code}</div>
                  <div className="text-xs text-slate-500">
                    {selectable ? t.theme_code : `${t.theme_code} · reserved`}
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        // Deferred/empty: no aspirant themes endpoint yet, or it returned none.
        // Fall back to manual entry so the canvas is still reachable.
        <div className="rounded border p-3" data-testid="theme-unavailable">
          <p className="text-sm text-slate-600">
            The theme picker isn&apos;t available yet (no aspirant-facing themes
            endpoint). Enter a theme id to open its canvas.
          </p>
          <form
            className="mt-2 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (manual.trim()) onPick(manual.trim(), null);
            }}
          >
            <input
              value={manual}
              onChange={(e) => setManual(e.target.value)}
              placeholder="theme_id (uuid)"
              className="input flex-1 text-sm"
              data-testid="theme-manual-input"
              aria-label="Theme id"
            />
            <button type="submit" className="btn btn-ghost text-sm" data-testid="theme-manual-open">
              Open
            </button>
          </form>
        </div>
      )}
    </section>
  );
}

ThemeSelector.propTypes = {
  onPick: PropTypes.func.isRequired,
};
