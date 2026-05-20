import React, { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Filter, Pencil, Plus, Search, ShieldCheck, X } from "lucide-react";
import SourceHealthBadge from "../../features/admin/sources/SourceHealthBadge";
import { api } from "../../lib/api";
import NextActionCallout from "../../features/admin/workflow/NextActionCallout";
import { NEXT_ACTION_MESSAGES, SOURCE_TYPE_LABELS } from "../../features/admin/workflow/adminWorkflowContract";
import { useFocusTrap } from "../../shared/a11y/useFocusTrap";
import { EmptyState, ErrorState, LoadingSkeleton, RowActions } from "../../shared/ui";
import useAdminAction from "../../features/admin/shared/useAdminAction";
import AuditTimelineDrawer from "../../features/admin/shared/AuditTimelineDrawer";
import { adminTrustService } from "../../services/adminTrustService";

const SOURCE_TYPES = Object.entries(SOURCE_TYPE_LABELS).map(([value, label]) => ({ value, label }));

const EMPTY_FORM = {
  source_name: "",
  official_url: "",
  source_type: "",
  is_active: true,
  is_verified: false,
  tier: "",
  category: "",
  max_items_per_run: 25,
  rate_limit_seconds: 5,
  timeout_seconds: 15,
  include_patterns: "",
  exclude_patterns: "",
  allowed_domains: "",
  notes: "",
};

function splitLines(value) {
  return String(value || "").split(/\n|,/).map((x) => x.trim()).filter(Boolean);
}

function sourceToForm(source) {
  const scrape = source?.scrape_config || {};
  const adapter = source?.adapter_config || {};
  return {
    ...EMPTY_FORM,
    source_name: source?.org || source?.source_name || "",
    official_url: source?.official_url || source?.source_url || source?.url || "",
    source_type: source?.source_type || source?.kind || "",
    is_active: source?.is_active !== false,
    is_verified: !!source?.is_verified,
    tier: source?.tier || "",
    category: source?.category || "",
    max_items_per_run: scrape.max_items_per_run || 25,
    rate_limit_seconds: scrape.rate_limit_seconds || 5,
    timeout_seconds: scrape.timeout_seconds || 15,
    include_patterns: (adapter.include_patterns || []).join("\n"),
    exclude_patterns: (adapter.exclude_patterns || []).join("\n"),
    allowed_domains: (adapter.allowed_domains || []).join("\n"),
    notes: source?.notes || "",
  };
}

function buildPayload(form) {
  if (!form.source_type) throw new Error("Select a source type before saving.");
  const isAggregator = form.source_type === "aggregator";
  // ``is_verified`` is intentionally not sent from this form. Trust is a
  // decision, not a form bit: it must come from POST /api/admin/sources/
  // {id}/verify, which runs the backend trust evaluator. Preserve the
  // existing flag on edit so a save here does not clobber prior verification.
  // Send only ``official_url`` — the backend mirrors it to the legacy
  // ``source_url`` column so older readers keep working. Stopping the
  // double-write here removes the schema-drift smell that asked
  // reviewers to wonder which field was authoritative.
  // is_verified / is_official_source are intentionally omitted: trust is
  // decided by POST /api/admin/sources/{id}/verify, which runs the backend
  // trust evaluator. Sending them from this form would let the admin tick a
  // checkbox to bypass the URL/domain checks, which is the exact mistake
  // the verify action exists to prevent.
  return {
    source_name: form.source_name.trim(),
    official_url: form.official_url.trim(),
    source_type: form.source_type,
    is_active: !!form.is_active,
    tier: form.tier === "" ? null : Number(form.tier),
    category: form.category || (isAggregator ? "aggregator" : null),
    notes: form.notes,
    discovery_only: isAggregator,
    can_publish_directly: false,
    requires_official_confirmation: isAggregator,
    scrape_config: {
      max_items_per_run: Number(form.max_items_per_run) || 25,
      rate_limit_seconds: Number(form.rate_limit_seconds) || 0,
      timeout_seconds: Number(form.timeout_seconds) || 15,
    },
    trust_config: {
      manual_review_required: true,
      requires_official_source: isAggregator,
      evidence_required: true,
      auto_promote: false,
      discovery_only: isAggregator,
    },
    adapter_config: {
      include_patterns: splitLines(form.include_patterns),
      exclude_patterns: splitLines(form.exclude_patterns),
      allowed_domains: splitLines(form.allowed_domains),
    },
  };
}

