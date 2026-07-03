import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../../../lib/api";
import useApiAction from "../../../../lib/hooks/useApiAction";

const base = (id) => `/api/admin/mocks/pyq-papers/${id}/projection`;

function reasonText(reason) {
  const [code, detail] = String(reason ?? "").split(":");
  const fixed = {
    eligible: "Eligible",
    not_mcq: "Not a multiple-choice question",
    empty_question_text: "Question text is empty",
    empty_verified_option_text: "A verified option has empty text",
    correct_option_id_mismatch: "Correct-answer option mismatch",
  };
  if (fixed[code]) return fixed[code];
  if (code === "paper_not_verified") return `Paper not verified${detail ? ` (${detail})` : ""}`;
  if (code === "question_not_verified") return `Question not verified${detail ? ` (${detail})` : ""}`;
  if (code === "too_few_verified_options") return `Fewer than 2 verified options${detail ? ` (${detail})` : ""}`;
  if (code === "not_exactly_one_correct") return `Needs exactly one correct option (has ${detail ?? "0"})`;
  if (code === "not_exactly_one_verified_primary_tag") {
    return Number(detail) > 1 ? `Multiple verified primary tags (${detail})` : "Missing verified primary topic tag";
  }
  return code ? code.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "Ineligible";
}

function groupKey(reason) {
  const [code, detail] = String(reason ?? "").split(":");
  if (code === "not_exactly_one_verified_primary_tag" || code === "not_exactly_one_correct") {
    return `${code}:${Number(detail) > 1 ? "multiple" : "missing"}`;
  }
  return code || "ineligible";
}

function groupLabel(key) {
  return ({
    "not_exactly_one_verified_primary_tag:missing": "Missing verified primary topic tag",
    "not_exactly_one_verified_primary_tag:multiple": "Multiple verified primary tags",
    "not_exactly_one_correct:missing": "No verified correct option",
    "not_exactly_one_correct:multiple": "Multiple verified correct options",
  })[key] || reasonText(key);
}

function groups(rows) {
  const counts = new Map();
  for (const row of rows ?? []) {
    if (!row.eligible) {
      const key = groupKey(row.reason);
      counts.set(key, (counts.get(key) || 0) + 1);
    }
  }
  return [...counts].map(([code, count]) => ({ code, count, label: groupLabel(code) }))
    .sort((a, b) => b.count - a.count);
}

const identity = (row) => row.label?.trim() || `${String(row.question_id).slice(0, 8)}…`;

