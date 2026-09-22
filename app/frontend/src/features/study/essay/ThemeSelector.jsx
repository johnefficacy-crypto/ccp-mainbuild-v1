import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";

import ErrorState from "../../../shared/ui/ErrorState";
import EmptyState from "../../../shared/ui/EmptyState";
import { api } from "../../../lib/api";

/**
 * Essay theme picker — the entry step for both essay screens.
 *
 * Reads `GET /api/essay-themes` (PR #1041): shared reference data, no
 * ownership scoping, active themes only unless a caller opts into reserved
 * ones. Response shape is `{ items: [{ id, theme_code, theme_name,
 * description, status }], count }`.
 *
 * Shared by the Idea Canvas and the Spine. The fetch, the four states and the
 * active-vs-reserved rule are identical on both screens, so they live here
 * once; the only per-screen differences are the heading copy and what picking
 * a theme does, and those are props.
 *
 * `status`: the endpoint defaults to active-only, so `reserved` rows normally
 * never arrive. The disabled branch stays because a caller may later ask for
 * them, and a reserved theme must be visible-but-unopenable rather than
 * silently missing.
 */
export default function ThemeSelector({ onPick, title, subtitle }) {
  const [status, setStatus] = useState("loading"); // loading | ready | empty | error
  const [themes, setThemes] = useState([]);

  const load = useCallback(() => {
    let live = true;
    setStatus("loading");
    api
      .get("/api/essay-themes")
      .then((res) => {
        if (!live) return;
        const items = Array.isArray(res?.items) ? res.items : [];
        setThemes(items);
        setStatus(items.length === 0 ? "empty" : "ready");
      })
      .catch(() => {
        if (!live) return;
        // Never fall through to a blank picker: a failed read is its own
        // state, distinct from "the catalogue is genuinely empty".
        setThemes([]);
        setStatus("error");
      });
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => load(), [load]);

  return (
    <section className="space-y-4" data-testid="essay-theme-selector">
      {title && <h1 className="font-heading text-2xl">{title}</h1>}
      {subtitle && <p className="text-sm text-slate-600">{subtitle}</p>}

      {status === "loading" && (
        <p className="text-sm text-slate-500" role="status" data-testid="theme-loading">
          Loading themes…
        </p>
      )}

      {status === "error" && (
        <div data-testid="theme-error">
          <ErrorState
            title="Could not load essay themes"
            message="The theme catalogue could not be reached. Nothing you have written is affected."
            onRetry={load}
          />
        </div>
      )}

      {status === "empty" && (
        <div data-testid="theme-empty">
          <EmptyState
            title="No essay themes available"
            description="The theme catalogue is empty. Once themes are published you will be able to pick one here."
          />
        </div>
      )}

      {status === "ready" && (
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
                    "h-full w-full rounded border p-3 text-left text-sm " +
                    (selectable ? "hover:border-slate-400" : "cursor-not-allowed opacity-50")
                  }
                >
                  <div className="font-medium">{t.theme_name || t.theme_code}</div>
                  {t.description && (
                    <p className="mt-1 text-xs text-slate-600">{t.description}</p>
                  )}
                  <div className="mt-1 text-xs text-slate-500">
                    {selectable ? t.theme_code : `${t.theme_code} · reserved`}
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

ThemeSelector.propTypes = {
  onPick: PropTypes.func.isRequired,
  title: PropTypes.string,
  subtitle: PropTypes.string,
};
