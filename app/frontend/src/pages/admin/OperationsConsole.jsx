import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { api, getApiUnverifiedFields } from "../../lib/api";
import useAdminAction from "../../features/admin/shared/useAdminAction";
import { computeProgress } from "../../features/admin/workflow/AdminProgressBar";
import CurrentActionCard from "../../features/admin/workflow/CurrentActionCard";
import AdminFixPanel from "../../features/admin/workflow/AdminFixPanel";
import DuplicateMergePreview from "../../features/admin/workflow/DuplicateMergePreview";
import SelectionContextBanner from "../../features/admin/workflow/SelectionContextBanner";
import useConflicts from "../../features/admin/workflow/useConflicts";
import { scoreToPct } from "../../features/admin/workflow/scoreUtils";
import { useToast } from "../../shared/ui/core";

// Filter ``key`` matches scrape_queue.status verbatim so the backend can do
// the filtering; ``approved`` is the storage value for a row that has been
// promoted into a recruitment draft. The label is always "Promoted" because
// "approved" leaks an internal state name and was confusable with publish.
const QUEUE_FILTERS = [
  { key: "pending", label: "Pending" },
  { key: "approved", label: "Promoted" },
  { key: "merged", label: "Merged" },
  { key: "duplicate", label: "Duplicate" },
  { key: "rejected", label: "Rejected" },
  { key: "all", label: "All" },
];

function tierForItem(item) {
  const tier = (item?.source_tier || "").toUpperCase();
  if (tier === "A" || tier === "B" || tier === "C") return tier;
  const kind = (item?.source_type || item?.source_kind || "").toLowerCase();
  if (kind === "aggregator") return "C";
  if (kind === "institutional") return "B";
  return "A";
}

function itemBadge(item) {
  const status = (item?.status || "pending").toLowerCase();
  if (status === "approved") return { cls: "badge resolved", text: "resolved" };
  if (status === "rejected") return { cls: "badge neutral", text: "rejected" };
  if (status === "duplicate") return { cls: "badge neutral", text: "duplicate" };
  if (status === "merged") return { cls: "badge info", text: "merged" };
  if ((item?.open_conflicts || 0) > 0) {
    return { cls: "badge blocker", text: "conflict" };
  }
  if (item?.unverified_fields?.length || item?.official_source_resolved === false) {
    return { cls: "badge blocker", text: "unresolved" };
  }
  if ((item?.duplicate_candidates || []).length) return { cls: "badge blocker", text: "conflict" };
  return { cls: "badge pending", text: "suggested" };
}

