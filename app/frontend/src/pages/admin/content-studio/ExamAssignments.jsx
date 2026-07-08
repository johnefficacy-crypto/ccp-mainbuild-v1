/**
 * Exam Assignments — writing_prompt_targets, the sole applicability authority.
 *
 * J2 authority split (locked): exam_intelligence.manage may only PROPOSE an
 * inert pending_review assignment; promoting it to active/excluded and removing
 * it require exam_intelligence.review. Default-deny: a prompt with no active
 * target is not applicable anywhere — global is an explicit is_global row,
 * never implied. Review/remove are CAS-guarded on the target's updated_at.
 */
import React, { useEffect, useRef, useState } from "react";
import useApiAction from "../../../lib/hooks/useApiAction";
import { getApiErrorMessage } from "../../../lib/api";
import { contentStudioApi, isValidReason } from "./contentStudioApi";
import { ExamFamilySelect, ExamSelect, ExamPhaseSelect } from "./selectors";

const SCOPES = [
  { id: "global", label: "Global (all exams)" },
  { id: "exam_family_id", label: "Exam family" },
  { id: "exam_id", label: "Exam" },
  { id: "exam_phase_id", label: "Exam phase" },
];

// Readable scope label — prefers the enriched *_name the backend resolves, and
// falls back to the raw id only if a name could not be resolved.
export function scopeLabel(t) {
  if (t.is_global) return "Global (all exams)";
  if (t.exam_phase_id) return `Phase: ${t.exam_phase_name || t.exam_phase_id}`;
  if (t.exam_id) return `Exam: ${t.exam_name || t.exam_id}`;
  if (t.exam_family_id) return `Family: ${t.exam_family_name || t.exam_family_id}`;
  return "unknown scope";
}

