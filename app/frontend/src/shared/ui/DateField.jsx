import React, { useEffect, useId, useRef, useState } from "react";
import { DayPicker } from "react-day-picker";
import { enIN } from "date-fns/locale";
import { CalendarDays } from "lucide-react";
import {
  formatDDMMYYYY,
  parseDDMMYYYY,
  isoToLocalDate,
  localDateToIso,
} from "../../shared/forms/dateFormat";

function yearBounds(mode) {
  const now = new Date().getFullYear();
  if (mode === "past") return { from: 1950, to: now };
  if (mode === "future") return { from: now, to: now + 10 };
  return { from: 1950, to: now + 10 };
}

// `value` / `onChange` speak ISO date-only strings (YYYY-MM-DD | null). The
// input always *displays* dd-mm-yyyy. Nothing here uses `new Date(iso)`, so a
// stored date never shifts across timezones.
export default function DateField({
  value = null,
  onChange,
  minDate,
  maxDate,
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
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(formatDDMMYYYY(value));
  const wrapRef = useRef(null);

  // Keep the visible text in sync when the controlled value changes from the
  // outside (reset, programmatic set), but leave mid-edit typing alone.
  useEffect(() => {
    setText(formatDDMMYYYY(value));
  }, [value]);

  useEffect(() => {
    if (!open) return undefined;
    function onDocMouseDown(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open]);

  const { from, to } = yearBounds(mode);
  const selected = isoToLocalDate(value);
  const min = isoToLocalDate(minDate);
  const max = isoToLocalDate(maxDate);

  const disabledMatcher = [];
  if (min) disabledMatcher.push({ before: min });
  if (max) disabledMatcher.push({ after: max });

  function withinRange(iso) {
    if (!iso) return true;
    if (minDate && iso < minDate) return false;
    if (maxDate && iso > maxDate) return false;
    return true;
  }

  function emit(iso) {
    if (onChange) onChange(iso);
  }

  function handleTextChange(e) {
    const raw = e.target.value;
    setText(raw);
    if (raw.trim() === "") {
      emit(null);
      return;
    }
    const iso = parseDDMMYYYY(raw);
    // Reject invalid or out-of-range typed values silently — no emit.
    if (iso && withinRange(iso)) emit(iso);
  }

  function handleSelect(day) {
    const iso = localDateToIso(day);
    if (iso && withinRange(iso)) {
      emit(iso);
      setText(formatDDMMYYYY(iso));
    }
    setOpen(false);
  }

  function handleToday() {
    const iso = localDateToIso(new Date());
    if (withinRange(iso)) {
      emit(iso);
      setText(formatDDMMYYYY(iso));
    }
    setOpen(false);
  }

  function handleClear() {
    emit(null);
    setText("");
    setOpen(false);
  }

  const describedBy =
    [helpText ? `${fieldId}-helper` : null, error ? `${fieldId}-error` : null]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <div className="space-y-1.5" ref={wrapRef}>
      {label && (
        <label
          htmlFor={fieldId}
          className="text-[11px] uppercase tracking-widest text-muted-foreground block"
        >
          {label}
          {required && <span className="text-destructive"> *</span>}
        </label>
      )}
      <div className="relative">
        <input
          id={fieldId}
          name={name}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          placeholder="dd-mm-yyyy"
          value={text}
          disabled={disabled}
          required={required}
          aria-label={label ? undefined : "Date"}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={describedBy}
          onChange={handleTextChange}
          onFocus={() => !disabled && setOpen(true)}
          onClick={() => !disabled && setOpen(true)}
          className="w-full px-4 py-2.5 pr-10 rounded-xl bg-white/80 border border-border text-sm outline-none"
        />
        <button
          type="button"
          tabIndex={-1}
          disabled={disabled}
          aria-label="Open calendar"
          onClick={() => !disabled && setOpen((o) => !o)}
          className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground"
        >
          <CalendarDays className="h-4 w-4" />
        </button>
        {open && !disabled && (
          <div
            role="dialog"
            aria-label="Choose date"
            className="absolute z-50 mt-1 rounded-xl border border-border bg-white p-2 shadow-lg"
          >
            <DayPicker
              mode="single"
              locale={enIN}
              selected={selected}
              defaultMonth={selected}
              captionLayout="dropdown"
              startMonth={new Date(from, 0)}
              endMonth={new Date(to, 11)}
              showOutsideDays={false}
              disabled={disabledMatcher.length ? disabledMatcher : undefined}
              onSelect={handleSelect}
            />
            <div className="flex justify-between gap-2 px-1 pb-1">
              <button
                type="button"
                onClick={handleToday}
                className="text-xs px-2 py-1 rounded-lg border border-border text-muted-foreground hover:bg-muted"
              >
                Today
              </button>
              {value && !required && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="text-xs px-2 py-1 rounded-lg border border-border text-muted-foreground hover:bg-muted"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        )}
      </div>
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
