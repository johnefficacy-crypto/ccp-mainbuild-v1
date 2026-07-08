import React, { useState } from "react";
import { Newspaper } from "lucide-react";
import { StatusBadge, SourceTrustBadge, EmptyState } from "../../../shared/ui/core";

// exam_policy_updates review surface.
//
// Two axes: reviewer_status (operator workflow) and source_type (trust
// origin). Only verified official rows ever reach the Study OS planner;
// non-official rows are discovery-only. The affects_* flags are set at row
// creation and gated by a DB check constraint — this surface only moves
// reviewer_status.
const REVIEW_ACTIONS = {
  pending: [
    { to: "verified", label: "Verify", tone: "primary" },
    { to: "rejected", label: "Reject", tone: "danger" },
    { to: "needs_correction", label: "Needs correction" },
  ],
  needs_correction: [
    { to: "verified", label: "Verify", tone: "primary" },
    { to: "rejected", label: "Reject", tone: "danger" },
    { to: "pending", label: "Reset to pending" },
  ],
  verified: [
    { to: "rejected", label: "Reject", tone: "danger" },
    { to: "needs_correction", label: "Needs correction" },
  ],
  rejected: [
    { to: "pending", label: "Reset to pending" },
    { to: "needs_correction", label: "Needs correction" },
  ],
};

// Named export so other affects_*-rendering surfaces (e.g. UpdatesPanel) can
// reuse the same flag set + correction-request affordance rather than
// re-deriving it (F5).
export const AFFECT_KEYS = [
  ["affects_plan", "plan"],
  ["affects_deadline", "deadline"],
  ["affects_eligibility", "eligibility"],
  ["affects_documents", "documents"],
  ["affects_syllabus", "syllabus"],
  ["affects_vacancy", "vacancy"],
];

function actionClasses(tone) {
  if (tone === "primary") {
    return "border-sage-300 bg-sage-50 text-sage-800 hover:bg-sage-100";
  }
  if (tone === "danger") {
    return "border-dusk-200 bg-dusk-50 text-dusk-800 hover:bg-dusk-100";
  }
  return "border-clay-200 text-clay-700 hover:bg-clay-50";
}

export function AffectsCell({ row }) {
  const active = AFFECT_KEYS.filter(([k]) => row[k]);
  if (!active.length) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {active.map(([, label]) => (
        <span
          key={label}
          className="pill pill-amber text-[10px]"
          title="Set at row creation; contact admin to correct"
          aria-label={`${label} — Set at row creation; contact admin to correct`}
        >
          <span>{label}</span>
        </span>
      ))}
    </div>
  );
}