function SourceFormDrawer({ open, mode, form, setForm, busy, error, onClose, onSubmit }) {
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  useFocusTrap({ active: open, containerRef: panelRef, onEscape: onClose, initialFocusRef: closeRef });
  if (!open) return null;

  const isAggregator = form.source_type === "aggregator";
  const updateType = (source_type) => {
    setForm((current) => ({
      ...current,
      source_type,
      is_verified: source_type === "aggregator" ? false : current.is_verified,
      category: source_type === "aggregator" ? "aggregator" : current.category,
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <div className="absolute inset-0" onClick={onClose} />
      <aside ref={panelRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="source-form-title" className="relative h-full w-full max-w-2xl overflow-auto border-l border-border bg-[#FBF6EF] p-5 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Source registry</div>
            <h2 id="source-form-title" className="font-heading text-2xl">{mode === "edit" ? "Editing source" : "Add source"}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{mode === "edit" ? `${form.source_name || "Unnamed source"} · ${sourceTypeLabel(form.source_type)} · ${form.is_active ? "active" : "inactive"} · ${form.is_verified ? "verified" : "unverified"}` : "Define where scraper can discover recruitment candidates."}</p>
          </div>
          <button ref={closeRef} type="button" className="btn btn-ghost h-9 w-9 p-0" onClick={onClose} aria-label="Close source form"><X className="h-4 w-4" /></button>
        </div>

        {isAggregator && (
          <div className="mt-4 flex gap-3 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>Aggregator sources are discovery-only. They can find candidates but cannot be used as final official proof.</div>
          </div>
        )}

        {error && <div className="mt-4 rounded-xl border border-destructive/30 bg-white/70 p-3 text-sm text-destructive">{error}</div>}

        {/* Identity — what this source is and where it lives */}
        <FormSection label="Identity">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Source name"><input className="input" value={form.source_name} onChange={(e) => setForm({ ...form, source_name: e.target.value })} /></Field>
            <Field label="Source type">
              <select className="input" value={form.source_type} onChange={(e) => updateType(e.target.value)} required>
                <option value="">Select source type</option>
                {SOURCE_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
              </select>
            </Field>
            <div className="sm:col-span-2">
              <Field label="Official URL"><input className="input" value={form.official_url} onChange={(e) => setForm({ ...form, official_url: e.target.value })} /></Field>
            </div>
          </div>
        </FormSection>

        {/* Run configuration — how the scraper hits this source */}
        <FormSection label="Run configuration">
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Max items / run"><input className="input" type="number" min="1" max="100" value={form.max_items_per_run} onChange={(e) => setForm({ ...form, max_items_per_run: e.target.value })} /></Field>
            <Field label="Rate limit (s)"><input className="input" type="number" min="0" value={form.rate_limit_seconds} onChange={(e) => setForm({ ...form, rate_limit_seconds: e.target.value })} /></Field>
            <Field label="Timeout (s)"><input className="input" type="number" min="1" value={form.timeout_seconds} onChange={(e) => setForm({ ...form, timeout_seconds: e.target.value })} /></Field>
          </div>
        </FormSection>

        <FormSection label="Notes">
          <Field label="Internal notes"><textarea className="input min-h-[80px]" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
        </FormSection>

        <details className="mt-5 rounded-xl border border-border bg-white/50 p-3">
          <summary className="cursor-pointer text-sm font-semibold">Advanced — crawler rules &amp; internals</summary>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label="Trust tier" help="Optional numeric ordering; trust itself is set by the Verify action."><input className="input" type="number" value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })} /></Field>
            <Field label="Source role / category"><input className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></Field>
            <Field label="Only follow links matching these patterns" help="Examples: recruitment, vacancy, notification, apply-online"><textarea className="input min-h-[80px]" value={form.include_patterns} onChange={(e) => setForm({ ...form, include_patterns: e.target.value })} /></Field>
            <Field label="Ignore links matching these patterns" help="Examples: login, syllabus, admit-card, result, handbook, user_manual"><textarea className="input min-h-[80px]" value={form.exclude_patterns} onChange={(e) => setForm({ ...form, exclude_patterns: e.target.value })} /></Field>
            <div className="sm:col-span-2">
              <Field label="Allowed domains for discovered links" help="Examples: ncs.gov.in, indgovtjobs.net"><textarea className="input min-h-[80px]" value={form.allowed_domains} onChange={(e) => setForm({ ...form, allowed_domains: e.target.value })} /></Field>
            </div>
          </div>
        </details>

        {/* Status — activation + read-only trust note (trust is set via Verify) */}
        <FormSection label="Status">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="soft-card flex items-center justify-between rounded-xl p-3 text-sm">
              <span>Active</span>
              <input type="checkbox" checked={!!form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
            </label>
            <div className="soft-card flex items-center justify-between rounded-xl p-3 text-sm">
              <span>Trust</span>
              {isAggregator ? (
                <span className="pill pill-amber">Discovery only</span>
              ) : form.is_verified ? (
                <span className="pill pill-sage">Verified official source</span>
              ) : (
                <span className="pill" title="Save the source, then run the Verify action to perform the trust check.">Not verified — use Verify action</span>
              )}
            </div>
          </div>
        </FormSection>

        <div className="mt-6 flex justify-end gap-2">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={onSubmit}>{busy ? "Saving..." : "Save source"}</button>
        </div>
        <style>{`.input { width:100%; padding: 0.55rem 0.85rem; border-radius: 0.75rem; background: rgba(255,255,255,0.85); border: 1px solid hsl(var(--border)); font-size: 14px; }`}</style>
      </aside>
    </div>
  );
}

function SourceDetailsDialog({ source, result, onEdit, onClose }) {
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  useFocusTrap({ active: !!source, containerRef: panelRef, onEscape: onClose, initialFocusRef: closeRef });
  if (!source) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <div className="absolute inset-0" onClick={onClose} />
      <aside ref={panelRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="source-details-title" className="relative h-full w-full max-w-xl overflow-auto border-l border-border bg-[#FBF6EF] p-5">
        <div className="flex items-start justify-between gap-3">
          <h2 id="source-details-title" className="font-heading text-2xl">{source.org || source.source_name} details</h2>
          <button ref={closeRef} className="btn btn-ghost h-9 w-9 p-0" onClick={onClose} aria-label="Close details"><X className="h-4 w-4" /></button>
        </div>
        <div className="mt-4 space-y-4 text-sm">
          {/* Decision summary first: can I trust and scrape this source? */}
          <section className="rounded-xl border border-border bg-white/60 p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="text-[11px] uppercase tracking-widest text-muted-foreground">Status &amp; health</div>
              <SourceHealthBadge source={source} />
            </div>
            <div className="mt-2 grid gap-3 sm:grid-cols-3">
              <Detail label="Verified" value={source.is_verified ? "Yes" : "No"} />
              <Detail label="Active" value={source.is_active === false ? "No" : "Yes"} />
              <Detail label="Trust policy" value={source.source_type === "aggregator" ? "Discovery only" : "Official candidate"} />
              <Detail label="Last success" value={source.last_success_at || "never"} />
              <Detail label="Consecutive fails" value={source.consecutive_fails || 0} />
              <Detail label="Currently scraping" value={source.currently_scraping_at ? `since ${source.currently_scraping_at}` : "no"} />
            </div>
            {(source.last_error || source.last_error_detail) ? (
              <div className="mt-2 rounded-lg border border-rose-200 bg-rose-50 p-2 text-[11px] text-rose-900">
                Last error{source.last_error_class ? ` (${source.last_error_class})` : ""}: {source.last_error_detail || source.last_error}
              </div>
            ) : null}
          </section>

          <section>
            <div className="mb-2 text-[11px] uppercase tracking-widest text-muted-foreground">What gets fetched</div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Detail label="Type" value={source.source_type || source.kind} />
              <Detail label="Adapter" value={source.adapter_type || "html"} />
              <Detail label="Fetch URL (used by runner)" value={primaryFetchUrl(source)} />
              <Detail label="Official URL" value={source.official_url} />
              <Detail label="Notification URL" value={source.notification_url} />
            </div>
          </section>

          <section>
            <div className="mb-2 text-[11px] uppercase tracking-widest text-muted-foreground">Run configuration</div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Detail label="Max items" value={source.scrape_config?.max_items_per_run} />
              <Detail label="Rate limit" value={source.scrape_config?.rate_limit_seconds ? `${source.scrape_config.rate_limit_seconds}s` : null} />
              <Detail label="Timeout" value={source.scrape_config?.timeout_seconds ? `${source.scrape_config.timeout_seconds}s` : null} />
              <Detail label="Listing cache" value={source.has_listing_cache ? "active (304 short-circuit)" : "cold"} />
              <Detail label="Listing last-modified" value={source.last_listing_modified} />
            </div>
          </section>

          {source.notes ? <Detail label="Notes" value={source.notes} /> : null}

          <details className="rounded-xl border border-border bg-white/60 p-3">
            <summary className="cursor-pointer text-xs font-semibold">Configuration JSON</summary>
            <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words text-[11px]">{JSON.stringify({ scrape_config: source.scrape_config, trust_config: source.trust_config, adapter_config: source.adapter_config }, null, 2)}</pre>
          </details>
          {result ? (
            <details className="rounded-xl border border-border bg-white/70 p-3">
              <summary className="cursor-pointer text-xs font-semibold">Last verification result</summary>
              <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words text-[11px]">{JSON.stringify(result, null, 2)}</pre>
            </details>
          ) : null}
        </div>
        <div className="mt-5 flex justify-end">
          <button className="btn btn-primary" onClick={() => onEdit(source)}><Pencil className="h-4 w-4" /> Edit source</button>
        </div>
      </aside>
    </div>
  );
}

export default function AdminSources() {
  const [items, setItems] = useState([]);
  const [resultById, setResultById] = useState({});
  const [selectedDetails, setSelectedDetails] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editing, setEditing] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(true);
  const [auditTarget, setAuditTarget] = useState(null);
  const [auditItems, setAuditItems] = useState([]);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [policyFilter, setPolicyFilter] = useState("all");
  const { runAction, busyKey, error: actionError } = useAdminAction();

  const load = async () => {
    setLoading(true); setError(null);
    try { const d = await api.get("/api/admin/sources"); setItems(d.items || []); } catch (e) { setError(e); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const openCreate = () => { setEditing(null); setForm(EMPTY_FORM); setFormError(""); setFormOpen(true); };
  const openEdit = (source) => { setEditing(source); setForm(sourceToForm(source)); setFormError(""); setFormOpen(true); setSelectedDetails(null); };
  const closeForm = () => { setFormOpen(false); setEditing(null); setFormError(""); };

  const save = async () => {
    setFormError("");
    let payload;
    try {
      payload = buildPayload(form);
    } catch (e) {
      setFormError(e.message);
      return;
    }
    const key = editing ? `update-${editing.id}` : "create";
    await runAction({
      key,
      successMessage: editing ? "Source updated" : "Source created. Next: verify source or run dry scrape if already trusted.",
      action: async () => {
        if (editing) await api.put(`/api/admin/sources/${editing.id}`, payload);
        else await api.post("/api/admin/sources", payload);
        closeForm();
        await load();
      },
    });
  };

  const verify = async (source) => runAction({ key: `verify-${source.id}`, successMessage: "Source verified. Next: use Scraper to discover candidates.", errorMessage: "Source verification failed. Review backend warnings/errors and fix the source URL or trust policy.", action: async () => { const r = await api.post(`/api/admin/sources/${source.id}/verify`, {}); setResultById((x) => ({ ...x, [source.id]: r })); await load(); } });
  const toggle = async (id, on) => runAction({ key: `${on ? "deactivate" : "activate"}-${id}`, confirm: `${on ? "Deactivate" : "Activate"} this source?`, successMessage: `Source ${on ? "deactivated" : "activated"}`, action: async () => { await api.post(`/api/admin/sources/${id}/${on ? "deactivate" : "activate"}`, {}); await load(); } });
  const summary = useMemo(() => ({
    total: items.length,
    active: items.filter((i) => i.is_active !== false).length,
    needsReview: items.filter((i) => i.verification_status === "needs_review").length,
    failed: items.filter((i) => (i.consecutive_fails || 0) > 0 || i.last_error).length,
    aggregators: items.filter((i) => i.source_type === "aggregator").length,
  }), [items]);
  const showHistory = async (s) => { const d = await adminTrustService.sourceAudit(s.id); setAuditItems(d.items || []); setAuditTarget(s); };
  const typeOptions = useMemo(() => Array.from(new Set(items.map((i) => i.source_type || i.kind).filter(Boolean))), [items]);
  const filteredItems = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return items.filter((source) => {
      const sourceType = source.source_type || source.kind || "";
      const haystack = `${source.org || source.source_name || ""} ${source.official_url || source.url || ""} ${sourceType} ${source.notes || ""}`.toLowerCase();
      const matchesText = !needle || haystack.includes(needle);
      const matchesType = typeFilter === "all" || sourceType === typeFilter;
      const matchesPolicy =
        policyFilter === "all"
        || (policyFilter === "active" && source.is_active !== false)
        || (policyFilter === "discovery" && sourceType === "aggregator")
        || (policyFilter === "official_verified" && sourceType !== "aggregator" && source.is_verified)
        || (policyFilter === "inactive" && source.is_active === false)
        || (policyFilter === "failed" && ((source.consecutive_fails || 0) > 0 || source.last_error))
        || (policyFilter === "review" && source.verification_status === "needs_review");
      return matchesText && matchesType && matchesPolicy;
    });
  }, [items, policyFilter, query, typeFilter]);
  const workflowMessage = useMemo(() => {
    const unverifiedOfficial = items.some((source) => (source.source_type || source.kind) !== "aggregator" && !source.is_verified);
    if (unverifiedOfficial) return NEXT_ACTION_MESSAGES.sourceVerify;
    if (items.some((source) => (source.source_type || source.kind) === "aggregator")) return NEXT_ACTION_MESSAGES.aggregatorDiscovery;
    return NEXT_ACTION_MESSAGES.runDryScrape;
  }, [items]);

  return (
    <div className="space-y-4" data-testid="admin-sources">
      <NextActionCallout message={workflowMessage} href="/admin/scraper" actionLabel="Open Scraper" tone={workflowMessage === NEXT_ACTION_MESSAGES.aggregatorDiscovery ? "warn" : "info"} />
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-heading text-3xl">Sources trust</h1>
          <p className="text-sm text-muted-foreground">Aggregator sources discover candidates only; official provenance is still required before publishing.</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}><Plus className="h-4 w-4" /> Add source</button>
      </div>
      <div className="grid gap-3 text-sm md:grid-cols-5">
        <Metric label="Total" value={summary.total} filterKey="all" active={policyFilter === "all"} onSelect={setPolicyFilter} />
        <Metric label="Active" value={summary.active} filterKey="active" active={policyFilter === "active"} onSelect={setPolicyFilter} />
        <Metric label="Needs review" value={summary.needsReview} tone="warn" filterKey="review" active={policyFilter === "review"} onSelect={setPolicyFilter} />
        <Metric label="Failed" value={summary.failed} tone="bad" filterKey="failed" active={policyFilter === "failed"} onSelect={setPolicyFilter} />
        <Metric label="Aggregators" value={summary.aggregators} filterKey="discovery" active={policyFilter === "discovery"} onSelect={setPolicyFilter} />
      </div>
      <section className="soft-card rounded-2xl p-4">
        <div className="grid gap-3 lg:grid-cols-[1fr_200px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <span className="sr-only">Search sources</span>
            <input value={query} onChange={(e) => setQuery(e.target.value)} className="w-full rounded-xl border border-border bg-white/80 py-2 pl-9 pr-3 text-sm" placeholder="Search source, URL, notes" />
          </label>
          <label className="relative block">
            <Filter className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <span className="sr-only">Filter source type</span>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-full rounded-xl border border-border bg-white/80 py-2 pl-9 pr-3 text-sm">
              <option value="all">All source types</option>
              {typeOptions.map((type) => <option key={type} value={type}>{sourceTypeLabel(type)}</option>)}
            </select>
          </label>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            ["all", "All"],
            ["active", "Active"],
            ["official_verified", "Official verified"],
            ["review", "Needs review"],
            ["failed", "Failed"],
            ["discovery", "Aggregator discovery-only"],
            ["inactive", "Inactive"],
          ].map(([value, label]) => (
            <button key={value} type="button" onClick={() => setPolicyFilter(value)} className={`rounded-full border px-3 py-1.5 text-xs ${policyFilter === value ? "border-dusk-700 bg-dusk-700 text-white" : "border-border bg-white/70 text-foreground/75 hover:bg-clay-100"}`}>{label}</button>
          ))}
        </div>
      </section>
      {actionError && <div className="soft-card rounded-xl p-3 text-xs text-destructive">{actionError.message}</div>}
      {loading ? <LoadingSkeleton variant="table" /> : null}
      {!loading && error ? <ErrorState title="Failed to load sources" message={error.message} onRetry={load} /> : null}
      {!loading && !error && items.length === 0 ? <EmptyState icon={ShieldCheck} title="No sources found" description="Create a source to begin trust verification." actionLabel="Add source" onAction={openCreate} /> : null}
      {!loading && !error && items.length > 0 && filteredItems.length === 0 ? <EmptyState icon={Search} title="No sources match this view" description="Adjust search or filters to widen the registry." /> : null}
      {!loading && !error && filteredItems.length > 0 ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {filteredItems.map((source) => (
            <SourceCard key={source.id} source={source} busyKey={busyKey} onDetails={() => setSelectedDetails(source.id)} onEdit={openEdit} onVerify={verify} onToggle={toggle} onHistory={showHistory} />
          ))}
        </div>
      ) : null}
      <SourceFormDrawer open={formOpen} mode={editing ? "edit" : "create"} form={form} setForm={setForm} busy={busyKey === "create" || busyKey === `update-${editing?.id}`} error={formError} onClose={closeForm} onSubmit={save} />
      <SourceDetailsDialog source={items.find((s) => s.id === selectedDetails)} result={resultById[selectedDetails]} onEdit={openEdit} onClose={() => setSelectedDetails(null)} />
      <AuditTimelineDrawer open={!!auditTarget} title={auditTarget?.org || auditTarget?.source_name || "Source"} items={auditItems} onClose={() => setAuditTarget(null)} />
    </div>
  );
}

