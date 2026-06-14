/**
 * CycleForm — shared controlled form fields for creating/editing an exam cycle.
 *
 * Source of truth: SetupPanel.jsx create-cycle form (more complete — includes
 * source_url and audit-trail reason field absent from GuidedExamWizard's StepCycle).
 *
 * Renders fields only; callers supply their own submit/cancel buttons.
 *
 * Used by:
 *   - GuidedExamWizard.jsx (Step 3 — Cycle)
 *   - SetupPanel.jsx (inline create-cycle section)
 */
import React from "react";
import DateField from "../../../../shared/ui/DateField";

export const CYCLE_STATUSES = ["expected", "open", "active", "closed", "completed", "cancelled"];

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
    notification_date = null,
    application_start = null,
    application_end = null,
    exam_start = null,
    exam_end = null,
    source_url = "",
    reason = "",
  } = values;

  return (
    <div data-testid="cycle-form">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input
          className="input"
          style={{ maxWidth: 220 }}
          placeholder="Cycle name"
          value={cycle_name}
          onChange={e => onChange("cycle_name", e.target.value)}
          autoFocus
          data-testid="cycle-form-name"
        />
        <input
          className="input"
          style={{ maxWidth: 80 }}
          placeholder="Year"
          type="number"
          value={year}
          onChange={e => onChange("year", e.target.value)}
          data-testid="cycle-form-year"
        />
        <select
          className="input"
          style={{ maxWidth: 130 }}
          value={status}
          onChange={e => onChange("status", e.target.value)}
          data-testid="cycle-form-status"
        >
          {CYCLE_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <input
          className="input"
          style={{ minWidth: 200 }}
          placeholder="Source URL (optional)"
          value={source_url}
          onChange={e => onChange("source_url", e.target.value)}
          data-testid="cycle-form-source-url"
        />
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
        <div style={{ minWidth: 170 }}>
          <DateField value={notification_date} onChange={v => onChange("notification_date", v)}
            mode="any" label="Notification date" name="cycle_notif_date" id="cycle-form-notif-date" />
        </div>
        <div style={{ minWidth: 170 }}>
          <DateField value={application_start} onChange={v => onChange("application_start", v)}
            mode="any" label="Application start" name="cycle_app_start" id="cycle-form-app-start" />
        </div>
        <div style={{ minWidth: 170 }}>
          <DateField value={application_end} onChange={v => onChange("application_end", v)}
            mode="any" label="Application end" name="cycle_app_end" id="cycle-form-app-end" />
        </div>
        <div style={{ minWidth: 170 }}>
          <DateField value={exam_start} onChange={v => onChange("exam_start", v)}
            mode="any" label="Exam start" name="cycle_exam_start" id="cycle-form-exam-start" />
        </div>
        <div style={{ minWidth: 170 }}>
          <DateField value={exam_end} onChange={v => onChange("exam_end", v)}
            mode="any" label="Exam end" name="cycle_exam_end" id="cycle-form-exam-end" />
        </div>
      </div>
      {showReason && (
        <div style={{ marginTop: 8 }}>
          <input
            className="input"
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
