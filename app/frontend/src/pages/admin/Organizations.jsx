import React, { useEffect, useMemo, useRef, useState } from "react";
import { Building2, History, Pencil, Plus, Search, ShieldCheck, X } from "lucide-react";
import OrganizationEditPanel from "../../features/admin/organizations/OrganizationEditPanel";
import { api } from "../../lib/api";
import { EmptyState, ErrorState, LoadingSkeleton, RowActions, StatusBadge } from "../../shared/ui/core";
import { useFocusTrap } from "../../shared/a11y/useFocusTrap";
import useAdminAction from "../../features/admin/shared/useAdminAction";
import useApiAction from "../../lib/hooks/useApiAction";
import AuditTimelineDrawer from "../../features/admin/shared/AuditTimelineDrawer";
import { adminTrustService } from "../../services/adminTrustService";

function OrganizationDrawer({ org, onClose, onVerify, onSave, onHistory, busyKey }) {
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  useFocusTrap({ active: !!org, containerRef: panelRef, onEscape: onClose, initialFocusRef: closeRef });
  if (!org) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <div className="absolute inset-0" onClick={onClose} />
      <aside ref={panelRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="organization-detail-title" className="relative h-full w-full max-w-2xl overflow-auto border-l border-border bg-[#FBF6EF] p-5 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Organization trust</div>
            <h2 id="organization-detail-title" className="mt-1 truncate font-heading text-2xl">{org.name}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{org.type || "Unknown type"} / {org.state || "Unknown state"}</p>
          </div>
          <button ref={closeRef} className="btn btn-ghost h-9 w-9 p-0" onClick={onClose} aria-label="Close organization details"><X className="h-4 w-4" /></button>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <StatusBadge status={org.trust_tier || "pending"} label={org.trust_tier || "Unknown tier"} />
          <StatusBadge status={org.is_verified ? "verified" : "pending"} label={org.is_verified ? "Verified" : "Pending"} />
        </div>

        <section className="mt-5 grid gap-3 md:grid-cols-2">
          <Info label="Website" value={org.website_url || org.official_website} />
          <Info label="Official domain" value={org.official_domain} />
          <Info label="Linked sources" value={org.linked_sources_count} />
          <Info label="Linked recruitments" value={org.linked_recruitments_count} />
          <Info label="Verified at" value={org.verified_at} />
          <Info label="Verification notes" value={org.verification_notes} />
        </section>

        <section className="mt-5 soft-card rounded-2xl p-4">
          <h3 className="font-semibold">Actions</h3>
          <div className="mt-3">
            <RowActions groupLabel={`Actions for ${org.name}`} actions={[
              { label: "Verify", ariaLabel: `Verify organization ${org.name}`, onClick: () => onVerify(org.id, org.name), disabled: busyKey === `verify-${org.id}` },
              { label: "History", ariaLabel: `View history for ${org.name}`, onClick: () => onHistory(org) },
            ]} />
          </div>
        </section>

        <section className="mt-5 soft-card rounded-2xl p-4">
          <h3 className="font-semibold">Edit website</h3>
          <div className="mt-3">
            <OrganizationEditPanel org={org} onSave={(payload) => onSave(org.id, payload)} busy={busyKey === `save-${org.id}`} />
          </div>
        </section>
      </aside>
    </div>
  );
}

const ORG_TYPES = [
  "state_psc", "central", "banking", "insurance", "railways",
  "defence", "upsc", "ssc", "other",
];

function NewOrgModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [shortName, setShortName] = useState("");
  const [state, setState] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [error, setError] = useState(null);
  const { run, busy } = useApiAction();
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  useFocusTrap({ active: true, containerRef: panelRef, onEscape: onClose, initialFocusRef: closeRef });

  async function submit(e) {
    e.preventDefault();
    setError(null);
    const payload = { name, type, short_name: shortName };
    if (state.trim()) payload.state = state.trim();
    if (websiteUrl.trim()) payload.website_url = websiteUrl.trim();
    const res = await run({
      action: () => api.post("/api/admin/organizations", payload),
      onSuccess: (result) => {
        const warnings = result.warnings?.length > 0 ? result.warnings : null;
        onCreated(warnings);
        onClose();
      },
      errorMessage: "Failed to create organization",
    });
    if (!res.ok && !res.cancelled) {
      setError(res.error?.message || "Failed to create organization");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="absolute inset-0" onClick={onClose} />
      <div ref={panelRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="new-org-title"
        className="relative w-full max-w-lg rounded-2xl border border-border bg-[#FBF6EF] p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 id="new-org-title" className="font-heading text-xl">New organization</h2>
          <button ref={closeRef} className="btn btn-ghost h-9 w-9 p-0" onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">Trust tier and verification status are set by the server — new orgs start as unverified.</p>
        <form onSubmit={submit} className="mt-4 space-y-3" noValidate>
          <Field label="Name *" id="new-org-name">
            <input id="new-org-name" required value={name} onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              data-testid="org-create-name" />
          </Field>
          <Field label="Type *" id="new-org-type">
            <select id="new-org-type" required value={type} onChange={(e) => setType(e.target.value)}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              data-testid="org-create-type">
              <option value="">Select type…</option>
              {ORG_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </Field>
          <Field label="Short name *" id="new-org-short_name">
            <input id="new-org-short_name" required value={shortName} onChange={(e) => setShortName(e.target.value)}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              placeholder="e.g. RPSC"
              data-testid="org-create-short_name" />
          </Field>
          <Field label="State" id="new-org-state">
            <input id="new-org-state" value={state} onChange={(e) => setState(e.target.value)}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              placeholder="e.g. rajasthan"
              data-testid="org-create-state" />
          </Field>
          <Field label="Website URL" id="new-org-website_url">
            <input id="new-org-website_url" value={websiteUrl} onChange={(e) => setWebsiteUrl(e.target.value)}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              placeholder="https://…"
              data-testid="org-create-website_url" />
          </Field>
          {error && (
            <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
              data-testid="org-create-error">{error}</div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn btn-ghost text-sm" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary text-sm" disabled={busy}
              aria-label="Create organization">
              {busy ? "Creating…" : "Create organization"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminOrganizations() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [auditTarget, setAuditTarget] = useState(null);
  const [auditItems, setAuditItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createWarnings, setCreateWarnings] = useState(null);
  const { runAction, busyKey, error: actionError } = useAdminAction();

  const load = async () => {
    setLoading(true); setError(null);
    try { const d = await api.get("/api/admin/organizations"); setItems(d.items || []); } catch (e) { setError(e); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const verify = async (id, name) => runAction({ key: `verify-${id}`, confirm: `Verify ${name}?`, successMessage: `${name} verified`, action: async () => { await api.post(`/api/admin/organizations/${id}/verify`, {}); await load(); } });
  const save = async (id, payload) => runAction({ key: `save-${id}`, successMessage: "Organization saved", action: async () => { await api.put(`/api/admin/organizations/${id}`, payload || {}); await load(); } });
  const showHistory = async (org) => { const d = await adminTrustService.organizationAudit(org.id); setAuditItems(d.items || []); setAuditTarget(org); };

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((org) => `${org.name || ""} ${org.type || ""} ${org.state || ""} ${org.official_domain || ""}`.toLowerCase().includes(needle));
  }, [items, query]);

  const stats = useMemo(() => ({
    total: items.length,
    verified: items.filter((org) => org.is_verified).length,
    pending: items.filter((org) => !org.is_verified).length,
  }), [items]);

  return (
    <div className="space-y-5" data-testid="admin-organizations">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">Organizations / trust</div>
          <h1 className="mt-1 font-heading text-3xl font-semibold tracking-tight">Organizations trust.</h1>
          <p className="mt-1 text-sm text-muted-foreground">Verify official domains and inspect linked source/recruitment coverage.</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status="pending" label={`${filtered.length} visible`} />
          <button className="btn btn-primary text-xs" onClick={() => setShowCreate(true)} aria-label="New organization">
            <Plus className="h-3.5 w-3.5" /> New organization
          </button>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <Metric label="Total" value={stats.total} />
        <Metric label="Verified" value={stats.verified} />
        <Metric label="Pending" value={stats.pending} />
      </div>

      <div className="soft-card rounded-2xl p-4">
        <label className="relative block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <span className="sr-only">Search organizations</span>
          <input value={query} onChange={(e) => setQuery(e.target.value)} className="w-full rounded-xl border border-border bg-white/80 py-2 pl-9 pr-3 text-sm" placeholder="Search organization, state, domain" />
        </label>
      </div>

      {actionError && <div className="soft-card rounded-xl p-3 text-xs text-destructive">{actionError.message}</div>}
      {createWarnings && createWarnings.length > 0 && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800"
          data-testid="org-create-warning">
          <strong>Organization created</strong> — possible duplicate{createWarnings.length > 1 ? "s" : ""} already exist:{" "}
          {createWarnings.map((w) => w.existing_name).join(", ")}.
          <button className="ml-2 underline text-xs" onClick={() => setCreateWarnings(null)}>Dismiss</button>
        </div>
      )}
      {loading ? <LoadingSkeleton variant="cards" /> : null}
      {!loading && error ? <ErrorState title="Failed to load organizations" message={error.message} onRetry={load} /> : null}
      {!loading && !error && filtered.length === 0 ? <EmptyState icon={Building2} title="No organizations match this view" description="Adjust the search to review more organizations." /> : null}
      {!loading && !error && filtered.length > 0 ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {filtered.map((org) => (
            <article key={org.id} className="soft-card rounded-2xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap gap-1.5">
                    <StatusBadge status={org.trust_tier || "pending"} label={org.trust_tier || "Unknown"} />
                    <StatusBadge status={org.is_verified ? "verified" : "pending"} label={org.is_verified ? "Verified" : "Pending"} />
                  </div>
                  <h2 className="mt-3 truncate font-heading text-xl">{org.name}</h2>
                  <p className="mt-1 truncate text-sm text-muted-foreground">{org.type || "-"} / {org.state || "-"} / {org.official_domain || "domain missing"}</p>
                </div>
                <button className="btn btn-ghost h-9 text-xs" onClick={() => setSelected(org)}>Details</button>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                <Mini label="Sources" value={org.linked_sources_count} />
                <Mini label="Recruitments" value={org.linked_recruitments_count} />
              </div>
              <div className="mt-4 flex flex-wrap justify-end gap-2">
                <button className="btn btn-ghost text-xs" onClick={() => setSelected(org)}><Pencil className="h-3.5 w-3.5" /> Edit</button>
                <button className="btn btn-ghost text-xs" onClick={() => showHistory(org)}><History className="h-3.5 w-3.5" /> History</button>
                <button className="btn btn-primary text-xs" disabled={busyKey === `verify-${org.id}`} onClick={() => verify(org.id, org.name)}><ShieldCheck className="h-3.5 w-3.5" /> Verify</button>
              </div>
            </article>
          ))}
        </div>
      ) : null}
      <OrganizationDrawer org={selected} onClose={() => setSelected(null)} onVerify={verify} onSave={save} onHistory={showHistory} busyKey={busyKey} />
      <AuditTimelineDrawer open={!!auditTarget} title={auditTarget?.name || "Organization"} items={auditItems} onClose={() => setAuditTarget(null)} />
      {showCreate && (
        <NewOrgModal
          onClose={() => setShowCreate(false)}
          onCreated={(warnings) => { setCreateWarnings(warnings || null); load(); }}
        />
      )}
    </div>
  );
}

function Field({ label, id, children }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

function Info({ label, value }) {
  return <div className="rounded-xl border border-border bg-white/60 p-3 text-sm"><div className="text-[11px] uppercase tracking-widest text-muted-foreground">{label}</div><div className="mt-1 break-words">{value ?? "-"}</div></div>;
}

function Metric({ label, value }) {
  return <div className="soft-card rounded-2xl p-4"><div className="text-[11px] uppercase tracking-widest text-muted-foreground">{label}</div><div className="mt-1 font-heading text-3xl">{value}</div></div>;
}

function Mini({ label, value }) {
  return <div className="rounded-xl border border-border bg-white/60 p-2"><div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div><div className="mt-1 font-semibold">{value ?? "-"}</div></div>;
}
