/**
 * DocumentsPanel — source-document management for the Exam Intelligence workspace.
 *
 * Upload flow (all endpoints from admin_exam_intel_documents.py; confirmed PR-0 §6):
 *   1. POST /exam-intelligence-cms/documents/upload-url
 *   2. PUT  bytes → signed storage URL  (client fetch, NOT api wrapper — binary body)
 *   3. POST /exam-intelligence-cms/documents/complete-upload
 *   4. GET  /exam-intelligence-cms/documents/{id}             (poll extraction status)
 *   5. POST /exam-intelligence-cms/documents/{id}/link-to-syllabus    (reason ≥ 8 chars)
 *   6. POST /exam-intelligence-cms/documents/{id}/link-to-pyq-paper   (reason ≥ 8 chars)
 *
 * Steps 5 and 6 are TWO separate calls; no combined link endpoint exists.
 * Linking never auto-verifies: syllabus_documents land at trust_status='pending'.
 * After link-to-syllabus the syllabus-documents list reloads, unblocking the
 * Syllabus Mapper's DocumentSelector.
 *
 * No new or changed backend endpoints are introduced.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { api } from "../../../../lib/api";

const CMS     = "/api/admin/exam-intelligence-cms";
const DOC_BASE = `${CMS}/documents`;

const DOC_KINDS = ["syllabus", "pyq_paper", "notification", "corrigendum", "answer_key"];

const SOURCE_KINDS = [
  { value: "unknown",            label: "— not classified —" },
  { value: "official_archive",   label: "Official archive (authoritative)" },
  { value: "sanitized_coaching", label: "Sanitized coaching PDF" },
  { value: "raw_coaching",       label: "Raw coaching (not extractable until sanitized)" },
  { value: "sme_authored",       label: "SME-authored" },
  { value: "official_scan",      label: "Official scan" },
];

const EXAM_IDENTITIES = [
  "upsc_cse_prelims_gs1", "upsc_cse_prelims_csat",
  "upsc_cse_mains_essay", "upsc_cse_mains_gs1", "upsc_cse_mains_gs2",
  "upsc_cse_mains_gs3", "upsc_cse_mains_gs4",
  "upsc_cse_mains_optional_sociology", "upsc_cse_mains_optional_psir",
  "upsc_cse_mains_optional_history", "upsc_cse_mains_optional_anthropology",
  "upsc_cse_mains_optional_technical",
  "upsc_other", "state_psc_other", "banking_other", "unknown",
];

const EXAM_TO_FORMAT_DEFAULT = {
  upsc_cse_prelims_gs1:              "mcq_bilingual_two_column",
  upsc_cse_prelims_csat:             "mcq_bilingual_two_column",
  upsc_cse_mains_essay:              "essay_long_form",
  upsc_cse_mains_gs1:                "essay_long_form",
  upsc_cse_mains_gs2:                "essay_long_form",
  upsc_cse_mains_gs3:                "essay_long_form",
  upsc_cse_mains_gs4:                "essay_long_form",
  upsc_cse_mains_optional_sociology: "essay_long_form",
  upsc_cse_mains_optional_psir:      "essay_long_form",
  upsc_cse_mains_optional_history:   "essay_long_form",
  upsc_cse_mains_optional_anthropology: "essay_long_form",
  upsc_cse_mains_optional_technical: "technical_with_figures",
};

// Job statuses from document_processing_jobs.status that are terminal.
function isTerminalJobStatus(s) {
  return s === "succeeded" || s === "failed" || s === "skipped";
}
// document_assets.status values that are terminal.
function isTerminalDocStatus(s) {
  return s === "processed" || s === "failed";
}

// ─── ExtractionBadge ────────────────────────────────────────────────────────

function ExtractionBadge({ status }) {
  const map = {
    succeeded:  { cls: "badge resolved", text: "extracted" },
    processing: { cls: "badge pending",  text: "extracting…" },
    pending:    { cls: "badge pending",  text: "queued" },
    failed:     { cls: "badge blocker",  text: "failed" },
    verified:   { cls: "badge resolved", text: "verified" },
    rejected:   { cls: "badge blocker",  text: "rejected" },
  };
  const b = map[status] || { cls: "badge neutral", text: status ?? "—" };
  return <span className={b.cls}>{b.text}</span>;
}

// ─── UploadForm ──────────────────────────────────────────────────────────────
// Drives steps 1-3 of the upload flow. Calls onUploaded({ id, filename,
// document_kind, status:"processing", extraction:{}, page_count:null }) on
// success so the parent can start polling step 4.

function UploadForm({ exam, cycles, phases, defaultCycleId, onUploaded }) {
  const [kind, setKind]                   = useState("syllabus");
  const [sourceKind, setSourceKind]       = useState("unknown");
  const [examIdentity, setExamIdentity]   = useState("");
  const [structuralFormat, setStructFmt]  = useState("unknown");
  const [formatOverridden]               = useState(false);
  const [selectedCycleId, setSelectedCycleId] = useState(defaultCycleId || "");
  const [selectedPhaseId, setSelectedPhaseId] = useState("");
  const [file, setFile]                   = useState(null);
  const [busy, setBusy]                   = useState(false);
  const [err, setErr]                     = useState("");

  function handleIdentityChange(val) {
    setExamIdentity(val);
    if (!formatOverridden) {
      setStructFmt(EXAM_TO_FORMAT_DEFAULT[val] || "unknown");
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErr("");
    if (!file)                          { setErr("Choose a PDF file."); return; }
    if (file.type !== "application/pdf") { setErr("Only PDF files are accepted."); return; }

    setBusy(true);
    try {
      // Step 1 — mint signed URL + create document_assets row
      const signed = await api.post(`${DOC_BASE}/upload-url`, {
        exam_id:       exam?.id,
        exam_cycle_id: selectedCycleId || null,
        exam_phase_id: selectedPhaseId || null,
        document_kind: kind,
        filename:      file.name,
        mime_type:     file.type,
        size_bytes:    file.size,
        exam_identity:      examIdentity || null,
        structural_format:  structuralFormat || null,
        source_kind:        sourceKind || null,
      });

      // Step 2 — PUT bytes directly to storage (must bypass api wrapper; binary body)
      const put = await fetch(signed.upload_url, {
        method:  "PUT",
        headers: { "content-type": file.type },
        body:    file,
      });
      if (!put.ok) throw new Error(`Storage upload failed (${put.status})`);

      // Step 3 — complete upload: status → processing, enqueue extraction
      await api.post(`${DOC_BASE}/complete-upload`, { document_id: signed.document_id });

      onUploaded({
        id:            signed.document_id,
        filename:      file.name,
        document_kind: kind,
        status:        "processing",
        extraction:    {},
        page_count:    null,
      });
      setFile(null);
    } catch (ex) {
      setErr(ex?.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="card"
      style={{ borderStyle: "dashed" }}
      data-testid="doc-upload-form"
    >
      <div className="card-body">
        <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 14 }}>
          Upload exam-intelligence PDF
        </div>
        <div style={{ fontSize: 13, color: "var(--ink-mute)", marginBottom: 12 }} data-testid="doc-upload-exam-label">
          Exam: {exam?.name ?? exam?.id ?? "—"}
        </div>

        <div style={{ fontSize: 12, color: "var(--ink-mute)", marginBottom: 10 }}>
          Syllabus is exam-level unless this document is cycle-specific.
        </div>

        <div className="row" style={{ flexWrap: "wrap", gap: 10, marginBottom: 12 }}>
          <label style={{ flex: "1 1 150px" }}>
            <div className="field-lbl">
              Document kind <span style={{ color: "var(--ink-accent)" }}>*</span>
            </div>
            <select
              className="field"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
              data-testid="doc-kind"
            >
              {DOC_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </label>

          <label style={{ flex: "1 1 220px" }}>
            <div className="field-lbl">
              Source kind <span style={{ color: "var(--ink-accent)" }}>*</span>
            </div>
            <select
              className="field"
              value={sourceKind}
              onChange={(e) => setSourceKind(e.target.value)}
              data-testid="doc-source-kind"
            >
              {SOURCE_KINDS.map((k) => (
                <option key={k.value} value={k.value}>{k.label}</option>
              ))}
            </select>
          </label>

          <label style={{ flex: "1 1 220px" }}>
            <div className="field-lbl">
              Exam identity{" "}
              <span style={{ color: "var(--ink-mute)", fontWeight: 400 }}>(optional)</span>
            </div>
            <select
              className="field"
              value={examIdentity}
              onChange={(e) => handleIdentityChange(e.target.value)}
              data-testid="doc-exam-identity"
            >
              <option value="">— not set —</option>
              {EXAM_IDENTITIES.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </label>
        </div>

        <div className="row" style={{ flexWrap: "wrap", gap: 10, marginBottom: 12 }}>
          <label style={{ flex: "1 1 200px" }}>
            <div className="field-lbl">
              Cycle{" "}
              <span style={{ color: "var(--ink-mute)", fontWeight: 400 }}>(optional — exam-level if blank)</span>
            </div>
            <select
              className="field"
              value={selectedCycleId}
              onChange={(e) => setSelectedCycleId(e.target.value)}
              data-testid="doc-cycle-select"
            >
              <option value="">Exam-level (no cycle)</option>
              {cycles.map((c) => (
                <option key={c.id} value={c.id}>{c.name ?? c.label ?? c.id}</option>
              ))}
            </select>
          </label>

          <label style={{ flex: "1 1 200px" }}>
            <div className="field-lbl">
              Phase{" "}
              <span style={{ color: "var(--ink-mute)", fontWeight: 400 }}>(optional)</span>
            </div>
            <select
              className="field"
              value={selectedPhaseId}
              onChange={(e) => setSelectedPhaseId(e.target.value)}
              data-testid="doc-phase-select"
            >
              <option value="">No phase</option>
              {phases.map((p) => (
                <option key={p.id} value={p.id}>{p.name ?? p.label ?? p.id}</option>
              ))}
            </select>
          </label>
        </div>

        <label style={{ display: "block", marginBottom: 12 }}>
          <div className="field-lbl">
            PDF file <span style={{ color: "var(--ink-accent)" }}>*</span>
          </div>
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            data-testid="doc-file"
            style={{ fontSize: 13 }}
          />
          {file && (
            <div style={{ fontSize: 12, color: "var(--ink-mute)", marginTop: 4 }}>
              {file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB
            </div>
          )}
        </label>

        {sourceKind === "raw_coaching" && (
          <div className="warn-row" data-testid="raw-coaching-warning" style={{ marginBottom: 10 }}>
            raw_coaching PDFs cannot be extracted until sanitized. Set source_kind to
            sanitized_coaching after removing watermarks.
          </div>
        )}

        {err && <div className="err-row" data-testid="doc-upload-err">{err}</div>}

        <button
          type="submit"
          className="btn small"
          disabled={busy}
          data-testid="doc-upload-submit"
        >
          {busy ? "Uploading…" : "Upload PDF"}
        </button>
      </div>
    </form>
  );
}

// ─── LinkForm ────────────────────────────────────────────────────────────────
// Drives steps 5 or 6.  For syllabus kinds, omitting syllabus_document_id causes
// the backend to auto-create a new syllabus_documents row (trust_status='pending').
// For pyq_paper a pyq_paper_id is required.

function LinkForm({ docId, docKind, pyqPapers, onLink, onCancel }) {
  const [reason,   setReason]   = useState("");
  const [targetId, setTargetId] = useState("");
  const [busy,     setBusy]     = useState(false);
  const [err,      setErr]      = useState("");

  const isPyq = docKind === "pyq_paper";

  async function handleSubmit(e) {
    e.preventDefault();
    setErr("");
    if (reason.trim().length < 8) {
      setErr("Reason must be at least 8 characters.");
      return;
    }
    if (isPyq && !targetId) {
      setErr("Select a PYQ paper to link to.");
      return;
    }
    setBusy(true);
    try {
      if (isPyq) {
        // Step 6 — link-to-pyq-paper (requires existing pyq_paper_id)
        await api.post(`${DOC_BASE}/${docId}/link-to-pyq-paper`, {
          reason:       reason.trim(),
          pyq_paper_id: targetId,
        });
      } else {
        // Step 5 — link-to-syllabus; omit syllabus_document_id → backend creates new row
        await api.post(`${DOC_BASE}/${docId}/link-to-syllabus`, {
          reason: reason.trim(),
        });
      }
      onLink();
    } catch (ex) {
      setErr(ex?.message || "Link failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} data-testid={`doc-link-form-${docId}`}>
      <div className="row" style={{ flexWrap: "wrap", gap: 8, alignItems: "flex-end" }}>
        {isPyq && (
          <label style={{ flex: "1 1 200px" }}>
            <div className="field-lbl">PYQ paper</div>
            {pyqPapers.length === 0 ? (
              <div style={{ fontSize: 12, color: "var(--ink-mute)" }} data-testid={`doc-link-no-pyq-${docId}`}>
                No PYQ paper records for this exam — create one in Setup first.
              </div>
            ) : (
              <select
                className="field"
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                data-testid={`doc-link-pyq-select-${docId}`}
              >
                <option value="">— select —</option>
                {pyqPapers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {[p.year, p.paper_code, p.shift].filter(Boolean).join(" · ")}
                  </option>
                ))}
              </select>
            )}
          </label>
        )}

        <label style={{ flex: "1 1 240px" }}>
          <div className="field-lbl">
            Reason <span style={{ color: "var(--ink-mute)", fontWeight: 400 }}>(≥ 8 chars)</span>
          </div>
          <input
            type="text"
            className="field"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={
              isPyq
                ? "e.g. Linking uploaded PYQ paper PDF"
                : "e.g. Linking official syllabus PDF"
            }
            data-testid={`doc-link-reason-${docId}`}
          />
        </label>

        <div className="row" style={{ gap: 6 }}>
          <button
            type="submit"
            className="btn small"
            disabled={busy || (isPyq && pyqPapers.length === 0)}
            data-testid={`doc-link-submit-${docId}`}
          >
            {busy
              ? "Linking…"
              : isPyq
              ? "Link to PYQ paper"
              : "Link to syllabus"}
          </button>
          <button
            type="button"
            className="btn small"
            onClick={onCancel}
            data-testid={`doc-link-cancel-${docId}`}
          >
            Cancel
          </button>
        </div>
      </div>

      {err && (
        <div className="err-row" style={{ marginTop: 6 }} data-testid={`doc-link-err-${docId}`}>
          {err}
        </div>
      )}
    </form>
  );
}

// ─── DocumentsPanel (main) ───────────────────────────────────────────────────

export default function DocumentsPanel({ onGotoTab, documentId = null, docStatus = null }) {
  const { exam, cycle, cycles, phases } = useExamWorkspace();

  // ── Linked docs (syllabus_documents + pyq_papers tables) ────────────────
  const [docs,      setDocs]      = useState([]);   // syllabus_documents rows
  const [papers,    setPapers]    = useState([]);   // pyq_papers rows
  const [loading,   setLoading]   = useState(false);
  const [listError, setListError] = useState("");

  // ── Upload UI ────────────────────────────────────────────────────────────
  const [formOpen, setFormOpen] = useState(false);

  // ── In-flight uploads: document_assets rows awaiting link ────────────────
  // Shape: { id, filename, document_kind, status, extraction:{}, page_count }
  const [inFlight,  setInFlight]  = useState([]);
  const pollRefs = useRef({});   // { [docId]: intervalId } — ref, not state

  // ── Link UI ──────────────────────────────────────────────────────────────
  const [linkingId,  setLinkingId]  = useState(null);
  const [pyqPapers,  setPyqPapers]  = useState([]);

  // ── Deep-link: asset fetched by document_assets.id ───────────────────────
  const [linkedAsset,        setLinkedAsset]        = useState(null);
  const [linkedAssetLoading, setLinkedAssetLoading] = useState(false);
  const [deepLinkNotFound,   setDeepLinkNotFound]   = useState(false);

  // ── Load linked docs ──────────────────────────────────────────────────────

  const load = useCallback(async () => {
    if (!exam?.id) return;
    setLoading(true);
    setListError("");
    try {
      const qs = new URLSearchParams({ exam_id: exam.id, limit: "100" });
      if (cycle?.id) qs.set("cycle_id", cycle.id);
      const [sylResult, pyqResult] = await Promise.all([
        api.get(`${CMS}/syllabus-documents?${qs}`),
        api.get(`${CMS}/pyq-papers?${qs}`),
      ]);
      setDocs(sylResult?.items   || sylResult   || []);
      setPapers(pyqResult?.items || pyqResult   || []);
    } catch (e) {
      setListError(e?.message || "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [exam?.id, cycle?.id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!documentId) { setLinkedAsset(null); setDeepLinkNotFound(false); return; }
    let cancelled = false;
    setLinkedAssetLoading(true);
    api.get(`${DOC_BASE}/${encodeURIComponent(documentId)}`)
      .then((r) => {
        if (cancelled) return;
        setLinkedAsset(r);
        setDeepLinkNotFound(false);
      })
      .catch(() => {
        if (cancelled) return;
        setLinkedAsset(null);
        setDeepLinkNotFound(true);
      })
      .finally(() => { if (!cancelled) setLinkedAssetLoading(false); });
    return () => { cancelled = true; };
  }, [documentId]);

  // ── Stop all polls on unmount ─────────────────────────────────────────────

  useEffect(() => {
    const refs = pollRefs.current;
    return () => { Object.values(refs).forEach(clearInterval); };
  }, []);

  // ── Step 4: poll extraction status for one in-flight doc ─────────────────

  const refreshInFlight = useCallback(async (docId) => {
    try {
      const r = await api.get(`${DOC_BASE}/${docId}`);
      const docStatus = r?.document?.status;
      const jobStatus = r?.extraction?.status;
      const pageCount = r?.pages_count ?? null;
      setInFlight((prev) =>
        prev.map((d) =>
          d.id === docId
            ? { ...d, status: docStatus, extraction: r?.extraction || {}, page_count: pageCount }
            : d,
        ),
      );
      if (isTerminalDocStatus(docStatus) || isTerminalJobStatus(jobStatus)) {
        clearInterval(pollRefs.current[docId]);
        delete pollRefs.current[docId];
      }
    } catch {
      // silent — keep polling
    }
  }, []);

  function startPoll(docId) {
    if (pollRefs.current[docId]) clearInterval(pollRefs.current[docId]);
    const id = setInterval(() => refreshInFlight(docId), 3000);
    pollRefs.current[docId] = id;
  }

  // ── After upload completes (step 3 returned ok) ───────────────────────────

  function handleUploaded(doc) {
    setInFlight((prev) => [...prev, doc]);
    setFormOpen(false);
    startPoll(doc.id);
  }

  // ── Open inline link form ─────────────────────────────────────────────────

  async function openLink(doc) {
    setLinkingId(doc.id);
    if (doc.document_kind === "pyq_paper") {
      try {
        const qs = new URLSearchParams({ exam_id: exam.id, limit: "100" });
        if (cycle?.id) qs.set("cycle_id", cycle.id);
        const r = await api.get(`${CMS}/pyq-papers?${qs}`);
        setPyqPapers(r?.items || r || []);
      } catch {
        setPyqPapers([]);
      }
    } else {
      setPyqPapers([]);
    }
  }

  function cancelLink() {
    setLinkingId(null);
    setPyqPapers([]);
  }

  // ── After successful link (step 5 or 6) ──────────────────────────────────

  async function handleLinkDone(docId) {
    if (pollRefs.current[docId]) {
      clearInterval(pollRefs.current[docId]);
      delete pollRefs.current[docId];
    }
    setInFlight((prev) => prev.filter((d) => d.id !== docId));
    setLinkingId(null);
    setPyqPapers([]);
    // Reload linked docs — this populates the Syllabus Mapper's DocumentSelector
    await load();
  }

  // ── Derived display data ──────────────────────────────────────────────────

  const linkedDocs = [
    ...docs.map((d) => ({ ...d, _kind: "syllabus" })),
    ...papers.map((p) => ({ ...p, _kind: "pyq" })),
  ];
  const hasProcessing = linkedDocs.some(
    (d) => d.extraction_status === "processing" || d.extraction_status === "pending",
  );

  // ── Shared header ─────────────────────────────────────────────────────────

  const header = (
    <div className="scrn-head">
      <div>
        <div className="scrn-tag">Always open · source documents</div>
        <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>
          Documents &amp; extraction
        </h2>
      </div>
      <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
        <button className="btn small" onClick={load} data-testid="doc-refresh">
          Refresh
        </button>
        <button
          className="btn small"
          onClick={() => setFormOpen((v) => !v)}
          data-testid="doc-toggle-upload"
        >
          {formOpen ? "Cancel upload" : "↑ Upload PDF"}
        </button>
      </div>
    </div>
  );

  // ── Loading skeleton ──────────────────────────────────────────────────────

  if (loading && linkedDocs.length === 0 && inFlight.length === 0) {
    return (
      <div className="stack" data-testid="docs-loading">
        <div className="scrn-head">
          <div>
            <div className="scrn-tag">Always open · source documents</div>
            <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>Documents</h2>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="skel" style={{ height: 20, marginBottom: 10 }} />
            <div className="skel" style={{ height: 20, marginBottom: 10 }} />
            <div className="skel" style={{ height: 20 }} />
          </div>
        </div>
      </div>
    );
  }

  // ── Empty state ───────────────────────────────────────────────────────────

  if (!loading && linkedDocs.length === 0 && inFlight.length === 0) {
    return (
      <div className="stack" data-testid="docs-empty">
        {header}
        {listError && (
          <div className="err-row" data-testid="docs-list-error">{listError}</div>
        )}
        {linkedAssetLoading && (
          <div className="skel" style={{ height: 40, marginBottom: 8 }} data-testid="doc-deep-link-loading" />
        )}
        {linkedAsset && !linkedAssetLoading && (
          <div
            className="card"
            style={{ outline: "2px solid var(--ink-accent)", background: "var(--paper-light)" }}
            data-testid="doc-deep-link-asset"
          >
            <div className="card-body" style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>
                  {linkedAsset.document?.title || linkedAsset.document?.original_filename || documentId}
                </div>
                {docStatus && (
                  <div style={{ fontSize: 11, color: "var(--ink-mute)", marginTop: 2 }}>
                    Extraction status: {docStatus}
                  </div>
                )}
              </div>
              <ExtractionBadge status={linkedAsset.extraction?.status || docStatus || "unknown"} />
            </div>
          </div>
        )}
        {deepLinkNotFound && (
          <div className="warn-row" data-testid="doc-deep-link-not-found">
            Document {documentId} was not found.
          </div>
        )}
        <div className="card" style={{ borderStyle: "dashed" }}>
          <div className="empty" style={{ padding: "28px 18px" }}>
            <div className="empty-title" data-testid="docs-empty-title">
              Upload syllabus PDF to enable Syllabus Mapper
            </div>
            <div style={{ maxWidth: 440, margin: "0 auto 16px", fontSize: 13 }}>
              Upload the official syllabus or a PYQ paper PDF, then link it. The Syllabus
              Mapper and PYQ Workbench require at least one linked document. Uploaded
              documents land pending review — linking does not auto-verify.
            </div>
          </div>
        </div>
        <UploadForm
          exam={exam}
          cycles={cycles ?? []}
          phases={phases ?? []}
          defaultCycleId={cycle?.id}
          onUploaded={handleUploaded}
        />
      </div>
    );
  }

  // ── Populated state ───────────────────────────────────────────────────────

  return (
    <div className="stack" data-testid="docs-populated">
      {header}
      {listError && (
        <div className="err-row" data-testid="docs-list-error">{listError}</div>
      )}
      {linkedAssetLoading && (
        <div className="skel" style={{ height: 40, marginBottom: 8 }} data-testid="doc-deep-link-loading" />
      )}
      {linkedAsset && !linkedAssetLoading && (
        <div
          className="card"
          style={{ outline: "2px solid var(--ink-accent)", background: "var(--paper-light)" }}
          data-testid="doc-deep-link-asset"
        >
          <div className="card-body" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>
                {linkedAsset.document?.title || linkedAsset.document?.original_filename || documentId}
              </div>
              {docStatus && (
                <div style={{ fontSize: 11, color: "var(--ink-mute)", marginTop: 2 }}>
                  Extraction status: {docStatus}
                </div>
              )}
            </div>
            <ExtractionBadge status={linkedAsset.extraction?.status || docStatus || "unknown"} />
          </div>
        </div>
      )}
      {deepLinkNotFound && (
        <div className="warn-row" data-testid="doc-deep-link-not-found">
          Document {documentId} was not found.
        </div>
      )}

      {/* In-flight uploads: document_assets pending link (steps 3-6) */}
      {inFlight.length > 0 && (
        <div className="card">
          <div className="card-body" style={{ paddingBottom: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
              Uploaded — pending link
            </div>
          </div>
          <table className="t" data-testid="inflight-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Kind</th>
                <th>Extraction</th>
                <th>Pages</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {inFlight.map((d) => {
                const jobStatus = d.extraction?.status || null;
                const badge = d.status === "processing"
                  ? (jobStatus || "pending")
                  : (d.status || "pending");
                return (
                  <React.Fragment key={d.id}>
                    <tr data-testid={`inflight-row-${d.id}`}>
                      <td>
                        <div className="row-ttl">{d.filename}</div>
                      </td>
                      <td>
                        <span className="badge neutral no-dot">{d.document_kind}</span>
                      </td>
                      <td><ExtractionBadge status={badge} /></td>
                      <td className="num">{d.page_count ?? "—"}</td>
                      <td style={{ textAlign: "right" }}>
                        <button
                          className="btn small"
                          onClick={() => openLink(d)}
                          disabled={linkingId !== null}
                          data-testid={`doc-link-open-${d.id}`}
                        >
                          Link →
                        </button>
                      </td>
                    </tr>

                    {linkingId === d.id && (
                      <tr data-testid={`doc-link-row-${d.id}`}>
                        <td
                          colSpan={5}
                          style={{ padding: "10px 12px", background: "var(--paper-light)" }}
                        >
                          <LinkForm
                            docId={d.id}
                            docKind={d.document_kind}
                            pyqPapers={pyqPapers}
                            onLink={() => handleLinkDone(d.id)}
                            onCancel={cancelLink}
                          />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Linked source documents (syllabus_documents + pyq_papers) */}
      {linkedDocs.length > 0 && (
        <div className="card">
          <table className="t" data-testid="linked-docs-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Kind</th>
                <th>Pages</th>
                <th>Trust</th>
                <th>Added</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {linkedDocs.map((d) => {
                const name =
                  d.title ??
                  d.document_name ?? d.file_name ?? d.label ??
                  [d.year, d.paper_code, d.shift].filter(Boolean).join(" · ") ??
                  d.id;
                const pages = d.page_count ?? d.pages ?? "—";
                const trust = d.trust_status ?? null;
                const added = d.created_at
                  ? new Date(d.created_at).toLocaleDateString("en-IN", {
                      day: "numeric", month: "short", year: "numeric",
                    })
                  : "—";
                return (
                  <tr
                    key={d.id}
                    data-testid={`linked-doc-row-${d.id}`}
                    style={d.id === documentId ? { background: "var(--paper-light)", outline: "2px solid var(--ink-accent)" } : undefined}
                  >
                    <td>
                      <div className="row-ttl">{name}</div>
                      {d.source_url && (
                        <div
                          className="row-sub"
                          style={{ wordBreak: "break-all" }}
                        >
                          {d.source_url}
                        </div>
                      )}
                    </td>
                    <td>
                      <span className="badge neutral no-dot">{d._kind}</span>
                    </td>
                    <td className="num">{pages}</td>
                    <td>
                      {trust
                        ? <ExtractionBadge status={trust} />
                        : <span className="badge neutral no-dot">—</span>}
                    </td>
                    <td className="num" style={{ color: "var(--ink-mute)" }}>
                      {added}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {d._kind === "syllabus" && (
                        <button
                          className="btn small"
                          onClick={() => onGotoTab && onGotoTab("syllabus")}
                          data-testid={`doc-goto-syllabus-${d.id}`}
                        >
                          Map →
                        </button>
                      )}
                      {d._kind === "pyq" && (
                        <button
                          className="btn small"
                          onClick={() => onGotoTab && onGotoTab("pyq")}
                          data-testid={`doc-goto-pyq-${d.id}`}
                        >
                          Review →
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {hasProcessing && (
        <div className="warn-row">
          One or more documents are still extracting — mappings stay unavailable until
          extraction succeeds.
        </div>
      )}

      {/* Upload form (collapsible when docs already exist) */}
      {formOpen && (
        <UploadForm
          exam={exam}
          cycles={cycles ?? []}
          phases={phases ?? []}
          defaultCycleId={cycle?.id}
          onUploaded={handleUploaded}
        />
      )}
    </div>
  );
}