export default function OperationsConsole() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sourceId = searchParams.get("source_id") || null;
  const queueId = searchParams.get("queue_id") || null;
  const recruitmentId = searchParams.get("recruitment_id") || null;

  const [sources, setSources] = useState([]);
  const [runs, setRuns] = useState([]);
  const [queue, setQueue] = useState([]);
  const [recruitments, setRecruitments] = useState([]);
  const [validateResult, setValidateResult] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState(null);
  const [mergeTarget, setMergeTarget] = useState(null);
  const [conflictTarget, setConflictTarget] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [queueFilter, setQueueFilter] = useState(() => searchParams.get("queue_status") || "pending");
  const [leftView, setLeftView] = useState(() => (recruitmentId ? "drafts" : "candidates"));
  // Heavy per-item detail (extracted_data / raw_extracted_item / raw_html)
  // is stripped from the lightweight queue list; we hydrate it on demand
  // when an item is selected so the resolver can auto-detect host
  // candidates and the field-review panels have data to render.
  const [queueDetail, setQueueDetail] = useState(null);
  // Whether the targeted item_id fetch came back empty (the item is genuinely
  // gone — rejected/merged) vs merely absent from the first paged list (sorted
  // off-page). Only the former should clear the selection.
  const [queueDetailMissing, setQueueDetailMissing] = useState(false);
  // Bumped at the end of every loadAll so the detail hydration effect
  // re-runs after a reload (e.g. post-resolve, post-field-correction).
  const [reloadNonce, setReloadNonce] = useState(0);

  const { conflicts, refetch: refetchConflicts } = useConflicts(queueId);

  const { runAction, busyKey, error: actionError } = useAdminAction();
  const toast = useToast();
  const navigate = useNavigate();

  const updateParams = useCallback((next) => {
    const merged = new URLSearchParams(searchParams);
    Object.entries(next).forEach(([k, v]) => {
      if (v == null || v === "") merged.delete(k);
      else merged.set(k, String(v));
    });
    setSearchParams(merged, { replace: false });
  }, [searchParams, setSearchParams]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [s, r, q, recs] = await Promise.all([
        api.get("/api/admin/sources"),
        api.get("/api/admin/scrape/runs?limit=10"),
        api.get("/api/admin/scrape/queue?status=all&limit=50"),
        api.get("/api/admin/recruitments"),
      ]);
      setSources(s.items || []);
      setRuns(r.items || []);
      setQueue(q.items || []);
      setRecruitments(recs.items || []);
    } catch (e) {
      setLoadError(e);
    } finally {
      setLoading(false);
      setReloadNonce((n) => n + 1);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  // A field verify/correct/reject only changes the selected candidate's gate
  // state — sources, runs and recruitments are untouched. Refetch just the
  // queue (not the full loadAll fan-out) so one click is one read, not four.
  // Bumps reloadNonce so the selected item's detail re-hydrates.
  const reloadQueue = useCallback(async () => {
    try {
      const q = await api.get("/api/admin/scrape/queue?status=all&limit=50");
      setQueue(q.items || []);
    } catch {
      // Keep the prior list; the field write already succeeded.
    } finally {
      setReloadNonce((n) => n + 1);
    }
  }, []);

  // Detail hydration: fetch the full row for the selected queue item via
  // the include_detail path and stash the heavy fields. Re-runs when the
  // selection changes or after any loadAll (reloadNonce). Failure is
  // non-fatal — the resolver falls back to manual add.
  const hydrateQueueDetail = useCallback(async (id) => {
    if (!id) { setQueueDetail(null); setQueueDetailMissing(false); return; }
    try {
      // include_duplicates=false skips the live 400-row scan but still returns
      // the precomputed duplicate_candidates column — enough for the merge UI.
      // We stash the WHOLE row (not just heavy fields): when the selected item
      // sorts off the first queue page after a resolve (risky-first sort moves
      // resolved rows down), this targeted fetch is the only source for the
      // gate/status fields the workspace needs to keep rendering.
      const r = await api.get(
        `/api/admin/scrape/queue?status=all&include_detail=true&include_duplicates=false&item_id=${encodeURIComponent(id)}&limit=1`,
      );
      const full = (r.items || [])[0] || null;
      if (full && full.id === id) {
        setQueueDetail(full);
        setQueueDetailMissing(false);
      } else {
        // Empty result = the item is truly gone (rejected/merged), not just
        // off-page. Flag it so the selection-clear effect may run.
        setQueueDetail(null);
        setQueueDetailMissing(true);
      }
    } catch {
      // Network/transient error is NOT a 404 — keep any prior detail and do
      // not flag the item as missing, so a blip can't blank the workspace.
      setQueueDetailMissing(false);
    }
  }, []);

  useEffect(() => { hydrateQueueDetail(queueId); }, [queueId, reloadNonce, hydrateQueueDetail]);

  // Keep the segmented selector in sync with URL-driven selection. Opening
  // a recruitment via deep link should switch the rail to "drafts"; clearing
  // it should fall back to "candidates" unless the admin manually toggled.
  useEffect(() => {
    if (recruitmentId) setLeftView("drafts");
    else if (!queueId) setLeftView("candidates");
  }, [recruitmentId, queueId]);

  const selectedSource = useMemo(
    () => sources.find((s) => s.id === sourceId) || null,
    [sources, sourceId],
  );
  // When the selected item has sorted off the first queue page (e.g. after a
  // resolve flips official_source_resolved=true under the default risky-first
  // sort), the lightweight 50-row list no longer contains it. Prepend the
  // targeted detail row so the left rail keeps the selection visible and the
  // base-find below still resolves. No-op when the item is already on the page.
  const effectiveQueue = useMemo(() => {
    if (
      queueId && queueDetail && queueDetail.id === queueId
      && !queue.some((q) => q.id === queueId)
    ) {
      return [queueDetail, ...queue];
    }
    return queue;
  }, [queue, queueId, queueDetail]);

  const selectedQueueItem = useMemo(() => {
    const base = effectiveQueue.find((q) => q.id === queueId) || null;
    if (!base) return null;
    if (queueDetail && queueDetail.id === base.id) {
      // Overlay the heavy content + relational evidence/duplicate fields the
      // lightweight list omits. Gate/status fields (official_source_resolved,
      // unverified_fields, promotable, field_evidence_status) are NOT overlaid
      // so they stay from the freshest queue list — a stale detail snapshot
      // can't revert the gate. field_evidence_details / duplicate_candidates
      // are absent from the list, so they must come from the detail fetch
      // (which is re-run after every reload, so they stay fresh).
      return {
        ...base,
        extracted_data: base.extracted_data ?? queueDetail.extracted_data,
        raw_extracted_item: base.raw_extracted_item ?? queueDetail.raw_extracted_item ?? queueDetail.extracted_data,
        raw_html: base.raw_html ?? queueDetail.raw_html,
        raw_payload: base.raw_payload ?? queueDetail.raw_payload,
        field_evidence_details: queueDetail.field_evidence_details ?? base.field_evidence_details ?? [],
        duplicate_candidates: (base.duplicate_candidates && base.duplicate_candidates.length)
          ? base.duplicate_candidates
          : (queueDetail.duplicate_candidates ?? base.duplicate_candidates ?? []),
      };
    }
    return base;
  }, [effectiveQueue, queueId, queueDetail]);

  // P0-2 fallback: selection is URL-param driven and survives loadAll by
  // re-finding the id (in the list OR the targeted detail fetch). Clear the
  // param ONLY when the targeted item_id fetch came back empty
  // (queueDetailMissing) — i.e. the item is genuinely gone (rejected/merged).
  // A selected item that merely sorted off the first page is kept alive via
  // effectiveQueue, so it must NOT be cleared.
  useEffect(() => {
    if (loading) return;
    if (queueId && !selectedQueueItem && queueDetailMissing) {
      toast.info("That candidate is no longer in the queue. Selection cleared.");
      updateParams({ queue_id: null });
    }
  }, [loading, queueId, selectedQueueItem, queueDetailMissing, toast, updateParams]);
  const selectedRecruitment = useMemo(
    () => recruitments.find((r) => r.id === recruitmentId) || null,
    [recruitments, recruitmentId],
  );
  const latestRun = runs[0] || null;

  useEffect(() => {
    setValidateResult(null);
    if (!recruitmentId) return;
    let cancelled = false;
    api.post(`/api/admin/recruitments/${recruitmentId}/validate-publish`, {})
      .then((r) => { if (!cancelled) setValidateResult(r); })
      .catch(() => { if (!cancelled) setValidateResult(null); });
    return () => { cancelled = true; };
  }, [recruitmentId]);

  const progressState = useMemo(() => ({
    source: selectedSource,
    latestRun,
    queueItem: selectedQueueItem,
    recruitment: selectedRecruitment,
    validateResult,
    conflicts,
  }), [selectedSource, latestRun, selectedQueueItem, selectedRecruitment, validateResult, conflicts]);

  // CurrentActionCard primary button: focus the matching AdminFixPanel
  // section and scroll it into view. Setup-phase kinds switch to the
  // setup view; everything else lives in the queue/review workspace.
  const onPrimaryAction = useCallback((kind) => {
    // Running scrapes lives in the Scrape Monitor now; setup-phase prompts
    // hand off there. Everything else scrolls to its panel in this workspace.
    const setupKinds = new Set(["source_ready", "dry_scrape", "live_scrape"]);
    if (setupKinds.has(kind)) {
      navigate("/admin/scraper");
      return;
    }
    const anchorByKind = {
      attach_official_source: "official-source-quick-resolver",
      verify_fields: "queue-fix-section",
      resolve_conflicts: "fix-panel-conflicts",
      promote_to_draft: "promote-bar",
    };
    const testid = anchorByKind[kind] || "ops-workspace";
    const scroll = () => {
      if (typeof document === "undefined") return;
      const el = document.querySelector(`[data-testid="${testid}"]`)
        || document.querySelector('[data-testid="ops-workspace"]');
      el?.scrollIntoView?.({ behavior: "smooth", block: "start" });
    };
    if (typeof requestAnimationFrame === "function") requestAnimationFrame(scroll);
    else scroll();
  }, [navigate]);

  const queueFieldAction = useCallback(async (id, field, action, correctedValue, scope) => {
    await runAction({
      key: `field-${id}-${field}-${action}-${scope?.entity_key || ""}`,
      successMessage: `${field} ${action} saved.`,
      action: async () => {
        await api.post(`/api/admin/scrape/items/${id}/fields/${field}/${action}`, {
          notes: scope?.notes || "operations console",
          corrected_value: correctedValue,
          entity_type: scope?.entity_type || null,
          entity_key: scope?.entity_key || null,
        });
        await reloadQueue();
      },
    });
  }, [runAction, reloadQueue]);

  const promote = useCallback(async (item) => {
    await runAction({
      key: `promote-${item.id}`,
      successMessage: "Recruitment draft created. Next: validate publish readiness.",
      action: async () => {
        try {
          const r = await api.post(`/api/admin/scrape/items/${item.id}/promote`, {});
          setMsg(`Promoted to recruitment ${(r.recruitment_id || "unknown").slice(0, 8)}. No alerts sent.`);
          await loadAll();
          updateParams({ recruitment_id: r.recruitment_id });
        } catch (e) {
          const fields = getApiUnverifiedFields(e);
          if (fields.length) setMsg(`Promote blocked. Verify required fields: ${fields.join(", ")}.`);
          throw e;
        }
      },
    });
  }, [runAction, loadAll, updateParams]);

  const validate = useCallback(async (rec) => {
    await runAction({
      key: `validate-${rec.id}`,
      successMessage: "Validation refreshed.",
      action: async () => {
        const r = await api.post(`/api/admin/recruitments/${rec.id}/validate-publish`, {});
        setValidateResult(r);
      },
    });
  }, [runAction]);

  const verify = useCallback(async (rec) => {
    await runAction({
      key: `verify-${rec.id}`,
      confirm: `Mark "${rec.name}" verified?`,
      successMessage: "Recruitment marked verified.",
      action: async () => {
        await api.post(`/api/admin/recruitments/${rec.id}/verify`, {});
        await loadAll();
      },
    });
  }, [runAction, loadAll]);

  const publish = useCallback(async (rec) => {
    await runAction({
      key: `publish-${rec.id}`,
      confirm: `Publish "${rec.name}"? This triggers alerts.`,
      successMessage: "Recruitment published.",
      action: async () => {
        await api.post(`/api/admin/recruitments/${rec.id}/publish`, {});
        await loadAll();
      },
    });
  }, [runAction, loadAll]);

  const openMergePreview = useCallback((_item, dup) => {
    const targetId = dup?.recruitment_id || dup?.id;
    if (!targetId) return;
    setMergeTarget({ id: targetId, name: dup.name || dup.title || targetId });
  }, []);

  const confirmMerge = useCallback(async ({ force_fields }) => {
    if (!queueId || !mergeTarget?.id) return;
    await runAction({
      key: `merge-${queueId}-${mergeTarget.id}`,
      successMessage: "Merged into existing recruitment.",
      action: async () => {
        await api.post(`/api/admin/scrape/items/${queueId}/merge-into/${mergeTarget.id}`, { force_fields });
        setMergeTarget(null);
        await loadAll();
      },
    });
  }, [queueId, mergeTarget, runAction, loadAll]);

  const markDuplicate = useCallback(async (item, dup) => {
    const targetId = dup?.recruitment_id || dup?.id;
    if (!targetId) return;
    await runAction({
      key: `mark-dup-${item.id}`,
      confirm: `Mark "${item.recruitment || item.id}" as duplicate of "${dup.name || targetId}"?`,
      successMessage: "Marked as duplicate.",
      action: async () => {
        await api.post(`/api/admin/scrape/items/${item.id}/mark-duplicate`, { notes: `duplicate of ${targetId}` });
        await loadAll();
      },
    });
  }, [runAction, loadAll]);

  const rejectCandidate = useCallback((item) => {
    if (!item?.id) return;
    setRejectReason("");
    setRejectTarget(item);
  }, []);

  const reopenCandidate = useCallback(async (item) => {
    if (!item?.id) return;
    await runAction({
      key: `reopen-${item.id}`,
      confirm: `Reopen "${item.recruitment || item.id}" for review?`,
      successMessage: "Candidate reopened — back in the pending queue.",
      action: async () => {
        await api.post(`/api/admin/scrape/items/${item.id}/reopen`, {});
        await reloadQueue();
      },
    });
  }, [runAction, reloadQueue]);

  const confirmReject = useCallback(async () => {
    if (!rejectTarget?.id) return;
    const trimmed = (rejectReason || "").trim();
    if (!trimmed) { setMsg("Reject cancelled — reason is required."); return; }
    const target = rejectTarget;
    await runAction({
      key: `reject-${target.id}`,
      successMessage: "Candidate rejected.",
      action: async () => {
        await api.post(`/api/admin/scrape/items/${target.id}/reject`, { notes: trimmed });
        setRejectTarget(null);
        setRejectReason("");
        await loadAll();
      },
    });
  }, [rejectTarget, rejectReason, runAction, loadAll]);

  const resolveConflict = useCallback(async (payload) => {
    const conflictId = payload?.conflict_id || conflictTarget?.id;
    if (!conflictId) return;
    await runAction({
      key: `resolve-conflict-${conflictId}`,
      successMessage: "Conflict resolved. Promotion gate updated.",
      action: async () => {
        await api.post(`/api/admin/conflicts/${conflictId}/resolve`, {
          value: payload?.value,
          scope: payload?.scope,
          reason: payload?.reason,
          evidence_url: payload?.evidence_url,
          // Destructive-op confirmation the backend requires verbatim
          // (admin_conflicts.ResolveBody / CONFIRM_OVERRIDE). ConflictResolver
          // already enforces reason>=10 + a valid evidence URL, so this is the
          // only remaining required field; without it every resolve 422s.
          confirmation_text: "CONFIRM_OVERRIDE",
        });
        setConflictTarget(null);
        await refetchConflicts();
        await loadAll();
      },
    });
  }, [conflictTarget, runAction, refetchConflicts, loadAll]);

  const rejectConflict = useCallback(async (conflictId, body) => {
    if (!conflictId) return;
    await runAction({
      key: `reject-conflict-${conflictId}`,
      successMessage: "Conflict rejected.",
      action: async () => {
        await api.post(`/api/admin/conflicts/${conflictId}/reject`, {
          reason: body?.reason || "rejected by admin",
        });
        setConflictTarget(null);
        await refetchConflicts();
        await loadAll();
      },
    });
  }, [runAction, refetchConflicts, loadAll]);

  if (loading && !sources.length && !queue.length) {
    return (
      <div className="stack">
        <div className="skel" style={{ height: 90 }} />
        <div className="skel" style={{ height: 180 }} />
      </div>
    );
  }
  if (loadError) {
    return (
      <div className="card">
        <div className="card-body">
          <div className="err-row">Failed to load Operations · {loadError.message}</div>
          <div style={{ marginTop: 10 }}>
            <button className="btn small" onClick={loadAll}>Retry</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="admin-operations-console">
      <div className="scrn" style={{ borderTop: "none", paddingLeft: 0, paddingRight: 0 }}>
        {(
          <ReviewAndPublish
            progressState={progressState}
            selectedSource={selectedSource}
            selectedQueueItem={selectedQueueItem}
            selectedRecruitment={selectedRecruitment}
            queue={effectiveQueue}
            queueId={queueId}
            recruitmentId={recruitmentId}
            recruitments={recruitments}
            sources={sources}
            validateResult={validateResult}
            queueFilter={queueFilter}
            onQueueFilter={(value) => { setQueueFilter(value); updateParams({ queue_status: value === "pending" ? null : value }); }}
            onSelectQueue={(id) => updateParams({ queue_id: id, recruitment_id: null })}
            onSelectRecruitment={(id) => updateParams({ recruitment_id: id, queue_id: null })}
            leftView={leftView}
            onLeftView={setLeftView}
            onPrimaryAction={onPrimaryAction}
            onClearSource={() => updateParams({ source_id: null })}
            onClearQueue={() => updateParams({ queue_id: null })}
            onClearRecruitment={() => updateParams({ recruitment_id: null })}
            onQueueFieldAction={queueFieldAction}
            onPromote={promote}
            onMergeIntoExisting={openMergePreview}
            onMarkDuplicate={markDuplicate}
            onRejectCandidate={rejectCandidate}
            onReopenCandidate={reopenCandidate}
            onValidate={validate}
            onVerify={verify}
            onPublish={publish}
            mergeTarget={mergeTarget}
            onCloseMerge={() => setMergeTarget(null)}
            onSourcesChanged={loadAll}
            onConfirmMerge={confirmMerge}
            conflicts={conflicts}
            conflictTarget={conflictTarget}
            onOpenConflict={setConflictTarget}
            onResolveConflict={resolveConflict}
            onRejectConflict={rejectConflict}
            onCloseConflict={() => setConflictTarget(null)}
            busy={Boolean(busyKey)}
            msg={msg}
            actionError={actionError}
          />
        )}
      </div>
      <RejectCandidateDialog
        open={Boolean(rejectTarget)}
        item={rejectTarget}
        reason={rejectReason}
        onReasonChange={setRejectReason}
        onCancel={() => { setRejectTarget(null); setRejectReason(""); }}
        onConfirm={confirmReject}
        busy={Boolean(busyKey)}
      />
    </div>
  );
}

function RejectCandidateDialog({ open, item, reason, onReasonChange, onCancel, onConfirm, busy }) {
  if (!open || !item) return null;
  const title = item.recruitment || item.id;
  const trimmed = (reason || "").trim();
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ops-reject-title"
      data-testid="ops-reject-dialog"
    >
      <div className="absolute inset-0" onClick={onCancel} />
      <div className="card" style={{ position: "relative", maxWidth: 460, width: "90%" }}>
        <div className="card-head-col">
          <div className="lbl">Reject candidate</div>
          <h3 id="ops-reject-title" className="oc-title" style={{ fontSize: 17 }}>{title}</h3>
        </div>
        <div className="card-body stack">
          <div className="anno">A reason is required. It is recorded in the audit log.</div>
          <textarea
            className="input"
            value={reason}
            onChange={(e) => onReasonChange(e.target.value)}
            placeholder="Why is this candidate being rejected?"
            data-testid="ops-reject-reason"
            autoFocus
            style={{ minHeight: 90 }}
          />
        </div>
        <div className="card-foot">
          <button type="button" className="btn ghost small" onClick={onCancel} disabled={busy}>Cancel</button>
          <button
            type="button"
            className="btn primary small"
            onClick={onConfirm}
            disabled={busy || !trimmed}
            data-testid="ops-reject-confirm"
          >
            {busy ? "Rejecting…" : "Reject candidate"}
          </button>
        </div>
      </div>
    </div>
  );
}


