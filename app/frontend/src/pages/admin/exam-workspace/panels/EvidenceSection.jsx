/**
 * EvidenceSection — D05 document-evidence registration + trust review (PR-4).
 *
 * Renders inside DocumentsPanel. Lets an operator promote an uploaded+completed
 * document_asset into the D05 evidence model (exam_document_evidence + roles),
 * run the human trust review (verify / reject / supersede), and see the resolved
 * requirement coverage for the selected cycle — the same evaluation Step 9
 * (Review & activate) uses.
 *
 * Permission tiers (locked J2 §D, mirrored from the backend router):
 *   reads               → manage OR review
 *   register            → exam_intelligence.manage  (operational edit)
 *   verify/reject/supersede → exam_intelligence.review  (trust/lifecycle)
 * cms is NOT a normal-surface capability here. Actions are hidden/disabled by
 * capability; super_admin sees everything.
 *
 * All mutations go through useApiAction (mandatory per AGENTS.md) — shared
 * toast + busy/error handling. Registering never auto-verifies (lands pending).
 *
 * Endpoints (admin_exam_intel_evidence.py):
 *   GET  /evidence?exam_id=&exam_cycle_id=   GET /evidence/coverage   GET /evidence/sources
 *   POST /evidence   POST /evidence/{id}/review   POST /evidence/{id}/supersede
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { api, getApiErrorMessage } from "../../../../lib/api";
import { useAuth } from "../../../../lib/authContext";
import useApiAction from "../../../../lib/hooks/useApiAction";

const CMS = "/api/admin/exam-intelligence-cms";
const EV_BASE = `${CMS}/evidence`;
const DOC_BASE = `${CMS}/documents`;

// Canonical exam_evidence_kinds vocabulary (migration 211). Display subtypes normalize to these.
const EVIDENCE_KINDS = [
  "primary_cycle_document", "syllabus", "exam_pattern", "pyq_paper", "answer_key",
  "phase_rules", "corrigendum", "notification", "application_instructions", "phase_schedule",
];

const TRUST_BADGE = {
  pending: { cls: "badge pending", text: "pending review" },
  verified: { cls: "badge resolved", text: "verified" },
  rejected: { cls: "badge blocker", text: "rejected" },
  superseded: { cls: "badge neutral", text: "superseded" },
};

function TrustBadge({ status }) {
  const b = TRUST_BADGE[status] || { cls: "badge neutral no-dot", text: status ?? "—" };
  return <span className={b.cls} data-testid={`ev-trust-${status}`}>{b.text}</span>;
}
TrustBadge.propTypes = { status: PropTypes.string };

const shortId = (id) => (id ? `…${String(id).slice(-6)}` : "—");
const phaseLabel = (p) => p?.phase_name ?? p?.name ?? p?.phase_slug ?? `Phase ${shortId(p?.id)}`;

// An asset is registerable only once its upload handshake is complete (independent of extraction).
// Mirrors the backend _upload_incomplete guard so the picker can't offer a placeholder.
function isRegisterableAsset(a) {
  if (!a || a.status === "archived" || a.status === "uploaded") return false;
  return !String(a.content_hash || "").startsWith("pending:");
}

// ── RegisterForm ────────────────────────────────────────────────────────────

function RegisterForm({ examId, cycleId, phases, assets, sources, onDone, onCancel }) {
  const [assetId, setAssetId] = useState("");
  const [kind, setKind] = useState("syllabus");
  const [phaseId, setPhaseId] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [reason, setReason] = useState("");
  const [err, setErr] = useState("");
  const { run, busy } = useApiAction();

  async function handleSubmit(e) {
    e.preventDefault();
    setErr("");
    if (!assetId) { setErr("Choose a document to register."); return; }
    if (reason.trim().length < 8) { setErr("Reason must be at least 8 characters."); return; }
    const res = await run({
      action: () => api.post(EV_BASE, {
        document_asset_id: assetId,
        exam_id: examId,
        exam_cycle_id: cycleId || null,
        exam_phase_id: phaseId || null,
        source_registry_id: sourceId || null,
        roles: [{ evidence_kind: kind, exam_phase_id: phaseId || null, exam_cycle_id: cycleId || null }],
        reason: reason.trim(),
      }),
      successMessage: "Evidence registered — pending review.",
      errorMessage: "Registration failed",
    });
    if (res.ok) onDone();
    else setErr(getApiErrorMessage(res.error) || "Registration failed");
  }

  return (
    <form onSubmit={handleSubmit} className="card" style={{ borderStyle: "dashed" }} data-testid="ev-register-form">
      <div className="card-body">
        <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>Register document as evidence</div>
        <div className="row" style={{ flexWrap: "wrap", gap: 10, marginBottom: 10 }}>
          <label style={{ flex: "1 1 240px" }}>
            <div className="field-lbl">Document <span style={{ color: "var(--ink-accent)" }}>*</span></div>
            {assets.length === 0 ? (
              <div style={{ fontSize: 12, color: "var(--ink-mute)" }} data-testid="ev-no-assets">
                No upload-complete documents for this exam — upload and finish a PDF first.
              </div>
            ) : (
              <select className="field" value={assetId} onChange={(e) => setAssetId(e.target.value)} data-testid="ev-asset-select">
                <option value="">— select —</option>
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {(a.title || a.original_filename || shortId(a.id))} · {a.document_kind} · {a.status}
                  </option>
                ))}
              </select>
            )}
          </label>
          <label style={{ flex: "1 1 180px" }}>
            <div className="field-lbl">Evidence role <span style={{ color: "var(--ink-accent)" }}>*</span></div>
            <select className="field" value={kind} onChange={(e) => setKind(e.target.value)} data-testid="ev-kind-select">
              {EVIDENCE_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </label>
        </div>
        <div className="row" style={{ flexWrap: "wrap", gap: 10, marginBottom: 10 }}>
          <label style={{ flex: "1 1 180px" }}>
            <div className="field-lbl">Phase <span style={{ color: "var(--ink-mute)", fontWeight: 400 }}>(optional)</span></div>
            <select className="field" value={phaseId} onChange={(e) => setPhaseId(e.target.value)} data-testid="ev-phase-select">
              <option value="">No phase (cycle/exam level)</option>
              {phases.map((p) => <option key={p.id} value={p.id}>{phaseLabel(p)}</option>)}
            </select>
          </label>
          <label style={{ flex: "1 1 220px" }}>
            <div className="field-lbl">Source <span style={{ color: "var(--ink-mute)", fontWeight: 400 }}>(authority)</span></div>
            <select className="field" value={sourceId} onChange={(e) => setSourceId(e.target.value)} data-testid="ev-source-select">
              <option value="">— no source registry link —</option>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.source_name}{s.is_authoritative ? " ✓ authoritative" : " (not authoritative)"}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label style={{ display: "block", marginBottom: 10 }}>
          <div className="field-lbl">Reason <span style={{ color: "var(--ink-mute)", fontWeight: 400 }}>(≥ 8 chars)</span></div>
          <input type="text" className="field" value={reason} onChange={(e) => setReason(e.target.value)}
                 placeholder="e.g. Official syllabus for Tier I" data-testid="ev-reason" />
        </label>
        {err && <div className="err-row" data-testid="ev-register-err">{err}</div>}
        <div className="row" style={{ gap: 6 }}>
          <button type="submit" className="btn small" disabled={busy || assets.length === 0} data-testid="ev-register-submit">
            {busy ? "Registering…" : "Register evidence"}
          </button>
          <button type="button" className="btn small" onClick={onCancel} data-testid="ev-register-cancel">Cancel</button>
        </div>
      </div>
    </form>
  );
}
RegisterForm.propTypes = {
  examId: PropTypes.string,
  cycleId: PropTypes.string,
  phases: PropTypes.array,
  assets: PropTypes.array,
  sources: PropTypes.array,
  onDone: PropTypes.func,
  onCancel: PropTypes.func,
};

// ── ReviewControls (inline verify/reject/supersede — review tier) ────────────

function ReviewControls({ ev, others, canReview, onChanged }) {
  const [mode, setMode] = useState(null); // 'reject' | 'supersede'
  const [reason, setReason] = useState("");
  const [target, setTarget] = useState("");
  const [err, setErr] = useState("");
  const { run, busy } = useApiAction();

  const terminal = ev.trust_status === "superseded";

  async function verify() {
    setErr("");
    const res = await run({
      action: () => api.post(`${EV_BASE}/${ev.id}/review`, { decision: "verified", reason: "operator verified evidence" }),
      successMessage: "Evidence verified.",
      errorMessage: "Verify failed",
    });
    if (res.ok) onChanged();
    else setErr(getApiErrorMessage(res.error) || "Verify failed");
  }

  async function submitReason() {
    setErr("");
    if (reason.trim().length < 8) { setErr("Reason must be at least 8 characters."); return; }
    if (mode === "supersede" && !target) { setErr("Choose the superseding evidence."); return; }
    const res = await run({
      action: () => (mode === "reject"
        ? api.post(`${EV_BASE}/${ev.id}/review`, { decision: "rejected", reason: reason.trim() })
        : api.post(`${EV_BASE}/${ev.id}/supersede`, { superseded_by_id: target, reason: reason.trim() })),
      successMessage: mode === "reject" ? "Evidence rejected." : "Evidence superseded.",
      errorMessage: "Action failed",
    });
    if (res.ok) { setMode(null); setReason(""); setTarget(""); onChanged(); }
    else setErr(getApiErrorMessage(res.error) || "Action failed");
  }

  if (terminal) return <span style={{ fontSize: 11, color: "var(--ink-mute)" }}>→ {shortId(ev.superseded_by_id)}</span>;
  if (!canReview) return <span style={{ fontSize: 11, color: "var(--ink-mute)" }} data-testid={`ev-review-na-${ev.id}`}>review-only</span>;

  if (mode) {
    return (
      <div className="stack" style={{ gap: 6 }} data-testid={`ev-reason-form-${ev.id}`}>
        {mode === "supersede" && (
          <select className="field" value={target} onChange={(e) => setTarget(e.target.value)} data-testid={`ev-supersede-target-${ev.id}`}>
            <option value="">— superseded by —</option>
            {others.map((o) => (
              <option key={o.id} value={o.id}>
                {(o.document?.title || shortId(o.id))} · {o.trust_status}
              </option>
            ))}
          </select>
        )}
        <input type="text" className="field" value={reason} onChange={(e) => setReason(e.target.value)}
               placeholder="Reason (≥ 8 chars)" data-testid={`ev-reason-input-${ev.id}`} />
        {err && <div className="err-row">{err}</div>}
        <div className="row" style={{ gap: 6 }}>
          <button className="btn small" onClick={submitReason} disabled={busy} data-testid={`ev-reason-confirm-${ev.id}`}>
            {busy ? "…" : "Confirm"}
          </button>
          <button className="btn small" onClick={() => { setMode(null); setErr(""); }} disabled={busy}>Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div className="row" style={{ gap: 4, justifyContent: "flex-end", flexWrap: "wrap" }}>
      {ev.trust_status !== "verified" && (
        <button className="btn small" onClick={verify} disabled={busy} data-testid={`ev-verify-${ev.id}`}>Verify</button>
      )}
      {ev.trust_status !== "rejected" && (
        <button className="btn small" onClick={() => setMode("reject")} disabled={busy} data-testid={`ev-reject-${ev.id}`}>Reject</button>
      )}
      <button className="btn small" onClick={() => setMode("supersede")} disabled={busy || others.length === 0}
              data-testid={`ev-supersede-${ev.id}`}>Supersede</button>
      {err && <div className="err-row" style={{ flexBasis: "100%" }}>{err}</div>}
    </div>
  );
}
ReviewControls.propTypes = { ev: PropTypes.object, others: PropTypes.array, canReview: PropTypes.bool, onChanged: PropTypes.func };

// ── CoverageSummary ─────────────────────────────────────────────────────────

function CoverageSummary({ coverage }) {
  if (!coverage) return null;
  if (!coverage.applicable) {
    return (
      <div className="card" data-testid="ev-coverage">
        <div className="card-body" style={{ fontSize: 12, color: "var(--ink-mute)" }}>
          Evidence gate not applicable for this cycle ({coverage.reason || "—"}).
        </div>
      </div>
    );
  }
  const unmet = coverage.unmet_requirements || [];
  return (
    <div className="card" data-testid="ev-coverage">
      <div className="card-body">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 600, fontSize: 13 }}>D05 required-phase coverage</div>
          {coverage.complete
            ? <span className="badge resolved" data-testid="ev-coverage-complete">complete</span>
            : <span className="badge blocker" data-testid="ev-coverage-incomplete">{unmet.length} unmet</span>}
        </div>
        {coverage.unclassified_phases > 0 && (
          <div className="warn-row" style={{ marginTop: 8 }}>
            {coverage.unclassified_phases} phase(s) missing a canonical phase_kind — classify them in Setup first.
          </div>
        )}
        {unmet.length > 0 && (
          <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 12 }} data-testid="ev-unmet-list">
            {unmet.map((u, i) => (
              <li key={i}>
                <span className="badge neutral no-dot">{u.scope}</span>{" "}
                {u.evidence_kind || u.reason || "requirement"}
                {u.phase_kind ? ` · ${u.phase_kind}` : ""}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
CoverageSummary.propTypes = { coverage: PropTypes.object };

// ── EvidenceSection (main) ──────────────────────────────────────────────────

export default function EvidenceSection({ examId, cycleId, phases }) {
  const { user } = useAuth();
  const canManage =
    user?.role === "super_admin" ||
    (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.manage"));
  const canReview =
    user?.role === "super_admin" ||
    (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.review"));

  const [items, setItems] = useState([]);
  const [coverage, setCoverage] = useState(null);
  const [assets, setAssets] = useState([]);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [formOpen, setFormOpen] = useState(false);

  const load = useCallback(async () => {
    if (!examId) return;
    setLoading(true);
    setError("");
    try {
      const evQs = new URLSearchParams({ exam_id: examId });
      if (cycleId) evQs.set("exam_cycle_id", cycleId);
      const [evRes, srcRes, docRes] = await Promise.all([
        api.get(`${EV_BASE}?${evQs}`),
        api.get(`${EV_BASE}/sources`),
        api.get(`${DOC_BASE}?${new URLSearchParams({ exam_id: examId, limit: "200" })}`),
      ]);
      setItems(evRes?.items || []);
      setSources(srcRes?.items || []);
      // Only upload-complete (registerable) assets are offered — mirrors backend guard.
      setAssets((docRes?.items || []).filter(isRegisterableAsset));
      if (cycleId) {
        try {
          const cov = await api.get(`${EV_BASE}/coverage?${new URLSearchParams({ exam_id: examId, exam_cycle_id: cycleId })}`);
          setCoverage(cov);
        } catch {
          setCoverage(null);
        }
      } else {
        setCoverage(null);
      }
    } catch (e) {
      setError(getApiErrorMessage(e) || "Failed to load evidence");
    } finally {
      setLoading(false);
    }
  }, [examId, cycleId]);

  useEffect(() => { load(); }, [load]);

  const supersedeCandidates = useMemo(
    () => (evId) => items.filter((o) => o.id !== evId && o.trust_status !== "superseded"),
    [items],
  );

  return (
    <div className="stack" data-testid="evidence-section">
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">D05 evidence · trust review</div>
          <h2 className="oc-title disp" style={{ fontSize: 18, marginTop: 3 }}>Document evidence</h2>
        </div>
        <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
          <button className="btn small" onClick={load} data-testid="ev-refresh">Refresh</button>
          {canManage && (
            <button className="btn small" onClick={() => setFormOpen((v) => !v)} data-testid="ev-toggle-register">
              {formOpen ? "Cancel" : "+ Register evidence"}
            </button>
          )}
        </div>
      </div>

      {error && <div className="err-row" data-testid="ev-error">{error}</div>}

      <CoverageSummary coverage={coverage} />

      {canManage && formOpen && (
        <RegisterForm
          examId={examId}
          cycleId={cycleId}
          phases={phases || []}
          assets={assets}
          sources={sources}
          onDone={() => { setFormOpen(false); load(); }}
          onCancel={() => setFormOpen(false)}
        />
      )}

      {loading && items.length === 0 ? (
        <div className="skel" style={{ height: 40 }} data-testid="ev-loading" />
      ) : items.length === 0 ? (
        <div className="card" style={{ borderStyle: "dashed" }}>
          <div className="empty" style={{ padding: "20px 16px", fontSize: 13 }} data-testid="ev-empty">
            No evidence registered yet. Register upload-complete documents so the Review &amp; Activate
            gate can evaluate required-phase completeness.
          </div>
        </div>
      ) : (
        <div className="card">
          <table className="t" data-testid="ev-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Roles</th>
                <th>Source</th>
                <th>Trust</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((ev) => (
                <tr key={ev.id} data-testid={`ev-row-${ev.id}`}>
                  <td>
                    <div className="row-ttl">{ev.document?.title || ev.document?.original_filename || shortId(ev.document_asset_id)}</div>
                    <div className="row-sub" style={{ fontSize: 11, color: "var(--ink-mute)" }}>
                      {ev.document?.document_kind || "—"}
                      {ev.extraction_status ? ` · extract: ${ev.extraction_status}` : ""}
                    </div>
                  </td>
                  <td>
                    {(ev.roles || []).map((r) => (
                      <span key={r.id || r.evidence_kind} className="badge neutral no-dot" style={{ marginRight: 4 }}>
                        {r.evidence_kind}
                      </span>
                    ))}
                  </td>
                  <td>
                    {ev.source_registry_id
                      ? (ev.source_authoritative
                          ? <span className="badge resolved" data-testid={`ev-src-ok-${ev.id}`}>authoritative</span>
                          : <span className="badge blocker" data-testid={`ev-src-bad-${ev.id}`}>not authoritative</span>)
                      : <span className="badge neutral no-dot">none</span>}
                  </td>
                  <td><TrustBadge status={ev.trust_status} /></td>
                  <td style={{ textAlign: "right", minWidth: 160 }}>
                    <ReviewControls ev={ev} others={supersedeCandidates(ev.id)} canReview={canReview} onChanged={load} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
EvidenceSection.propTypes = {
  examId: PropTypes.string,
  cycleId: PropTypes.string,
  phases: PropTypes.array,
};
