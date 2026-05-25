import React, { useMemo, useState } from "react";
import { Copy, X } from "lucide-react";

/**
 * Presentational searchable single-select.
 *
 * Stateless w.r.t. data fetching — the caller passes already-normalized
 * `options` ({ id, label, secondary }) and owns the selected `value` (an
 * id string). Used to replace raw UUID text inputs with a human-readable
 * picker while still submitting the underlying id.
 */
export default function Combobox({
  value = "",
  onChange,
  options = [],
  loading = false,
  placeholder = "Search…",
  testId = "combobox",
  disabled = false,
}) {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);

  const selected = useMemo(
    () => options.find((o) => o.id === value) || null,
    [options, value],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((o) =>
      [o.label, o.secondary, o.id]
        .filter(Boolean)
        .some((s) => String(s).toLowerCase().includes(q)),
    );
  }, [options, query]);

  function copyId() {
    if (value && typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(value);
    }
  }

  return (
    <div className="relative">
      {value ? (
        <div
          className="flex items-center gap-2 mb-1 text-xs"
          data-testid={`${testId}-selected`}
        >
          <span className="font-medium truncate">
            {selected ? selected.label : "(unknown — id not in list)"}
          </span>
          <span className="font-mono text-muted-foreground truncate" title={value}>
            {value.slice(0, 8)}…
          </span>
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground"
            onClick={copyId}
            title="Copy UUID"
            aria-label="Copy UUID"
            data-testid={`${testId}-copy`}
          >
            <Copy className="h-3 w-3" />
          </button>
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground"
            onClick={() => onChange("")}
            title="Clear selection"
            aria-label="Clear selection"
            data-testid={`${testId}-clear`}
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      ) : null}

      <input
        type="text"
        value={query}
        disabled={disabled}
        placeholder={selected ? selected.label : placeholder}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
        data-testid={testId}
        autoComplete="off"
      />

      {focused ? (
        <div
          className="absolute z-10 mt-1 w-full max-h-52 overflow-auto rounded border border-border/60 bg-card shadow"
          data-testid={`${testId}-options`}
        >
          {loading ? (
            <div className="px-2 py-1.5 text-xs text-muted-foreground">Loading…</div>
          ) : filtered.length === 0 ? (
            <div className="px-2 py-1.5 text-xs text-muted-foreground">No matches.</div>
          ) : (
            filtered.map((o) => (
              <button
                key={o.id}
                type="button"
                // mouseDown fires before the input's blur, so selection
                // registers even though blur would otherwise close the list.
                onMouseDown={(e) => {
                  e.preventDefault();
                  onChange(o.id);
                  setQuery("");
                  setFocused(false);
                }}
                className="block w-full text-left px-2 py-1.5 text-xs hover:bg-muted"
                data-testid={`${testId}-option-${o.id}`}
              >
                <span className="font-medium">{o.label}</span>
                {o.secondary ? (
                  <span className="text-muted-foreground"> · {o.secondary}</span>
                ) : null}
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