function ReviewAndPublish({
  progressState, selectedSource, selectedQueueItem, selectedRecruitment,
  queue, queueId, recruitmentId, recruitments, sources, validateResult,
  queueFilter, onQueueFilter, onSelectQueue, onSelectRecruitment,
  onClearSource, onClearQueue, onClearRecruitment,
  onQueueFieldAction,
  onPromote, onMergeIntoExisting, onMarkDuplicate, onRejectCandidate, onReopenCandidate,
  onValidate, onVerify, onPublish,
  mergeTarget, onCloseMerge,
  onSourcesChanged, onConfirmMerge,
  conflicts, conflictTarget, onOpenConflict, onResolveConflict, onRejectConflict, onCloseConflict,
  busy, msg, actionError,
  leftView, onLeftView, onPrimaryAction,
}) {
  const progress = computeProgress(progressState);
  return (
    <>
      <section className="scrn" style={{ padding: "0 0 18px", border: "none" }}>
        <div className="scrn-head">
          <h3 className="oc-title">Review pipeline state</h3>
          <span className="scrn-tag">current action + selection context</span>
        </div>
        <div className="stack">
          <CurrentActionCard progress={progress} onPrimaryAction={onPrimaryAction} />
          <SelectionContextBanner
            source={selectedSource}
            queueItem={selectedQueueItem}
            recruitment={selectedRecruitment}
            onClearSource={onClearSource}
            onClearQueue={onClearQueue}
            onClearRecruitment={onClearRecruitment}
          />
          {msg ? <div className="warn-row" data-testid="ops-msg">{msg}</div> : null}
          {actionError ? <div className="err-row">{actionError.message}</div> : null}
        </div>
      </section>

      <section className="scrn" style={{ borderTop: "1px solid var(--rule)" }}>
        <div className="scrn-head">
          <h3 className="oc-title">Workspace</h3>
          <span className="scrn-tag">queue · fix panel</span>
        </div>
        <div className="grid" style={{ display: "grid", gridTemplateColumns: "minmax(280px, 340px) 1fr", gap: 16 }}>
          <div className="stack" data-testid="ops-left-column">
            <div
              className="oc-segmented"
              role="tablist"
              aria-label="Left rail selection"
              data-testid="ops-left-segmented"
            >
              <button
                type="button"
                role="tab"
                aria-selected={leftView === "candidates"}
                className={`oc-segmented__option${leftView === "candidates" ? " active" : ""}`}
                onClick={() => onLeftView("candidates")}
                data-testid="ops-left-tab-candidates"
              >
                Candidates
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={leftView === "drafts"}
                className={`oc-segmented__option${leftView === "drafts" ? " active" : ""}`}
                onClick={() => onLeftView("drafts")}
                data-testid="ops-left-tab-drafts"
              >
                Drafts
              </button>
            </div>

            {leftView === "candidates" ? (
              <div className="card" data-testid="ops-left-candidates">
                <div className="filter-bar">
                  <label className="sr-only" htmlFor="ops-queue-status">Filter candidates by status</label>
                  <select
                    id="ops-queue-status"
                    className="input"
                    value={queueFilter}
                    onChange={(e) => onQueueFilter(e.target.value)}
                    data-testid="ops-queue-status"
                    style={{ fontSize: 12, padding: "4px 8px" }}
                  >
                    {QUEUE_FILTERS.map((f) => (
                      <option key={f.key} value={f.key}>{f.label}</option>
                    ))}
                  </select>
                </div>
                <QueueList items={queue} filter={queueFilter} selectedId={queueId} onSelect={onSelectQueue} />
              </div>
            ) : (
              <div data-testid="ops-left-drafts">
                <RecruitmentList items={recruitments} selectedId={recruitmentId} onSelect={onSelectRecruitment} />
              </div>
            )}
          </div>

          <div className="stack" data-testid="ops-workspace">
            <AdminFixPanel
              queueItem={selectedQueueItem}
              recruitment={selectedRecruitment}
              validateResult={validateResult}
              sources={sources}
              conflicts={conflicts}
              conflictTarget={conflictTarget}
              onQueueFieldAction={onQueueFieldAction}
              onPromote={onPromote}
              onMergeIntoExisting={onMergeIntoExisting}
              onMarkDuplicate={onMarkDuplicate}
              onRejectCandidate={onRejectCandidate}
              onReopenCandidate={onReopenCandidate}
              onValidate={onValidate}
              onVerify={onVerify}
              onPublish={onPublish}
              onSourcesChanged={onSourcesChanged}
              onOpenConflict={onOpenConflict}
              onResolveConflict={onResolveConflict}
              onRejectConflict={onRejectConflict}
              onCloseConflict={onCloseConflict}
              busy={busy}
            />
            <DuplicateMergePreview
              open={Boolean(mergeTarget && queueId)}
              queueId={queueId}
              recruitment={mergeTarget}
              busy={busy}
              onClose={onCloseMerge}
              onConfirmMerge={onConfirmMerge}
            />
          </div>
        </div>
      </section>
    </>
  );
}

