import React, { useEffect, useState } from "react";
import { SYNC } from "./useAnswerSync";

/**
 * Compact, top-right sync state for the current question. "Saved" shows a check
 * for ~2s then fades; failures surface a red banner with Retry / View details.
 */
export default function AnswerSyncIndicator({ entry, onRetry }) {
  const state = entry?.state;
  const [showSaved, setShowSaved] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    if (state === SYNC.SAVED) {
      setShowSaved(true);
      const t = setTimeout(() => setShowSaved(false), 2000);
      return () => clearTimeout(t);
    }
    setShowSaved(false);
    return undefined;
  }, [state, entry?.savedAt]);

  useEffect(() => {
    if (state !== SYNC.FAILED) setShowDetails(false);
  }, [state]);

  if (!state) return null;
  if (state === SYNC.SAVED && !showSaved) {
    return <div data-testid="attempt-sync-status" data-state="idle" style={styles.wrap} />;
  }

  if (state === SYNC.SAVED) {
    return (
      <div data-testid="attempt-sync-status" data-state="saved" style={{ ...styles.wrap, ...styles.saved }}>
        ✓ Saved
      </div>
    );
  }

  if (state === SYNC.SAVING || state === SYNC.UNSAVED) {
    return (
      <div data-testid="attempt-sync-status" data-state="saving" style={{ ...styles.wrap, ...styles.saving }}>
        <span style={styles.spinner} className="attempt-sync-pulse" />
        Saving…
      </div>
    );
  }

  if (state === SYNC.RETRYING) {
    return (
      <div data-testid="attempt-sync-status" data-state="retrying" style={{ ...styles.wrap, ...styles.saving }}>
        <span style={styles.spinner} className="attempt-sync-pulse" />
        Retrying… (attempt {entry.attempt}/3)
      </div>
    );
  }

  // failed
  const detail = entry?.error?.message || "Save failed.";
  return (
    <div data-testid="attempt-sync-status" data-state="failed" style={{ ...styles.wrap, ...styles.failed }}>
      <span>⚠ Save failed</span>
      <button type="button" data-testid="attempt-sync-retry" style={styles.linkBtn} onClick={onRetry}>
        Retry
      </button>
      <button
        type="button"
        data-testid="attempt-sync-details"
        style={styles.linkBtn}
        onClick={() => setShowDetails((v) => !v)}
      >
        View details
      </button>
      {showDetails && (
        <span data-testid="attempt-sync-detail-text" style={styles.detail}>
          {detail}
        </span>
      )}
    </div>
  );
}

const styles = {
  wrap: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    fontSize: 13,
    minHeight: 22,
    fontWeight: 600,
  },
  saved: { color: "#16a34a" },
  saving: { color: "#9ca3af" },
  failed: {
    color: "#fecaca",
    background: "#7f1d1d",
    border: "1px solid #ef4444",
    borderRadius: 6,
    padding: "4px 10px",
  },
  spinner: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    background: "currentColor",
    display: "inline-block",
  },
  linkBtn: {
    background: "transparent",
    border: "none",
    color: "#fff",
    textDecoration: "underline",
    cursor: "pointer",
    fontSize: 13,
    padding: 0,
    fontWeight: 600,
  },
  detail: { fontWeight: 400, opacity: 0.9 },
};
