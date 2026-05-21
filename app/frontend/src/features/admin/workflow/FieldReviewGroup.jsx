import React, { useMemo, useState } from "react";

// Post-scoped fields are reviewed in the per-post table
// (PostEligibilityReviewGroup), not here, so we never repeat them once per
// post in this flat list.
const POST_SCOPED_FIELDS = new Set(["requires_domicile"]);

const FIELD_TYPES = {
  apply_start_date: "date",
  apply_end_date: "date",
  notification_date: "date",
  total_vacancies: "integer",
  min_age: "integer",
  max_age: "integer",
  official_notification_url: "url",
  official_apply_url: "url",
  requires_domicile: "boolean",
};

const FIELD_LABELS = {
  apply_start_date: "Apply start date",
  apply_end_date: "Apply end date",
  notification_date: "Notification date",
  total_vacancies: "Total vacancies",
  official_notification_url: "Official notification URL",
  official_apply_url: "Official apply URL",
  organization_name: "Organization",
  title: "Title",
};

function fieldType(name) { return FIELD_TYPES[name] || "text"; }
function fieldLabel(name) { return FIELD_LABELS[name] || name; }

function parseCorrection(type, raw) {
  if (raw === "" || raw == null) return null;
  if (type === "integer") {
    const n = Number(raw);
    if (!Number.isFinite(n) || !Number.isInteger(n)) throw new Error("Enter a whole number.");
    return n;
  }
  if (type === "number") {
    const n = Number(raw);
    if (!Number.isFinite(n)) throw new Error("Enter a number.");
    return n;
  }
  if (type === "boolean") return raw === "true";
  if (type === "url") {
    try { new URL(raw); return raw; } catch { throw new Error("Enter a valid URL (https://…)."); }
  }
  if (type === "date") return raw;
  return raw;
}

