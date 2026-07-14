/**
 * Reasoning Strategy Review Queue — the pending → verified|rejected|needs_correction
 * lifecycle for reasoning_strategies (migration 261, GQR-S3).
 *
 * The transition matrix matches quant heuristics (REASONING_REVIEW_TRANSITIONS):
 * needs_correction routes back to pending (never straight to verified), a verified
 * strategy can only be reopened for correction, and rejected can reopen to pending.
 * Reopening a verified strategy for correction REQUIRES a reviewer note (the RPC
 * enforces this too). Review dual-CAS-guards on BOTH the reviewer_status the reviewer
 * saw (`expected_status`) AND the content `updated_at` (`expected_updated_at`) — a
 * 409 means the strategy changed under review: refetch and re-read before deciding.
 *
 * Opening a review fetches the FULL strategy snapshot so the reviewer never verifies
 * content they could not see; verifying never activates.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import useApiCollection from "../../../lib/hooks/useApiCollection";
import useApiAction from "../../../lib/hooks/useApiAction";
import { getApiErrorMessage } from "../../../lib/api";
import { ErrorState, EmptyState } from "../../../shared/ui/core";
import MathRenderer from "../../study/mocks/components/questions/shared/MathRenderer";
import { contentStudioApi, REASONING_REVIEW_TRANSITIONS, isValidReason } from "./contentStudioApi";

// `rejected` is included so a rejected strategy can be fetched and reopened to
// pending (REASONING_REVIEW_TRANSITIONS.rejected === ["pending"]); without it the
// advertised rejected→pending lifecycle would be unreachable from the UI.
const QUEUE_STATUSES = ["pending", "needs_correction", "verified", "rejected"];
const PAGE_SIZE = 50;

function asMath(latex) {
  const s = (latex || "").trim();
  if (!s) return "";
  return /\$[^$]+\$/.test(s) ? s : `$$${s}$$`;
}

const SNAPSHOT_ROWS = [
  ["Type", "strategy_type"],
  ["Topic", "topic_name", "topic_id"],
  ["Microtopic", "microtopic_name", "microtopic_id"],
];

// Every canonical review-bearing field (migration 261). A reviewer must see the
// full method/observation/trap content before verifying — not just name + faster.
const SNAPSHOT_TEXT_ROWS = [
  ["Standard method", "standard_method"],
  ["Key observation", "key_observation"],
  ["Worked example", "worked_example"],
  ["Common traps", "common_traps"],
  ["Existing reviewer notes", "reviewer_notes"],
];

function fmt(v) {
  if (v === null || v === undefined || v === "") return "—";
  return String(v).replaceAll("_", " ");
}

function ReviewDialog({ strategyRow, onClose, onDone }) {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [status, setStatus] = useState("");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const { run, busy } = useApiAction();
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    let alive = true;
    contentStudioApi
      .getStrategy(strategyRow.id)
      .then((s) => {
        if (!alive) return;
        setSnapshot(s);
        const transitions = REASONING_REVIEW_TRANSITIONS[s.reviewer_status] || [];
        setStatus(transitions[0] || "");
        setLoading(false);
      })
      .catch((e) => {
        if (!alive) return;
        setLoadError(getApiErrorMessage(e));
        setLoading(false);
      });
    return () => { alive = false; };
  }, [strategyRow.id]);

  useEffect(() => {
    const prevFocus = typeof document !== "undefined" ? document.activeElement : null;
    const node = dialogRef.current;
    const first = node && node.querySelector("input, textarea, select, button");
    if (first) first.focus();
    const onKey = (e) => { if (e.key === "Escape") closeRef.current(); };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (prevFocus && typeof prevFocus.focus === "function") prevFocus.focus();
    };
  }, []);

  const transitions = snapshot ? (REASONING_REVIEW_TRANSITIONS[snapshot.reviewer_status] || []) : [];
  // Reopening a verified strategy for correction requires a note (RPC-enforced).
  const notesRequired = !!snapshot && snapshot.reviewer_status === "verified" && status === "needs_correction";

  const submit = async () => {
    if (!snapshot || !status) return;
    if (!isValidReason(reason)) {
      setError("Reason must be 8–500 characters.");
      return;
    }
    if (notesRequired && !notes.trim()) {
      setError("Reviewer notes are required when reopening a verified strategy.");
      return;
    }
    setError("");
    setConflict(false);
    const res = await run({
      action: () =>
        contentStudioApi.reviewStrategy(snapshot.id, {
          status,
          expected_status: snapshot.reviewer_status,
          // Content CAS bound to the exact revision the reviewer read; a 409 means
          // the strategy changed under review.
          expected_updated_at: snapshot.updated_at,
          reason: reason.trim(),
          reviewer_notes: notes.trim() || undefined,
        }),
      successMessage: `Strategy marked ${status}.`,
      errorMessage: " ",
      onSuccess: onDone,
    });
    if (!res.ok && res.error) {
      if (res.error.status === 409) setConflict(true);
      else setError(getApiErrorMessage(res.error));
    }
  };

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={onClose}
      data-testid="strategy-review-dialog-overlay"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Review reasoning strategy"
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(560px, 95vw)", maxHeight: "85vh", overflowY: "auto", background: "var(--paper, #fff)", borderRadius: 6, padding: "1.25rem", boxShadow: "0 4px 16px rgba(0,0,0,0.25)" }}
        data-testid="strategy-review-dialog"
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Review strategy</h2>
          <button type="button" className="btn small" onClick={onClose} aria-label="Close review">✕</button>
        </div>

        {loading ? <div style={{ padding: "1.5rem", opacity: 0.7 }}>Loading full strategy…</div> : null}
        {loadError ? <div style={{ color: "var(--err, #c00)", fontSize: 12 }} role="alert">{loadError}</div> : null}

        {snapshot ? (
          <>
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{snapshot.name}</div>
              <div style={{ fontSize: 12, opacity: 0.7, fontFamily: "monospace" }}>{snapshot.strategy_code}</div>
            </div>

            {snapshot.formula_latex ? (
              <div style={{ marginBottom: 10 }} data-testid="review-strategy-formula">
                <MathRenderer text={asMath(snapshot.formula_latex)} />
              </div>
            ) : null}

            {snapshot.faster_method ? (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7 }}>Faster method</div>
                <p style={{ fontSize: 12, whiteSpace: "pre-wrap", margin: "2px 0 0" }}>{snapshot.faster_method}</p>
              </div>
            ) : null}

            <table className="data-table" style={{ fontSize: 12, marginBottom: 12 }} data-testid="review-strategy-snapshot">
              <tbody>
                {SNAPSHOT_ROWS.map(([label, key, fallbackKey]) => {
                  const val = snapshot[key];
                  const shown = (val === null || val === undefined || val === "") && fallbackKey
                    ? snapshot[fallbackKey] : val;
                  return (
                    <tr key={key}>
                      <td style={{ opacity: 0.7, width: 150 }}>{label}</td>
                      <td>{fmt(shown)}</td>
                    </tr>
                  );
                })}
                <tr>
                  <td style={{ opacity: 0.7 }}>Current status</td>
                  <td><strong>{snapshot.reviewer_status}</strong> (active: {String(!!snapshot.is_active)})</td>
                </tr>
              </tbody>
            </table>

            {SNAPSHOT_TEXT_ROWS.map(([label, key]) =>
              snapshot[key] ? (
                <div key={key} style={{ marginBottom: 10 }} data-testid={`review-strategy-${key}`}>
                  <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7 }}>{label}</div>
                  <p style={{ fontSize: 12, whiteSpace: "pre-wrap", margin: "2px 0 0" }}>{snapshot[key]}</p>
                </div>
              ) : null,
            )}

            <div style={{ marginBottom: 12 }} data-testid="review-strategy-applicability_rule">
              <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7, marginBottom: 2 }}>Applicability rule</div>
              <pre style={{ fontSize: 11, background: "var(--paper-dim, #f5f6f7)", padding: "0.6rem", borderRadius: 4, overflowX: "auto", margin: 0 }}>
                {JSON.stringify(snapshot.applicability_rule ?? {}, null, 2)}
              </pre>
            </div>

            {conflict ? (
              <div className="badge blocker" style={{ display: "block", padding: "0.6rem", marginBottom: 10, fontSize: 12 }} role="alert">
                The strategy changed since you loaded it (409). Refresh the queue and
                review the latest revision — do not verify content you have not seen.
              </div>
            ) : null}
            {error && error.trim() ? (
              <div style={{ color: "var(--err, #c00)", fontSize: 12, marginBottom: 10 }} role="alert">{error}</div>
            ) : null}

            {transitions.length ? (
              <>
                <label style={{ fontSize: 12, display: "block", marginBottom: 10 }}>
                  Decision
                  <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="strategy-review-status">
                    {transitions.map((t) => <option key={t} value={t}>{t.replaceAll("_", " ")}</option>)}
                  </select>
                </label>
                <label style={{ fontSize: 12, display: "block", marginBottom: 10 }}>
                  Reason (required, 8–500 chars — recorded in the audit log)
                  <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} data-testid="strategy-review-reason" />
                </label>
                <label style={{ fontSize: 12, display: "block", marginBottom: 14 }}>
                  Reviewer notes{notesRequired ? " (required)" : " (optional — recorded in the audit log)"}
                  <textarea className="input" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="strategy-review-notes" />
                </label>
                <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
                  <button type="button" className="btn" onClick={onClose} disabled={busy}>Cancel</button>
                  <button type="button" className="btn primary" onClick={submit} disabled={busy || !status} data-testid="strategy-review-submit">
                    {busy ? "Submitting…" : "Submit decision"}
                  </button>
                </div>
              </>
            ) : (
              <div style={{ fontSize: 12, opacity: 0.7 }}>No further transitions from this status.</div>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}

export default function ReasoningStrategyReviewQueue({ perms }) {
  const [statusFilter, setStatusFilter] = useState("pending");
  const [offset, setOffset] = useState(0);
  const [reviewing, setReviewing] = useState(null);

  const params = useMemo(
    () => ({ reviewer_status: statusFilter, limit: PAGE_SIZE, offset }),
    [statusFilter, offset],
  );
  const { items, status, total, refresh } = useApiCollection(
    "/api/admin/content-studio/reasoning-strategies",
    [],
    { params },
  );

  const setQueue = (s) => { setOffset(0); setStatusFilter(s); };
  const hasNext =
    total !== null ? offset + PAGE_SIZE < total : status === "live" && items.length === PAGE_SIZE;

  return (
    <div style={{ padding: 16 }} data-testid="reasoning-strategy-review-queue">
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        <label style={{ fontSize: 12 }}>
          Queue
          <select className="input" value={statusFilter} onChange={(e) => setQueue(e.target.value)} data-testid="strategy-review-queue-filter">
            {QUEUE_STATUSES.map((s) => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}
          </select>
        </label>
        {!perms.canReview ? (
          <span style={{ fontSize: 12, opacity: 0.7 }}>
            Read-only — reviewing requires content_studio.review.
          </span>
        ) : null}
      </div>

      {status === "loading" ? <div style={{ padding: "2rem", opacity: 0.7 }}>Loading queue…</div> : null}
      {status === "error" ? <ErrorState message="Could not load the review queue." onRetry={refresh} /> : null}
      {status === "empty" ? <EmptyState title="Queue is clear" description={`No ${statusFilter.replaceAll("_", " ")} strategies.`} /> : null}

      {status === "live" ? (
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" data-testid="strategy-review-queue-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Code</th>
                <th>Type</th>
                <th>Topic</th>
                <th style={{ width: 90 }} />
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <td style={{ fontSize: 13 }}>{s.name}</td>
                  <td style={{ fontSize: 12, fontFamily: "monospace", opacity: 0.8 }}>{s.strategy_code}</td>
                  <td style={{ fontSize: 12 }}>{(s.strategy_type || "").replaceAll("_", " ")}</td>
                  <td style={{ fontSize: 12, opacity: 0.85 }} data-testid={`strategy-review-taxonomy-${s.id}`}>
                    {[s.topic_name || s.topic_id, s.microtopic_name].filter(Boolean).join(" › ") || "—"}
                  </td>
                  <td>
                    {perms.canReview && (REASONING_REVIEW_TRANSITIONS[s.reviewer_status] || []).length > 0 ? (
                      <button type="button" className="btn small" onClick={() => setReviewing(s)} data-testid={`strategy-review-open-${s.id}`}>
                        Review
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 8, marginTop: 12 }}>
        {total !== null && (status === "live" || status === "empty") ? (
          <span style={{ fontSize: 12, opacity: 0.7, marginRight: "auto" }} data-testid="strategy-review-pagination-summary">
            {total === 0 ? "0" : `${offset + 1}–${offset + items.length}`} of {total}
          </span>
        ) : null}
        {offset > 0 ? (
          <button type="button" className="btn small" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} data-testid="strategy-review-prev">
            ← Prev
          </button>
        ) : null}
        {hasNext ? (
          <button type="button" className="btn small" onClick={() => setOffset(offset + PAGE_SIZE)} data-testid="strategy-review-next">
            Next →
          </button>
        ) : null}
      </div>

      {reviewing ? (
        <ReviewDialog
          strategyRow={reviewing}
          onClose={() => setReviewing(null)}
          onDone={() => {
            setReviewing(null);
            refresh();
          }}
        />
      ) : null}
    </div>
  );
}
