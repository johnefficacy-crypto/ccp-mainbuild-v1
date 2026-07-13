/**
 * Content Studio — Current-Affairs Question Review Queue (GQR-G4b).
 *
 * The operator human gate (ADR 0006) over shadow-generated candidates. Lists
 * candidates by status and opens a drill-in showing the question, options, the
 * deterministic validation verdict, the (advisory) verifier verdict, the parent
 * event with its editorial/relevance fields, and — per current-affairs-pipeline.md
 * §5 Stage E — each candidate-linked claim with its exact evidence spans, document
 * source, and source authority level, plus ADR-0007 warnings and the generation
 * audit. Actions: approve / reject / send-back (review) and, for an approved
 * candidate, Promote (a separate `mock_questions:publish` action).
 *
 * Every decision carries the candidate's exact `updated_at` content token (dual CAS
 * with status) and an 8-500 char audit reason, so an operator can never approve or
 * publish a revision they did not read; a 409 surfaces a refetch banner. Affordance-
 * hiding only; the backend RPCs are authoritative. No new sidebar surface.
 */
import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";

import useApiCollection from "../../../lib/hooks/useApiCollection";
import useApiAction from "../../../lib/hooks/useApiAction";
import { contentStudioApi, CA_REVIEW_TRANSITIONS, isValidReason } from "./contentStudioApi";

const BASE = "/api/admin/content-studio";
const LIST_URL = `${BASE}/ca-question-candidates`;
const PAGE_SIZE = 25;
const STATUSES = ["review_ready", "approved", "rejected", "promoted"];

function ReviewDialog({ candidateId, perms, onClose, onDone }) {
  const [envelope, setEnvelope] = useState(null);
  const [decision, setDecision] = useState("");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [conflict, setConflict] = useState(false);
  const { run, busy } = useApiAction();

  React.useEffect(() => {
    let alive = true;
    contentStudioApi.getCaCandidate(candidateId).then((res) => {
      if (alive && res && !res.error) setEnvelope(res);
    });
    return () => {
      alive = false;
    };
  }, [candidateId]);

  if (!envelope) return null;
  const cand = envelope.candidate || {};
  const payload = cand.question_payload || {};
  const current = cand.status;
  const token = cand.updated_at;
  const transitions = CA_REVIEW_TRANSITIONS[current] || [];
  const canPromote = current === "approved" && perms.canPublish;
  const reasonOk = isValidReason(reason);

  const handle409 = (res) => {
    if (!res.ok && res.error?.status === 409) setConflict(true);
    return res.ok;
  };

  const submitReview = async () => {
    if (!decision || !reasonOk) return;
    const notesTrimmed = notes.trim();
    if (current === "approved" && decision === "review_ready" && !notesTrimmed) return;
    const res = await run({
      action: () =>
        contentStudioApi.reviewCaCandidate(cand.id, {
          status: decision,
          expected_status: current,
          expected_updated_at: token,
          reason: reason.trim(),
          reviewer_notes: notesTrimmed || undefined,
        }),
      errorMessage: "Could not record the decision.",
    });
    if (handle409(res)) onDone();
  };

  const promote = async () => {
    if (!reasonOk) return;
    const res = await run({
      action: () =>
        contentStudioApi.promoteCaCandidate(cand.id, {
          expected_status: "approved",
          expected_updated_at: token,
          reason: reason.trim(),
        }),
      errorMessage: "Could not promote the candidate.",
    });
    if (handle409(res)) onDone();
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
        style={{ maxWidth: 720, width: "92%", maxHeight: "88vh", overflow: "auto", padding: 20 }}
        data-testid="ca-review-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginTop: 0 }}>Current-affairs question — review</h3>

        {(envelope.warnings || []).length > 0 ? (
          <ul style={{ color: "#8a5a00" }} data-testid="ca-review-warnings">
            {envelope.warnings.map((w) => <li key={w}>{w.replaceAll("_", " ")}</li>)}
          </ul>
        ) : null}

        <div data-testid="ca-review-stem" style={{ fontWeight: 600, marginBottom: 8 }}>
          {payload.stem || "(no stem)"}
        </div>
        <ol type="a" data-testid="ca-review-options" style={{ marginBottom: 10 }}>
          {(payload.options || []).map((o) => (
            <li key={o.id} style={{ fontWeight: o.id === payload.correct_option_id ? 700 : 400 }}>
              {o.text}{o.id === payload.correct_option_id ? " ✓" : ""}
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
            <tr><th>Event</th><td>{envelope.event?.canonical_title || "—"}</td></tr>
            <tr><th>Relevance</th>
              <td>{envelope.event?.relevance_from || "—"} → {envelope.event?.relevance_until || "—"}</td></tr>
            <tr><th>Importance</th><td>{envelope.event?.editorial_importance || "—"}</td></tr>
            <tr><th>Status</th><td data-testid="ca-review-status-current">{current}</td></tr>
          </tbody>
        </table>

        <h4 style={{ margin: "8px 0" }}>Evidence</h4>
        <div data-testid="ca-review-claims">
          {(envelope.claims || []).length === 0 ? (
            <p style={{ color: "#8a5a00" }}>No linked claims.</p>
          ) : (
            (envelope.claims || []).map((c) => (
              <div key={c.id} style={{ marginBottom: 8, fontSize: 12 }} data-testid={`ca-review-claim-${c.id}`}>
                <div style={{ fontWeight: 600 }}>
                  {c.claim_text || "(missing claim)"}{" "}
                  <span style={{ opacity: 0.7 }}>[{c.factual_status || "?"}]</span>
                </div>
                {(c.evidence || []).map((e, i) => (
                  <div key={i} style={{ marginLeft: 12, opacity: 0.9 }}>
                    “{e.evidence_text}” —{" "}
                    <span data-testid="ca-review-source-authority">
                      {e.source?.name || "unknown source"} ({e.source?.authority_level || "?"})
                    </span>
                    {e.document?.source_url ? (
                      <> · <a href={e.document.source_url} target="_blank" rel="noreferrer">source</a></>
                    ) : null}
                  </div>
                ))}
              </div>
            ))
          )}
        </div>

        {conflict ? (
          <p style={{ color: "#b00" }} data-testid="ca-review-conflict">
            This candidate changed since you loaded it (409). Refresh the queue and re-read
            before deciding.
          </p>
        ) : (
          <>
            <div style={{ display: "grid", gap: 8, margin: "12px 0" }}>
              <label>
                Audit reason (8-500 chars, required)
                <input
                  className="input" value={reason} onChange={(e) => setReason(e.target.value)}
                  data-testid="ca-review-reason"
                />
              </label>
              {transitions.length > 0 ? (
                <>
                  <label>
                    Decision
                    <select
                      className="input" value={decision} onChange={(e) => setDecision(e.target.value)}
                      data-testid="ca-review-decision"
                    >
                      <option value="">Select…</option>
                      {transitions.map((t) => <option key={t} value={t}>{t}</option>)}
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
                    disabled={busy || !decision || !reasonOk || !perms.canReview}
                    data-testid="ca-review-submit"
                  >
                    Submit decision
                  </button>
                </>
              ) : null}
              {canPromote ? (
                <button
                  type="button" className="btn" onClick={promote} disabled={busy || !reasonOk}
                  data-testid="ca-review-promote"
                >
                  Promote to question bank
                </button>
              ) : null}
            </div>
          </>
        )}

        <button type="button" className="btn small" onClick={onClose} data-testid="ca-review-close">
          Close
        </button>
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
  const { items, status, total, refresh } = useApiCollection(LIST_URL, [], { params });

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
            {STATUSES.map((s) => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}
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
