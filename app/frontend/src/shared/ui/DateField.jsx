import React, { useId } from "react";

// `value` / `onChange` speak ISO date-only strings (YYYY-MM-DD | null). This
// is now a thin wrapper around the browser's native `<input type="date">`,
// whose value IDL attribute is already YYYY-MM-DD — so there is no text
// parsing, no `Date` object round-trip, and therefore no timezone drift.
// (Previously this wrapped react-day-picker behind a dd-mm-yyyy text input;
// see docs/status/career-copilot-checklist.md, "Slow/heavy date inputs".)
export default function DateField({
  value = null,
  onChange,
  minDate,
  maxDate,
  // `mode` ("any" | "past" | "future") is accepted for backward compatibility
  // with existing callers but, as before, is purely advisory — it never
  // constrained which dates could be selected/typed (only minDate/maxDate do).
  mode = "any",
  required = false,
  label,
  helpText,
  error,
  name,
  id,
  disabled = false,
}) {
  const generatedId = useId();
  const fieldId = id || generatedId;

  function withinRange(iso) {
    if (!iso) return true;
    if (minDate && iso < minDate) return false;
    if (maxDate && iso > maxDate) return false;
    return true;
  }

  function handleChange(e) {
    const iso = e.target.value || null;
    // Defense in depth: the `min`/`max` attributes already steer the native
    // picker UI, but a keyboard-typed value can still land out of range.
    // Silently reject it, same as the previous implementation.
    if (iso && !withinRange(iso)) return;
    if (onChange) onChange(iso);
  }

  const describedBy =
    [helpText ? `${fieldId}-helper` : null, error ? `${fieldId}-error` : null]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <div className="space-y-1.5">
      {label && (
        <label
          htmlFor={fieldId}
          className="text-[11px] uppercase tracking-widest text-muted-foreground block"
        >
          {label}
          {required && <span className="text-destructive"> *</span>}
        </label>
      )}
      <input
        id={fieldId}
        name={name}
        type="date"
        value={value || ""}
        min={minDate || undefined}
        max={maxDate || undefined}
        disabled={disabled}
        required={required}
        aria-label={label ? undefined : "Date"}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={describedBy}
        onChange={handleChange}
        className="w-full px-4 py-2.5 rounded-xl bg-white/80 border border-border text-sm outline-none"
      />
      {helpText && (
        <p id={`${fieldId}-helper`} className="text-xs text-muted-foreground">
          {helpText}
        </p>
      )}
      {error && (
        <p id={`${fieldId}-error`} className="text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
