/**
 * Quant Heuristic Library — read-only governance browse over quant_heuristics
 * (migration 243, GQR-Q7). Content Studio is where quant heuristics are governed
 * (subject-practice-framework.md §3.1/§6); this Library lets an operator filter
 * by topic / type / reviewer status and open a full detail drawer.
 *
 * There is NO create/edit/activate/assign affordance here — migration 243 ships
 * only the review-lifecycle RPC, so authoring is a later governed PR. The
 * lifecycle transition itself lives in the Review Queue tab. formula_latex is
 * rendered through the existing KaTeX path (MathRenderer), matching how question
 * math already renders — no new rendering work (§3.1).
 */
import React, { useMemo, useState } from "react";
import useApiCollection from "../../../lib/hooks/useApiCollection";
import { ErrorState, EmptyState } from "../../../shared/ui/core";
import MathRenderer from "../../study/mocks/components/questions/shared/MathRenderer";
import { HEURISTIC_TYPES } from "./contentStudioApi";

const REVIEWER_STATUSES = ["", "pending", "needs_correction", "verified", "rejected"];
const PAGE_SIZE = 50;

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
      <span className="badge" data-testid="heuristic-status">{(status || "").replaceAll("_", " ")}</span>
      {isActive === false ? <span style={{ opacity: 0.6, marginLeft: 6 }}>(inactive)</span> : null}
    </span>
  );
}

const DETAIL_TEXT_ROWS = [
  ["Standard method", "standard_method"],
  ["Shortcut method", "shortcut_method"],
  ["Worked example", "worked_example"],
  ["Common traps", "common_traps"],
  ["Reviewer notes", "reviewer_notes"],
];