function ProposeForm({ promptId, onDone }) {
  const [scope, setScope] = useState("exam_id");
  // Intermediate family/exam picks are UI-only filters; only the LEAF id for the
  // chosen scope is ever sent, preserving the migration-214 exactly-one contract.
  const [familyId, setFamilyId] = useState("");
  const [examId, setExamId] = useState("");
  const [scopeId, setScopeId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const { run, busy } = useApiAction();

  const resetScope = (nextScope) => {
    setScope(nextScope);
    setFamilyId("");
    setExamId("");
    setScopeId("");
  };

  const submit = async () => {
    if (!isValidReason(reason)) { setError("Reason must be 8–500 characters."); return; }
    if (scope !== "global" && !scopeId.trim()) { setError("Select the exam scope."); return; }
    setError("");
    // EXACTLY ONE scope key on the body: global OR exactly one of the id columns.
    const body = { reason: reason.trim() };
    if (scope === "global") body.is_global = true;
    else body[scope] = scopeId.trim();
    const res = await run({
      action: () => contentStudioApi.proposeTarget(promptId, body),
      successMessage: "Assignment proposed (pending review — not yet effective).",
      errorMessage: " ",
      onSuccess: onDone,
    });
    if (!res.ok && res.error) {
      setError(
        res.error.status === 409
          ? "An assignment for this exact scope already exists — review or remove it instead."
          : getApiErrorMessage(res.error),
      );
    }
  };

  return (
    <div style={{ border: "1px solid var(--rule, #ddd)", borderRadius: 4, padding: "0.75rem", marginTop: 10 }} data-testid="assignment-propose">
      <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Propose assignment (lands pending review)</div>
      {error ? <div style={{ color: "var(--err, #c00)", fontSize: 12, marginBottom: 8 }} role="alert">{error}</div> : null}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end" }}>
        <label style={{ fontSize: 12 }}>
          Scope (exactly one)
          <select className="input" value={scope} onChange={(e) => resetScope(e.target.value)} data-testid="assignment-scope">
            {SCOPES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </label>

        {scope === "exam_family_id" ? (
          <label style={{ fontSize: 12 }}>
            Exam family
            <ExamFamilySelect value={scopeId} onChange={setScopeId} testId="assignment-scope-family" />
          </label>
        ) : null}

        {scope === "exam_id" ? (
          <>
            <label style={{ fontSize: 12 }}>
              Exam family (filter)
              <ExamFamilySelect value={familyId} onChange={(v) => { setFamilyId(v); setScopeId(""); }} testId="assignment-filter-family" />
            </label>
            <label style={{ fontSize: 12 }}>
              Exam
              <ExamSelect familyId={familyId} value={scopeId} onChange={setScopeId} testId="assignment-scope-exam" />
            </label>
          </>
        ) : null}

        {scope === "exam_phase_id" ? (
          <>
            <label style={{ fontSize: 12 }}>
              Exam family (filter)
              <ExamFamilySelect value={familyId} onChange={(v) => { setFamilyId(v); setExamId(""); setScopeId(""); }} testId="assignment-filter-family" />
            </label>
            <label style={{ fontSize: 12 }}>
              Exam (filter)
              <ExamSelect familyId={familyId} value={examId} onChange={(v) => { setExamId(v); setScopeId(""); }} testId="assignment-filter-exam" />
            </label>
            <label style={{ fontSize: 12 }}>
              Phase
              <ExamPhaseSelect examId={examId} value={scopeId} onChange={setScopeId} testId="assignment-scope-phase" />
            </label>
          </>
        ) : null}

        <label style={{ fontSize: 12, flex: 1, minWidth: 200 }}>
          Reason (8–500 chars)
          <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} data-testid="assignment-reason" />
        </label>
        <button type="button" className="btn primary small" onClick={submit} disabled={busy} data-testid="assignment-propose-submit">
          {busy ? "Proposing…" : "Propose"}
        </button>
      </div>
    </div>
  );
}

function TargetRow({ target, perms, promptId, onChanged }) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const { run, busy } = useApiAction();

  const act = async (fn, successMessage) => {
    if (!isValidReason(reason)) { setError("Reason must be 8–500 characters."); return; }
    setError("");
    const res = await run({ action: fn, successMessage, errorMessage: " ", onSuccess: onChanged });
    if (!res.ok && res.error) {
      setError(
        res.error.status === 409
          ? "This assignment changed under you (409) — refresh and retry."
          : getApiErrorMessage(res.error),
      );
    }
  };

  const promote = (applicability_status) =>
    act(
      () => contentStudioApi.reviewTarget(target.id, {
        reason: reason.trim(),
        applicability_status,
        expected_updated_at: target.updated_at,
      }),
      `Assignment marked ${applicability_status}.`,
    );
  const remove = () =>
    act(
      () => contentStudioApi.removeTarget(target.id, {
        reason: reason.trim(),
        expected_updated_at: target.updated_at,
      }),
      "Assignment removed.",
    );

  const reviewable = perms.canReviewAssignment;

  return (
    <tr data-testid={`assignment-row-${target.id}`}>
      <td style={{ fontSize: 12 }}>{scopeLabel(target)}</td>
      <td>
        <span className="badge info">{target.applicability_status}</span>
        {target.applicability_status === "pending_review" ? (
          <span style={{ fontSize: 11, opacity: 0.6, marginLeft: 6 }}>(inert — confers no applicability)</span>
        ) : null}
      </td>
      <td style={{ fontSize: 12, textAlign: "right" }}>{target.priority_score ?? "—"}</td>
      <td>
        {reviewable ? (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
            <input
              className="input"
              style={{ width: 180, fontSize: 12 }}
              placeholder="Reason (8–500 chars)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              data-testid={`assignment-action-reason-${target.id}`}
            />
            {target.applicability_status !== "active" ? (
              <button type="button" className="btn small" disabled={busy} onClick={() => promote("active")} data-testid={`assignment-activate-${target.id}`}>
                Activate
              </button>
            ) : null}
            {!target.is_global && target.applicability_status !== "excluded" ? (
              <button type="button" className="btn small" disabled={busy} onClick={() => promote("excluded")} data-testid={`assignment-exclude-${target.id}`}>
                Exclude
              </button>
            ) : null}
            <button type="button" className="btn small" disabled={busy} onClick={remove} data-testid={`assignment-remove-${target.id}`}>
              Remove
            </button>
          </div>
        ) : (
          <span style={{ fontSize: 11, opacity: 0.6 }}>awaiting review (exam_intelligence.review)</span>
        )}
        {error ? <div style={{ color: "var(--err, #c00)", fontSize: 11, marginTop: 4 }} role="alert">{error}</div> : null}
      </td>
    </tr>
  );
}

