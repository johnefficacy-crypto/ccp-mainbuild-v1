import React, { useRef, useState } from "react";
import { InputField } from "../../../shared/ui/core";
import { useFocusTrap } from "../../../shared/a11y/useFocusTrap";

// Mirrors the backend's editable set exactly (admin_trust.update_organization,
// PUT /api/admin/organizations/{id}): name, type, state, website_url,
// official_domain, trust_tier, verification_notes. Any field not in this
// list is server-owned (is_verified, verified_at, short_name, ...) and has
// no place in this form.
const ORG_TYPES = [
  "state_psc", "central", "banking", "insurance", "railways",
  "defence", "upsc", "ssc", "other",
];
const TRUST_TIERS = ["unverified", "unknown", "trusted", "verified"];

export default function OrganizationEditPanel({ org, onSave, busy }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(org.name || "");
  const [type, setType] = useState(org.type || "");
  const [state, setState] = useState(org.state || "");
  const [websiteUrl, setWebsiteUrl] = useState(org.website_url || org.official_website || "");
  const [officialDomain, setOfficialDomain] = useState(org.official_domain || "");
  const [trustTier, setTrustTier] = useState(org.trust_tier || "unknown");
  const [verificationNotes, setVerificationNotes] = useState(org.verification_notes || "");
  const [error, setError] = useState(null);
  const panelRef = useRef(null);
  useFocusTrap({ active: open, containerRef: panelRef, onEscape: () => setOpen(false) });

  function submit() {
    if (!name.trim()) { setError("Name is required."); return; }
    if (!type) { setError("Type is required."); return; }
    setError(null);
    onSave({
      name: name.trim(),
      type,
      state: state.trim(),
      website_url: websiteUrl.trim(),
      official_domain: officialDomain.trim(),
      trust_tier: trustTier,
      verification_notes: verificationNotes,
    });
  }

  return (
    <div className="space-y-2">
      <button type="button" className="text-xs link-under" onClick={() => setOpen((v) => !v)} data-testid="org-edit-toggle">
        {open ? "Hide edit" : "Edit organization"}
      </button>
      {open && (
        <div ref={panelRef} tabIndex={-1} role="dialog" aria-modal="false" aria-labelledby="organization-edit-title" className="rounded-xl border border-border p-3 bg-white/60 space-y-2">
          <h3 id="organization-edit-title" className="text-sm font-semibold">Edit organization</h3>
          <InputField label="Name" value={name} onChange={(e) => setName(e.target.value)} data-testid="org-edit-name" />
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-muted-foreground">Type</span>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              data-testid="org-edit-type"
            >
              <option value="">Select type…</option>
              {ORG_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <InputField label="State" value={state} onChange={(e) => setState(e.target.value)} placeholder="e.g. rajasthan" data-testid="org-edit-state" />
          <InputField label="Website URL" value={websiteUrl} onChange={(e) => setWebsiteUrl(e.target.value)} placeholder="https://…" data-testid="org-edit-website_url" />
          <InputField label="Official domain" value={officialDomain} onChange={(e) => setOfficialDomain(e.target.value)} placeholder="e.g. upsc.gov.in" data-testid="org-edit-official_domain" />
          <p className="text-[11px] text-muted-foreground">
            Changing the website URL or official domain resets verification — re-verify from the Actions panel.
          </p>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-muted-foreground">Trust tier</span>
            <select
              value={trustTier}
              onChange={(e) => setTrustTier(e.target.value)}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              data-testid="org-edit-trust_tier"
            >
              {TRUST_TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-muted-foreground">Verification notes</span>
            <textarea
              value={verificationNotes}
              onChange={(e) => setVerificationNotes(e.target.value)}
              rows={3}
              className="w-full rounded-xl border border-border bg-white/80 px-3 py-2 text-sm"
              data-testid="org-edit-verification_notes"
            />
          </label>
          {error && <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive" data-testid="org-edit-error">{error}</div>}
          <button type="button" className="btn btn-primary text-xs" disabled={busy} onClick={submit} data-testid="org-edit-save">
            {busy ? "Saving…" : "Save organization"}
          </button>
        </div>
      )}
    </div>
  );
}