function Field({ label, help, children }) {
  return <label className="block text-sm"><div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</div>{children}{help ? <div className="mt-1 text-[11px] text-muted-foreground">{help}</div> : null}</label>;
}

function FormSection({ label, children }) {
  return (
    <section className="mt-5">
      <div className="mb-2 text-[11px] uppercase tracking-widest text-muted-foreground">{label}</div>
      {children}
    </section>
  );
}

function Detail({ label, value }) {
  return <div><div className="text-[11px] uppercase tracking-widest text-muted-foreground">{label}</div><div className="break-words">{value || "-"}</div></div>;
}

function Metric({ label, value, tone, filterKey, active, onSelect }) {
  const toneClass = tone === "bad" ? "text-destructive" : tone === "warn" ? "text-amber-700" : "text-foreground";
  const inner = (
    <>
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className={`mt-1 font-heading text-2xl ${toneClass}`}>{value}</div>
    </>
  );
  if (!filterKey) return <div className="soft-card rounded-xl p-3">{inner}</div>;
  return (
    <button
      type="button"
      onClick={() => onSelect(filterKey)}
      aria-pressed={active}
      className={`soft-card rounded-xl p-3 text-left transition ${active ? "ring-2 ring-dusk-700" : "hover:bg-clay-100"}`}
      data-testid={`source-metric-${filterKey}`}
    >
      {inner}
    </button>
  );
}