function formatValue(v) {
  if (v == null || v === "") return "—";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

// A field with no extracted value can't be "verified" — there is nothing to
// confirm. It must be corrected (given a value) or flagged instead. Numbers
// and booleans (including 0 / false) count as real values.
function isBlank(v) {
  if (v == null) return true;
  if (typeof v === "string") return v.trim() === "";
  if (Array.isArray(v)) return v.length === 0;
  return false;
}

const STATUS_BADGE = {
  verified: { cls: "badge resolved", text: "verified" },
  unverified: { cls: "badge blocker", text: "unverified" },
  // "rejected" is non-terminal: the admin flagged the value as wrong and a
  // correction is owed before promotion. It must read as action-owed, so it
  // uses the destructive blocker token rather than the muted neutral one.
  rejected: { cls: "badge blocker", text: "Flagged — correction required" },
  corrected: { cls: "badge info", text: "corrected" },
  suggested: { cls: "badge pending", text: "suggested" },
};

function EvidenceSnippet({ details }) {
  if (!details) return null;
  const text = details.evidence_text;
  const page = details.page_number ?? details.source_page;
  const conf = details.confidence;
  if (!text && page == null && conf == null) return null;
  const parts = [];
  if (page != null) parts.push(`page ${page}`);
  if (conf != null) parts.push(`confidence ${Math.round(Number(conf) * 100)}%`);
  return (
    <div className="fld-evidence">
      {parts.length ? <span>{parts.join(" · ")} · </span> : null}
      {text ? `"${text}"` : "No source snippet captured."}
    </div>
  );
}

// One field row. The common path is a single "Verify" click that confirms
// the scraped value as-is. Correcting and flagging are tucked behind an
// "Edit" toggle so the list stays scannable.
function FieldRow({ field, value, status, details, blocking, entityScope, onFieldAction }) {
  const type = fieldType(field);
  const [editing, setEditing] = useState(false);
  const [correction, setCorrection] = useState("");
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [localError, setLocalError] = useState("");
  const heading = fieldLabel(field);
  const statusKey = status || "unverified";
  const meta = STATUS_BADGE[statusKey] || { cls: "badge neutral", text: statusKey };
  const verified = statusKey === "verified";
  const correctedValue = details?.corrected_value;
  // A corrected field carries its new value; otherwise use the scraped value.
  const effectiveValue = statusKey === "corrected" && correctedValue != null ? correctedValue : value;
  const blank = isBlank(effectiveValue);

  const verify = () => { if (!blank) onFieldAction(field, "verify", null, entityScope); };

  const saveCorrection = () => {
    setLocalError("");
    let parsed;
    try { parsed = parseCorrection(type, correction); }
    catch (e) { setLocalError(e.message); return; }
    if (parsed == null) { setLocalError("Enter a corrected value."); return; }
    onFieldAction(field, "correct", parsed, entityScope);
    setEditing(false);
    setCorrection("");
  };

  const submitReject = () => {
    const reason = rejectReason.trim();
    if (!reason) { setLocalError("Reason is required to flag."); return; }
    onFieldAction(field, "reject", null, { ...entityScope, notes: reason });
    setRejecting(false);
    setRejectReason("");
  };

  return (
    <div className="fld" id={`field-${field}`} data-field={field}>
      <div className="fld-head">
        <span className="fld-key">
          {heading}
          {blocking ? <span title="Required — blocks promotion" aria-label="required" style={{ color: "var(--blocker)", fontWeight: 700, marginLeft: 4 }}>*</span> : null}
        </span>
        <span className={meta.cls}>{meta.text}</span>
      </div>
      <div className="fld-val">
        {statusKey === "corrected" && correctedValue != null && correctedValue !== value ? (
          <>
            <span style={{ textDecoration: "line-through", color: "var(--ink-mute)" }}>{formatValue(value)}</span>
            {" → "}
            <strong>{formatValue(correctedValue)}</strong>
          </>
        ) : (
          formatValue(value)
        )}
      </div>
      <EvidenceSnippet details={details} />
      {statusKey === "rejected" && details?.reviewer_notes ? (
        <div className="anno" style={{ marginTop: 4 }} data-testid={`field-flag-reason-${field}`}>
          Flag reason: {details.reviewer_notes}
        </div>
      ) : null}
      {localError ? <div className="err-row" style={{ marginTop: 6 }}>{localError}</div> : null}

      {verified ? null : rejecting ? (
        <div className="stack" style={{ marginTop: 8 }}>
          <textarea
            className="input"
            value={rejectReason}
            onChange={(e) => { setRejectReason(e.target.value); if (e.target.value.trim()) setLocalError(""); }}
            placeholder="Why is this evidence wrong? (required)"
            rows={2}
            aria-label={`Flag reason for ${heading}`}
          />
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button type="button" className="btn small" onClick={() => { setRejecting(false); setRejectReason(""); setLocalError(""); }}>Cancel</button>
            <button type="button" className="btn primary small" onClick={submitReject}>Confirm flag</button>
          </div>
        </div>
      ) : editing ? (
        <div className="row" style={{ marginTop: 8 }}>
          {type === "boolean" ? (
            <select className="input" style={{ flex: 1, minWidth: 120 }} value={correction} onChange={(e) => setCorrection(e.target.value)} aria-label={`Corrected ${heading}`}>
              <option value="">Select…</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          ) : (
            <input
              type={type === "date" ? "date" : type === "url" ? "url" : (type === "integer" || type === "number") ? "number" : "text"}
              step={type === "integer" ? "1" : undefined}
              className="input"
              style={{ flex: 1, minWidth: 140 }}
              value={correction}
              onChange={(e) => setCorrection(e.target.value)}
              placeholder={type === "date" ? "YYYY-MM-DD" : type === "url" ? "https://…" : "Corrected value"}
              aria-label={`Corrected value for ${heading}`}
            />
          )}
          <button type="button" className="btn primary small" disabled={correction === ""} onClick={saveCorrection}>Save</button>
          <button type="button" className="btn ghost small" onClick={() => { setEditing(false); setCorrection(""); setLocalError(""); }}>Cancel</button>
        </div>
      ) : statusKey === "rejected" ? (
        <div className="row" style={{ marginTop: 8 }}>
          <button
            type="button"
            className="btn primary small"
            onClick={() => { setEditing(true); setLocalError(""); }}
            data-testid={`field-correct-${field}`}
          >
            Correct value
          </button>
          <button
            type="button"
            className="btn ghost small"
            onClick={verify}
            disabled={blank}
            title={blank ? "No value extracted — correct this field" : undefined}
            data-testid={`field-verify-${field}`}
          >
            Verify instead
          </button>
        </div>
      ) : (
        <div className="row" style={{ marginTop: 8 }}>
          <button
            type="button"
            className="btn small"
            onClick={verify}
            disabled={blank}
            title={blank ? "No value extracted — correct or flag this field" : undefined}
            data-testid={`field-verify-${field}`}
          >
            Verify
          </button>
          <button type="button" className="btn ghost small" onClick={() => { setEditing(true); setLocalError(""); }}>Edit</button>
          <button type="button" className="btn ghost small" onClick={() => { setRejecting(true); setLocalError(""); }} aria-label={`Flag ${heading}`}>Flag</button>
          {blank ? <span className="anno" style={{ marginLeft: 4 }}>No value — correct or flag</span> : null}
        </div>
      )}
    </div>
  );
}

function findDetail(detailsList, field) {
  if (!Array.isArray(detailsList)) return null;
  return detailsList.find((d) => (d?.field_name || "") === field
    && (d?.entity_type || "other").toLowerCase() === "other"
    && !((d?.entity_key || "").trim())) || null;
}

function statusFor(field, evidence, evidenceDetails) {
  const detail = findDetail(evidenceDetails, field);
  return { status: detail?.reviewer_status || evidence?.[field] || "unverified", detail };
}

function Row({ field, blocking, extracted, evidence, evidenceDetails, onFieldAction }) {
  const { status, detail } = statusFor(field, evidence, evidenceDetails);
  return (
    <FieldRow
      field={field}
      value={extracted?.[field]}
      status={status}
      details={detail}
      blocking={blocking}
      entityScope={{ entity_type: "other", entity_key: null }}
      onFieldAction={onFieldAction}
    />
  );
}

export default function FieldReviewGroup({ extracted, evidence, evidenceDetails, requiredFields, recommendedFields, onFieldAction }) {
  const details = useMemo(() => evidenceDetails || [], [evidenceDetails]);
  // Post-scoped fields live in the per-post table, so they are excluded from
  // this flat list to avoid repeating a field once per post.
  const required = useMemo(
    () => (requiredFields || []).filter((f) => !POST_SCOPED_FIELDS.has(f)),
    [requiredFields],
  );
  const recommended = useMemo(
    () => (recommendedFields || []).filter((f) => !POST_SCOPED_FIELDS.has(f) && !required.includes(f)),
    [recommendedFields, required],
  );

  // Fields the "Verify all" shortcut still needs to confirm. We exclude the
  // two terminal gate-pass states (verified, corrected) and — separately —
  // explicitly-flagged fields: the admin chose to reject those, so a bulk
  // "Verify all" must not silently re-verify them. Each flagged field needs
  // its own per-field correction instead. Blank fields are also skipped
  // because there is nothing to verify.
  const pending = useMemo(() => {
    const all = [...required, ...recommended];
    return all.filter((f) => {
      const { status, detail } = statusFor(f, evidence, details);
      if (status === "verified" || status === "corrected") return false;
      // Non-terminal but requires explicit per-field correction, not bulk
      // re-verify — never auto-override the admin's flag.
      if (status === "rejected") return false;
      const effective = detail?.corrected_value != null ? detail.corrected_value : extracted?.[f];
      return !isBlank(effective);
    });
  }, [required, recommended, evidence, details, extracted]);

  // Any field still blocking promotion. Only the terminal gate-pass states
  // (verified, corrected) count as resolved; flagged ("rejected") is
  // non-terminal and stays unresolved until corrected.
  const anyUnresolved = useMemo(() => [...required, ...recommended].some((f) => {
    const { status } = statusFor(f, evidence, details);
    return status !== "verified" && status !== "corrected";
  }), [required, recommended, evidence, details]);

  // Bucket every field for the header summary. "reviewed" = terminal
  // gate-pass (verified|corrected); "flagged" = rejected (blocks promotion,
  // correction owed); "pending" = everything still awaiting first review.
  const counts = useMemo(() => {
    const all = [...required, ...recommended];
    let reviewed = 0;
    let flagged = 0;
    let pendingReview = 0;
    for (const f of all) {
      const { status } = statusFor(f, evidence, details);
      if (status === "verified" || status === "corrected") reviewed += 1;
      else if (status === "rejected") flagged += 1;
      else pendingReview += 1;
    }
    return { total: all.length, reviewed, flagged, pending: pendingReview };
  }, [required, recommended, evidence, details]);

  const verifyAll = async () => {
    for (const field of pending) {
      // eslint-disable-next-line no-await-in-loop
      await onFieldAction(field, "verify", null, { entity_type: "other", entity_key: null });
    }
  };

  if (!required.length && !recommended.length) return null;

  return (
    <div className="stack" data-testid="field-review-group">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <div className="lbl">Verify fields</div>
        {pending.length ? (
          <button type="button" className="btn small" onClick={verifyAll} data-testid="field-verify-all">
            Verify all ({pending.length})
          </button>
        ) : counts.flagged > 0 ? (
          <span className="badge blocker" data-testid="field-review-flagged-block">Flagged fields block promotion</span>
        ) : anyUnresolved ? (
          <span className="anno">Blank fields need a correction or flag</span>
        ) : (
          <span className="badge resolved">all verified</span>
        )}
      </div>
      <div
        className="anno"
        data-testid="field-review-summary"
        style={counts.flagged > 0 ? { color: "var(--blocker)", fontWeight: 600 } : undefined}
      >
        {counts.reviewed}/{counts.total} reviewed
        {" · "}
        <span
          data-testid="field-review-flagged-count"
          style={counts.flagged > 0 ? { color: "var(--blocker)", fontWeight: 700 } : undefined}
        >
          {counts.flagged} flagged
        </span>
        {" · "}
        {counts.pending} pending
      </div>
      <div className="anno">
        Promotion is blocked until fields marked <span style={{ color: "var(--blocker)", fontWeight: 700 }}>*</span> are verified or corrected.
        {counts.flagged > 0 ? " Flagged fields must be corrected first." : null}
      </div>
      {required.length ? (
        <div className="fld-list">
          {required.map((field) => (
            <Row key={field} field={field} blocking extracted={extracted} evidence={evidence} evidenceDetails={details} onFieldAction={onFieldAction} />
          ))}
        </div>
      ) : null}
      {recommended.length ? (
        <details className="fx-disclosure" data-testid="field-review-optional">
          <summary className="fx-disclosure-summary">Optional quality checks (not blocking)</summary>
          <div className="fld-list" style={{ marginTop: 8 }}>
            {recommended.map((field) => (
              <Row key={field} field={field} blocking={false} extracted={extracted} evidence={evidence} evidenceDetails={details} onFieldAction={onFieldAction} />
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}
