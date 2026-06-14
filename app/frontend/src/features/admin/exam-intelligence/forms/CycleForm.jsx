/**
 * CycleForm — shared controlled form fields for creating/editing an exam cycle.
 *
 * Source of truth: SetupPanel.jsx create-cycle form (more complete — includes
 * source_url and audit-trail reason field absent from GuidedExamWizard's StepCycle).
 *
 * Uses native <input type="date"> for date fields (not DateField) so both
 * GuidedExamWizard (which tests type="date" and data-testid="cycle-*") and
 * SetupPanel can share the same component.
 *
 * Renders fields only; callers supply their own submit/cancel buttons.
 *
 * Used by:
 *   - GuidedExamWizard.jsx (Step 3 — Cycle)
 *   - SetupPanel.jsx (inline create-cycle section)
 */
import React from "react";

export const CYCLE_STATUSES = ["expected", "open", "active", "closed", "completed", "cancelled"];

const DATE_FIELDS = [
  ["notification_date", "Notification date"],
  ["application_start", "Application start"],
  ["application_end", "Application end"],
  ["exam_start", "Exam start"],
  ["exam_end", "Exam end"],
];

const INPUT_CLS = "input";

/**
 * @param {{
 *   values: object,
 *   onChange: (key: string, val: any) => void,
 *   showReason?: boolean,
 * }} props
 */
export default function CycleForm({ values, onChange, showReason = true }) {
  const {
    cycle_name = "",
    year = "",
    status = "expected",
    source_url = "",
    reason = "",
  } = values;

  return (
    <div data-testid="cycle-form">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input
          className={INPUT_CLS}
          style={{ maxWidth: 220 }}
          placeholder="Cycle name"
          value={cycle_name}
          onChange={e => onChange("cycle_name", e.target.value)}
          autoFocus
          data-testid="cycle-name"
        />
        <input
          className={INPUT_CLS}
          style={{ maxWidth: 80 }}
          placeholder="Year"
          type="number"
          value={year}
          onChange={e => onChange("year", e.target.value)}
          data-testid="cycle-year"
        />
        <select
          className={INPUT_CLS}
          style={{ maxWidth: 130 }}
          value={status}
          onChange={e => onChange("status", e.target.value)}
          data-testid="cycle-status"
        >
          {CYCLE_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <input
          className={INPUT_CLS}
          style={{ minWidth: 200 }}
          placeholder="Source URL (optional)"
          value={source_url}
          onChange={e => onChange("source_url", e.target.value)}
          data-testid="cycle-source-url"
        />
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
        {DATE_FIELDS.map(([key, label]) => (
          <div key={key} style={{ minWidth: 170 }}>
            <label style={{ display: "block", fontSize: 11, color: "var(--ink-mute, #888)", marginBottom: 2 }}>
              {label}
            </label>
            <input
              className={INPUT_CLS}
              type="date"
              value={values[key] || ""}
              onChange={e => onChange(key, e.target.value)}
              data-testid={`cycle-${key}`}
            />
          </div>
        ))}
      </div>
      {showReason && (
        <div style={{ marginTop: 8 }}>
          <input
            className={INPUT_CLS}
            style={{ width: "100%" }}
            placeholder="Reason (required, ≥ 8 chars)"
            value={reason}
            onChange={e => onChange("reason", e.target.value)}
            data-testid="cycle-form-reason"
          />
        </div>
      )}
    </div>
  );
}
