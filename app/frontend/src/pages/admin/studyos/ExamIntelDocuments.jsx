import React, { useCallback, useEffect, useRef, useState } from "react";
import { RotateCcw, Upload, FileText } from "lucide-react";
import { api, getApiErrorMessage } from "../../../lib/api";
import CmsRefField from "../../../features/admin/shared/CmsRefField";

const DOC_BASE = "/api/admin/exam-intelligence-cms/documents";
const DOC_KINDS = ["syllabus", "pyq_paper", "notification", "corrigendum", "answer_key"];

const EXAM_IDENTITIES = [
  "upsc_cse_prelims_gs1", "upsc_cse_prelims_csat",
  "upsc_cse_mains_essay", "upsc_cse_mains_gs1", "upsc_cse_mains_gs2",
  "upsc_cse_mains_gs3", "upsc_cse_mains_gs4",
  "upsc_cse_mains_optional_sociology", "upsc_cse_mains_optional_psir",
  "upsc_cse_mains_optional_history", "upsc_cse_mains_optional_anthropology",
  "upsc_cse_mains_optional_technical",
  "upsc_other", "state_psc_other", "banking_other", "unknown",
];

const STRUCTURAL_FORMATS = [
  "mcq_bilingual_two_column", "mcq_monolingual_single", "essay_long_form",
  "mixed_objective_subjective", "technical_with_figures", "vernacular_non_devanagari", "unknown",
];

const SOURCE_KINDS = [
  { value: "official_archive", label: "Official UPSC archive (no watermark, authoritative)" },
  { value: "sanitized_coaching", label: "Sanitized coaching PDF (watermark removed)" },
  { value: "raw_coaching", label: "Raw coaching PDF (will need sanitization)" },
  { value: "sme_authored", label: "SME-authored test content" },
  { value: "official_scan", label: "Official scan (legacy; use official_archive instead)" },
  { value: "crowd_sourced", label: "Crowd-sourced (not eligible for extraction)" },
  { value: "unknown", label: "(not classified)" },
];

// exam_identity → inferred structural_format (mirrors dispatch.py EXAM_TO_FORMAT_DEFAULT)
const EXAM_TO_FORMAT_DEFAULT = {
  upsc_cse_prelims_gs1: "mcq_bilingual_two_column",
  upsc_cse_prelims_csat: "mcq_bilingual_two_column",
  upsc_cse_mains_essay: "essay_long_form",
  upsc_cse_mains_gs1: "essay_long_form",
  upsc_cse_mains_gs2: "essay_long_form",
  upsc_cse_mains_gs3: "essay_long_form",
  upsc_cse_mains_gs4: "essay_long_form",
  upsc_cse_mains_optional_sociology: "essay_long_form",
  upsc_cse_mains_optional_psir: "essay_long_form",
  upsc_cse_mains_optional_history: "essay_long_form",
  upsc_cse_mains_optional_anthropology: "essay_long_form",
  upsc_cse_mains_optional_technical: "technical_with_figures",
};

const REF_EXAM = { endpoint: "exams", labelKey: "name", secondaryKey: "slug" };
const refCycle = (filters) => ({ endpoint: "exam-cycles", labelKey: "cycle_name", secondaryKey: "year", filters });
const refPhase = (filters) => ({ endpoint: "exam-phases", labelKey: "phase_name", secondaryKey: "phase_slug", filters });

/**
 * Admin PDF upload + document list for Exam Intelligence. Drives the
 * upload-url → PUT bytes → complete-upload → poll-extraction flow and lets an
 * operator inspect extracted pages and link a document into a syllabus /
 * PYQ-paper row. Reuses the shared Combobox pickers.
 */
