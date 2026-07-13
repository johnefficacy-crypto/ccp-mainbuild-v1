/**
 * Content Studio — Current-Affairs Question Review Queue (GQR-G4b).
 *
 * The operator human gate (ADR 0006) over shadow-generated candidates. Lists
 * candidates by status and opens a drill-in showing the question, options, the
 * deterministic validation verdict, the (advisory) verifier verdict, the parent
 * event, and its claims. Actions: approve / reject / send-back (review) and, for an
 * approved candidate, Promote into the objective bank (a separate, higher-trust
 * `mock_questions:publish` action). All decisions CAS-guard on `expected_status`
 * server-side — a 409 means the candidate changed under review; refetch first.
 *
 * Affordance-hiding only; the backend RPCs are authoritative. No new sidebar surface
 * — this renders inside ContentStudio as a content type (no-new-surface rule).
 */
import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";

import useApiCollection from "../../../lib/hooks/useApiCollection";
import useApiAction from "../../../lib/hooks/useApiAction";
import { contentStudioApi, CA_REVIEW_TRANSITIONS } from "./contentStudioApi";

const PAGE_SIZE = 25;
const STATUSES = ["review_ready", "approved", "rejected", "promoted"];

function ReviewDialog({ candidateId, perms, onClose, onDone }) {
  const [snapshot, setSnapshot] = useState(null);
  const [status, setStatus] = useState("");
  const [notes, setNotes] = useState("");
  const [conflict, setConflict] = useState(false);
  const { run, busy } = useApiAction();

  // Full snapshot on open (candidate + event + claims + generation runs).
  React.useEffect(() => {
    let alive = true;
    contentStudioApi.getCaCandidate(candidateId).then((res) => {
      if (alive && res && !res.error) setSnapshot(res);
    });
    return () => {
      alive = false;
    };
  }, [candidateId]);

  if (!snapshot) return null;
  const cand = snapshot.candidate || {};
  const payload = cand.question_payload || {};
  const current = cand.status;
  const transitions = CA_REVIEW_TRANSITIONS[current] || [];
  const canPromote = current === "approved" && perms.canPublish;

  const submitReview = async () => {
    if (!status) return;
    const notesTrimmed = notes.trim();
    // Sending an approved candidate back requires a reason (mirrors the RPC).
    if (current === "approved" && status === "review_ready" && !notesTrimmed) return;
    const res = await run(() =>
      contentStudioApi.reviewCaCandidate(cand.id, {
        status,
        expected_status: current,
        reviewer_notes: notesTrimmed || undefined,
      })
    );
    if (res.error) {
      if (res.error.status === 409) setConflict(true);
      return;
    }
    onDone();
  };

  const promote = async () => {
    const res = await run(() =>
      contentStudioApi.promoteCaCandidate(cand.id, { expected_status: "approved" })
    );
    if (res.error) {
      if (res.error.status === 409) setConflict(true);
      return;
    }
    onDone();
  };

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex",
               alignItems: "center", justifyContent: "center", zIndex: 50 }}
      data-testid="ca-review-dialog-overlay"
      onClick={onClose}
    >
      <div
        className="soft-card"
        style={{ maxWidth: 640, width: "90%", maxHeight: "85vh", overflow: "auto", padding: 20 }}
        data-testid="ca-review-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginTop: 0 }}>Current-affairs question — review</h3>

        <div data-testid="ca-review-stem" style={{ fontWeight: 600, marginBottom: 8 }}>
          {payload.stem || "(no stem)"}
        </div>
        <ol type="a" data-testid="ca-review-options" style={{ marginBottom: 10 }}>
          {(payload.options || []).map((o) => (
            <li key={o.id} style={{ fontWeight: o.id === payload.correct_option_id ? 700 : 400 }}>
              {o.text}
              {o.id === payload.correct_option_id ? " ✓" : ""}
            </li>
          ))}
        </ol>
        {payload.explanation ? (
          <p data-testid="ca-review-explanation" style={{ fontSize: 13 }}>{payload.explanation}</p>
        ) : null}

        <table className="data-table" style={{ fontSize: 12, marginBottom: 12 }} data-testid="ca-review-verdicts">
          <tbody>
            <tr><th>Validation</th><td>{cand.validation_result?.ok ? "passed" : "failed"}</td></tr>
            <tr><th>Verifier</th><td>{JSON.stringify(cand.verifier_verdict || {})}</td></tr>
            <tr><th>Event</th><td>{snapshot.event?.canonical_title || "—"}</td></tr>
            <tr><th>Claims</th><td>{(snapshot.claims || []).length}</td></tr>
            <tr><th>Status</th><td data-testid="ca-review-status-current">{current}</td></tr>
          </tbody>
        </table>

        {conflict ? (
          <p style={{ color: "#b00" }} data-testid="ca-review-conflict">
            This candidate changed since you loaded it (409). Refresh the queue and re-read
            before deciding.
          </p>
        ) : (
          <>
            {transitions.length > 0 ? (
              <div style={{ display: "grid", gap: 8, marginBottom: 12 }}>
                <label>
                  Decision
                  <select
                    className="input" value={status} onChange={(e) => setStatus(e.target.value)}
                    data-testid="ca-review-decision"
                  >
                    <option value="">Select…</option>
                    {transitions.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Notes {current === "approved" ? "(required to send back)" : "(optional)"}
                  <textarea
                    className="input" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)}
                    data-testid="ca-review-notes"
                  />
                </label>
                <button
                  type="button" className="btn primary" onClick={submitReview}
                  disabled={busy || !status || !perms.canReview}
                  data-testid="ca-review-submit"
                >
                  Submit decision
                </button>
              </div>
            ) : null}

            {canPromote ? (
              <button
                type="button" className="btn" onClick={promote} disabled={busy}
                data-testid="ca-review-promote"
              >
                Promote to question bank
              </button>
            ) : null}
          </>
        )}

        <div style={{ marginTop: 12 }}>
          <button type="button" className="btn small" onClick={onClose} data-testid="ca-review-close">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