function QueueList({ items, filter, selectedId, onSelect }) {
  const filtered = filter === "all" ? items : items.filter((q) => (q.status || "pending") === filter);
  if (filtered.length === 0) {
    return <div className="empty"><div className="empty-title">No queue items</div>No items in this view.</div>;
  }
  return (
    <div className="qlist" style={{ maxHeight: "60vh", overflowY: "auto" }}>
      {filtered.map((q) => {
        const conf = scoreToPct(q.confidence_score ?? q.confidence);
        const quality = scoreToPct(q.data_quality_score);
        const tier = tierForItem(q);
        const status = itemBadge(q);
        const title = q.recruitment || q.extracted_data?.title || q.source_name || q.id;
        const action = q.status === "approved" ? "→ already promoted"
          : status.text === "unresolved" ? "→ resolve official source"
          : status.text === "conflict" ? "→ resolve conflict"
          : status.text === "suggested" ? "→ confirm suggested proof"
          : "→ review";
        return (
          <button
            key={q.id}
            type="button"
            className={`qitem${selectedId === q.id ? " selected" : ""}`}
            onClick={() => onSelect(q.id)}
            data-testid={`ops-queue-${q.id}`}
          >
            <div className="row" style={{ gap: 5 }}>
              <span className={`badge tier-${tier.toLowerCase()}`}>{tier}</span>
              <span className={status.cls}>{status.text}</span>
            </div>
            <div className="qttl">{title}</div>
            <div className="qsub">
              {q.source_name || q.source || "—"}
              {conf != null ? ` · conf ${(conf / 100).toFixed(2)}` : ""}
              {quality != null ? ` · quality ${quality}%` : ""}
            </div>
            <div className="qaction">{action}</div>
          </button>
        );
      })}
    </div>
  );
}

function RecruitmentList({ items, selectedId, onSelect }) {
  if (!items.length) {
    return (
      <section className="card">
        <div className="card-body">
          <div className="empty"><div className="empty-title">No drafts</div>No recruitment drafts yet.</div>
        </div>
      </section>
    );
  }
  return (
    <section className="card">
      <div className="card-head">
        <h4 className="oc-title">Recruitments</h4>
        <span className="row-sub">{items.length}</span>
      </div>
      <div className="qlist" style={{ maxHeight: "40vh", overflowY: "auto" }}>
        {items.map((r) => (
          <button
            key={r.id}
            type="button"
            className={`qitem${selectedId === r.id ? " selected" : ""}`}
            onClick={() => onSelect(r.id)}
            data-testid={`ops-recruitment-${r.id}`}
          >
            <div className="qttl">{r.name}</div>
            <div className="qsub">
              {r.publish_status || "draft"} · {(r.blocking_issues || []).length} blocker{(r.blocking_issues || []).length === 1 ? "" : "s"}
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
