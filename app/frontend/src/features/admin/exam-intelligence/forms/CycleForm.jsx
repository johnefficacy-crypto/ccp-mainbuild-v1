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
import React, { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

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
/**
 * Source registry picker embedded in CycleForm.
 * Selecting a source auto-fills the source_url field from official_url.
 * Toggle "Show discovery/aggregator sources" refetches with include_discovery=true.
 */
function SourcePicker({ onSelect }) {
  const [includeDiscovery, setIncludeDiscovery] = useState(false);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const result = api.get(`/api/admin/exam-intelligence-cms/source-registry?include_discovery=${includeDiscovery}&limit=200`);
    if (result && typeof result.then === "function") {
      result
        .then((d) => { if (active) setSources(Array.isArray(d?.items) ? d.items : []); })
        .catch(() => {})
        .finally(() => { if (active) setLoading(false); });
    } else {
      setLoading(false);
    }
    return () => { active = false; };
  }, [includeDiscovery]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <select
        className="input"
        style={{ minWidth: 220 }}
        defaultValue=""
        onChange={(e) => {
          const src = sources.find((s) => s.id === e.target.value);
          if (src) onSelect(src);
        }}
        data-testid="cycle-source-picker"
      >
        <option value="">Pick source registry…</option>
        {loading && <option disabled>Loading…</option>}
        {sources.map((s) => (
          <option key={s.id} value={s.id}>
            {s.source_name}{s.source_type ? ` (${s.source_type})` : ""}
          </option>
        ))}
      </select>
      <label style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--ink-mute)" }}>
        <input
          type="checkbox"
          checked={includeDiscovery}
          onChange={(e) => setIncludeDiscovery(e.target.checked)}
          data-testid="cycle-source-picker-toggle"
        />
        Show discovery/aggregator sources
      </label>
    </div>
  );
}

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
        <SourcePicker onSelect={(src) => onChange("source_url", src.official_url || "")} />
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