ReviewDialog.propTypes = {
  candidateId: PropTypes.string.isRequired,
  perms: PropTypes.object.isRequired,
  onClose: PropTypes.func.isRequired,
  onDone: PropTypes.func.isRequired,
};

export default function CaQuestionReviewQueue({ perms }) {
  const [statusFilter, setStatusFilter] = useState("review_ready");
  const [offset, setOffset] = useState(0);
  const [reviewingId, setReviewingId] = useState(null);

  const params = useMemo(
    () => ({ status: statusFilter, limit: PAGE_SIZE, offset }),
    [statusFilter, offset]
  );
  const { items, status, total, refresh } = useApiCollection(
    contentStudioApi.listCaCandidates,
    params
  );

  const setQueue = (s) => {
    setOffset(0);
    setStatusFilter(s);
  };

  return (
    <div style={{ padding: 16 }} data-testid="ca-question-review-queue">
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
        <label>
          Status
          <select
            className="input" value={statusFilter} onChange={(e) => setQueue(e.target.value)}
            data-testid="ca-review-queue-filter"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s.replaceAll("_", " ")}</option>
            ))}
          </select>
        </label>
        {!perms.canReview ? (
          <span style={{ fontSize: 12, opacity: 0.7 }} data-testid="ca-review-noperm">
            Read-only — review permission required to act.
          </span>
        ) : null}
      </div>

      {status === "empty" ? (
        <p data-testid="ca-review-empty">No {statusFilter.replaceAll("_", " ")} candidates.</p>
      ) : null}

      {status !== "empty" ? (
        <table className="data-table" data-testid="ca-review-queue-table">
          <thead>
            <tr><th>Question</th><th>Validation</th><th>Status</th><th /></tr>
          </thead>
          <tbody>
            {(items || []).map((c) => (
              <tr key={c.id}>
                <td style={{ fontSize: 13 }}>{c.question_payload?.stem || "(no stem)"}</td>
                <td>{c.validation_result?.ok ? "passed" : "failed"}</td>
                <td>{c.status}</td>
                <td>
                  <button
                    type="button" className="btn small" onClick={() => setReviewingId(c.id)}
                    data-testid={`ca-review-open-${c.id}`}
                  >
                    Review
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}

      <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12 }}>
        <span style={{ fontSize: 12, opacity: 0.7, marginRight: "auto" }} data-testid="ca-review-pagination">
          {total != null ? `${offset + 1}–${offset + (items || []).length} of ${total}` : ""}
        </span>
        <button
          type="button" className="btn small" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          disabled={offset === 0} data-testid="ca-review-prev"
        >
          Prev
        </button>
        <button
          type="button" className="btn small" onClick={() => setOffset(offset + PAGE_SIZE)}
          disabled={total != null && offset + PAGE_SIZE >= total} data-testid="ca-review-next"
        >
          Next
        </button>
      </div>

      {reviewingId ? (
        <ReviewDialog
          candidateId={reviewingId}
          perms={perms}
          onClose={() => setReviewingId(null)}
          onDone={() => {
            setReviewingId(null);
            refresh();
          }}
        />
      ) : null}
    </div>
  );
}

CaQuestionReviewQueue.propTypes = {
  perms: PropTypes.object.isRequired,
};
