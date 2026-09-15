/**
 * Content Card Library — read-only governance browse over `content_cards`
 * (migration 291, CONTENT-01).
 *
 * ONE component for every card type. The type is a PROP, not a copy of this
 * file: before the merge there were two of these, the second made by copying the
 * first, and a third type would have meant a third copy. Adding a type now means
 * adding an entry to CARD_TYPES in contentStudioApi.js and nothing here.
 *
 * There is NO create/edit affordance here — the authoring RPC is still a later
 * governed slice. The review transition lives in the Review Queue tab, and
 * activation is a separate, higher-trust authority again (content_studio.activate).
 * formula_latex renders through the existing KaTeX path (MathRenderer), matching
 * how question math already renders.
 *
 * applicability_rule is deliberately absent. Migration 291 dropped the column:
 * it was declared, stored, rendered here, and never read by anything — no
 * matcher ever existed. Rendering a dropped column would print "{}" forever.
 */
import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";
import useApiCollection from "../../../lib/hooks/useApiCollection";
import { ErrorState, EmptyState } from "../../../shared/ui/core";
import MathRenderer from "../../study/mocks/components/questions/shared/MathRenderer";
import { CARD_TYPES } from "./contentStudioApi";

const REVIEWER_STATUSES = ["", "pending", "needs_correction", "verified", "rejected"];
const PAGE_SIZE = 50;

// useApiCollection serializes params through `new URLSearchParams(params)`, which
// stringifies `undefined` as the literal "undefined" — the backend would then
// filter on card_subtype='undefined' etc. and return nothing. Mirror
// PromptLibrary's cleanParams: emit ONLY set filters plus limit/offset, so the
// default (unfiltered) request carries no stray keys. Exported for regression test.
export function buildListParams(filters, offset) {
  const params = { limit: PAGE_SIZE, offset };
  if (filters.content_type) params.content_type = filters.content_type;
  if (filters.card_subtype) params.card_subtype = filters.card_subtype;
  if (filters.reviewer_status) params.reviewer_status = filters.reviewer_status;
  const q = (filters.q || "").trim();
  if (q) params.q = q;
  return params;
}

// formula_latex is stored as raw LaTeX (no delimiters); MathRenderer keys off
// `$…$`/`$$…$$`. Wrap a bare formula in block delimiters so it renders, but pass
// an already-delimited string through untouched so an author can author inline.
function asMath(latex) {
  const s = (latex || "").trim();
  if (!s) return "";
  return /\$[^$]+\$/.test(s) ? s : `$$${s}$$`;
}

function StatusBadge({ status, isActive }) {
  return (
    <span style={{ fontSize: 12 }}>
      <span className="badge" data-testid="card-status">{(status || "").replaceAll("_", " ")}</span>
      {isActive === false ? <span style={{ opacity: 0.6, marginLeft: 6 }}>(inactive)</span> : null}
    </span>
  );
}
StatusBadge.propTypes = { status: PropTypes.string, isActive: PropTypes.bool };

// key_observation is the one field only some types populate. It is rendered for
// every type and simply skipped when absent, so a type that starts populating it
// needs no change here.
const DETAIL_TEXT_ROWS = [
  ["Standard method", "standard_method"],
  ["Faster method", "faster_method"],
  ["Key observation", "key_observation"],
  ["Worked example", "worked_example"],
  ["Common traps", "common_traps"],
  ["Reviewer notes", "reviewer_notes"],
];

function DetailDrawer({ card, onClose }) {
  const c = card;
  const typeLabel = CARD_TYPES[c.content_type]?.label || c.content_type;
  const subtypeLabel = CARD_TYPES[c.content_type]?.subtypeLabel || "Type";

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 100, display: "flex", justifyContent: "flex-end" }}
      onClick={onClose}
      data-testid="card-detail-overlay"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`${typeLabel} ${c.name}`}
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(560px, 96vw)", height: "100%", overflowY: "auto", background: "var(--paper, #fff)", padding: "1.25rem", boxShadow: "-4px 0 16px rgba(0,0,0,0.2)" }}
        data-testid="card-detail"
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>{c.name}</h2>
            <div style={{ fontSize: 12, opacity: 0.7, fontFamily: "monospace" }}>{c.card_code}</div>
          </div>
          <button type="button" className="btn small" onClick={onClose} aria-label="Close detail">✕</button>
        </div>

        <table className="data-table" style={{ fontSize: 12, marginBottom: 12 }}>
          <tbody>
            <tr><td style={{ opacity: 0.7, width: 150 }}>Content type</td><td data-testid="card-content-type">{typeLabel}</td></tr>
            <tr><td style={{ opacity: 0.7 }}>{subtypeLabel}</td><td>{(c.card_subtype || "").replaceAll("_", " ")}</td></tr>
            <tr><td style={{ opacity: 0.7 }}>Topic</td><td>{c.topic_name || c.topic_id || "—"}</td></tr>
            <tr><td style={{ opacity: 0.7 }}>Microtopic</td><td>{c.microtopic_name || c.microtopic_id || "—"}</td></tr>
            <tr><td style={{ opacity: 0.7 }}>Status</td><td><StatusBadge status={c.reviewer_status} isActive={c.is_active} /></td></tr>
          </tbody>
        </table>

        {c.formula_latex ? (
          <div style={{ marginBottom: 12 }} data-testid="card-formula">
            <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7, marginBottom: 2 }}>Formula</div>
            <MathRenderer text={asMath(c.formula_latex)} />
          </div>
        ) : null}

        {DETAIL_TEXT_ROWS.map(([label, key]) =>
          c[key] ? (
            <div key={key} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7 }}>{label}</div>
              <p style={{ fontSize: 12, whiteSpace: "pre-wrap", margin: "2px 0 0" }}>{c[key]}</p>
            </div>
          ) : null,
        )}
      </div>
    </div>
  );
}
DetailDrawer.propTypes = { card: PropTypes.object.isRequired, onClose: PropTypes.func.isRequired };

