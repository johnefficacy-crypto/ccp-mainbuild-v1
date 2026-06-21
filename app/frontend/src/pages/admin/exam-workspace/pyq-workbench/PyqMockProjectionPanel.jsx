/**
 * PyqMockProjectionPanel — embedded "Mock projection" section inside the
 * PYQ Workbench (NOT a new route or sidebar entry).
 *
 * Shows the projection status for the selected paper and lets a publisher
 * trigger a sync.  Preview mode shows what would change without writing.
 *
 * Permission model matches the backend:
 *   GET  preview/status — mock_questions:author
 *   POST sync           — mock_questions:publish
 */
import React, { useCallback, useEffect, useState } from "react";
import { api } from "../../../../lib/api";
import useApiAction from "../../../../lib/hooks/useApiAction";

const _BASE = (paperId) => `/api/admin/mocks/pyq-papers/${paperId}/projection`;

function StatusPill({ status }) {
  const colors = {
    active:   "bg-emerald-50 text-emerald-700 border border-emerald-200",
    stale:    "bg-amber-50 text-amber-700 border border-amber-200",
    blocked:  "bg-rose-50 text-rose-700 border border-rose-200",
    archived: "bg-gray-50 text-gray-500 border border-gray-200",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[status] ?? "bg-gray-50 text-gray-500"}`}
    >
      {status}
    </span>
  );
}

function OutcomeBadge({ outcome }) {
  const colors = {
    created:    "text-emerald-700",
    updated:    "text-sky-700",
    unchanged:  "text-gray-500",
    ineligible: "text-amber-600",
    error:      "text-rose-700",
  };
  return (
    <span className={`text-xs font-medium ${colors[outcome] ?? "text-gray-500"}`}>
      {outcome}
    </span>
  );
}

export default function PyqMockProjectionPanel({ paperId }) {
  const [status, setStatus]     = useState(null);
  const [preview, setPreview]   = useState(null);
  const [syncResult, setSyncResult] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [statusError, setStatusError] = useState(null);
  const { run: runSync, busy: syncing } = useApiAction();

  const fetchStatus = useCallback(async () => {
    if (!paperId) return;
    setLoadingStatus(true);
    setStatusError(null);
    try {
      const data = await api.get(_BASE(paperId) + "/status");
      setStatus(data);
    } catch (e) {
      setStatusError(e?.message || "Failed to load projection status");
    } finally {
      setLoadingStatus(false);
    }
  }, [paperId]);

  const fetchPreview = useCallback(async () => {
    if (!paperId) return;
    setLoadingPreview(true);
    setPreview(null);
    try {
      const data = await api.get(_BASE(paperId) + "/preview");
      setPreview(data);
    } catch (e) {
      // Non-fatal — preview is optional.
    } finally {
      setLoadingPreview(false);
    }
  }, [paperId]);

  useEffect(() => {
    if (paperId) {
      fetchStatus();
      setPreview(null);
      setSyncResult(null);
    }
  }, [paperId, fetchStatus]);

  const handleSync = () => {
    runSync({
      action: async () => {
        const data = await api.post(_BASE(paperId) + "/sync", {});
        return data;
      },
      onSuccess: (data) => {
        setSyncResult(data);
        fetchStatus();
      },
      successMessage: "Projection sync complete.",
      errorMessage: "Sync failed. Check permissions or paper status.",
    });
  };

  if (!paperId) return null;

  return (
    <section
      className="border-t border-gray-200 bg-gray-50 px-4 py-3"
      data-testid="pyq-mock-projection-panel"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">Mock projection</span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={fetchPreview}
            disabled={loadingPreview}
            className="text-xs px-2.5 py-1 rounded border border-gray-300 text-gray-600 hover:bg-white disabled:opacity-50"
            data-testid="projection-preview-btn"
          >
            {loadingPreview ? "Loading…" : "Preview"}
          </button>
          <button
            type="button"
            onClick={handleSync}
            disabled={syncing}
            className="text-xs px-2.5 py-1 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
            data-testid="projection-sync-btn"
          >
            {syncing ? "Syncing…" : "Sync to mock bank"}
          </button>
        </div>
      </div>

      {/* Status summary */}
      {loadingStatus && (
        <p className="text-xs text-gray-400">Loading status…</p>
      )}
      {statusError && (
        <p className="text-xs text-rose-600" data-testid="projection-status-error">
          {statusError}
        </p>
      )}
      {status && !loadingStatus && (
        <div className="text-xs text-gray-600 space-y-1">
          <div className="flex flex-wrap gap-3">
            <span>
              Total questions: <strong>{status.total_questions}</strong>
            </span>
            <span>
              Unprojected: <strong>{status.unprojected_count}</strong>
            </span>
            {Object.entries(status.projection_counts ?? {}).map(([k, v]) =>
              v > 0 ? (
                <span key={k} className="flex items-center gap-1">
                  <StatusPill status={k} />
                  <strong>{v}</strong>
                </span>
              ) : null
            )}
          </div>
          {status.stale_projections?.length > 0 && (
            <p className="text-amber-600">
              {status.stale_projections.length} stale — sync recommended.
            </p>
          )}
        </div>
      )}

      {/* Preview results */}
      {preview && (
        <div className="mt-3 border border-gray-200 rounded bg-white" data-testid="projection-preview-results">
          <div className="px-3 py-2 border-b border-gray-100 flex gap-4 text-xs text-gray-600">
            <span>Eligible: <strong>{preview.eligible_count}</strong></span>
            <span>Ineligible: <strong>{preview.ineligible_count}</strong></span>
            <span>Would create: <strong>{preview.would_create_count}</strong></span>
            <span>Would update: <strong>{preview.would_update_count}</strong></span>
          </div>
          <div className="max-h-40 overflow-y-auto divide-y divide-gray-50">
            {(preview.questions ?? []).map((q) => (
              <div
                key={q.question_id}
                className="px-3 py-1.5 flex items-center justify-between gap-2 text-xs"
                data-testid={`preview-row-${q.question_id}`}
              >
                <span className="font-mono text-gray-400 truncate max-w-[12ch]">
                  {q.question_id.slice(0, 8)}…
                </span>
                <span className={`${q.eligible ? "text-gray-700" : "text-amber-600"}`}>
                  {q.eligible ? (q.would_update ? "update" : "create/no-change") : q.reason}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sync results */}
      {syncResult && (
        <div className="mt-3 border border-gray-200 rounded bg-white" data-testid="projection-sync-results">
          <div className="px-3 py-2 border-b border-gray-100 text-xs text-gray-600">
            <span className="font-medium">Sync results</span>
            {" — "}attempted: {syncResult.attempted}
            {Object.entries(syncResult.outcomes ?? {}).map(([k, v]) =>
              v > 0 ? (
                <span key={k} className="ml-2">
                  <OutcomeBadge outcome={k} /> {v}
                </span>
              ) : null
            )}
          </div>
          <div className="max-h-40 overflow-y-auto divide-y divide-gray-50">
            {(syncResult.questions ?? []).map((q) => (
              <div
                key={q.question_id}
                className="px-3 py-1.5 flex items-center justify-between gap-2 text-xs"
                data-testid={`sync-row-${q.question_id}`}
              >
                <span className="font-mono text-gray-400 truncate max-w-[12ch]">
                  {q.question_id.slice(0, 8)}…
                </span>
                <OutcomeBadge outcome={q.outcome} />
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
