import React, { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { api } from "../../lib/api";
import useApiCollection from "../../lib/hooks/useApiCollection";
import useApiAction from "../../lib/hooks/useApiAction";
import { useAuth } from "../../lib/authContext";
import { useFocusTrap } from "../../shared/a11y/useFocusTrap";
import { EmptyState, ErrorState, LoadingSkeleton, StatusBadge } from "../../shared/ui/core";
import VerificationReportCard from "../../features/admin/workflow/VerificationReportCard";
import BulkActionPreview from "../../features/admin/workflow/BulkActionPreview";


const ACTION_TYPES = [
  { value: "cycle_date_update", label: "Cycle date update" },
  { value: "phase_date_update", label: "Phase date update" },
  { value: "policy_update_create", label: "Policy update — create" },
  { value: "policy_update_edit", label: "Policy update — edit" },
];

// FK picker endpoints (CMS router, exam_id scoped when available)
const CYCLE_URL = "/api/admin/exam-intelligence-cms/exam-cycles";
const PHASE_URL = "/api/admin/exam-intelligence-cms/exam-phases";
const POLICY_URL = "/api/admin/exam-intelligence-cms/policy-updates";

// ─── FK select field backed by a collection ───────────────────────────────────

function FkSelect({ url, value, onChange, labelKey = "name", testId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    api.get(url)
      .then((d) => { if (active) setItems(Array.isArray(d?.items) ? d.items : []); })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [url]);

  return (
    <select
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
      data-testid={testId}
    >
      <option value="">— select —</option>
      {loading && <option disabled>Loading…</option>}
      {items.map((it) => (
        <option key={it.id} value={it.id}>
          {it[labelKey] || it.id}
        </option>
      ))}
    </select>
  );
}

// ─── Apply-registry-action panel ──────────────────────────────────────────────

function ApplyRegistryActionPanel({ reportId, onSuccess }) {
  const [actionType, setActionType] = useState("");
  const [examCycleId, setExamCycleId] = useState("");
  const [examPhaseId, setExamPhaseId] = useState("");
  const [policyUpdateId, setPolicyUpdateId] = useState("");
  const [patch, setPatch] = useState("{}");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState(null);
  const { run, busy } = useApiAction();

  async function submit(e) {
    e.preventDefault();
    setError(null);

    if (reason.trim().length < 8 || reason.trim().length > 500) {
      setError("Reason must be 8–500 characters.");
      return;
    }
    if (notes.length > 2000) {
      setError("Notes must be ≤2000 characters.");
      return;
    }

    let parsedPatch;
    try {
      parsedPatch = JSON.parse(patch);
      if (typeof parsedPatch !== "object" || Array.isArray(parsedPatch) || parsedPatch === null) {
        throw new Error("must be a JSON object");
      }
    } catch {
      setError("Patch must be a valid JSON object.");
      return;
    }

    const body = {
      action_type: actionType,
      patch: parsedPatch,
      reason: reason.trim(),
    };
    if (examCycleId) body.exam_cycle_id = examCycleId;
    if (examPhaseId) body.exam_phase_id = examPhaseId;
    if (policyUpdateId) body.policy_update_id = policyUpdateId;
    if (notes.trim()) body.notes = notes.trim();

    const res = await run({
      action: () => api.post(`/api/admin/verification-reports/${reportId}/apply-registry-action`, body),
      successMessage: "Registry action applied.",
      errorMessage: "Failed to apply registry action.",
      onSuccess,
    });

    if (!res.ok && !res.cancelled) {
      setError(res.error?.message || "Failed to apply registry action.");
    }
  }

  return (
    <form onSubmit={submit} className="mt-4 space-y-3" noValidate data-testid="apply-action-form">
      <h4 className="text-sm font-semibold text-gray-900">Apply registry action</h4>

      {/* action_type */}
      <div>
        <label className="block text-xs text-gray-500 mb-1" htmlFor="rar-action-type">Action type *</label>
        <select
          id="rar-action-type"
          value={actionType}
          onChange={(e) => { setActionType(e.target.value); setExamCycleId(""); setExamPhaseId(""); setPolicyUpdateId(""); }}
          className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
          data-testid="rar-action-type"
          required
        >
          <option value="">— choose action —</option>
          {ACTION_TYPES.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
        </select>
      </div>

      {/* FK pickers — shown based on action_type */}
      {actionType === "cycle_date_update" && (
        <div>
          <label className="block text-xs text-gray-500 mb-1">Exam cycle *</label>
          <FkSelect
            url={CYCLE_URL}
            value={examCycleId}
            onChange={setExamCycleId}
            labelKey="cycle_name"
            testId="rar-exam-cycle-id"
          />
        </div>
      )}
      {actionType === "phase_date_update" && (
        <div>
          <label className="block text-xs text-gray-500 mb-1">Exam phase *</label>
          <FkSelect
            url={PHASE_URL}
            value={examPhaseId}
            onChange={setExamPhaseId}
            labelKey="phase_name"
            testId="rar-exam-phase-id"
          />
        </div>
      )}
      {actionType === "policy_update_edit" && (
        <div>
          <label className="block text-xs text-gray-500 mb-1">Policy update *</label>
          <FkSelect
            url={POLICY_URL}
            value={policyUpdateId}
            onChange={setPolicyUpdateId}
            labelKey="title"
            testId="rar-policy-update-id"
          />
        </div>
      )}

      {/* patch JSON */}
      <div>
        <label className="block text-xs text-gray-500 mb-1" htmlFor="rar-patch">
          Patch (JSON object)
        </label>
        <textarea
          id="rar-patch"
          value={patch}
          onChange={(e) => setPatch(e.target.value)}
          rows={3}
          className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-xs font-mono"
          data-testid="rar-patch"
        />
      </div>

      {/* reason */}
      <div>
        <label className="block text-xs text-gray-500 mb-1" htmlFor="rar-reason">
          Reason * (8–500 chars)
        </label>
        <textarea
          id="rar-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
          className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
          data-testid="rar-reason"
          required
        />
      </div>

      {/* notes */}
      <div>
        <label className="block text-xs text-gray-500 mb-1" htmlFor="rar-notes">
          Notes (optional, ≤2000)
        </label>
        <textarea
          id="rar-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
          data-testid="rar-notes"
        />
      </div>

      {error && (
        <div
          className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
          data-testid="rar-error"
        >
          {error}
        </div>
      )}

      <div className="flex justify-end pt-1">
        <button
          type="submit"
          className="btn btn-primary text-sm"
          disabled={busy || !actionType}
          data-testid="rar-submit"
        >
          {busy ? "Applying…" : "Apply action"}
        </button>
      </div>
    </form>
  );
}

// ─── Run-resolver panel ───────────────────────────────────────────────────────

function RunResolverPanel({ report, onSuccess }) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin" || user?.role === "super_admin";
  const [cooldownMsg, setCooldownMsg] = useState(null);
  const [resolverError, setResolverError] = useState(null);
  const { run, busy } = useApiAction();

  if (!isAdmin) return null;

  async function handleRun() {
    setCooldownMsg(null);
    setResolverError(null);
    const res = await run({
      action: () => api.post(`/api/admin/verification-reports/${report.id}/run-resolver`, {}),
      successMessage: "Resolver re-run complete.",
      errorMessage: "Resolver re-run failed.",
      onSuccess,
    });
    if (!res.ok && !res.cancelled) {
      const msg = res.error?.message || "";
      if (msg.toLowerCase().includes("cooldown") || msg.toLowerCase().includes("cap") || res.error?.status === 429) {
        setCooldownMsg(msg || "Resolver cooldown active. Please wait before retrying.");
      } else {
        setResolverError(msg || "Resolver re-run failed.");
      }
    }
  }

  return (
    <div className="mt-6 rounded-2xl border border-border bg-white/60 px-5 py-4 space-y-3" data-testid="run-resolver-panel">
      <h4 className="text-sm font-semibold text-gray-900">Run resolver</h4>
      <p className="text-xs text-muted-foreground">
        Force a resolver re-run to re-check the official URL. Subject to per-report cooldown and hourly cap.
      </p>
      <button
        type="button"
        className="btn btn-ghost text-sm"
        onClick={handleRun}
        disabled={busy || !!cooldownMsg}
        data-testid="run-resolver-btn"
      >
        {busy ? "Running…" : "Re-run resolver"}
      </button>
      {cooldownMsg && (
        <div
          className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800"
          data-testid="resolver-cooldown-msg"
        >
          {cooldownMsg}
        </div>
      )}
      {resolverError && (
        <div
          className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
          data-testid="resolver-error"
        >
          {resolverError}
        </div>
      )}
    </div>
  );
}

// ─── Confirm-proof panel ──────────────────────────────────────────────────────

function ConfirmProofPanel({ report, onSuccess }) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin" || user?.role === "super_admin";
  const [chosenUrl, setChosenUrl] = useState("");
  const [proofError, setProofError] = useState(null);
  const { run, busy } = useApiAction();

  const suggestedUrls = report.suggested_official_urls || [];

  if (!isAdmin || suggestedUrls.length === 0) return null;

  async function handleConfirm(e) {
    e.preventDefault();
    setProofError(null);
    if (!chosenUrl) {
      setProofError("Select a URL to confirm.");
      return;
    }
    const valid = suggestedUrls.some((u) => u.url === chosenUrl);
    if (!valid) {
      setProofError("Chosen URL is not in the suggested set.");
      return;
    }
    const res = await run({
      action: () => api.post(`/api/admin/verification-reports/${report.id}/confirm-suggested-proof`, { chosen_url: chosenUrl }),
      successMessage: "Official proof confirmed.",
      errorMessage: "Failed to confirm proof.",
      onSuccess,
    });
    if (!res.ok && !res.cancelled) {
      setProofError(res.error?.message || "Failed to confirm proof.");
    }
  }

  return (
    <div className="mt-6 rounded-2xl border border-border bg-white/60 px-5 py-4 space-y-3" data-testid="confirm-proof-panel">
      <h4 className="text-sm font-semibold text-gray-900">Confirm official proof</h4>
      <form onSubmit={handleConfirm} className="space-y-3" noValidate>
        <div>
          <label className="block text-xs text-gray-500 mb-1" htmlFor="proof-url-select">
            Suggested official URL *
          </label>
          <select
            id="proof-url-select"
            value={chosenUrl}
            onChange={(e) => setChosenUrl(e.target.value)}
            className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
            data-testid="proof-url-select"
          >
            <option value="">— choose a URL —</option>
            {suggestedUrls.map((u) => (
              <option key={u.url} value={u.url}>
                {u.url} ({u.method}, conf {u.confidence?.toFixed?.(2)})
              </option>
            ))}
          </select>
        </div>

        {proofError && (
          <div
            className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
            data-testid="proof-error"
          >
            {proofError}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            className="btn btn-primary text-sm"
            disabled={busy}
            data-testid="proof-submit-btn"
          >
            {busy ? "Confirming…" : "Confirm proof"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ─── Override-conflict panel ──────────────────────────────────────────────────

function OverrideConflictPanel({ report, onSuccess }) {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === "super_admin";
  const hasOverridePerm = isSuperAdmin || (
    (user?.role === "admin") &&
    Array.isArray(user?.permissions) &&
    user.permissions.includes("recruitments.manage")
  );

  const [activeConflictId, setActiveConflictId] = useState(null);
  const [chosenValue, setChosenValue] = useState("");
  const [overrideScope, setOverrideScope] = useState("field");
  const [overrideReason, setOverrideReason] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [overrideError, setOverrideError] = useState(null);
  const { run, busy } = useApiAction();

  const openConflicts = (report.conflicts || []).filter(
    (c) => c.status !== "resolved_by_admin" && c.status !== "resolved",
  );

  if (!hasOverridePerm || openConflicts.length === 0) return null;

  const activeConflict = openConflicts.find((c) => c.conflict_id === activeConflictId);

  function openConflict(c) {
    setActiveConflictId(c.conflict_id);
    setChosenValue("");
    setOverrideScope("field");
    setOverrideReason("");
    setEvidenceUrl("");
    setOverrideError(null);
  }

  async function handleOverride(e) {
    e.preventDefault();
    setOverrideError(null);
    if (!chosenValue.trim()) {
      setOverrideError("Chosen value is required.");
      return;
    }
    if (!overrideReason.trim()) {
      setOverrideError("Reason is required.");
      return;
    }
    const res = await run({
      action: () => api.post(`/api/admin/verification-reports/${report.id}/override-conflict`, {
        conflict_id: activeConflictId,
        chosen_value: chosenValue.trim(),
        override_scope: overrideScope,
        reason: overrideReason.trim(),
        evidence_url: evidenceUrl.trim() || null,
      }),
      successMessage: "Conflict overridden.",
      errorMessage: "Failed to override conflict.",
      onSuccess: () => { setActiveConflictId(null); onSuccess(); },
    });
    if (!res.ok && !res.cancelled) {
      setOverrideError(res.error?.message || "Override failed.");
    }
  }

  return (
    <div className="mt-6 rounded-2xl border border-border bg-white/60 px-5 py-4 space-y-3" data-testid="override-conflict-panel">
      <h4 className="text-sm font-semibold text-gray-900">Override conflict</h4>

      {!activeConflictId ? (
        <ul className="space-y-1">
          {openConflicts.map((c) => (
            <li key={c.conflict_id} className="flex items-center justify-between text-xs">
              <span className="font-mono text-gray-900">{c.field_path}</span>
              <button
                type="button"
                className="btn btn-ghost text-xs"
                onClick={() => openConflict(c)}
                data-testid={`override-open-${c.conflict_id}`}
              >
                Override
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <form onSubmit={handleOverride} className="space-y-3" noValidate data-testid="override-form">
          <p className="text-xs text-gray-500">
            Conflict: <span className="font-mono">{activeConflict?.field_path}</span>
          </p>

          <div>
            <label className="block text-xs text-gray-500 mb-1" htmlFor="override-chosen-value">
              Chosen value *
            </label>
            <input
              id="override-chosen-value"
              type="text"
              value={chosenValue}
              onChange={(e) => setChosenValue(e.target.value)}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              data-testid="override-chosen-value"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1" htmlFor="override-scope-select">
              Scope *
            </label>
            <select
              id="override-scope-select"
              value={overrideScope}
              onChange={(e) => setOverrideScope(e.target.value)}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              data-testid="override-scope-select"
            >
              <option value="field">field</option>
              <option value="recruitment">recruitment</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1" htmlFor="override-reason">
              Reason *
            </label>
            <textarea
              id="override-reason"
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              rows={2}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              data-testid="override-reason"
              required
            />
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1" htmlFor="override-evidence-url">
              Evidence URL (optional)
            </label>
            <input
              id="override-evidence-url"
              type="url"
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              data-testid="override-evidence-url"
            />
          </div>

          {overrideError && (
            <div
              className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
              data-testid="override-error"
            >
              {overrideError}
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="submit"
              className="btn btn-primary text-sm"
              disabled={busy}
              data-testid="override-submit-btn"
            >
              {busy ? "Saving…" : "Save override"}
            </button>
            <button
              type="button"
              className="btn btn-ghost text-sm"
              onClick={() => setActiveConflictId(null)}
              data-testid="override-cancel-btn"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

// ─── Promote / Reject panel ───────────────────────────────────────────────────

function PromoteRejectPanel({ report, onSuccess }) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin" || user?.role === "super_admin";

  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [rejectError, setRejectError] = useState(null);
  const [promoteError, setPromoteError] = useState(null);
  const { run: runPromote, busy: promoteBusy } = useApiAction();
  const { run: runReject, busy: rejectBusy } = useApiAction();

  if (!isAdmin) return null;

  const alreadyPromoted = !!report.recruitment_id;

  async function handlePromote() {
    setPromoteError(null);
    const res = await runPromote({
      action: () => api.post(`/api/admin/verification-reports/${report.id}/promote`, {}),
      successMessage: "Report promoted to recruitment.",
      errorMessage: "Failed to promote report.",
      onSuccess,
    });
    if (!res.ok && !res.cancelled) {
      setPromoteError(res.error?.message || "Promotion failed.");
    }
  }

  async function handleReject(e) {
    e.preventDefault();
    setRejectError(null);
    const trimmed = rejectReason.trim();
    if (trimmed.length < 8 || trimmed.length > 500) {
      setRejectError("Reason must be 8–500 characters.");
      return;
    }
    const res = await runReject({
      action: () => api.post(`/api/admin/verification-reports/${report.id}/reject`, { reason: trimmed }),
      successMessage: "Report rejected.",
      errorMessage: "Failed to reject report.",
      onSuccess,
    });
    if (!res.ok && !res.cancelled) {
      setRejectError(res.error?.message || "Rejection failed.");
    }
  }

  return (
    <div className="mt-6 rounded-2xl border border-border bg-white/60 px-5 py-4 space-y-4" data-testid="promote-reject-panel">
      <h4 className="text-sm font-semibold text-gray-900">Promote / Reject</h4>

      {/* Promote */}
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="btn btn-primary text-sm"
            onClick={handlePromote}
            disabled={promoteBusy || alreadyPromoted}
            data-testid="promote-btn"
            aria-disabled={alreadyPromoted}
          >
            {promoteBusy ? "Promoting…" : alreadyPromoted ? "Promoted" : "Promote"}
          </button>
          {alreadyPromoted && (
            <span className="text-xs text-muted-foreground" data-testid="already-promoted-note">
              Already linked to recruitment {report.recruitment_id}
            </span>
          )}
        </div>
        {promoteError && (
          <div
            className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
            data-testid="promote-error"
          >
            {promoteError}
          </div>
        )}
      </div>

      {/* Reject */}
      {!rejectOpen ? (
        <button
          type="button"
          className="btn btn-ghost text-sm text-destructive"
          onClick={() => { setRejectOpen(true); setRejectError(null); }}
          data-testid="reject-open-btn"
        >
          Reject…
        </button>
      ) : (
        <form onSubmit={handleReject} className="space-y-3" noValidate data-testid="reject-form">
          <div>
            <label className="block text-xs text-gray-500 mb-1" htmlFor="reject-reason">
              Reason * (8–500 chars)
            </label>
            <textarea
              id="reject-reason"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              data-testid="reject-reason-input"
              required
            />
          </div>

          {rejectError && (
            <div
              className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
              data-testid="reject-error"
            >
              {rejectError}
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="submit"
              className="btn btn-destructive text-sm"
              disabled={rejectBusy}
              data-testid="reject-submit-btn"
            >
              {rejectBusy ? "Rejecting…" : "Confirm reject"}
            </button>
            <button
              type="button"
              className="btn btn-ghost text-sm"
              onClick={() => { setRejectOpen(false); setRejectReason(""); setRejectError(null); }}
              data-testid="reject-cancel-btn"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

// ─── Detail drawer ─────────────────────────────────────────────────────────────

function VerificationReportDetail({ reportId, onClose, onActionApplied }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  useFocusTrap({ active: !!reportId, containerRef: panelRef, onEscape: onClose, initialFocusRef: closeRef });

  useEffect(() => {
    if (!reportId) return;
    let active = true;
    setLoading(true);
    setFetchError(null);
    api.get(`/api/admin/verification-reports/${reportId}`)
      .then((d) => { if (active) setReport(d); })
      .catch((e) => { if (active) setFetchError(e?.message || "Failed to load report"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [reportId]);

  if (!reportId) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" data-testid="report-detail-drawer">
      <div className="absolute inset-0" onClick={onClose} />
      <aside
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-detail-title"
        className="relative h-full w-full max-w-2xl overflow-auto border-l border-border bg-[#FBF6EF] p-5 shadow-xl"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="report-detail-title" className="font-heading text-xl">Verification Report</h2>
          <button
            ref={closeRef}
            className="btn btn-ghost h-9 w-9 p-0"
            onClick={onClose}
            aria-label="Close"
            data-testid="report-detail-close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading && <LoadingSkeleton className="mt-4" />}
        {fetchError && <p className="mt-4 text-sm text-destructive">{fetchError}</p>}

        {!loading && !fetchError && report && (
          <>
            <div className="mt-4" data-testid="report-detail-card">
              <VerificationReportCard report={report} />
            </div>
            <PromoteRejectPanel report={report} onSuccess={onActionApplied} />
            <RunResolverPanel report={report} onSuccess={onActionApplied} />
            <ConfirmProofPanel report={report} onSuccess={onActionApplied} />
            <OverrideConflictPanel report={report} onSuccess={onActionApplied} />
            <div className="mt-6 rounded-2xl border border-border bg-white/60 px-5 py-4">
              <ApplyRegistryActionPanel
                reportId={reportId}
                onSuccess={onActionApplied}
              />
            </div>
          </>
        )}
      </aside>
    </div>
  );
}

// ─── List table ───────────────────────────────────────────────────────────────

// ─── Multi-select table ───────────────────────────────────────────────────────

function VerificationReportsTable({ items, onOpen, selectedIds, onToggle, onToggleAll }) {
  const allSelected = items.length > 0 && items.every((r) => selectedIds.includes(r.id));
  const someSelected = items.some((r) => selectedIds.includes(r.id));

  return (
    <div className="soft-card grain relative overflow-hidden rounded-[18px]">
      <table className="tbl" data-testid="vr-table">
        <thead>
          <tr>
            <th>
              <input
                type="checkbox"
                aria-label="Select all"
                checked={allSelected}
                ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected; }}
                onChange={() => onToggleAll(items.map((r) => r.id))}
                data-testid="vr-select-all"
              />
            </th>
            <th>ID</th>
            <th>Exam family</th>
            <th>Lifecycle</th>
            <th>Tier</th>
            <th>Recommended action</th>
            <th>Created</th>
            <th className="right">Open</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.id} data-testid={`vr-row-${r.id}`}>
              <td>
                <input
                  type="checkbox"
                  aria-label={`Select ${r.id}`}
                  checked={selectedIds.includes(r.id)}
                  onChange={() => onToggle(r.id)}
                  data-testid={`vr-check-${r.id}`}
                />
              </td>
              <td className="num-mono text-xs">{r.id}</td>
              <td>{r.exam_family_key || "—"}</td>
              <td><StatusBadge status={r.lifecycle_status} /></td>
              <td><StatusBadge status={r.criticality_tier} /></td>
              <td className="text-xs">{r.recommended_action}</td>
              <td className="num-mono text-xs">{r.created_at ? r.created_at.slice(0, 10) : "—"}</td>
              <td className="right">
                <button
                  type="button"
                  className="text-[11px] px-2.5 py-1 rounded-full border border-[#E7DECB] font-semibold text-clay-700"
                  onClick={() => onOpen(r)}
                  data-testid={`vr-open-${r.id}`}
                >
                  Open
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Bulk toolbar ─────────────────────────────────────────────────────────────

function BulkToolbar({ selectedIds, onClear, onDryRun, dryRunResult, onApply, busy, bulkReason, onReasonChange }) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin" || user?.role === "super_admin";
  const [action, setAction] = useState("bulk_promote");

  if (!isAdmin || selectedIds.length === 0) return null;

  const isBulkReject = action === "bulk_reject";
  const reasonTrimLen = bulkReason.trim().length;
  const reasonValid = reasonTrimLen >= 8 && reasonTrimLen <= 500;
  const previewDisabled = busy || (isBulkReject && !reasonValid);

  return (
    <div className="rounded-2xl border border-border bg-white/80 px-4 py-3 flex flex-wrap items-center gap-3" data-testid="bulk-toolbar">
      <span className="text-sm font-medium text-gray-900">
        {selectedIds.length} selected
      </span>

      <select
        value={action}
        onChange={(e) => setAction(e.target.value)}
        className="rounded-xl border border-border bg-white/80 px-3 py-1.5 text-sm"
        data-testid="bulk-action-select"
      >
        <option value="bulk_promote">Bulk promote</option>
        <option value="bulk_reject">Bulk reject</option>
      </select>

      {isBulkReject && (
        <div className="w-full">
          <label className="block text-xs text-gray-500 mb-1" htmlFor="bulk-reason-input">
            Rejection reason * (8–500 chars)
          </label>
          <textarea
            id="bulk-reason-input"
            value={bulkReason}
            onChange={(e) => onReasonChange(e.target.value)}
            rows={2}
            className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
            data-testid="bulk-reason-input"
          />
        </div>
      )}

      <button
        type="button"
        className="btn btn-ghost text-sm"
        onClick={() => onDryRun(selectedIds, action)}
        disabled={previewDisabled}
        data-testid="bulk-dry-run-btn"
      >
        {busy ? "Checking…" : "Preview"}
      </button>

      <button
        type="button"
        className="btn btn-ghost text-xs text-muted-foreground"
        onClick={onClear}
        data-testid="bulk-clear-btn"
      >
        Clear
      </button>

      {dryRunResult && (
        <div className="w-full mt-2" data-testid="bulk-preview-wrapper">
          <BulkActionPreview
            dryRun={dryRunResult}
            onApply={() => onApply(selectedIds, action)}
            disabled={busy || (isBulkReject && !reasonValid)}
          />
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

// Separate component so useApiCollection only mounts — and fetches — when the
// user actually has the required permission. The parent renders the denial UI
// before this component ever mounts, preventing the GET from leaking report
// data to admins who lack exam_intelligence.cms.
function VerificationReportsContent() {
  const [selectedId, setSelectedId] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [dryRunResult, setDryRunResult] = useState(null);
  const [bulkError, setBulkError] = useState(null);
  const [bulkReason, setBulkReason] = useState("");
  const { items, status, refresh } = useApiCollection(
    "/api/admin/verification-reports",
    [],
  );
  const { run: runBulk, busy: bulkBusy } = useApiAction();

  function toggleOne(id) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
    setDryRunResult(null);
  }

  function toggleAll(ids) {
    const allSelected = ids.every((id) => selectedIds.includes(id));
    setSelectedIds(allSelected ? [] : ids);
    setDryRunResult(null);
  }

  function clearSelection() {
    setSelectedIds([]);
    setDryRunResult(null);
    setBulkError(null);
    setBulkReason("");
  }

  async function handleDryRun(ids, action) {
    setBulkError(null);
    setDryRunResult(null);
    const res = await runBulk({
      action: () => api.post("/api/admin/verification-reports/bulk-dry-run", {
        selected_ids: ids,
        action,
        dry_run: true,
        ...(action === "bulk_reject" && { reason: bulkReason }),
      }),
      errorMessage: "Bulk dry-run failed.",
    });
    if (res.ok) {
      setDryRunResult(res.data);
    } else if (!res.cancelled) {
      setBulkError(res.error?.message || "Bulk dry-run failed.");
    }
  }

  async function handleApply(ids, action) {
    setBulkError(null);
    const res = await runBulk({
      action: () => api.post("/api/admin/verification-reports/bulk-apply", {
        selected_ids: ids,
        action,
        dry_run: false,
        ...(action === "bulk_reject" && { reason: bulkReason }),
      }),
      successMessage: "Bulk action applied.",
      errorMessage: "Bulk action failed.",
      onSuccess: () => { clearSelection(); refresh(); },
    });
    if (!res.ok && !res.cancelled) {
      setBulkError(res.error?.message || "Bulk action failed.");
    }
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl">Verification Reports</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Active (non-superseded) reports — newest first.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-ghost text-sm"
          onClick={refresh}
          data-testid="vr-refresh"
        >
          Refresh
        </button>
      </div>

      <BulkToolbar
        selectedIds={selectedIds}
        onClear={clearSelection}
        onDryRun={handleDryRun}
        dryRunResult={dryRunResult}
        onApply={handleApply}
        busy={bulkBusy}
        bulkReason={bulkReason}
        onReasonChange={setBulkReason}
      />

      {bulkError && (
        <div
          className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
          data-testid="bulk-error"
        >
          {bulkError}
        </div>
      )}

      {status === "loading" && <LoadingSkeleton />}
      {status === "error" && <ErrorState message="Failed to load verification reports." onRetry={refresh} />}
      {status === "empty" && <EmptyState message="No verification reports in the attention queue." />}
      {status === "live" && (
        <VerificationReportsTable
          items={items}
          onOpen={(r) => setSelectedId(r.id)}
          selectedIds={selectedIds}
          onToggle={toggleOne}
          onToggleAll={toggleAll}
        />
      )}

      <VerificationReportDetail
        reportId={selectedId}
        onClose={() => setSelectedId(null)}
        onActionApplied={() => { setSelectedId(null); refresh(); }}
      />
    </div>
  );
}

export default function AdminVerificationReports() {
  const { user } = useAuth();

  const hasPerm =
    user?.role === "super_admin" ||
    user?.role === "admin";

  if (!hasPerm) {
    return (
      <div className="p-6" data-testid="vr-permission-denied">
        <p className="text-sm text-muted-foreground">
          Admin or super_admin role is required to access this console.
        </p>
      </div>
    );
  }

  return <VerificationReportsContent />;
}
