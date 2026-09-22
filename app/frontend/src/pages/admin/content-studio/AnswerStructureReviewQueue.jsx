/**
 * Answer Structure Review Queue — draft → in_review → verified | rejected for
 * `answer_structures` (migration 303).
 *
 * AI drafts, a human verifies: nothing reaches an aspirant until a reviewer
 * approves it here. The reviewer can edit every content field first
 * ("edit-then-approve"), reject with a note, or regenerate — which drafts a NEW
 * version and leaves the current one exactly as it is (a verified version
 * stays live until its replacement is approved, which demotes it atomically).
 *
 * Every write is CAS-guarded on the `updated_at` the reviewer loaded, so a 409
 * means the structure changed under review: reload before deciding. Every
 * write is audited server-side; the trail is shown in the dialog.
 *
 * The model's own uncertainty flags and the fabrication lint (numbers, named
 * cases, dated reports) are shown to the reviewer beside the structure — they
 * are the first things to check before approving.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import useApiCollection from "../../../lib/hooks/useApiCollection";
import useApiAction from "../../../lib/hooks/useApiAction";
import { getApiErrorMessage } from "../../../lib/api";
import { ErrorState, EmptyState } from "../../../shared/ui/core";
import {
  contentStudioApi,
  ANSWER_STRUCTURE_STATUSES,
  ANSWER_STRUCTURE_TRANSITIONS,
  isValidReason,
} from "./contentStudioApi";

const PAGE_SIZE = 50;

const LIST_FIELDS = [
  ["intro_angles", "Intro angles"],
  ["dimensions", "Dimensions"],
  ["examples", "Examples"],
  ["conclusion_angles", "Conclusion angles"],
  ["pitfalls", "Pitfalls"],
];

const DECISION_LABEL = {
  in_review: "Send to review",
  verified: "Approve",
  rejected: "Reject",
  draft: "Back to draft",
};

function label(s) {
  return String(s || "").replaceAll("_", " ");
}

const linesOf = (text) =>
  String(text || "")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

/** The editable form state, built from a stored structure. Lists are edited as
 * one line per item; body points as their own rows. */
export function toForm(s) {
  return {
    directive: s.directive || "",
    demand: s.demand || "",
    sources_note: s.sources_note || "",
    word_budget: s.word_budget || null,
    ...Object.fromEntries(LIST_FIELDS.map(([k]) => [k, (s[k] || []).join("\n")])),
    body_points: (s.body_points || []).map((p) => ({
      id: p.id || "",
      point: p.point || "",
      why: p.why || "",
      evidence_type: p.evidence_type || "",
      example: p.example || "",
      thinker: p.thinker || "",
      sub_points: (p.sub_points || []).join("\n"),
    })),
  };
}

/** The PATCH payload for the fields that actually changed. */
export function formPatch(original, form) {
  const out = {};
  const base = toForm(original);
  ["directive", "demand"].forEach((k) => {
    if (form[k] !== base[k]) out[k] = form[k];
  });
  if (form.sources_note !== base.sources_note) out.sources_note = form.sources_note || null;
  LIST_FIELDS.forEach(([k]) => {
    if (form[k] !== base[k]) out[k] = linesOf(form[k]);
  });
  if (JSON.stringify(form.body_points) !== JSON.stringify(base.body_points)) {
    out.body_points = form.body_points.map((p) => ({
      id: p.id.trim(),
      point: p.point,
      why: p.why || null,
      evidence_type: p.evidence_type || null,
      example: p.example || null,
      thinker: p.thinker || null,
      sub_points: linesOf(p.sub_points),
    }));
  }
  if (JSON.stringify(form.word_budget) !== JSON.stringify(base.word_budget)) {
    out.word_budget = form.word_budget;
  }
  return out;
}

function nextPointId(points) {
  const used = new Set(points.map((p) => p.id));
  let n = points.length + 1;
  while (used.has(`p${n}`)) n += 1;
  return `p${n}`;
}