function DetailDrawer({ heuristic, onClose }) {
  const h = heuristic;
  const rule = useMemo(() => {
    try {
      return JSON.stringify(h.applicability_rule ?? {}, null, 2);
    } catch {
      return String(h.applicability_rule);
    }
  }, [h.applicability_rule]);

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 100, display: "flex", justifyContent: "flex-end" }}
      onClick={onClose}
      data-testid="heuristic-detail-overlay"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Heuristic ${h.name}`}
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(560px, 96vw)", height: "100%", overflowY: "auto", background: "var(--paper, #fff)", padding: "1.25rem", boxShadow: "-4px 0 16px rgba(0,0,0,0.2)" }}
        data-testid="heuristic-detail"
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>{h.name}</h2>
            <div style={{ fontSize: 12, opacity: 0.7, fontFamily: "monospace" }}>{h.heuristic_code}</div>
          </div>
          <button type="button" className="btn small" onClick={onClose} aria-label="Close detail">✕</button>
        </div>

        <table className="data-table" style={{ fontSize: 12, marginBottom: 12 }}>
          <tbody>
            <tr><td style={{ opacity: 0.7, width: 150 }}>Type</td><td>{(h.heuristic_type || "").replaceAll("_", " ")}</td></tr>
            <tr><td style={{ opacity: 0.7 }}>Topic</td><td>{h.topic_name || h.topic_id || "—"}</td></tr>
            <tr><td style={{ opacity: 0.7 }}>Microtopic</td><td>{h.microtopic_name || h.microtopic_id || "—"}</td></tr>
            <tr><td style={{ opacity: 0.7 }}>Status</td><td><StatusBadge status={h.reviewer_status} isActive={h.is_active} /></td></tr>
          </tbody>
        </table>

        {h.formula_latex ? (
          <div style={{ marginBottom: 12 }} data-testid="heuristic-formula">
            <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7, marginBottom: 2 }}>Formula</div>
            <MathRenderer text={asMath(h.formula_latex)} />
          </div>
        ) : null}

        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7, marginBottom: 2 }}>Applicability rule</div>
          <pre style={{ fontSize: 11, background: "var(--paper-dim, #f5f6f7)", padding: "0.6rem", borderRadius: 4, overflowX: "auto", margin: 0 }} data-testid="heuristic-rule">
            {rule}
          </pre>
        </div>

        {DETAIL_TEXT_ROWS.map(([label, key]) =>
          h[key] ? (
            <div key={key} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7 }}>{label}</div>
              <p style={{ fontSize: 12, whiteSpace: "pre-wrap", margin: "2px 0 0" }}>{h[key]}</p>
            </div>
          ) : null,
        )}
      </div>
    </div>
  );
}

export default function QuantHeuristicLibrary() {
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState(null);

  const params = useMemo(
    () => ({
      heuristic_type: typeFilter || undefined,
      reviewer_status: statusFilter || undefined,
      q: query.trim() || undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [typeFilter, statusFilter, query, offset],
  );
  const { items, status, total, refresh } = useApiCollection(
    "/api/admin/content-studio/quant-heuristics",
    [],
    { params },
  );

  const reset = (fn) => (v) => { setOffset(0); fn(v); };
  const hasNext =
    total !== null ? offset + PAGE_SIZE < total : status === "live" && items.length === PAGE_SIZE;

  return (
    <div style={{ padding: 16 }} data-testid="quant-heuristic-library">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        <label style={{ fontSize: 12 }}>
          Type
          <select className="input" value={typeFilter} onChange={(e) => reset(setTypeFilter)(e.target.value)} data-testid="heuristic-type-filter">
            <option value="">All types</option>
            {HEURISTIC_TYPES.map((t) => <option key={t} value={t}>{t.replaceAll("_", " ")}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 12 }}>
          Status
          <select className="input" value={statusFilter} onChange={(e) => reset(setStatusFilter)(e.target.value)} data-testid="heuristic-status-filter">
            {REVIEWER_STATUSES.map((s) => <option key={s} value={s}>{s ? s.replaceAll("_", " ") : "All statuses"}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 12, flex: "1 1 200px" }}>
          Search name
          <input className="input" value={query} onChange={(e) => reset(setQuery)(e.target.value)} placeholder="Heuristic name…" data-testid="heuristic-search" />
        </label>
      </div>

      {status === "loading" ? <div style={{ padding: "2rem", opacity: 0.7 }}>Loading heuristics…</div> : null}
      {status === "error" ? <ErrorState message="Could not load quant heuristics." onRetry={refresh} /> : null}
      {status === "empty" ? <EmptyState title="No heuristics" description="No quant heuristics match these filters." /> : null}

      {status === "live" ? (
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" data-testid="heuristic-table">
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
              {items.map((h) => (
                <tr key={h.id}>
                  <td style={{ fontSize: 13 }}>{h.name}</td>
                  <td style={{ fontSize: 12, fontFamily: "monospace", opacity: 0.8 }}>{h.heuristic_code}</td>
                  <td style={{ fontSize: 12 }}>{(h.heuristic_type || "").replaceAll("_", " ")}</td>
                  <td style={{ fontSize: 12, opacity: 0.85 }}>
                    {[h.topic_name || h.topic_id, h.microtopic_name].filter(Boolean).join(" › ") || "—"}
                  </td>
                  <td><StatusBadge status={h.reviewer_status} isActive={h.is_active} /></td>
                  <td>
                    <button type="button" className="btn small" onClick={() => setSelected(h)} data-testid={`heuristic-open-${h.id}`}>
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
          <span style={{ fontSize: 12, opacity: 0.7, marginRight: "auto" }} data-testid="heuristic-pagination-summary">
            {total === 0 ? "0" : `${offset + 1}–${offset + items.length}`} of {total}
          </span>
        ) : null}
        {offset > 0 ? (
          <button type="button" className="btn small" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} data-testid="heuristic-prev">
            ← Prev
          </button>
        ) : null}
        {hasNext ? (
          <button type="button" className="btn small" onClick={() => setOffset(offset + PAGE_SIZE)} data-testid="heuristic-next">
            Next →
          </button>
        ) : null}
      </div>

      {selected ? <DetailDrawer heuristic={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}