export default function ContentCardLibrary({ contentType }) {
  const [subtypeFilter, setSubtypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState(null);

  const config = CARD_TYPES[contentType] || null;
  const typeLabel = config?.label || contentType;
  const subtypes = config?.subtypes || [];

  const params = useMemo(
    () => buildListParams(
      { content_type: contentType, card_subtype: subtypeFilter, reviewer_status: statusFilter, q: query },
      offset,
    ),
    [contentType, subtypeFilter, statusFilter, query, offset],
  );
  const { items, status, total, refresh } = useApiCollection(
    "/api/admin/content-studio/content-cards",
    [],
    { params },
  );

  const reset = (fn) => (v) => { setOffset(0); fn(v); };
  const hasNext =
    total !== null ? offset + PAGE_SIZE < total : status === "live" && items.length === PAGE_SIZE;

  return (
    <div style={{ padding: 16 }} data-testid="content-card-library">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        <label style={{ fontSize: 12 }}>
          {config?.subtypeLabel || "Type"}
          <select className="input" value={subtypeFilter} onChange={(e) => reset(setSubtypeFilter)(e.target.value)} data-testid="card-subtype-filter">
            <option value="">All types</option>
            {subtypes.map((t) => <option key={t} value={t}>{t.replaceAll("_", " ")}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 12 }}>
          Status
          <select className="input" value={statusFilter} onChange={(e) => reset(setStatusFilter)(e.target.value)} data-testid="card-status-filter">
            {REVIEWER_STATUSES.map((s) => <option key={s} value={s}>{s ? s.replaceAll("_", " ") : "All statuses"}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 12, flex: "1 1 200px" }}>
          Search name
          <input className="input" value={query} onChange={(e) => reset(setQuery)(e.target.value)} placeholder={`${typeLabel} name…`} data-testid="card-search" />
        </label>
      </div>

      {status === "loading" ? <div style={{ padding: "2rem", opacity: 0.7 }}>Loading {typeLabel.toLowerCase()}s…</div> : null}
      {status === "error" ? <ErrorState message={`Could not load ${typeLabel.toLowerCase()}s.`} onRetry={refresh} /> : null}
      {status === "empty" ? <EmptyState title="No cards" description={`No ${typeLabel.toLowerCase()}s match these filters.`} /> : null}

      {status === "live" ? (
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" data-testid="card-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Code</th>
                <th>Type</th>
                <th>Topic</th>
                <th>Status</th>
                <th style={{ width: 70 }} />
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id}>
                  <td style={{ fontSize: 13 }}>{c.name}</td>
                  <td style={{ fontSize: 12, fontFamily: "monospace", opacity: 0.8 }}>{c.card_code}</td>
                  <td style={{ fontSize: 12 }}>{(c.card_subtype || "").replaceAll("_", " ")}</td>
                  <td style={{ fontSize: 12, opacity: 0.85 }}>
                    {[c.topic_name || c.topic_id, c.microtopic_name].filter(Boolean).join(" › ") || "—"}
                  </td>
                  <td><StatusBadge status={c.reviewer_status} isActive={c.is_active} /></td>
                  <td>
                    <button type="button" className="btn small" onClick={() => setSelected(c)} data-testid={`card-open-${c.id}`}>
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 8, marginTop: 12 }}>
        {total !== null && (status === "live" || status === "empty") ? (
          <span style={{ fontSize: 12, opacity: 0.7, marginRight: "auto" }} data-testid="card-pagination-summary">
            {total === 0 ? "0" : `${offset + 1}–${offset + items.length}`} of {total}
          </span>
        ) : null}
        {offset > 0 ? (
          <button type="button" className="btn small" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} data-testid="card-prev">
            ← Prev
          </button>
        ) : null}
        {hasNext ? (
          <button type="button" className="btn small" onClick={() => setOffset(offset + PAGE_SIZE)} data-testid="card-next">
            Next →
          </button>
        ) : null}
      </div>

      {selected ? <DetailDrawer card={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}
ContentCardLibrary.propTypes = { contentType: PropTypes.string.isRequired };