export default function ExamAssignments({ perms, promptIdParam = "" }) {
  const [promptId, setPromptId] = useState(promptIdParam);
  const [loadedFor, setLoadedFor] = useState("");
  const [targets, setTargets] = useState([]);
  const [summary, setSummary] = useState(null); // selected prompt snapshot
  const [state, setState] = useState("idle"); // idle | loading | live | empty | error
  const [loadError, setLoadError] = useState("");
  const loadRef = useRef(null);

  const load = async (id) => {
    const target = (id ?? promptId).trim();
    if (!target) return;
    setState("loading");
    setLoadError("");
    try {
      // Fetch the prompt snapshot (so the operator sees WHAT they are assigning,
      // not just a UUID) and its targets together.
      const [prompt, d] = await Promise.all([
        contentStudioApi.getPrompt(target).catch(() => null),
        contentStudioApi.listTargets(target),
      ]);
      const items = Array.isArray(d?.items) ? d.items : [];
      setSummary(prompt);
      setTargets(items);
      setLoadedFor(target);
      setState(items.length ? "live" : "empty");
    } catch (e) {
      setLoadError(getApiErrorMessage(e));
      setState("error");
    }
  };
  loadRef.current = load;

  // Deep link from the Library ("Assign") arrives as ?prompt_id=… — auto-load it.
  useEffect(() => {
    if (promptIdParam) {
      setPromptId(promptIdParam);
      loadRef.current(promptIdParam);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [promptIdParam]);

  return (
    <div style={{ padding: 16, maxWidth: 900 }} data-testid="exam-assignments">
      <p style={{ fontSize: 12, opacity: 0.75, marginBottom: 12 }}>
        Applicability is default-deny: a prompt with no <strong>active</strong>{" "}
        assignment is not deliverable anywhere. Managers propose assignments
        (pending review); reviewers make them active/excluded or remove them.
      </p>

      <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        <label style={{ fontSize: 12, flex: 1, maxWidth: 420 }}>
          Writing prompt ID
          <input
            className="input"
            value={promptId}
            onChange={(e) => setPromptId(e.target.value)}
            placeholder="UUID (from the Library tab)"
            data-testid="assignments-prompt-id"
          />
        </label>
        <button type="button" className="btn primary small" onClick={() => load()} disabled={!promptId.trim() || state === "loading"} data-testid="assignments-load">
          {state === "loading" ? "Loading…" : "Load assignments"}
        </button>
      </div>

      {summary && (state === "live" || state === "empty") ? (
        <div style={{ border: "1px solid var(--rule, #ddd)", borderRadius: 4, padding: "0.6rem 0.75rem", marginBottom: 12, fontSize: 12 }} data-testid="assignments-selected-prompt">
          <div style={{ fontWeight: 600, marginBottom: 2 }}>Selected prompt</div>
          <div style={{ opacity: 0.85 }}>
            {(summary.exercise_type || "").replaceAll("_", " ")} · difficulty {summary.difficulty_level}/10 · {summary.reviewer_status}
          </div>
          {summary.subject_name || summary.topic_name ? (
            <div style={{ opacity: 0.7, marginTop: 2 }} data-testid="assignments-prompt-taxonomy">
              {[summary.subject_name, summary.topic_name, summary.microtopic_name].filter(Boolean).join(" › ")}
            </div>
          ) : null}
          <div style={{ opacity: 0.7, marginTop: 2, maxWidth: 640, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {summary.prompt_text}
          </div>
        </div>
      ) : null}

      {state === "error" ? (
        <div style={{ color: "var(--err, #c00)", fontSize: 12, marginBottom: 12 }} role="alert">{loadError}</div>
      ) : null}
      {state === "empty" ? (
        <div style={{ fontSize: 13, opacity: 0.75, marginBottom: 12 }} data-testid="assignments-empty">
          No assignments — this prompt is currently not applicable to any exam.
        </div>
      ) : null}

      {state === "live" ? (
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" data-testid="assignments-table">
            <thead>
              <tr>
                <th>Scope</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Priority</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {targets.map((t) => (
                <TargetRow key={t.id} target={t} perms={perms} promptId={loadedFor} onChanged={() => load(loadedFor)} />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {(state === "live" || state === "empty") && perms.canProposeAssignment ? (
        <ProposeForm promptId={loadedFor} onDone={() => load(loadedFor)} />
      ) : null}
    </div>
  );
}
