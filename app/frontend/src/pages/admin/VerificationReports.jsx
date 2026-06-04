import React, { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { api } from "../../lib/api";
import useApiCollection from "../../lib/hooks/useApiCollection";
import useApiAction from "../../lib/hooks/useApiAction";
import { useAuth } from "../../lib/authContext";
import { useFocusTrap } from "../../shared/a11y/useFocusTrap";
import { EmptyState, ErrorState, LoadingSkeleton, StatusBadge } from "../../shared/ui/core";
import VerificationReportCard from "../../features/admin/workflow/VerificationReportCard";

const PERM = "exam_intelligence.cms";

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

function VerificationReportsTable({ items, onOpen }) {
  return (
    <div className="soft-card grain relative overflow-hidden rounded-[18px]">
      <table className="tbl" data-testid="vr-table">
        <thead>
          <tr>
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

// ─── Page ─────────────────────────────────────────────────────────────────────

// Separate component so useApiCollection only mounts — and fetches — when the
// user actually has the required permission. The parent renders the denial UI
// before this component ever mounts, preventing the GET from leaking report
// data to admins who lack exam_intelligence.cms.
function VerificationReportsContent() {
  const [selectedId, setSelectedId] = useState(null);
  const { items, status, refresh } = useApiCollection(
    "/api/admin/verification-reports",
    [],
  );

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

      {status === "loading" && <LoadingSkeleton />}
      {status === "error" && <ErrorState message="Failed to load verification reports." onRetry={refresh} />}
      {status === "empty" && <EmptyState message="No verification reports in the attention queue." />}
      {status === "live" && (
        <VerificationReportsTable items={items} onOpen={(r) => setSelectedId(r.id)} />
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
    (Array.isArray(user?.permissions) && user.permissions.includes(PERM));

  if (!hasPerm) {
    return (
      <div className="p-6" data-testid="vr-permission-denied">
        <p className="text-sm text-muted-foreground">
          You need the <code>{PERM}</code> permission to access this console.
        </p>
      </div>
    );
  }

  return <VerificationReportsContent />;
}
