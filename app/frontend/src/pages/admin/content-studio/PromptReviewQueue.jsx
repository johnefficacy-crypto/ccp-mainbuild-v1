/**
 * Writing-prompt Review Queue — the pending → verified|rejected|needs_correction
 * lifecycle. Every decision carries a reason and the CAS tokens the reviewer
 * actually saw ({expected_status, expected_updated_at}); a 409 means the prompt
 * changed under review — refetch and re-read before deciding.
 *
 * Opening a review fetches the FULL prompt snapshot (all constraints +
 * provenance) and binds the CAS token to that exact fetched revision, so a
 * reviewer never verifies content they could not see. Only legal transitions are
 * offered (REVIEW_TRANSITIONS); rejected is terminal. Verifying never activates —
 * activation is migration-gated.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import useApiCollection from "../../../lib/hooks/useApiCollection";
import useApiAction from "../../../lib/hooks/useApiAction";
import { getApiErrorMessage } from "../../../lib/api";
import { ErrorState, EmptyState } from "../../../shared/ui/core";
import { contentStudioApi, REVIEW_TRANSITIONS, isValidReason } from "./contentStudioApi";

const QUEUE_STATUSES = ["pending", "needs_correction", "verified"];
const PAGE_SIZE = 50;

// The full set of review-relevant fields a reviewer must see before verifying.
// Taxonomy/provenance rows show the backend-resolved *_name label (readable),
// falling back to the raw id only if a name could not be resolved.
const SNAPSHOT_ROWS = [
  ["Subject", "subject_name", "subject_id"],
  ["Topic", "topic_name", "topic_id"],
  ["Microtopic", "microtopic_name", "microtopic_id"],
  ["Exercise type", "exercise_type"],
  ["Difficulty", "difficulty_level"],
  ["Required sentence count", "required_sentence_count"],
  ["Min words", "min_words"],
  ["Max words", "max_words"],
  ["Max rewrite attempts", "max_rewrite_attempts"],
  ["Rubric", "rubric_name", "rubric_id"],
  ["Source document", "source_document_title", "source_document_id"],
];

function fmt(v) {
  if (v === null || v === undefined || v === "") return "—";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "—";
  return String(v);
}

function ReviewDialog({ promptRow, onClose, onDone }) {
  // Fetch the full, current revision so the CAS token matches what is shown.
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
      .getPrompt(promptRow.id)
      .then((p) => {
        if (!alive) return;
        setSnapshot(p);
        const transitions = REVIEW_TRANSITIONS[p.reviewer_status] || [];
        setStatus(transitions[0] || "");
        setLoading(false);
      })
      .catch((e) => {
        if (!alive) return;
        setLoadError(getApiErrorMessage(e));
        setLoading(false);
      });
    return () => { alive = false; };
  }, [promptRow.id]);

  // A11y: Escape closes; focus into the dialog on open, restore on close.
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

  const transitions = snapshot ? (REVIEW_TRANSITIONS[snapshot.reviewer_status] || []) : [];

  const submit = async () => {
    if (!snapshot || !status) return;
    if (!isValidReason(reason)) {
      setError("Reason must be 8–500 characters.");
      return;
    }
    setError("");
    setConflict(false);
    const res = await run({
      action: () =>
        contentStudioApi.reviewPrompt(snapshot.id, {
          status,
          expected_status: snapshot.reviewer_status,
          expected_updated_at: snapshot.updated_at,
          reason: reason.trim(),
          reviewer_notes: notes.trim() || undefined,
        }),
      successMessage: `Prompt marked ${status}.`,
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
      data-testid="prompt-review-dialog-overlay"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Review writing prompt"
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(560px, 95vw)", maxHeight: "85vh", overflowY: "auto", background: "var(--paper, #fff)", borderRadius: 6, padding: "1.25rem", boxShadow: "0 4px 16px rgba(0,0,0,0.25)" }}
        data-testid="prompt-review-dialog"
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Review prompt</h2>
          <button type="button" className="btn small" onClick={onClose} aria-label="Close review">✕</button>
        </div>

        {loading ? <div style={{ padding: "1.5rem", opacity: 0.7 }}>Loading full prompt…</div> : null}
        {loadError ? <div style={{ color: "var(--err, #c00)", fontSize: 12 }} role="alert">{loadError}</div> : null}

        {snapshot ? (
          <>
            <p style={{ fontSize: 13, whiteSpace: "pre-wrap", background: "var(--paper-dim, #f5f6f7)", padding: "0.6rem", borderRadius: 4, marginBottom: 10 }} data-testid="review-prompt-text">
              {snapshot.prompt_text}
            </p>
            {snapshot.source_text ? (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7 }}>Source text</div>
                <p style={{ fontSize: 12, whiteSpace: "pre-wrap", margin: "2px 0 0" }}>{snapshot.source_text}</p>
              </div>
            ) : null}
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.7 }}>Required words</div>
              <div style={{ fontSize: 12 }}>{fmt(snapshot.required_words)}</div>
            </div>
            <table className="data-table" style={{ fontSize: 12, marginBottom: 12 }} data-testid="review-snapshot">
              <tbody>
                {SNAPSHOT_ROWS.map(([label, key, fallbackKey]) => {
                  const val = snapshot[key];
                  const shown = (val === null || val === undefined || val === "")
                    && fallbackKey ? snapshot[fallbackKey] : val;
                  return (
                    <tr key={key}>
                      <td style={{ opacity: 0.7, width: 190 }}>{label}</td>
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

            {conflict ? (
              <div className="badge blocker" style={{ display: "block", padding: "0.6rem", marginBottom: 10, fontSize: 12 }} role="alert">
                The prompt changed since you loaded it (409). Refresh the queue and review
                the latest revision — do not verify content you have not seen.
              </div>
            ) : null}
            {error && error.trim() ? (
              <div style={{ color: "var(--err, #c00)", fontSize: 12, marginBottom: 10 }} role="alert">{error}</div>
            ) : null}

            <label style={{ fontSize: 12, display: "block", marginBottom: 10 }}>
              Decision
              <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="review-status">
                {transitions.map((t) => <option key={t} value={t}>{t.replaceAll("_", " ")}</option>)}
              </select>
            </label>
            <label style={{ fontSize: 12, display: "block", marginBottom: 10 }}>
              Reason (required, 8–500 chars)
              <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} data-testid="review-reason" />
            </label>
            <label style={{ fontSize: 12, display: "block", marginBottom: 14 }}>
              Reviewer notes (optional — recorded in the audit log)
              <textarea className="input" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="review-notes" />
            </label>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button type="button" className="btn" onClick={onClose} disabled={busy}>Cancel</button>
              <button type="button" className="btn primary" onClick={submit} disabled={busy || !status} data-testid="review-submit">
                {busy ? "Submitting…" : "Submit decision"}
              </button>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

export default function PromptReviewQueue({ perms }) {
  const [statusFilter, setStatusFilter] = useState("pending");
  const [offset, setOffset] = useState(0);
  const [reviewing, setReviewing] = useState(null);

  const params = useMemo(
    () => ({ reviewer_status: statusFilter, limit: PAGE_SIZE, offset }),
    [statusFilter, offset],
  );
  const { items, status, total, refresh } = useApiCollection(
    "/api/admin/content-studio/writing-prompts",
    [],
    { params },
  );

  const setQueue = (s) => { setOffset(0); setStatusFilter(s); };
  const hasNext =
    total !== null ? offset + PAGE_SIZE < total : status === "live" && items.length === PAGE_SIZE;

  return (
    <div style={{ padding: 16 }} data-testid="prompt-review-queue">
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        <label style={{ fontSize: 12 }}>
          Queue
          <select className="input" value={statusFilter} onChange={(e) => setQueue(e.target.value)} data-testid="review-queue-filter">
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
      {status === "empty" ? <EmptyState title="Queue is clear" description={`No ${statusFilter.replaceAll("_", " ")} prompts.`} /> : null}

      {status === "live" ? (
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" data-testid="review-queue-table">
            <thead>
              <tr>
                <th>Prompt</th>
                <th>Exercise type</th>
                <th style={{ textAlign: "right" }}>Difficulty</th>
                <th>Updated</th>
                <th style={{ width: 90 }} />
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td>
                    <span style={{ display: "block", maxWidth: 460, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 13 }}>
                      {p.prompt_text}
                    </span>
                  </td>
                  <td style={{ fontSize: 12 }}>{(p.exercise_type || "").replaceAll("_", " ")}</td>
                  <td style={{ textAlign: "right", fontSize: 12 }}>{p.difficulty_level}/10</td>
                  <td style={{ fontSize: 12, opacity: 0.7 }}>
                    {p.updated_at ? new Date(p.updated_at).toLocaleDateString() : "—"}
                  </td>
                  <td>
                    {perms.canReview && (REVIEW_TRANSITIONS[p.reviewer_status] || []).length > 0 ? (
                      <button type="button" className="btn small" onClick={() => setReviewing(p)} data-testid={`review-open-${p.id}`}>
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
          <span style={{ fontSize: 12, opacity: 0.7, marginRight: "auto" }} data-testid="review-pagination-summary">
            {total === 0 ? "0" : `${offset + 1}–${offset + items.length}`} of {total}
          </span>
        ) : null}
        {offset > 0 ? (
          <button type="button" className="btn small" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} data-testid="review-prev">
            ← Prev
          </button>
        ) : null}
        {hasNext ? (
          <button type="button" className="btn small" onClick={() => setOffset(offset + PAGE_SIZE)} data-testid="review-next">
            Next →
          </button>
        ) : null}
      </div>

      {reviewing ? (
        <ReviewDialog
          promptRow={reviewing}
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