// F5: correction-request affordance. The affects_* flags stay immutable here
// — this only captures which flag(s) an operator disputes plus a reason, and
// hands the pair to the parent-owned mutation (onRequestCorrection), which
// wires it through useApiAction to PATCH .../policy-updates/{id}/review with
// reviewer_status=needs_correction + disputed_flags + reviewer_notes. That
// endpoint records an admin_audit_logs entry and never edits the flags.
export function CorrectionRequestControl({ row, onRequestCorrection, busy }) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(() => new Set());
  const [reason, setReason] = useState("");

  function toggleFlag(key) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function reset() {
    setOpen(false);
    setSelected(new Set());
    setReason("");
  }

  function submit() {
    const disputedFlags = Array.from(selected);
    if (!disputedFlags.length || reason.trim().length < 8 || busy) return;
    onRequestCorrection(row, { disputedFlags, reason: reason.trim() });
    reset();
  }

  if (!open) {
    return (
      <button
        type="button"
        className="block mt-1 text-[11px] underline text-clay-600 hover:text-clay-800"
        onClick={() => setOpen(true)}
        data-testid={`policy-correction-open-${row.id}`}
      >
        Request correction
      </button>
    );
  }

  const canSubmit = selected.size > 0 && reason.trim().length >= 8 && !busy;

  return (
    <div
      className="mt-1.5 border border-clay-200 rounded-md p-2 bg-white space-y-1.5 w-56"
      data-testid={`policy-correction-form-${row.id}`}
    >
      <div className="text-[10px] font-medium text-clay-700">Which flag(s) are wrong?</div>
      <div className="flex flex-wrap gap-x-2 gap-y-1">
        {AFFECT_KEYS.map(([key, label]) => (
          <label key={key} className="flex items-center gap-1 text-[11px]">
            <input
              type="checkbox"
              checked={selected.has(key)}
              onChange={() => toggleFlag(key)}
              data-testid={`policy-correction-flag-${row.id}-${key}`}
            />
            {label}
          </label>
        ))}
      </div>
      <textarea
        className="w-full text-[11px] border border-clay-200 rounded px-1.5 py-1"
        rows={2}
        placeholder="Why is this wrong? (min 8 characters)"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        data-testid={`policy-correction-reason-${row.id}`}
      />
      <div className="flex gap-1.5">
        <button
          type="button"
          disabled={!canSubmit}
          onClick={submit}
          className="text-[11px] rounded-full border px-2 py-0.5 border-sage-300 bg-sage-50 text-sage-800 disabled:opacity-50"
          data-testid={`policy-correction-submit-${row.id}`}
        >
          {busy ? "…" : "Submit request"}
        </button>
        <button
          type="button"
          onClick={reset}
          className="text-[11px] rounded-full border px-2 py-0.5 border-clay-200 text-clay-700"
          data-testid={`policy-correction-cancel-${row.id}`}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function PolicyUpdatesTable({ items, onReview, busyRowId, onRequestCorrection, correctionBusyRowId }) {
  const rows = Array.isArray(items) ? items : [];
  const interactive = typeof onReview === "function";
  const correctable = typeof onRequestCorrection === "function";

  if (!rows.length) {
    return (
      <EmptyState
        icon={Newspaper}
        title="No policy updates yet"
        description="Official notification / cycle / syllabus / vacancy changes and unverified aggregator discoveries appear here for review."
      />
    );
  }

  return (
    <div className="space-y-3">
      {/* F5: The affects_* flags (plan, deadline, eligibility, documents, syllabus, vacancy) are
           set at row creation and enforced by a DB check constraint. They cannot be changed via
           this surface. "Request correction" on a row records an auditable dispute (reviewer_status
           -> needs_correction + reason) without editing the flags — a cms-permission operator
           resolves it in Advanced Repair. */}
      <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-1.5" data-testid="affects-immutability-notice">
        The <strong>Affects</strong> flags (plan, deadline, eligibility, documents, syllabus, vacancy) are set at row creation and are immutable — this surface only moves reviewer status.
        {correctable
          ? " If a flag is incorrect, use “Request correction” below to record an auditable dispute; the flag itself is not changed here."
          : " To correct an incorrect flag, contact an admin."}
      </p>
    <div className="soft-card grain relative overflow-hidden rounded-[18px]" data-testid="policy-updates-table">
      <table className="tbl">
        <thead>
          <tr>
            <th>Exam</th>
            <th>Type</th>
            <th>Title</th>
            <th>Source</th>
            <th>Affects</th>
            <th>Status</th>
            {interactive ? <th>Actions</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((u) => {
            const actions = REVIEW_ACTIONS[u.status] || [];
            const busy = busyRowId === u.id;
            const isOfficial = u.source_type === "official";
            return (
              <tr key={u.id} className="border-t border-clay-100 align-top">
                <td className="px-4 py-2 text-xs">{u.exam || u.exam_slug || "—"}</td>
                <td className="px-4 py-2 text-xs text-muted-foreground">
                  {(u.update_type || "—").replace(/_/g, " ")}
                </td>
                <td className="px-4 py-2">
                  <div className="font-medium">{u.title || "—"}</div>
                  {u.summary ? (
                    <div className="text-xs text-muted-foreground mt-0.5 max-w-md">
                      {u.summary}
                    </div>
                  ) : null}
                </td>
                <td className="px-4 py-2">
                  <SourceTrustBadge
                    kind={isOfficial ? "official" : u.source_type || "needs_verification"}
                    compact
                  />
                </td>
                <td className="px-4 py-2">
                  <AffectsCell row={u} />
                  {correctable && (
                    <CorrectionRequestControl
                      row={u}
                      onRequestCorrection={onRequestCorrection}
                      busy={correctionBusyRowId === u.id}
                    />
                  )}
                </td>
                <td className="px-4 py-2">
                  <StatusBadge status={u.status} />
                </td>
                {interactive ? (
                  <td className="px-4 py-2">
                    <div className="flex flex-wrap gap-1.5">
                      {actions.length ? (
                        actions.map((a) => (
                          <button
                            key={a.to}
                            type="button"
                            disabled={busy}
                            onClick={() => onReview(u, a.to)}
                            className={`text-[11px] rounded-full border px-2 py-1 disabled:opacity-50 ${actionClasses(
                              a.tone,
                            )}`}
                            data-testid={`policy-action-${u.id}-${a.to}`}
                          >
                            {busy ? "…" : a.label}
                          </button>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </div>
                  </td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
    </div>
  );
}
