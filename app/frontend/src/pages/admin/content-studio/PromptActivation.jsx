/**
 * Prompt activation affordance (EWP-SP2-UI) — the operator control that surfaces
 * the SEPARATE content_studio.activate authority (activate / deactivate).
 *
 * Governance contract (docs/status/career-copilot-checklist.md EWP-SP2 row,
 * app/backend/app/api/content_studio.py, migration 226):
 * - Neither author nor review may flip is_active. This control is gated on
 *   content_studio.activate (perms.canActivate) — hidden without it.
 * - The CLIENT's `expected_updated_at` (the updated_at the browser read) is sent
 *   UNCHANGED (no pre-write refetch), so a stale-browser activation loses with 409.
 * - Eligibility is NEVER computed here. The RPC is the sole authority: a blocked
 *   activation is a NORMAL HTTP 200 answer carrying `{eligible:false, blockers}`,
 *   which we render verbatim (code → human label). Success reflects the new
 *   is_active. 409 → conflict/re-read; 404/422 → mapped error. No silent failure.
 */
import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import useApiAction from "../../../lib/hooks/useApiAction";
import { getApiErrorMessage } from "../../../lib/api";
import { contentStudioApi, describeActivationBlocker, isValidReason } from "./contentStudioApi";

export default function PromptActivationDialog({ prompt, mode, onClose, onDone }) {
  const isActivate = mode === "activate";
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [blockers, setBlockers] = useState(null); // null | string[] (eligible:false)
  const { run, busy } = useApiAction();
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  // A11y: Escape closes; focus into the dialog on open, restore on close.
  useEffect(() => {
    const prevFocus = typeof document !== "undefined" ? document.activeElement : null;
    const node = dialogRef.current;
    const first = node && node.querySelector("input, textarea, select, button");
    if (first) first.focus();
    const onKey = (e) => { if (e.key === "Escape") closeRef.current(); };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (prevFocus && typeof prevFocus.focus === "function") prevFocus.focus();
    };
  }, []);

  const submit = async () => {
    if (!isValidReason(reason)) {
      setError("Reason must be 8–500 characters (audit requirement).");
      return;
    }
    setError("");
    setConflict(false);
    setBlockers(null);

    const res = await run({
      action: () =>
        (isActivate
          ? contentStudioApi.activateWritingPrompt(prompt.id, {
              // CLIENT's token, unchanged — no pre-write refetch.
              expected_updated_at: prompt.updated_at,
              reason: reason.trim(),
            })
          : contentStudioApi.deactivateWritingPrompt(prompt.id, {
              expected_updated_at: prompt.updated_at,
              reason: reason.trim(),
            })),
      // Success toast is decided AFTER inspecting the RPC verdict below (a blocked
      // activation is a 200, not a success), so no successMessage here.
      errorMessage: " ",
    });

    if (!res.ok && res.error) {
      if (res.error.status === 409) setConflict(true);
      else setError(getApiErrorMessage(res.error));
      return;
    }
    // res.ok — inspect the structured RPC verdict (never computed client-side).
    const result = res.data && res.data.result ? res.data.result : {};
    if (isActivate && result.eligible === false) {
      setBlockers(Array.isArray(result.blockers) ? result.blockers : []);
      return;
    }
    onDone({ is_active: !!result.is_active });
  };

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={onClose}
      data-testid="prompt-activation-overlay"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={isActivate ? "Activate writing prompt" : "Deactivate writing prompt"}
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(520px, 95vw)", maxHeight: "85vh", overflowY: "auto", background: "var(--paper, #fff)", borderRadius: 6, padding: "1.25rem", boxShadow: "0 4px 16px rgba(0,0,0,0.25)" }}
        data-testid="prompt-activation-dialog"
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>
            {isActivate ? "Activate prompt" : "Deactivate prompt"}
          </h2>
          <button type="button" className="btn small" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <p style={{ fontSize: 12, opacity: 0.75, marginBottom: 10 }}>
          {isActivate
            ? "Activation is verified by the server under lock. If any precondition fails the prompt stays inactive and the exact blockers are shown below — eligibility is never decided in the browser."
            : "Deactivation hides this prompt from aspirant launch. Records a reason in the audit log."}
        </p>

        <div style={{ fontSize: 12, marginBottom: 10 }}>
          Current state: <strong data-testid="activation-current-state">{prompt.is_active ? "active" : "inactive"}</strong>
        </div>

        {conflict ? (
          <div className="badge blocker" style={{ display: "block", padding: "0.6rem", marginBottom: 10, fontSize: 12 }} role="alert" data-testid="activation-conflict">
            This prompt changed since you loaded it (409). Refresh the list and re-read
            the latest revision before activating.
          </div>
        ) : null}

        {blockers !== null ? (
          <div className="badge blocker" style={{ display: "block", padding: "0.6rem", marginBottom: 10, fontSize: 12 }} role="alert" data-testid="activation-blocked">
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Activation blocked</div>
            {blockers.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {blockers.map((code) => (
                  <li key={code} data-testid={`activation-blocker-${code}`}>{describeActivationBlocker(code)}</li>
                ))}
              </ul>
            ) : (
              <span>The server reported the prompt is not eligible for activation.</span>
            )}
          </div>
        ) : null}

        {error && error.trim() ? (
          <div style={{ color: "var(--err, #c00)", fontSize: 12, marginBottom: 10 }} role="alert" data-testid="activation-error">{error}</div>
        ) : null}

        <label style={{ fontSize: 12, display: "block", marginBottom: 14 }}>
          Reason (required, 8–500 chars — recorded in the audit log)
          <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} data-testid="activation-reason" />
        </label>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="button" className="btn primary" onClick={submit} disabled={busy} data-testid="activation-submit">
            {busy ? "Submitting…" : isActivate ? "Activate" : "Deactivate"}
          </button>
        </div>
      </div>
    </div>
  );
}

PromptActivationDialog.propTypes = {
  prompt: PropTypes.shape({
    id: PropTypes.string.isRequired,
    updated_at: PropTypes.string,
    is_active: PropTypes.bool,
  }).isRequired,
  mode: PropTypes.oneOf(["activate", "deactivate"]).isRequired,
  onClose: PropTypes.func.isRequired,
  onDone: PropTypes.func.isRequired,
};
