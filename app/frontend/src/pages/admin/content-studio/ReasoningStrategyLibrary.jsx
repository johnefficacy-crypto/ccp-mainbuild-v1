/**
 * Reasoning Strategy Library — read-only governance browse over reasoning_strategies
 * (migration 262, GQR-S3). Content Studio is where reasoning strategies are governed
 * (solution-strategies-improvement-lab.md §8.2/§8.5); this Library lets an operator
 * filter by type / reviewer status / name and open a full detail drawer.
 *
 * There is NO create/edit/activate/assign affordance here — migration 262 ships
 * only the review-lifecycle RPC, so authoring is a later governed slice (exactly as
 * the Quant heuristic Library deferred it). The lifecycle transition itself lives in
 * the Review Queue tab. formula_latex is rendered through the existing KaTeX path
 * (MathRenderer), matching how question math already renders — no new rendering work.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import useApiCollection from "../../../lib/hooks/useApiCollection";
import { ErrorState, EmptyState } from "../../../shared/ui/core";
import MathRenderer from "../../study/mocks/components/questions/shared/MathRenderer";
import { REASONING_STRATEGY_TYPES } from "./contentStudioApi";

const REVIEWER_STATUSES = ["", "pending", "needs_correction", "verified", "rejected"];
const PAGE_SIZE = 50;

// useApiCollection serializes params through `new URLSearchParams(params)`, which
// stringifies `undefined` as the literal "undefined" — the backend would then
// filter on strategy_type='undefined' etc. and return nothing. Emit ONLY set
// filters plus limit/offset, so the default (unfiltered) request carries no stray
// keys. Exported for regression test.
export function buildListParams(filters, offset) {
  const params = { limit: PAGE_SIZE, offset };
  if (filters.strategy_type) params.strategy_type = filters.strategy_type;
  if (filters.reviewer_status) params.reviewer_status = filters.reviewer_status;
  const q = (filters.q || "").trim();
  if (q) params.q = q;
  return params;
}

// formula_latex is stored as raw LaTeX (no delimiters); MathRenderer keys off
// `$…$`/`$$…$$`. Wrap a bare formula in block delimiters so it renders, but pass
// an already-delimited string through untouched.
function asMath(latex) {
  const s = (latex || "").trim();
  if (!s) return "";
  return /\$[^$]+\$/.test(s) ? s : `$$${s}$$`;
}

function StatusBadge({ status, isActive }) {
  return (
    <span style={{ fontSize: 12 }}>
      <span className="badge" data-testid="strategy-status">{(status || "").replaceAll("_", " ")}</span>
      {isActive === false ? <span style={{ opacity: 0.6, marginLeft: 6 }}>(inactive)</span> : null}
    </span>
  );
}

const DETAIL_TEXT_ROWS = [
  ["Standard method", "standard_method"],
  ["Faster method", "faster_method"],
  ["Key observation", "key_observation"],
  ["Worked example", "worked_example"],
  ["Common traps", "common_traps"],
  ["Reviewer notes", "reviewer_notes"],
];

function DetailDrawer({ strategy, onClose }) {
  const s = strategy;
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const rule = useMemo(() => {
    try {
      return JSON.stringify(s.applicability_rule ?? {}, null, 2);
    } catch {
      return String(s.applicability_rule);
    }
  }, [s.applicability_rule]);

  useEffect(() => {
    const previousFocus = document.activeElement;
    const root = dialogRef.current;
    root?.querySelector("button")?.focus();

    function onKey(e) {
      if (e.key === "Escape") {
        e.stopPropagation();
        closeRef.current();
        return;
      }
      if (e.key !== "Tab" || !root) return;
      const focusables = root.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      previousFocus?.focus?.();
    };
  }, []);

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 100, display: "flex", justifyContent: "flex-end" }}
      onClick={onClose}
      data-testid="strategy-detail-overlay"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Strategy ${s.name}`}
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(560px, 96vw)", height: "100%", overflowY: "auto", background: "var(--paper, #fff)", padding: "1.25rem", boxShadow: "-4px 0 16px rgba(0,0,0,0.2)" }}
        data-testid="strategy-detail"
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>{s.name}</h2>
            <div style={{ fontSize: 12, opacity: 0.7, fontFamily: "monospace" }}>{s.strategy_code}</div>
          </div>
          <button type="button" className="btn small" onClick={onClose} aria-label="Close detail">✕</button>
        </div>

        <table className="data-table" style={{ fontSize: 12, marginBottom: 12 }}>
          <tbody>
            <tr><td style={{ opacity: 0.7, width: 150 }}>Type</td><td>{(s.strategy_type || "").replaceAll("_", " ")}</td></tr>
            <tr><td style={{ opacity: 0.7 }}>Topic</td><td>{s.topic_name || s.topic_id || "—"}</td></tr>
            <tr><td style={{ opacity: 0.7 }}>Microtopic</td><td>{s.microtopic_name || s.microtopic_id || "—"}</td></tr>
            <tr><td style={{ opacity: 0.7 }}>Status</td><td><StatusBadge status={s.reviewer_status} isActive={s.is_active} /></td></tr>
          </tbody>
        </table>

        {s.formula_latex ? (
          <div style={{ marginBottom: 12 }} data-testid="strategy-formula">
            <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7, marginBottom: 2 }}>Formula</div>
            <MathRenderer text={asMath(s.formula_latex)} />
          </div>
        ) : null}

        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7, marginBottom: 2 }}>Applicability rule</div>
          <pre style={{ fontSize: 11, background: "var(--paper-dim, #f5f6f7)", padding: "0.6rem", borderRadius: 4, overflowX: "auto", margin: 0 }} data-testid="strategy-rule">
            {rule}
          </pre>
        </div>

        {DETAIL_TEXT_ROWS.map(([label, key]) =>
          s[key] ? (
            <div key={key} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7 }}>{label}</div>
              <p style={{ fontSize: 12, whiteSpace: "pre-wrap", margin: "2px 0 0" }}>{s[key]}</p>
            </div>
          ) : null,
        )}
      </div>
    </div>
  );
}

export default function ReasoningStrategyLibrary() {
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState(null);

  const params = useMemo(
    () => buildListParams({ strategy_type: typeFilter, reviewer_status: statusFilter, q: query }, offset),
    [typeFilter, statusFilter, query, offset],
  );
  const { items, status, total, refresh } = useApiCollection(
    "/api/admin/content-studio/reasoning-strategies",
    [],
    { params },
  );

  const reset = (fn) => (v) => { setOffset(0); fn(v); };
  const hasNext =
    total !== null ? offset + PAGE_SIZE < total : status === "live" && items.length === PAGE_SIZE;

  return (
    <div style={{ padding: 16 }} data-testid="reasoning-strategy-library">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        <label style={{ fontSize: 12 }}>
          Type
          <select className="input" value={typeFilter} onChange={(e) => reset(setTypeFilter)(e.target.value)} data-testid="strategy-type-filter">
            <option value="">All types</option>
            {REASONING_STRATEGY_TYPES.map((t) => <option key={t} value={t}>{t.replaceAll("_", " ")}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 12 }}>
          Status
          <select className="input" value={statusFilter} onChange={(e) => reset(setStatusFilter)(e.target.value)} data-testid="strategy-status-filter">
            {REVIEWER_STATUSES.map((s) => <option key={s} value={s}>{s ? s.replaceAll("_", " ") : "All statuses"}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 12, flex: "1 1 200px" }}>
          Search name
          <input className="input" value={query} onChange={(e) => reset(setQuery)(e.target.value)} placeholder="Strategy name…" data-testid="strategy-search" />
        </label>
      </div>

      {status === "loading" ? <div style={{ padding: "2rem", opacity: 0.7 }}>Loading strategies…</div> : null}
      {status === "error" ? <ErrorState message="Could not load reasoning strategies." onRetry={refresh} /> : null}
      {status === "empty" ? <EmptyState title="No strategies" description="No reasoning strategies match these filters." /> : null}

      {status === "live" ? (
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" data-testid="strategy-table">
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
              {items.map((s) => (
                <tr key={s.id}>
                  <td style={{ fontSize: 13 }}>{s.name}</td>
                  <td style={{ fontSize: 12, fontFamily: "monospace", opacity: 0.8 }}>{s.strategy_code}</td>
                  <td style={{ fontSize: 12 }}>{(s.strategy_type || "").replaceAll("_", " ")}</td>
                  <td style={{ fontSize: 12, opacity: 0.85 }}>
                    {[s.topic_name || s.topic_id, s.microtopic_name].filter(Boolean).join(" › ") || "—"}
                  </td>
                  <td><StatusBadge status={s.reviewer_status} isActive={s.is_active} /></td>
                  <td>
                    <button type="button" className="btn small" onClick={() => setSelected(s)} data-testid={`strategy-open-${s.id}`}>
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
          <span style={{ fontSize: 12, opacity: 0.7, marginRight: "auto" }} data-testid="strategy-pagination-summary">
            {total === 0 ? "0" : `${offset + 1}–${offset + items.length}`} of {total}
          </span>
        ) : null}
        {offset > 0 ? (
          <button type="button" className="btn small" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} data-testid="strategy-prev">
            ← Prev
          </button>
        ) : null}
        {hasNext ? (
          <button type="button" className="btn small" onClick={() => setOffset(offset + PAGE_SIZE)} data-testid="strategy-next">
            Next →
          </button>
        ) : null}
      </div>

      {selected ? <DetailDrawer strategy={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}