function BodyPointsEditor({ points, onChange, disabled }) {
  const set = (i, key, value) =>
    onChange(points.map((p, j) => (j === i ? { ...p, [key]: value } : p)));
  const move = (i, d) => {
    const j = i + d;
    if (j < 0 || j >= points.length) return;
    const next = [...points];
    [next[i], next[j]] = [next[j], next[i]];
    onChange(next);
  };
  return (
    <fieldset disabled={disabled} data-testid="structure-body-points">
      <legend style={{ fontSize: 12, fontWeight: 600 }}>Body points (ordered — learners tick these)</legend>
      {points.map((p, i) => (
        <div
          key={`${p.id}-${i}`}
          style={{ border: "1px solid var(--line, #ddd)", borderRadius: 4, padding: 8, marginTop: 6 }}
          data-testid={`structure-point-${i}`}
        >
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input
              className="input"
              style={{ width: 70, fontFamily: "monospace" }}
              aria-label={`Point ${i + 1} id`}
              value={p.id}
              onChange={(e) => set(i, "id", e.target.value)}
            />
            <input
              className="input"
              style={{ flex: 1 }}
              aria-label={`Point ${i + 1}`}
              value={p.point}
              onChange={(e) => set(i, "point", e.target.value)}
              data-testid={`structure-point-${i}-text`}
            />
            <button type="button" className="btn small" aria-label={`Move point ${i + 1} up`} onClick={() => move(i, -1)}>↑</button>
            <button type="button" className="btn small" aria-label={`Move point ${i + 1} down`} onClick={() => move(i, 1)}>↓</button>
            <button
              type="button"
              className="btn small"
              aria-label={`Remove point ${i + 1}`}
              onClick={() => onChange(points.filter((_, j) => j !== i))}
            >
              ✕
            </button>
          </div>
          {[
            ["why", "Why the examiner expects it"],
            ["evidence_type", "Evidence type"],
            ["example", "Example (optional)"],
            ["thinker", "Thinker (optional)"],
          ].map(([key, text]) => (
            <label key={key} style={{ display: "block", fontSize: 11, marginTop: 4 }}>
              {text}
              <input className="input" value={p[key]} onChange={(e) => set(i, key, e.target.value)} />
            </label>
          ))}
          <label style={{ display: "block", fontSize: 11, marginTop: 4 }}>
            Sub-points (one per line)
            <textarea className="input" rows={2} value={p.sub_points} onChange={(e) => set(i, "sub_points", e.target.value)} />
          </label>
        </div>
      ))}
      <button
        type="button"
        className="btn small"
        style={{ marginTop: 6 }}
        onClick={() =>
          onChange([...points, { id: nextPointId(points), point: "", why: "", evidence_type: "", example: "", thinker: "", sub_points: "" }])
        }
        data-testid="structure-add-point"
      >
        + Add point
      </button>
    </fieldset>
  );
}
BodyPointsEditor.propTypes = {
  points: PropTypes.arrayOf(PropTypes.object).isRequired,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};

