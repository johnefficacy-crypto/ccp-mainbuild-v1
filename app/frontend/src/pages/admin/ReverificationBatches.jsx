import React from "react";
import { RefreshCcw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/authContext";
import useApiCollection from "../../lib/hooks/useApiCollection";
import useApiAction from "../../lib/hooks/useApiAction";
import ReverificationBatchAlert from "../../features/admin/workflow/ReverificationBatchAlert";

// Backend gate is require_admin-effective; mirror with role only.

export default function ReverificationBatches() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { items, status, refresh } = useApiCollection(
    "/api/admin/reverification-batches",
  );
  const { run, busy } = useApiAction();

  function handleOpenAffected(batch) {
    const params = new URLSearchParams({
      source_id: batch.source_id,
      staleness_status: "pending_reverification_batch",
    });
    navigate(`/admin/verification-reports?${params.toString()}`);
  }

  const canAcknowledge =
    user?.role === "super_admin" ||
    user?.role === "admin";

  async function handleAcknowledge(batchId) {
    await run({
      action: () =>
        api.post(
          `/api/admin/verification-reports/acknowledge-batch/${batchId}`,
          {},
        ),
      successMessage: "Batch acknowledged — reports released to queue",
      errorMessage: "Failed to acknowledge batch",
      onSuccess: () => refresh(),
    });
  }

  return (
    <div className="admin-page">
      <header className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Reverification Batches</h1>
          <p className="admin-page-sub">
            Unacknowledged mass-change batches awaiting release into the
            verification queue.
          </p>
        </div>
        <button
          type="button"
          className="btn ghost icon-btn"
          onClick={refresh}
          title="Refresh"
          aria-label="Refresh batches"
        >
          <RefreshCcw size={16} />
        </button>
      </header>

      {status === "loading" && (
        <div className="stack" aria-busy="true" data-testid="batches-loading">
          <div className="skel" style={{ height: 160 }} />
          <div className="skel" style={{ height: 160 }} />
        </div>
      )}

      {status === "empty" && (
        <div className="empty-state" data-testid="batches-empty">
          <p>No unacknowledged reverification batches. All clear.</p>
          {!canAcknowledge && (
            <p style={{ marginTop: 8, opacity: 0.7 }}>
              Admin or super_admin role is required to acknowledge batches.
            </p>
          )}
        </div>
      )}

      {status === "error" && (
        <div className="error-state" data-testid="batches-error">
          <p>Failed to load batches.</p>
          <button type="button" className="btn" onClick={refresh}>
            Retry
          </button>
        </div>
      )}

      {status === "live" && (
        <ul
          className="batch-list"
          aria-label="Reverification batches"
          data-testid="batches-list"
        >
          {items.map((batch) => (
            <li key={batch.id}>
              <ReverificationBatchAlert
                batch={batch}
                onAcknowledge={canAcknowledge ? handleAcknowledge : null}
                onOpenAffected={batch.source_id ? handleOpenAffected : null}
                onSnooze={null}
                disabled={busy || !canAcknowledge}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
