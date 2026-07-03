/**
 * Writing-prompt Review Queue — the pending → verified|rejected|needs_correction
 * lifecycle. Every decision carries a reason and the CAS tokens the reviewer
 * actually saw ({expected_status, expected_updated_at}); a 409 means the prompt
 * changed under review — refetch and re-read before deciding.
 *
 * Only legal transitions are offered (REVIEW_TRANSITIONS); rejected is terminal.
 * Verifying never activates — activation is migration-gated.
 */
import React, { useMemo, useState } from "react";
import useApiCollection from "../../../lib/hooks/useApiCollection";
import useApiAction from "../../../lib/hooks/useApiAction";
import { getApiErrorMessage } from "../../../lib/api";
import { ErrorState, EmptyState } from "../../../shared/ui/core";
import { contentStudioApi, REVIEW_TRANSITIONS, isValidReason } from "./contentStudioApi";

const QUEUE_STATUSES = ["pending", "needs_correction", "verified"];

function ReviewDialog({ prompt, onClose, onDone }) {
  const transitions = REVIEW_TRANSITIONS[prompt.reviewer_status] || [];
  const [status, setStatus] = useState(transitions[0] || "");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const { run, busy } = useApiAction();

  const submit = async () => {
    if (!status) return;
    if (!isValidReason(reason)) {
      setError("Reason must be 8–500 characters.");
      return;
    }
    setError("");
    setConflict(false);
    const res = await run({
      action: () =>
        contentStudioApi.reviewPrompt(prompt.id, {
          status,
          expected_status: prompt.reviewer_status,
          expected_updated_at: prompt.updated_at,
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
      role="dialog"
      aria-modal="true"
      aria-label="Review writing prompt"
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={onClose}
      data-testid="prompt-review-dialog"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(520px, 95vw)", maxHeight: "85vh", overflowY: "auto", background: "var(--paper, #fff)", borderRadius: 6, padding: "1.25rem", boxShadow: "0 4px 16px rgba(0,0,0,0.25)" }}
      >
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>Review prompt</h2>
        <p style={{ fontSize: 13, whiteSpace: "pre-wrap", background: "var(--paper-dim, #f5f6f7)", padding: "0.6rem", borderRadius: 4, marginBottom: 10 }}>
          {prompt.prompt_text}
        </p>
        <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 12 }}>
          Current status: <strong>{prompt.reviewer_status}</strong>
          {" · "}type: {(prompt.exercise_type || "").replaceAll("_", " ")}
          {" · "}difficulty {prompt.difficulty_level}/10
        </div>

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
          Reviewer notes (optional — shown to authors)
          <textarea className="input" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="review-notes" />
        </label>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="button" className="btn primary" onClick={submit} disabled={busy || !status} data-testid="review-submit">
            {busy ? "Submitting…" : "Submit decision"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function PromptReviewQueue({ perms }) {
  const [statusFilter, setStatusFilter] = useState("pending");
  const [reviewing, setReviewing] = useState(null);

  const params = useMemo(() => ({ reviewer_status: statusFilter, limit: 50, offset: 0 }), [statusFilter]);
  const { items, status, refresh } = useApiCollection(
    "/api/admin/content-studio/writing-prompts",
    [],
    { params },
  );

  return (
    <div style={{ padding: 16 }} data-testid="prompt-review-queue">
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        <label style={{ fontSize: 12 }}>
          Queue
          <select className="input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} data-testid="review-queue-filter">
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

      {reviewing ? (
        <ReviewDialog
          prompt={reviewing}
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
