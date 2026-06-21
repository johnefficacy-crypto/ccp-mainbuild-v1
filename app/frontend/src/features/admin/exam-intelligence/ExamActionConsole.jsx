import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../../lib/api";
import { StatusBadge } from "../../../shared/ui/core";
import { humanizeToken } from "./operatorChrome";

/**
 * ExamActionConsole — Wave 4.6I-FE.
 *
 * Read-only per-exam triage view for /admin/exam-intelligence/console/:exam_id,
 * consuming GET /api/admin/exam-intelligence/console/exams/{exam_id} (PR #707).
 * The backend OWNS verdict status, action order, check states, reasons, and CTA
 * routes — this component never recomputes them. Editing happens by following an
 * action's CTA into /workspace/:exam_id. No evidence fetch / drawer yet, no
 * mutations, no readiness/confidence percentage.
 *
 * When `data` prop is supplied (e.g. from ExamWorkspace management endpoint),
 * the component renders that data directly and skips the fetch entirely.
 * The management endpoint shape has flat exam fields at the top level; the
 * console endpoint shape has an `exam` sub-object — both are handled.
 */

const VERDICT_META = {
  blocked: { tone: "pill-rose", label: "Blocked" },
  needs_action: { tone: "pill-amber", label: "Needs action" },
  ready: { tone: "pill-sage", label: "Ready" },
};

const MOCK_META = {
  ready: { tone: "pill-sage", label: "Ready" },
  thin_bank: { tone: "pill-amber", label: "Thin bank" },
  blocked: { tone: "pill-rose", label: "Blocked" },
  unknown: { tone: "pill-dusk", label: "Unknown" },
};

const SEVERITY_META = {
  blocker: { tone: "pill-rose", label: "Blocker", rank: 0 },
  action: { tone: "pill-amber", label: "Action", rank: 1 },
  advisory: { tone: "pill-dusk", label: "Advisory", rank: 2 },
};

const CHECK_STATE_META = {
  done: { tone: "pill-sage", label: "Done" },
  needs_action: { tone: "pill-amber", label: "Needs action" },
  blocked: { tone: "pill-rose", label: "Blocked" },
  unknown: { tone: "pill-dusk", label: "Unknown" },
};

const GATE_LABELS = { hard: "Hard gate", advisory: "Advisory" };

const AREA_LABELS = {
  setup: "Setup", documents: "Documents", syllabus: "Syllabus",
  topic_coverage: "Topic coverage", pyq: "PYQ", updates: "Updates",
  competition: "Competition", mock_readiness: "Mock readiness", publish: "Publish",
};

// Mirrors ConsoleWorkQueue's flag/reason vocabulary; unmapped tokens fall back
// to a safe humanized label — raw snake_case is never rendered.
const REASON_LABELS = {
  no_phases: "No exam phases",
  no_locked_coverage: "No locked coverage",
  missing_coverage: "Missing locked coverage",
  missing_pyq: "Missing PYQ",
  pending_review: "Pending review",
  stale_review_queue: "Stale review",
};

function reasonLabel(token) {
  return REASON_LABELS[token] || humanizeToken(token) || "Other";
}

function areaLabel(area) {
  return AREA_LABELS[area] || humanizeToken(area) || "Other";
}

function evidenceCount(refs) {
  return Array.isArray(refs) ? refs.length : 0;
}

// ── Data hook: loading | live | not_found | error, stale-protected ──────────