export default function PyqMockProjectionPanel({ paperId }) {
  const [status, setStatus] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [statusError, setStatusError] = useState(null);
  const [previewError, setPreviewError] = useState(null);
  const [auditReason, setAuditReason] = useState("");
  const { run } = useApiAction();
  const mounted = useRef(true);
  const scope = useRef({ paperId, version: 0 });

  if (scope.current.paperId !== paperId) {
    scope.current = { paperId, version: scope.current.version + 1 };
  }

  useEffect(() => () => {
    mounted.current = false;
    scope.current = { paperId: null, version: scope.current.version + 1 };
  }, []);

  const current = useCallback((id, version) => (
    mounted.current && scope.current.paperId === id && scope.current.version === version
  ), []);

  const loadStatus = useCallback(async (id, version) => {
    if (!id || !current(id, version)) return;
    setStatusLoading(true);
    setStatusError(null);
    try {
      const data = await api.get(`${base(id)}/status`);
      if (current(id, version)) setStatus(data);
    } catch (error) {
      if (current(id, version)) setStatusError(error?.message || "Failed to load projection status");
    } finally {
      if (current(id, version)) setStatusLoading(false);
    }
  }, [current]);

  useEffect(() => {
    const version = scope.current.version;
    setStatus(null);
    setPreview(null);
    setResult(null);
    setStatusError(null);
    setPreviewError(null);
    setStatusLoading(false);
    setPreviewLoading(false);
    setSyncing(false);
    setAuditReason("");
    if (paperId) loadStatus(paperId, version);
  }, [paperId, loadStatus]);

  const loadPreview = useCallback(async () => {
    const id = paperId;
    const version = scope.current.version;
    if (!id) return;
    setPreviewLoading(true);
    setPreview(null);
    setPreviewError(null);
    try {
      const data = await api.get(`${base(id)}/preview`);
      if (current(id, version)) setPreview(data);
    } catch (error) {
      if (current(id, version)) setPreviewError(error?.message || "Failed to load projection preview");
    } finally {
      if (current(id, version)) setPreviewLoading(false);
    }
  }, [paperId, current]);

  const sync = useCallback(async () => {
    if (!paperId || auditReason.trim().length < 8) return;
    const id = paperId;
    const version = scope.current.version;
    setSyncing(true);
    await run({
      action: () => api.post(`${base(id)}/sync`, { audit_reason: auditReason.trim() }),
      onSuccess: (data) => {
        if (!current(id, version)) return;
        setResult(data);
        setAuditReason("");
        loadStatus(id, version);
      },
      successMessage: "Projection sync complete.",
      errorMessage: "Sync failed. Check permissions or paper status.",
    });
    if (current(id, version)) setSyncing(false);
  }, [paperId, auditReason, run, current, loadStatus]);

  if (!paperId) return null;
  const zeroEligible = preview != null && (preview.eligible_count ?? 0) === 0;
  const blockerGroups = preview ? groups(preview.questions) : [];

  return (
    <section className="border-t border-gray-200 bg-gray-50 px-4 py-3" data-testid="pyq-mock-projection-panel">
      <div className="flex justify-between mb-2">
        <strong>Mock projection</strong>
        <button type="button" onClick={loadPreview} disabled={previewLoading} data-testid="projection-preview-btn">{previewLoading ? "Loading…" : "Preview"}</button>
      </div>
      <details className="mb-2 text-xs" data-testid="projection-info-disclosure">
        <summary>ⓘ What gets projected?</summary>
        <p>Projection requires a verified paper and question, MCQ type, non-empty question and verified option text, at least two verified options, exactly one verified correct option, a matching correct-option reference, and exactly one verified primary topic tag. Preview shows what would change; Sync writes eligible questions.</p>
      </details>
      <div className="flex gap-2 mb-2">
        <input value={auditReason} onChange={(e) => setAuditReason(e.target.value)} placeholder="Audit reason (min 8 chars)" maxLength={500} data-testid="projection-audit-reason-input" />
        <button type="button" onClick={sync} disabled={syncing || auditReason.trim().length < 8 || zeroEligible} data-testid="projection-sync-btn">{syncing ? "Syncing…" : "Sync to mock bank"}</button>
      </div>
      {zeroEligible && <p data-testid="projection-zero-eligible-note">0 eligible for projection — sync is disabled until at least one question clears the blockers.</p>}
      {statusLoading && <p>Loading status…</p>}
      {statusError && <p data-testid="projection-status-error">{statusError}</p>}
      {status && !statusLoading && <div><span>Total questions: <strong>{status.total_questions}</strong></span>{" · "}<span>Unprojected: <strong>{status.unprojected_count}</strong></span>{Object.entries(status.projection_counts ?? {}).map(([key, value]) => value > 0 ? <span key={key}>{" · "}{key}: <strong>{value}</strong></span> : null)}{status.stale_projections?.length > 0 && <p>{status.stale_projections.length} stale — sync recommended.</p>}</div>}
      {previewError && <p data-testid="projection-preview-error">{previewError}</p>}
      {preview && <div data-testid="projection-preview-results">
        <div>Eligible: <strong>{preview.eligible_count}</strong>{" · "}Ineligible: <strong>{preview.ineligible_count}</strong>{" · "}Would create: <strong>{preview.would_create_count}</strong>{" · "}Would update: <strong>{preview.would_update_count}</strong></div>
        {blockerGroups.length > 0 && <div data-testid="projection-blocker-summary">{blockerGroups.map((group) => <span key={group.code} data-testid={`blocker-group-${group.code}`}><strong>{group.count}</strong> {group.label}{" · "}</span>)}<span><strong>{preview.eligible_count}</strong> eligible for projection</span></div>}
        {(preview.questions ?? []).map((row) => <div key={row.question_id} data-testid={`preview-row-${row.question_id}`}><span title={identity(row)}>{identity(row)}</span>{" — "}<span>{row.eligible ? (row.would_update ? "update" : "create / no change") : reasonText(row.reason)}</span></div>)}
      </div>}
      {result && <div data-testid="projection-sync-results"><div>Sync results — attempted: {result.attempted}{Object.entries(result.outcomes ?? {}).map(([key, value]) => value > 0 ? <span key={key}>{" · "}{key}: {value}</span> : null)}</div>{(result.questions ?? []).map((row) => <div key={row.question_id} data-testid={`sync-row-${row.question_id}`}><span title={identity(row)}>{identity(row)}</span>{" — "}<span>{row.outcome}</span></div>)}</div>}
    </section>
  );
}