export default function ExamIntelDocuments({ scopeExamId, scopeCycleId }) {
  const [form, setForm] = useState(() => ({
    structural_format: "unknown",
    source_kind: "unknown",
    exam_id: scopeExamId || "",
    exam_cycle_id: scopeCycleId || "",
  }));
  const [formatOverridden, setFormatOverridden] = useState(false);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);
  const [docs, setDocs] = useState([]);
  const [pages, setPages] = useState({ docId: null, items: null });
  const [pollId, setPollId] = useState(null);
  const [linkTarget, setLinkTarget] = useState({ docId: null, kind: null, targetId: "", reason: "" });

  const filterExamId = form.exam_id || "";
  const loadGenRef = useRef(0);
  const scopeGenRef = useRef(0);

  const loadList = useCallback(async () => {
    if (!filterExamId) {
      setDocs([]);
      return;
    }
    const gen = ++loadGenRef.current;
    try {
      const r = await api.get(`${DOC_BASE}?exam_id=${encodeURIComponent(filterExamId)}`);
      if (gen !== loadGenRef.current) return;
      setDocs(r.items || []);
    } catch (e) {
      if (gen !== loadGenRef.current) return;
      setStatus({ ok: false, message: getApiErrorMessage(e) });
    }
  }, [filterExamId]);

  useEffect(() => {
    loadGenRef.current += 1;
    scopeGenRef.current += 1;
    setDocs([]);
    setPages({ docId: null, items: null });
    setLinkTarget({ docId: null, kind: null, targetId: "", reason: "" });
    setStatus(null);
    setPollId(null);
    setFile(null);
    setBusy(false);
    setForm((prev) => ({
      ...prev,
      exam_id: scopeExamId ?? "",
      exam_cycle_id: scopeCycleId ?? "",
      exam_phase_id: "",
    }));
  }, [scopeExamId, scopeCycleId]);

  useEffect(() => {
    loadList();
  }, [loadList]);

  async function refreshStatus(docId) {
    const scopeGen = scopeGenRef.current;
    try {
      const r = await api.get(`${DOC_BASE}/${docId}`);
      if (scopeGen !== scopeGenRef.current) return null;
      setDocs((prev) => prev.map((d) => (d.id === docId
        ? { ...d, status: r.document.status, pages_count: r.pages_count, extraction: r.extraction }
        : d)));
      return r.document.status;
    } catch {
      return null;
    }
  }

  async function doUpload(e) {
    e.preventDefault();
    setStatus(null);
    if (!form.exam_id) return setStatus({ ok: false, message: "Select an exam first." });
    if (!form.document_kind) return setStatus({ ok: false, message: "Select a document kind." });
    if (!file) return setStatus({ ok: false, message: "Choose a PDF file." });
    if (file.type !== "application/pdf") return setStatus({ ok: false, message: "Only PDF files are accepted." });

    const scopeGen = scopeGenRef.current;
    setBusy(true);
    try {
      const signed = await api.post(`${DOC_BASE}/upload-url`, {
        exam_id: form.exam_id,
        exam_cycle_id: form.exam_cycle_id || null,
        exam_phase_id: form.exam_phase_id || null,
        document_kind: form.document_kind,
        filename: file.name,
        mime_type: file.type,
        size_bytes: file.size,
        exam_identity: form.exam_identity || null,
        structural_format: form.structural_format || null,
        source_kind: form.source_kind || null,
        sanitized_from_document_id: form.sanitized_from_document_id || null,
      });
      if (scopeGen !== scopeGenRef.current) return;
      // PUT the bytes straight into Supabase Storage via the signed URL.
      const put = await fetch(signed.upload_url, {
        method: "PUT",
        headers: { "content-type": file.type },
        body: file,
      });
      if (!put.ok) throw new Error(`Storage upload failed (${put.status})`);
      if (scopeGen !== scopeGenRef.current) return;
      await api.post(`${DOC_BASE}/complete-upload`, { document_id: signed.document_id });
      if (scopeGen !== scopeGenRef.current) return;
      setStatus({ ok: true, message: `Uploaded ${file.name}. Extraction queued.` });
      setFile(null);
      await loadList();
      if (scopeGen !== scopeGenRef.current) return;
      startPoll(signed.document_id, scopeGen);
    } catch (ex) {
      if (scopeGen !== scopeGenRef.current) return;
      setStatus({ ok: false, message: getApiErrorMessage(ex) });
    } finally {
      setBusy(false);
    }
  }

  function startPoll(docId, scopeGen) {
    if (pollId) clearInterval(pollId);
    const id = setInterval(async () => {
      if (scopeGen !== scopeGenRef.current) {
        clearInterval(id);
        setPollId(null);
        return;
      }
      const st = await refreshStatus(docId);
      if (st === "processed" || st === "failed" || st == null) {
        clearInterval(id);
        setPollId(null);
      }
    }, 3000);
    setPollId(id);
  }

  useEffect(() => () => { if (pollId) clearInterval(pollId); }, [pollId]);

  async function viewPages(docId) {
    if (pages.docId === docId) {
      setPages({ docId: null, items: null });
      return;
    }
    const scopeGen = scopeGenRef.current;
    try {
      const r = await api.get(`${DOC_BASE}/${docId}/pages`);
      if (scopeGen !== scopeGenRef.current) return;
      setPages({ docId, items: r.items || [] });
    } catch (e) {
      if (scopeGen !== scopeGenRef.current) return;
      setStatus({ ok: false, message: getApiErrorMessage(e) });
    }
  }

  async function confirmLink() {
    const { docId, kind, targetId, reason } = linkTarget;
    if (!targetId) return setStatus({ ok: false, message: "Pick a target first." });
    if (!reason || reason.trim().length < 8) {
      return setStatus({ ok: false, message: "Reason must be at least 8 characters." });
    }
    const scopeGen = scopeGenRef.current;
    const path = kind === "syllabus" ? "link-to-syllabus" : "link-to-pyq-paper";
    const payload = kind === "syllabus"
      ? { reason: reason.trim(), syllabus_document_id: targetId }
      : { reason: reason.trim(), pyq_paper_id: targetId };
    try {
      await api.post(`${DOC_BASE}/${docId}/${path}`, payload);
      if (scopeGen !== scopeGenRef.current) return;
      setStatus({ ok: true, message: `Linked document to ${kind}.` });
      setLinkTarget({ docId: null, kind: null, targetId: "", reason: "" });
    } catch (e) {
      if (scopeGen !== scopeGenRef.current) return;
      setStatus({ ok: false, message: getApiErrorMessage(e) });
    }
  }

  function setRef(key, val) {
    setForm((p) => ({ ...p, [key]: val }));
  }

  function handleExamIdentityChange(val) {
    setForm((p) => {
      const inferred = EXAM_TO_FORMAT_DEFAULT[val] || "unknown";
      return { ...p, exam_identity: val, structural_format: formatOverridden ? p.structural_format : inferred };
    });
  }

  function handleFormatChange(val) {
    setFormatOverridden(true);
    setForm((p) => ({ ...p, structural_format: val }));
  }

  return (
    <div className="space-y-4" data-testid="exam-intel-documents">
      <form onSubmit={doUpload} className="rounded border border-border/60 bg-card p-4 space-y-2" data-testid="doc-upload-form">
        <h3 className="text-sm font-semibold">Upload exam-intelligence PDF</h3>
        <p className="text-xs text-amber-700">
          Admin-only. Uploaded documents land in <code>admin_only</code> visibility; link them into a syllabus / PYQ paper after extraction.
        </p>
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">exam_id <span className="text-red-700">*</span></span>
            <CmsRefField field={{ key: "exam_id", ref: REF_EXAM }} value={form.exam_id || ""} formValues={form} onChange={(v) => setRef("exam_id", v)} testId="doc-field-exam_id" />
          </label>
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">document_kind <span className="text-red-700">*</span></span>
            <select
              value={form.document_kind || ""}
              onChange={(e) => setRef("document_kind", e.target.value)}
              className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
              data-testid="doc-field-document_kind"
            >
              <option value="">(select)</option>
              {DOC_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">exam_cycle_id</span>
            <CmsRefField field={{ key: "exam_cycle_id", ref: refCycle({ exam_id: "exam_id" }) }} value={form.exam_cycle_id || ""} formValues={form} onChange={(v) => setRef("exam_cycle_id", v)} testId="doc-field-exam_cycle_id" />
          </label>
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">exam_phase_id</span>
            <CmsRefField field={{ key: "exam_phase_id", ref: refPhase({ exam_id: "exam_id" }) }} value={form.exam_phase_id || ""} formValues={form} onChange={(v) => setRef("exam_phase_id", v)} testId="doc-field-exam_phase_id" />
          </label>
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">exam_identity</span>
            <select
              value={form.exam_identity || ""}
              onChange={(e) => handleExamIdentityChange(e.target.value)}
              className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
              data-testid="doc-field-exam_identity"
            >
              <option value="">(select)</option>
              {EXAM_IDENTITIES.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">
              structural_format <span className="text-muted-foreground/60 font-normal">(auto-inferred; override if needed)</span>
            </span>
            <select
              value={form.structural_format || "unknown"}
              onChange={(e) => handleFormatChange(e.target.value)}
              className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
              data-testid="doc-field-structural_format"
            >
              {STRUCTURAL_FORMATS.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">
              source_kind <span className="text-red-700">*</span>
            </span>
            <select
              value={form.source_kind || "unknown"}
              onChange={(e) => setRef("source_kind", e.target.value)}
              className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
              data-testid="doc-field-source_kind"
            >
              {SOURCE_KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
            </select>
            {form.source_kind === "raw_coaching" && (
              <p className="text-xs text-amber-700 mt-1" data-testid="raw-coaching-warning">
                raw_coaching PDFs cannot be extracted until sanitized. Set source_kind to
                sanitized_coaching after removing watermarks/overlays. See sanitization-sop-v1.md.
              </p>
            )}
          </label>
          {form.source_kind === "sanitized_coaching" && (
            <label className="block" data-testid="sanitized-from-field">
              <span className="block text-xs text-muted-foreground mb-1">sanitized_from_document_id <span className="text-muted-foreground/60 font-normal">(UUID of the raw_coaching source document)</span></span>
              <input
                type="text"
                value={form.sanitized_from_document_id || ""}
                onChange={(e) => setRef("sanitized_from_document_id", e.target.value)}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background font-mono"
                data-testid="doc-field-sanitized_from_document_id"
              />
            </label>
          )}
        </div>
        <label className="block">
          <span className="block text-xs text-muted-foreground mb-1">PDF file</span>
          <input type="file" accept="application/pdf,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} data-testid="doc-file" className="block text-xs" />
        </label>
        <button type="submit" className="btn small" disabled={busy} data-testid="doc-upload-submit">
          <Upload className="h-3 w-3" /> {busy ? "Uploading…" : "Upload"}
        </button>
      </form>

      {status ? (
        <div className={`text-sm ${status.ok ? "text-emerald-700" : "text-red-700"}`} role="status" aria-live="polite">{status.message}</div>
      ) : null}

      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold">Documents{filterExamId ? "" : " — select an exam to list"}</h3>
        <button type="button" className="btn small" onClick={loadList} data-testid="doc-reload"><RotateCcw className="h-3 w-3" /> Reload</button>
      </div>

      <section className="rounded border border-border/60 bg-card overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-muted/50"><tr>
            <th className="text-left p-2">id</th><th className="text-left p-2">kind</th>
            <th className="text-left p-2">filename</th><th className="text-left p-2">status</th>
            <th className="text-left p-2">pages</th><th className="text-left p-2">actions</th>
          </tr></thead>
          <tbody>
            {!docs.length ? (
              <tr><td colSpan={6} className="p-3 text-center text-muted-foreground">No documents.</td></tr>
            ) : docs.map((d) => (
              <React.Fragment key={d.id}>
                <tr className="border-t border-border/40" data-testid={`doc-row-${d.id}`}>
                  <td className="p-2 font-mono">{String(d.id).slice(0, 8)}…</td>
                  <td className="p-2">{d.document_kind}</td>
                  <td className="p-2">{d.original_filename}</td>
                  <td className="p-2">{d.status}</td>
                  <td className="p-2">{d.page_count ?? d.pages_count ?? "—"}</td>
                  <td className="p-2 space-x-1">
                    <button type="button" className="btn small" onClick={() => viewPages(d.id)} data-testid={`doc-pages-${d.id}`}><FileText className="h-3 w-3" /> Pages</button>
                    <button type="button" className="btn small" onClick={() => refreshStatus(d.id)} data-testid={`doc-refresh-${d.id}`}>Status</button>
                    <button type="button" className="btn small" onClick={() => setLinkTarget({ docId: d.id, kind: "syllabus", targetId: "", reason: "" })} data-testid={`doc-link-syllabus-${d.id}`}>→ Syllabus</button>
                    <button type="button" className="btn small" onClick={() => setLinkTarget({ docId: d.id, kind: "pyq", targetId: "", reason: "" })} data-testid={`doc-link-pyq-${d.id}`}>→ PYQ paper</button>
                  </td>
                </tr>
                {linkTarget.docId === d.id ? (
                  <tr className="border-t border-border/40 bg-muted/30"><td colSpan={6} className="p-2">
                    <div className="flex items-end gap-2 flex-wrap" data-testid={`doc-link-picker-${d.id}`}>
                      <label className="block flex-1">
                        <span className="block text-xs text-muted-foreground mb-1">
                          {linkTarget.kind === "syllabus" ? "Pick a syllabus_document" : "Pick a pyq_paper"}
                        </span>
                        <CmsRefField
                          field={linkTarget.kind === "syllabus"
                            ? { key: "t", ref: { endpoint: "syllabus-documents", labelKey: "title", secondaryKey: "document_type", filters: { exam_id: "exam_id" } } }
                            : { key: "t", ref: { endpoint: "pyq-papers", labelKey: "paper_code", secondaryKey: "year", filters: { exam_id: "exam_id" } } }}
                          value={linkTarget.targetId}
                          formValues={{ exam_id: filterExamId }}
                          onChange={(v) => setLinkTarget((p) => ({ ...p, targetId: v }))}
                          testId={`doc-link-target-${d.id}`}
                        />
                      </label>
                      <label className="block flex-1">
                        <span className="block text-xs text-muted-foreground mb-1">Reason (≥ 8 chars)</span>
                        <input
                          type="text"
                          className="w-full px-2 py-1.5 text-xs border border-border/60 rounded bg-background"
                          value={linkTarget.reason}
                          onChange={(e) => setLinkTarget((p) => ({ ...p, reason: e.target.value }))}
                          placeholder="e.g. Linking official syllabus PDF"
                          data-testid={`doc-link-reason-${d.id}`}
                        />
                      </label>
                      <button type="button" className="btn small" onClick={confirmLink} data-testid={`doc-link-confirm-${d.id}`}>Link</button>
                      <button type="button" className="btn small" onClick={() => setLinkTarget({ docId: null, kind: null, targetId: "", reason: "" })}>Cancel</button>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-1">No target? Create it in the matching CMS entity first.</p>
                  </td></tr>
                ) : null}
                {pages.docId === d.id ? (
                  <tr className="border-t border-border/40 bg-muted/30"><td colSpan={6} className="p-2">
                    <div className="max-h-72 overflow-auto space-y-2" data-testid={`doc-pages-view-${d.id}`}>
                      {!pages.items?.length ? <div className="text-muted-foreground">No extracted pages yet.</div>
                        : pages.items.map((p) => (
                          <div key={p.page_number}>
                            <div className="font-semibold">Page {p.page_number} <span className="text-muted-foreground">({p.extraction_status})</span></div>
                            <pre className="whitespace-pre-wrap text-[11px]">{p.text_content}</pre>
                          </div>
                        ))}
                    </div>
                  </td></tr>
                ) : null}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
