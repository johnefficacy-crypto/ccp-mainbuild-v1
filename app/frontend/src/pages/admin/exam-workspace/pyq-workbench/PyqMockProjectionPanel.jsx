import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../../../lib/api";
import useApiAction from "../../../../lib/hooks/useApiAction";

const base = (id) => `/api/admin/mocks/pyq-papers/${id}/projection`;
const ui = {
  preview: "text-xs px-2.5 py-1 rounded border border-gray-300 text-gray-600 hover:bg-white disabled:opacity-50",
  sync: "text-xs px-2.5 py-1 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 disabled:opacity-50",
  input: "flex-1 text-xs px-2 py-1 rounded border border-gray-300 focus:outline-none focus:ring-1 focus:ring-indigo-300",
  card: "mt-3 border border-gray-200 rounded bg-white",
  row: "px-3 py-1.5 flex items-center justify-between gap-2 text-xs",
};

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

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      scope.current = { ...scope.current, version: scope.current.version + 1 };
    };
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
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">Mock projection</span>
        <button type="button" onClick={loadPreview} disabled={previewLoading} className={ui.preview} data-testid="projection-preview-btn">{previewLoading ? "Loading…" : "Preview"}</button>
      </div>
      <details className="mb-2 text-xs text-gray-500" data-testid="projection-info-disclosure">
        <summary className="cursor-pointer select-none text-gray-600">ⓘ What gets projected?</summary>
        <p className="mt-1 leading-relaxed">Projection requires a verified paper and question, MCQ type, non-empty question and verified option text, at least two verified options, exactly one verified correct option, a matching correct-option reference, and exactly one verified primary topic tag. Preview shows what would change; Sync writes eligible questions.</p>
      </details>
      <div className="flex gap-2 mb-2">
        <input value={auditReason} onChange={(e) => setAuditReason(e.target.value)} placeholder="Audit reason (min 8 chars)" maxLength={500} className={ui.input} data-testid="projection-audit-reason-input" />
        <button type="button" onClick={sync} disabled={syncing || auditReason.trim().length < 8 || zeroEligible} className={ui.sync} data-testid="projection-sync-btn">{syncing ? "Syncing…" : "Sync to mock bank"}</button>
      </div>
      {zeroEligible && <p className="text-xs text-amber-600 mb-2" data-testid="projection-zero-eligible-note">0 eligible for projection — sync is disabled until at least one question clears the blockers.</p>}
      {statusLoading && <p className="text-xs text-gray-400">Loading status…</p>}
      {statusError && <p className="text-xs text-rose-600" data-testid="projection-status-error">{statusError}</p>}
      {status && !statusLoading && <div className="text-xs text-gray-600 space-y-1"><span>Total questions: <strong>{status.total_questions}</strong></span>{" · "}<span>Unprojected: <strong>{status.unprojected_count}</strong></span>{Object.entries(status.projection_counts ?? {}).map(([key, value]) => value > 0 ? <span key={key}>{" · "}{key}: <strong>{value}</strong></span> : null)}{status.stale_projections?.length > 0 && <p className="text-amber-600">{status.stale_projections.length} stale — sync recommended.</p>}</div>}
      {previewError && <p className="text-xs text-rose-600 mt-1" data-testid="projection-preview-error">{previewError}</p>}
      {preview && <div className={ui.card} data-testid="projection-preview-results">
        <div className="px-3 py-2 border-b border-gray-100 text-xs text-gray-600">Eligible: <strong>{preview.eligible_count}</strong>{" · "}Ineligible: <strong>{preview.ineligible_count}</strong>{" · "}Would create: <strong>{preview.would_create_count}</strong>{" · "}Would update: <strong>{preview.would_update_count}</strong></div>
        {blockerGroups.length > 0 && <div className="px-3 py-2 border-b border-gray-100 flex flex-wrap gap-x-4 text-xs" data-testid="projection-blocker-summary">{blockerGroups.map((group) => <span key={group.code} className="text-amber-700" data-testid={`blocker-group-${group.code}`}><strong>{group.count}</strong> {group.label}</span>)}<span className="text-gray-500"><strong>{preview.eligible_count}</strong> eligible for projection</span></div>}
        <div className="max-h-40 overflow-y-auto divide-y divide-gray-50">{(preview.questions ?? []).map((row) => <div key={row.question_id} className={ui.row} data-testid={`preview-row-${row.question_id}`}><span className="text-gray-700 truncate max-w-[60%]" title={identity(row)}>{identity(row)}</span><span className={row.eligible ? "text-gray-600" : "text-amber-600"}>{row.eligible ? (row.would_update ? "update" : "create / no change") : reasonText(row.reason)}</span></div>)}</div>
      </div>}
      {result && <div className={ui.card} data-testid="projection-sync-results"><div className="px-3 py-2 border-b border-gray-100 text-xs text-gray-600">Sync results — attempted: {result.attempted}{Object.entries(result.outcomes ?? {}).map(([key, value]) => value > 0 ? <span key={key}>{" · "}{key}: {value}</span> : null)}</div><div className="max-h-40 overflow-y-auto divide-y divide-gray-50">{(result.questions ?? []).map((row) => <div key={row.question_id} className={ui.row} data-testid={`sync-row-${row.question_id}`}><span className="text-gray-700 truncate max-w-[60%]" title={identity(row)}>{identity(row)}</span><span>{row.outcome}</span></div>)}</div></div>}
    </section>
  );
}