function useExamDetail(examId) {
  const [state, setState] = useState({ status: examId ? "loading" : "idle", data: null, error: null });
  const seq = useRef(0);

  const load = useCallback(() => {
    if (!examId) return;
    const mySeq = ++seq.current;
    // Clear any prior exam's data immediately so stale rows never linger.
    setState({ status: "loading", data: null, error: null });
    api
      .get(`/api/admin/exam-intelligence/console/exams/${encodeURIComponent(examId)}`)
      .then((d) => {
        if (mySeq !== seq.current) return;
        setState({ status: "live", data: d, error: null });
      })
      .catch((e) => {
        if (mySeq !== seq.current) return;
        if (e?.status === 404) setState({ status: "not_found", data: null, error: e });
        else setState({ status: "error", data: null, error: e });
      });
  }, [examId]);

  useEffect(() => {
    if (!examId) return;
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);
  return { ...state, reload: load };
}

// ── Small presentational pieces ─────────────────────────────────────────────

function EvidenceTag({ refs }) {
  const n = evidenceCount(refs);
  if (!n) return null;
  return <span className="anno" data-testid="evidence-count">{n} evidence</span>;
}

function ReasonTags({ reasons, testid }) {
  if (!Array.isArray(reasons) || !reasons.length) return null;
  return (
    <div className="row" style={{ flexWrap: "wrap", gap: 4, marginTop: 4 }} data-testid={testid}>
      {reasons.map((r) => (
        <span key={r} className="pill pill-outline" data-testid={`${testid}-${r}`}>{reasonLabel(r)}</span>
      ))}
    </div>
  );
}

// ── Component ────────────────────────────────────────────────────────────────

export default function ExamActionConsole({ examId, embedded = false, data: injectedData = null }) {
  // When injectedData is provided, skip the fetch entirely.
  const fetchTarget = injectedData ? null : examId;
  const { status, data: fetchedData, reload } = useExamDetail(fetchTarget);

  // Fetch-path error/loading states (only when not using injected data)
  if (!injectedData) {
    if (status === "loading") {
      if (embedded) return <div data-testid="action-console-loading" style={{ padding: "8px 22px", color: "var(--ink-mute)", fontSize: 13 }}>Loading action data…</div>;
      return <div className="oc-main" style={{ padding: 22 }} data-testid="action-console-loading">Loading exam console…</div>;
    }

    if (status === "not_found") {
      if (embedded) {
        return (
          <div data-testid="action-console-not-found" style={{ padding: "8px 22px" }}>
            <span className="err-row" style={{ fontSize: 13 }}>Exam not found in action console.</span>
          </div>
        );
      }
      return (
        <div className="oc-main" style={{ padding: 22 }} data-testid="action-console-not-found">
          <div className="empty">
            <div className="empty-title">Exam not found.</div>
            <Link to="/admin/exam-intelligence/console" className="btn" data-testid="not-found-back">Back to work queue</Link>
          </div>
        </div>
      );
    }

    if (status === "error" || !fetchedData) {
      if (embedded) return <div data-testid="action-console-error" style={{ padding: "8px 22px" }}><span className="err-row" style={{ fontSize: 13 }}>Could not load action data.{" "}<button type="button" className="btn" onClick={reload} data-testid="action-console-retry">Retry</button></span></div>;
      return (
        <div className="oc-main" style={{ padding: 22 }} data-testid="action-console-error">
          <div className="err-row">
            Could not load the exam console.{" "}
            <button type="button" className="btn" onClick={reload} data-testid="action-console-retry">Retry</button>
          </div>
        </div>
      );
    }
  }

  const raw = injectedData ?? fetchedData;
  if (!raw) return null;

  // Normalize shape: management endpoint has flat exam fields at top level;
  // console endpoint wraps them in an `exam` sub-object.
  const exam = raw.exam || {
    id: raw.id,
    slug: raw.slug,
    name: raw.name,
    organization_name: raw.organization_name,
    family_name: raw.family_name,
  };
  const verdict = raw.activation_verdict || {};
  const mock = raw.mock_readiness || { status: "unknown" };
  const actions = Array.isArray(raw.action_queue) ? raw.action_queue : [];
  const checks = Array.isArray(raw.activation_checks) ? raw.activation_checks : [];
  const stages = Array.isArray(raw.stages) ? raw.stages : [];
  const checkByArea = Object.fromEntries(checks.map((c) => [c.area, c]));

  const vMeta = VERDICT_META[verdict.status] || { tone: "pill-dusk", label: humanizeToken(verdict.status) || "Unknown" };
  const mMeta = MOCK_META[mock.status] || MOCK_META.unknown;
  const manageRoute = `/admin/exam-intelligence/exams/${encodeURIComponent(exam.id)}`;

  const padding = embedded ? "12px 22px" : 22;

  return (
    <div className="oc-main" style={{ padding }} data-testid="exam-action-console">
      {/* 1. Header — identity from the detail response (no extra request).
          Hidden when embedded inside ExamWorkspace (which already shows the header). */}
      {!embedded && (
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 12 }}>
        <div style={{ minWidth: 0 }}>
          <div className="lbl">Exam Governance Console</div>
          <h1 className="oc-title disp" style={{ fontSize: 24, margin: "2px 0" }} data-testid="action-console-name">
            {exam.name || exam.slug || "Unnamed exam"}
          </h1>
          <div className="anno" data-testid="action-console-meta">
            {[exam.organization_name, exam.family_name].filter(Boolean).join(" · ") || "—"}
            {exam.slug ? <span className="mono" style={{ marginLeft: 8 }}>{exam.slug}</span> : null}
          </div>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <Link to="/admin/exam-intelligence/console" className="btn btn-ghost" data-testid="action-console-back">Back to work queue</Link>
          <Link to={manageRoute} className="btn btn-ghost" data-testid="action-console-workspace">Manage exam</Link>
        </div>
      </div>
      )}

      {/* 2. Activation verdict (backend status, no recompute, no %). */}
      <div className="card" style={{ marginBottom: 12 }} data-testid="activation-verdict">
        <div className="card-body">
          <div className="row" style={{ gap: 10, alignItems: "center" }}>
            <StatusBadge status={verdict.status} tone={vMeta.tone} label={vMeta.label} />
            <strong data-testid="verdict-headline">{verdict.headline}</strong>
          </div>
          <ReasonTags reasons={verdict.reasons} testid="verdict-reasons" />
        </div>
      </div>

      {/* 3. Action queue — preserve backend order (blockers → actions → advisories). */}
      <div className="lbl" style={{ marginBottom: 6 }}>Action queue</div>
      {actions.length === 0 ? (
        <div className="empty" data-testid="action-queue-empty">
          <div className="empty-title">No activation actions.</div>
        </div>
      ) : (
        <ul className="stack" style={{ listStyle: "none", padding: 0, margin: "0 0 12px" }} data-testid="action-queue">
          {actions.map((a, i) => {
            const sMeta = SEVERITY_META[a.severity] || SEVERITY_META.advisory;
            return (
              <li key={a.id || i} className="card" data-testid={`action-${a.area}`} data-severity={a.severity}>
                <div className="card-body" style={{ display: "flex", gap: 12, justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ minWidth: 0 }}>
                    <div className="row" style={{ gap: 8, alignItems: "center" }}>
                      <span className={`pill ${sMeta.tone}`} data-testid={`action-severity-${a.area}`}>{sMeta.label}</span>
                      <strong>{a.title}</strong>
                    </div>
                    <div className="anno" style={{ marginTop: 2 }}>{a.why}</div>
                    <EvidenceTag refs={a.evidence_refs} />
                  </div>
                  {a.cta_route ? (
                    <Link to={a.cta_route} className="btn" data-testid={`action-cta-${a.area}`}>
                      {a.cta_label || "Open"}
                    </Link>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* 4. Activation checks grouped by backend stages (order preserved). */}
      <div className="lbl" style={{ marginBottom: 6 }}>Activation checks</div>
      <div className="stack" style={{ marginBottom: 12 }} data-testid="activation-checks">
        {stages.map((stage) => (
          <div key={stage.id} className="card" data-testid={`stage-${stage.id}`}>
            <div className="card-head"><strong>{stage.label}</strong></div>
            <div className="card-body" style={{ display: "grid", gap: 8 }}>
              {(stage.areas || []).map((area) => {
                const c = checkByArea[area];
                if (!c) return null;
                const csMeta = CHECK_STATE_META[c.state] || CHECK_STATE_META.unknown;
                return (
                  <div key={area} className="row" style={{ gap: 10, alignItems: "flex-start", justifyContent: "space-between" }}
                       data-testid={`check-${area}`}>
                    <div style={{ minWidth: 0 }}>
                      <div className="row" style={{ gap: 8, alignItems: "center" }}>
                        <strong style={{ fontSize: 13 }}>{areaLabel(area)}</strong>
                        <span className="anno" data-testid={`check-gate-${area}`}>{GATE_LABELS[c.gate] || humanizeToken(c.gate) || "Advisory"}</span>
                      </div>
                      <div className="anno" style={{ marginTop: 2 }}>{c.detail}</div>
                      <ReasonTags reasons={c.reasons} testid={`check-reasons-${area}`} />
                      <EvidenceTag refs={c.evidence_refs} />
                    </div>
                    <span className={`pill ${csMeta.tone}`} data-testid={`check-state-${area}`}>{csMeta.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* 5. Mock readiness — separate advisory card; never overrides the verdict. */}
      <div className="card" data-testid="mock-readiness">
        <div className="card-body">
          <div className="row" style={{ gap: 8, alignItems: "center" }}>
            <span className="lbl">Mock readiness</span>
            <span className="pill pill-outline" data-testid="mock-advisory-tag">Advisory</span>
            <span className={`pill ${mMeta.tone}`} data-testid="mock-status">{mMeta.label}</span>
          </div>
          {mock.detail ? <div className="anno" style={{ marginTop: 4 }}>{mock.detail}</div> : null}
        </div>
      </div>
    </div>
  );
}