function SourceCard({ source, busyKey, onDetails, onEdit, onVerify, onToggle, onHistory }) {
  const sourceType = source.source_type || source.kind;
  const isAggregator = sourceType === "aggregator";
  const failed = (source.consecutive_fails || 0) > 0 || source.last_error;
  const lastSuccess = source.last_success_at ? String(source.last_success_at).slice(0, 10) : "never";

  return (
    <article className="soft-card rounded-xl p-3" data-testid={`source-card-${source.id}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="truncate font-heading text-base">{source.org || source.source_name}</h2>
          <p className="truncate text-[11px] text-muted-foreground">{source.official_url || source.url || "-"}</p>
        </div>
        <SourceHealthBadge source={source} />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
        <span className="pill">{sourceTypeLabel(sourceType)}</span>
        {isAggregator
          ? <span className="pill pill-amber" title="Cannot publish from this source alone">Discovery only</span>
          : <span className="pill pill-sage">{source.is_verified ? "Verified" : "Unverified"}</span>}
        <span className={`pill${source.is_active ? " pill-sage" : ""}`}>{source.is_active ? "Active" : "Inactive"}</span>
        {source.currently_scraping_at ? <span className="pill pill-amber">Scraping…</span> : null}
        {failed ? <span className="pill pill-amber" title={source.last_error || source.last_error_class || "recent failures"}>{source.consecutive_fails || 0} fails</span> : null}
        <span className="text-muted-foreground">· scraped {lastSuccess}</span>
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-2">
        <button className="btn btn-ghost h-7 text-[11px]" onClick={onDetails}>Details</button>
        <RowActions groupLabel={`Row actions for ${source.org || source.source_name || "source"}`} actions={[
          { label: "Edit", ariaLabel: `Edit source ${source.org || source.source_name}`, onClick: () => onEdit(source) },
          ...(!source.is_verified ? [{ label: "Verify", ariaLabel: `Verify source ${source.org || source.source_name}`, onClick: () => onVerify(source), disabled: isAggregator || busyKey === `verify-${source.id}` }] : []),
          { label: source.is_active ? "Deactivate" : "Activate", ariaLabel: `${source.is_active ? "Deactivate" : "Activate"} source ${source.org || source.source_name}`, onClick: () => onToggle(source.id, !!source.is_active), disabled: busyKey === `${source.is_active ? "deactivate" : "activate"}-${source.id}` },
          { label: "History", ariaLabel: `View history for source ${source.org || source.source_name}`, onClick: () => onHistory(source) },
        ]} />
      </div>
    </article>
  );
}

function sourceTypeLabel(value) {
  return SOURCE_TYPES.find((type) => type.value === value)?.label || value || "Unknown";
}

function primaryFetchUrl(source) {
  // Mirrors ScrapeSource.primary_fetch_url() in app/backend/app/scraping/sources.py
  // so the admin sees exactly which URL the runner will hit for this adapter.
  const adapter = (source?.adapter_type || "").toLowerCase();
  if (adapter === "rss") return source?.rss_url || null;
  if (adapter === "api") return source?.api_url || null;
  if (adapter === "pdf") return source?.pdf_bulletin_url || null;
  if (adapter === "sitemap") {
    const cfg = source?.adapter_config?.sitemap_url;
    if (cfg) return cfg;
    const base = (source?.crawl_url || source?.official_url || "").replace(/\/$/, "");
    return base ? `${base}/sitemap.xml` : null;
  }
  if (source?.discovery_only || (source?.source_type || "").toLowerCase() === "aggregator") {
    return source?.crawl_url || source?.notification_url || source?.official_url || null;
  }
  return source?.notification_url || source?.crawl_url || source?.official_url || null;
}