function ReviewDialog({ row, perms, onClose, onDone }) {
  const [detail, setDetail] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [form, setForm] = useState(null);
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const { run, busy } = useApiAction();
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  const load = () => {
    setLoadError("");
    contentStudioApi
      .getAnswerStructure(row.id)
      .then((d) => {
        setDetail(d);
        setForm(toForm(d.structure));
        setConflict(false);
      })
      .catch((e) => setLoadError(getApiErrorMessage(e)));
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [row.id]);

  useEffect(() => {
    const prevFocus = typeof document !== "undefined" ? document.activeElement : null;
    const onKey = (e) => { if (e.key === "Escape") closeRef.current(); };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (prevFocus && typeof prevFocus.focus === "function") prevFocus.focus();
    };
  }, []);

  useEffect(() => {
    const node = dialogRef.current;
    const first = node && node.querySelector("input, textarea, select, button");
    if (first && detail) first.focus();
  }, [detail]);

  const s = detail?.structure;
  const editable = !!detail?.editable && (perms.canAuthor || perms.canReview);
  const patch = s && form ? formPatch(s, form) : {};
  const dirty = Object.keys(patch).length > 0;
  const transitions = s ? ANSWER_STRUCTURE_TRANSITIONS[s.status] || [] : [];
  const meta = s?.generation_meta || {};

  const handleError = (res) => {
    if (res.ok || !res.error) return;
    if (res.error.status === 409) setConflict(true);
    else setError(getApiErrorMessage(res.error));
  };

  /** Save edits; resolves to the new updated_at (the next CAS token) or null. */
  const saveEdits = async () => {
    if (!isValidReason(reason)) {
      setError("Reason for the edit must be 8–500 characters.");
      return null;
    }
    const res = await run({
      action: () =>
        contentStudioApi.updateAnswerStructure(s.id, {
          expected_updated_at: s.updated_at,
          reason: reason.trim(),
          payload: patch,
        }),
      successMessage: "Edits saved.",
      errorMessage: " ",
    });
    handleError(res);
    return res.ok ? res.data?.result?.updated_at || null : null;
  };

  const decide = async (status) => {
    setError("");
    setConflict(false);
    if (status === "rejected" && !notes.trim()) {
      setError("A rejection needs a note saying why.");
      return;
    }
    let token = s.updated_at;
    // EDIT-THEN-APPROVE: unsaved edits are saved first, and the decision is
    // made against the revision those edits produced — never against the
    // stale one the dialog opened with.
    if (dirty && editable && status !== "rejected") {
      token = await saveEdits();
      if (!token) return;
    }
    const res = await run({
      action: () =>
        contentStudioApi.reviewAnswerStructure(s.id, {
          status,
          expected_status: s.status,
          expected_updated_at: token,
          review_notes: notes.trim() || undefined,
        }),
      successMessage: `Structure ${label(status)}.`,
      errorMessage: " ",
      onSuccess: onDone,
    });
    handleError(res);
  };

  const regenerate = async () => {
    setError("");
    if (!isValidReason(reason)) {
      setError("Say why you are regenerating (8–500 characters) in the reason field.");
      return;
    }
    const res = await run({
      action: () => contentStudioApi.regenerateAnswerStructure(s.id, { reason: reason.trim() }),
      successMessage: "A new draft version was generated.",
      errorMessage: " ",
      onSuccess: onDone,
      confirm: "Generate a new draft version with the model? The current version is left unchanged.",
    });
    handleError(res);
  };

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={onClose}
      data-testid="structure-review-overlay"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Review answer structure"
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(880px, 96vw)", maxHeight: "90vh", overflowY: "auto", background: "var(--paper, #fff)", borderRadius: 6, padding: "1.25rem", boxShadow: "0 4px 16px rgba(0,0,0,0.25)" }}
        data-testid="structure-review-dialog"
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Review answer structure</h2>
          <button type="button" className="btn small" onClick={onClose} aria-label="Close review">✕</button>
        </div>

        {!detail && !loadError ? <div style={{ padding: "1.5rem", opacity: 0.7 }}>Loading full structure…</div> : null}
        {loadError ? <div style={{ color: "var(--err, #c00)", fontSize: 12 }} role="alert">{loadError}</div> : null}

        {s && form ? (
          <>
            <div style={{ fontSize: 13, marginBottom: 6 }} data-testid="structure-question">
              {detail.question?.text}
            </div>
            <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 10 }}>
              {[detail.question?.subject, detail.question?.paper, detail.question?.year,
                detail.question?.marks ? `${detail.question.marks} marks` : null,
                detail.question?.word_limit ? `${detail.question.word_limit} words` : null]
                .filter(Boolean).join(" · ")}
              {" · "}v{s.version} · <strong>{label(s.status)}</strong> · {s.generated_by}
            </div>

            {(meta.uncertainty?.length > 0 || meta.lint_warnings?.length > 0) && (
              <div
                role="note"
                style={{ padding: "0.6rem", marginBottom: 10, fontSize: 12, borderLeft: "3px solid var(--blocker, #b3382d)", background: "var(--paper-sunk, #f3eee4)", whiteSpace: "normal" }}
                data-testid="structure-flags"
              >
                <strong>Check before approving</strong>
                <ul style={{ margin: "4px 0 0 16px" }}>
                  {(meta.uncertainty || []).map((u) => <li key={`u-${u}`}>Model unsure: {u}</li>)}
                  {(meta.lint_warnings || []).map((w) => (
                    <li key={`${w.field}-${w.kind}-${w.match}`}>
                      {label(w.kind)} in {w.field}: “{w.match}”
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <fieldset disabled={!editable || busy} style={{ border: 0, padding: 0 }}>
              <label style={{ display: "block", fontSize: 12, marginBottom: 8 }}>
                Directive
                <input className="input" value={form.directive} onChange={(e) => setForm({ ...form, directive: e.target.value })} data-testid="structure-directive" />
              </label>
              <label style={{ display: "block", fontSize: 12, marginBottom: 8 }}>
                Demand (1–2 lines)
                <textarea className="input" rows={2} value={form.demand} onChange={(e) => setForm({ ...form, demand: e.target.value })} data-testid="structure-demand" />
              </label>
              {LIST_FIELDS.map(([key, text]) => (
                <label key={key} style={{ display: "block", fontSize: 12, marginBottom: 8 }}>
                  {text} (one per line)
                  <textarea className="input" rows={3} value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} data-testid={`structure-${key}`} />
                </label>
              ))}
              <BodyPointsEditor
                points={form.body_points}
                onChange={(body_points) => setForm({ ...form, body_points })}
                disabled={!editable || busy}
              />
              <div style={{ display: "flex", gap: 8, marginTop: 8, fontSize: 12 }} data-testid="structure-word-budget">
                {["total", "intro", "body", "conclusion"].map((k) => (
                  <label key={k}>
                    {k}
                    <input
                      className="input"
                      type="number"
                      min={1}
                      style={{ width: 80 }}
                      value={form.word_budget?.[k] ?? ""}
                      onChange={(e) => {
                        const v = e.target.value === "" ? null : Number(e.target.value);
                        setForm({ ...form, word_budget: { ...(form.word_budget || { basis: null }), [k]: v } });
                      }}
                    />
                  </label>
                ))}
              </div>
              <label style={{ display: "block", fontSize: 12, margin: "8px 0" }}>
                Sources note
                <input className="input" value={form.sources_note} onChange={(e) => setForm({ ...form, sources_note: e.target.value })} />
              </label>
            </fieldset>
            {!detail.editable ? (
              <p style={{ fontSize: 12, opacity: 0.7 }}>
                A {label(s.status)} structure is not edited in place. Regenerate to draft a new version.
              </p>
            ) : null}

            {conflict ? (
              <div className="badge blocker" style={{ display: "block", padding: "0.6rem", margin: "10px 0", fontSize: 12 }} role="alert">
                The structure changed since you loaded it (409). Reload and review the latest revision.
                {" "}
                <button type="button" className="btn small" onClick={load}>Reload</button>
              </div>
            ) : null}
            {error && error.trim() ? (
              <div style={{ color: "var(--err, #c00)", fontSize: 12, margin: "10px 0" }} role="alert">{error}</div>
            ) : null}

            <label style={{ display: "block", fontSize: 12, margin: "10px 0" }}>
              Reason (edits and regenerate; 8–500 chars, recorded in the audit log)
              <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} data-testid="structure-reason" />
            </label>
            <label style={{ display: "block", fontSize: 12, marginBottom: 12 }}>
              Review note (required to reject)
              <textarea className="input" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="structure-notes" />
            </label>

            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "flex-end", gap: 8 }}>
              {editable && dirty ? (
                <button type="button" className="btn" disabled={busy} onClick={async () => { setError(""); if (await saveEdits()) load(); }} data-testid="structure-save">
                  Save edits
                </button>
              ) : null}
              {perms.canAuthor ? (
                <button type="button" className="btn" disabled={busy} onClick={regenerate} data-testid="structure-regenerate">
                  Regenerate
                </button>
              ) : null}
              {perms.canReview
                ? transitions.map((t) => (
                    <button
                      key={t}
                      type="button"
                      className={`btn${t === "verified" ? " primary" : ""}`}
                      disabled={busy}
                      onClick={() => decide(t)}
                      data-testid={`structure-decide-${t}`}
                    >
                      {t === "verified" && dirty && editable ? "Save & approve" : DECISION_LABEL[t]}
                    </button>
                  ))
                : null}
            </div>

            {detail.versions?.length > 1 ? (
              <div style={{ marginTop: 14, fontSize: 12 }} data-testid="structure-versions">
                <strong>Versions:</strong>{" "}
                {detail.versions.map((v) => `v${v.version} ${label(v.status)}`).join(" · ")}
              </div>
            ) : null}
            <div style={{ marginTop: 10 }} data-testid="structure-audit">
              <div style={{ fontSize: 12, fontWeight: 600 }}>Audit trail</div>
              <ul style={{ fontSize: 11, margin: "4px 0 0 16px", opacity: 0.85 }}>
                {(detail.audit || []).map((a) => (
                  <li key={a.id}>
                    {String(a.created_at || "").slice(0, 16).replace("T", " ")} · {label(a.action)}
                    {a.new_value?.status ? ` → ${label(a.new_value.status)}` : ""}
                    {a.actor_email ? ` · ${a.actor_email}` : ""}
                    {a.notes ? ` · “${a.notes}”` : ""}
                  </li>
                ))}
              </ul>
              {meta.model ? (
                <div style={{ fontSize: 11, opacity: 0.7, marginTop: 4 }}>
                  Generated by {meta.model} ({meta.prompt_version}) · {meta.attempts} attempt(s)
                  {typeof meta.cost_usd === "number" ? ` · $${meta.cost_usd.toFixed(4)}` : ""}
                </div>
              ) : null}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
ReviewDialog.propTypes = {
  row: PropTypes.object.isRequired,
  perms: PropTypes.object.isRequired,
  onClose: PropTypes.func.isRequired,
  onDone: PropTypes.func.isRequired,
};

export default function AnswerStructureReviewQueue({ perms }) {
  const [filters, setFilters] = useState({ status: "draft", subject: "", paper: "", year: "" });
  const [offset, setOffset] = useState(0);
  const [facets, setFacets] = useState({ subjects: [], papers: [], years: [] });
  const [reviewing, setReviewing] = useState(null);

  useEffect(() => {
    let live = true;
    contentStudioApi
      .listAnswerStructures({ limit: 1 })
      .then((d) => live && d?.facets && setFacets(d.facets))
      .catch(() => {});
    return () => { live = false; };
  }, []);

  const params = useMemo(() => ({ ...filters, limit: PAGE_SIZE, offset }), [filters, offset]);
  const { items, status, total, refresh } = useApiCollection(
    "/api/admin/content-studio/answer-structures",
    [],
    { params },
  );

  const setFilter = (key, value) => {
    setOffset(0);
    setFilters((f) => ({ ...f, [key]: value }));
  };
  const hasNext =
    total !== null ? offset + PAGE_SIZE < total : status === "live" && items.length === PAGE_SIZE;

  const select = (key, text, options) => (
    <label style={{ fontSize: 12 }}>
      {text}
      <select className="input" value={filters[key]} onChange={(e) => setFilter(key, e.target.value)} data-testid={`structure-filter-${key}`}>
        <option value="">All</option>
        {options.map((o) => <option key={o} value={o}>{label(o)}</option>)}
      </select>
    </label>
  );

  return (
    <div style={{ padding: 16 }} data-testid="answer-structure-review-queue">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        {select("status", "Status", ANSWER_STRUCTURE_STATUSES)}
        {select("subject", "Subject", facets.subjects || [])}
        {select("paper", "Paper", facets.papers || [])}
        {select("year", "Year", (facets.years || []).map(String))}
        {!perms.canReview ? (
          <span style={{ fontSize: 12, opacity: 0.7 }}>
            Read-only decisions — approving requires content_studio.review.
          </span>
        ) : null}
      </div>

      {status === "loading" ? <div style={{ padding: "2rem", opacity: 0.7 }}>Loading queue…</div> : null}
      {status === "error" ? <ErrorState message="Could not load the answer-structure queue." onRetry={refresh} /> : null}
      {status === "empty" ? (
        <EmptyState title="Queue is clear" description="No answer structures match these filters." />
      ) : null}

      {status === "live" ? (
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" data-testid="structure-queue-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Subject · Paper · Year</th>
                <th>Directive</th>
                <th>Version</th>
                <th>Status</th>
                <th style={{ width: 90 }} />
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id} data-testid="structure-queue-row">
                  <td style={{ fontSize: 13, maxWidth: 360 }}>{r.question?.excerpt}</td>
                  <td style={{ fontSize: 12 }}>
                    {[r.question?.subject, r.question?.paper, r.question?.year].filter(Boolean).join(" · ")}
                  </td>
                  <td style={{ fontSize: 12 }}>{r.directive}</td>
                  <td style={{ fontSize: 12 }}>v{r.version}</td>
                  <td style={{ fontSize: 12 }}>{label(r.status)}</td>
                  <td>
                    <button type="button" className="btn small" onClick={() => setReviewing(r)} data-testid={`structure-open-${r.id}`}>
                      {perms.canReview || perms.canAuthor ? "Review" : "View"}
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
          <span style={{ fontSize: 12, opacity: 0.7, marginRight: "auto" }}>
            {total === 0 ? "0" : `${offset + 1}–${offset + items.length}`} of {total}
          </span>
        ) : null}
        {offset > 0 ? (
          <button type="button" className="btn small" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>← Prev</button>
        ) : null}
        {hasNext ? (
          <button type="button" className="btn small" onClick={() => setOffset(offset + PAGE_SIZE)}>Next →</button>
        ) : null}
      </div>

      {reviewing ? (
        <ReviewDialog
          row={reviewing}
          perms={perms}
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
AnswerStructureReviewQueue.propTypes = {
  perms: PropTypes.object.isRequired,
};
