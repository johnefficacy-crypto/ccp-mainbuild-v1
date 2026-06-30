import React, { useEffect, useRef, useState } from "react";
import { getApiBlockingFields } from "../../../../lib/api";
import PyqProvenanceFields from "./PyqProvenanceFields";

// ─── AddPyqPaperModal ────────────────────────────────────────────────────────
// Guided "Add PYQ paper" form embedded in the PYQ Workbench (no new route).
// Composes the shared PyqProvenanceFields for the source step and the evidence
// (document picker) step. Picker-only for the raw UUID (OD-4): there is NO
// raw-UUID input. Exam is prefilled+immutable from context; a selected cycle
// prefills exam_cycle_id/exam_phase_id provenance.
//
// Evidence step (OD-5 follow-up): the default is "Select existing" (the #763
// exam-scoped picker). An "Upload new PDF" alternative runs the upload sequence
// inline (via uploadPyqDocument from the hook) and, on completion, sets the
// selected document_id to the freshly-created asset so submit links it.
//
// On submit it builds the LOCKED /pyq-onboarding contract body and calls
// onboardPaper(body); the returned paper.id is handed to onSuccess.

const UPLOAD_PHASE_LABEL = {
  "requesting-url": "Requesting upload URL…",
  uploading: "Uploading PDF…",
  completing: "Finalizing upload…",
  extracting: "Extracting…",
  ready: "Extraction complete",
  failed: "Extraction failed",
};

export default function AddPyqPaperModal({
  examId,
  examName,
  cycleId = null,
  phaseId = null,
  cycleLabel = null,
  phaseLabel = null,
  pyqDocuments,
  pyqSources,
  onboardPaper,
  uploadPyqDocument,
  onCancel,
  onSuccess,
}) {
  // ── Paper identity ──
  const [year, setYear] = useState("");
  const [paperDate, setPaperDate] = useState("");
  const [shift, setShift] = useState("");
  const [paperCode, setPaperCode] = useState("");
  const [expectedCount, setExpectedCount] = useState("");

  // ── Source step (reuses PyqProvenanceFields) ──
  const [existingSourceId, setExistingSourceId] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [sourceTitle, setSourceTitle] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [registrySourceId, setRegistrySourceId] = useState("");

  // ── Evidence step (reuses the document picker; OD-5 follow-up adds upload) ──
  const [documentId, setDocumentId] = useState("");
  // "select" (default — existing exam-scoped picker) | "upload" (inline upload)
  const [evidenceMode, setEvidenceMode] = useState("select");
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadPhase, setUploadPhase] = useState(null);
  const [uploadErr, setUploadErr] = useState(null);
  // Docs uploaded inline this session, so the picker label can resolve the new
  // asset even though the parent's pyqDocuments list has not refetched.
  const [uploadedDocs, setUploadedDocs] = useState([]);

  // ── Audit ──
  const [reason, setReason] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState(null);

  const uploadInputRef = useRef(null);

  async function handleInlineUpload() {
    setUploadErr(null);
    if (!uploadFile) { setUploadErr("Choose a PDF file."); return; }
    if (uploadFile.type !== "application/pdf") { setUploadErr("Only PDF files are accepted."); return; }
    if (typeof uploadPyqDocument !== "function") { setUploadErr("Upload is unavailable."); return; }
    setUploading(true);
    setUploadPhase("requesting-url");
    try {
      const result = await uploadPyqDocument(uploadFile, {
        onProgress: (p) => setUploadPhase(p?.phase ?? null),
      });
      if (!result?.id) throw new Error("Upload did not return a document.");
      if (result.ok === false) {
        // Terminal extraction failure. The backend provenance gate rejects
        // failed documents, so do NOT link it or present a success state —
        // surface the error and leave the evidence step unset.
        setUploadErr("Extraction failed for this PDF. Try another file or use the Documents tab.");
        return;
      }
      // Link the freshly uploaded asset for onboarding.
      setDocumentId(result.id);
      setUploadedDocs((prev) =>
        prev.some((d) => d.id === result.id)
          ? prev
          : [...prev, {
              id: result.id,
              original_filename: uploadFile.name,
              page_count: null,
              status: result.status ?? "processing",
            }],
      );
    } catch (ex) {
      setUploadErr(ex?.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  // Picker options = parent-provided exam docs + any uploaded inline this session.
  const pickerDocuments = [
    ...(pyqDocuments || []),
    ...uploadedDocs.filter((u) => !(pyqDocuments || []).some((d) => d.id === u.id)),
  ];

  const yearRef = useRef(null);
  useEffect(() => { yearRef.current?.focus(); }, []);

  // When an existing reusable source is picked, the inline source fields are
  // not used to create a new source — make that visually clear by collapsing
  // them. They re-enable when no existing source is selected.
  const usingExistingSource = Boolean(existingSourceId);

  async function handleSubmit(e) {
    e.preventDefault();
    setErr(null);

    const yearInt = parseInt(year, 10);
    if (!year || Number.isNaN(yearInt)) {
      setErr("Year is required and must be a number.");
      return;
    }
    if (reason.trim().length < 8) {
      setErr("Reason must be at least 8 characters.");
      return;
    }

    // Build the source block per the LOCKED contract. null when nothing given.
    let source = null;
    if (usingExistingSource) {
      source = {
        existing_pyq_source_id: existingSourceId,
        source_id: null,
        source_type: sourceType || null,
        title: null,
        source_url: null,
        metadata: {},
      };
    } else if (sourceType || sourceTitle.trim() || sourceUrl.trim() || registrySourceId) {
      source = {
        existing_pyq_source_id: null,
        // CANONICAL registry FK is source.source_id (NOT source_registry_id).
        source_id: registrySourceId || null,
        source_type: sourceType || null,
        title: sourceTitle.trim() || null,
        source_url: sourceUrl.trim() || null,
        metadata: {},
      };
    }

    const expectedInt =
      expectedCount === "" ? null : parseInt(expectedCount, 10);

    const body = {
      reason: reason.trim(),
      exam_id: examId,
      exam_cycle_id: cycleId || null,
      exam_phase_id: phaseId || null,
      source,
      paper: {
        year: yearInt,
        paper_date: paperDate.trim() || null,
        shift: shift.trim() || null,
        paper_code: paperCode.trim() || null,
        // Paper-level provenance mirrors the chosen source anchor so a paper
        // can be complete (OD-1) even without a reusable source record.
        source_url: sourceUrl.trim() || null,
        source_type: sourceType || null,
        metadata: {
          expected_question_count: Number.isNaN(expectedInt) ? null : expectedInt,
        },
      },
      document_id: documentId || null,
    };

    setSubmitting(true);
    try {
      const newPaperId = await onboardPaper(body);
      onSuccess(newPaperId);
    } catch (ex) {
      const fields = getApiBlockingFields(ex);
      if (fields.length > 0) {
        setErr(`Onboarding blocked — fix: ${fields.join(", ")}`);
      } else {
        setErr(ex?.message || "Failed to add paper");
      }
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" data-testid="add-pyq-paper-modal">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-lg shadow-xl w-full max-w-xl p-6 flex flex-col gap-4 max-h-[90vh] overflow-y-auto"
      >
        <h2 className="text-base font-semibold text-gray-800">
          Add PYQ paper{examName ? ` — ${examName}` : ""}
        </h2>

        {/* Exam / cycle / phase context — immutable from workspace */}
        <p className="text-xs text-gray-500" data-testid="add-pyq-exam-immutable">
          Exam is set from this workspace and cannot be changed here.
        </p>
        <div className="text-xs text-gray-500 flex gap-4" data-testid="add-pyq-cycle-context">
          <span data-testid="add-pyq-cycle-label">
            Cycle: {cycleLabel ?? "All cycles"}
          </span>
          <span data-testid="add-pyq-phase-label">
            Phase: {phaseLabel ?? "No phase selected"}
          </span>
        </div>

        {/* ── Paper identity ── */}
        <fieldset className="flex flex-col gap-3 border border-gray-200 rounded p-3">
          <legend className="px-1 text-xs font-medium text-gray-500">Paper</legend>
          <label className="flex flex-col gap-1 text-sm text-gray-700">
            Year <span className="text-gray-400 font-normal">(required)</span>
            <input
              ref={yearRef}
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
              placeholder="2024"
              data-testid="add-pyq-year"
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1 text-sm text-gray-700">
              Paper date <span className="text-gray-400 font-normal">(optional)</span>
              <input
                type="text"
                value={paperDate}
                onChange={(e) => setPaperDate(e.target.value)}
                className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
                placeholder="2024-06-16"
                data-testid="add-pyq-paper-date"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-gray-700">
              Shift <span className="text-gray-400 font-normal">(optional)</span>
              <input
                type="text"
                value={shift}
                onChange={(e) => setShift(e.target.value)}
                className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
                placeholder="Morning"
                data-testid="add-pyq-shift"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-gray-700">
              Paper code <span className="text-gray-400 font-normal">(optional)</span>
              <input
                type="text"
                value={paperCode}
                onChange={(e) => setPaperCode(e.target.value)}
                className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
                placeholder="GS-I"
                data-testid="add-pyq-paper-code"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-gray-700">
              Expected questions <span className="text-gray-400 font-normal">(optional)</span>
              <input
                type="number"
                value={expectedCount}
                onChange={(e) => setExpectedCount(e.target.value)}
                className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
                placeholder="100"
                data-testid="add-pyq-expected-count"
              />
            </label>
          </div>
        </fieldset>

        {/* ── Source step (offered first; optional per OD-1) ── */}
        <fieldset className="flex flex-col gap-3 border border-gray-200 rounded p-3">
          <legend className="px-1 text-xs font-medium text-gray-500">Source (optional, recommended)</legend>

          {/* Pick an existing reusable pyq_source */}
          {(pyqSources || []).length > 0 && (
            <label className="flex flex-col gap-1 text-sm text-gray-700">
              Reuse existing source record <span className="text-gray-400 font-normal">(optional)</span>
              <select
                value={existingSourceId}
                onChange={(e) => setExistingSourceId(e.target.value)}
                className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
                data-testid="add-pyq-existing-source-id"
              >
                <option value="">— create new or none —</option>
                {(pyqSources || []).map((s) => (
                  <option key={s.id} value={s.id} title={s.title || s.source_url || s.id}>
                    {s.title || s.source_url || s.id}
                  </option>
                ))}
              </select>
            </label>
          )}

          {/* New-source fields — collapse when reusing an existing record. */}
          {!usingExistingSource && (
            <>
              <PyqProvenanceFields
                idPrefix="add-pyq-source"
                sourceType={sourceType}
                onSourceTypeChange={setSourceType}
                sourceUrl={sourceUrl}
                onSourceUrlChange={setSourceUrl}
                pyqSourceId={registrySourceId}
                onPyqSourceIdChange={setRegistrySourceId}
                pyqSources={pyqSources}
                show={{ document: false }}
              />
              <label className="flex flex-col gap-1 text-sm text-gray-700">
                Source title <span className="text-gray-400 font-normal">(optional)</span>
                <input
                  type="text"
                  value={sourceTitle}
                  onChange={(e) => setSourceTitle(e.target.value)}
                  className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
                  placeholder="UPSC Official 2024"
                  data-testid="add-pyq-source-title"
                />
              </label>
            </>
          )}
        </fieldset>

        {/* ── Evidence step (document picker default; inline upload alt — OD-5) ── */}
        <fieldset className="flex flex-col gap-3 border border-gray-200 rounded p-3">
          <legend className="px-1 text-xs font-medium text-gray-500">Evidence (uploaded document)</legend>

          {/* Mode toggle: select existing (default) vs upload new PDF */}
          <div className="flex gap-2" role="radiogroup" aria-label="Evidence source">
            <button
              type="button"
              onClick={() => setEvidenceMode("select")}
              className={`text-xs px-2.5 py-1 rounded border ${
                evidenceMode === "select"
                  ? "border-indigo-400 bg-indigo-50 text-indigo-700"
                  : "border-gray-300 text-gray-600 hover:bg-gray-50"
              }`}
              data-testid="add-pyq-evidence-mode-select"
              aria-pressed={evidenceMode === "select"}
            >
              Select existing
            </button>
            <button
              type="button"
              onClick={() => setEvidenceMode("upload")}
              className={`text-xs px-2.5 py-1 rounded border ${
                evidenceMode === "upload"
                  ? "border-indigo-400 bg-indigo-50 text-indigo-700"
                  : "border-gray-300 text-gray-600 hover:bg-gray-50"
              }`}
              data-testid="add-pyq-evidence-mode-upload"
              aria-pressed={evidenceMode === "upload"}
            >
              Upload new PDF
            </button>
          </div>

          {evidenceMode === "select" ? (
            <>
              <PyqProvenanceFields
                idPrefix="add-pyq-evidence"
                documentId={documentId}
                onDocumentIdChange={setDocumentId}
                pyqDocuments={pickerDocuments}
                show={{ sourceType: false, sourceUrl: false, pyqSource: false }}
              />
              <p className="text-xs text-gray-400">
                Existing exam documents appear here. Or choose “Upload new PDF” to add one now.
              </p>
            </>
          ) : (
            <div className="flex flex-col gap-2" data-testid="add-pyq-upload-panel">
              <input
                ref={uploadInputRef}
                type="file"
                accept="application/pdf,.pdf"
                onChange={(e) => { setUploadFile(e.target.files?.[0] || null); setUploadErr(null); }}
                className="text-sm"
                data-testid="add-pyq-upload-file"
                disabled={uploading}
              />
              {uploadFile && (
                <div className="text-xs text-gray-500">
                  {uploadFile.name} · {(uploadFile.size / 1024 / 1024).toFixed(2)} MB
                </div>
              )}
              <button
                type="button"
                onClick={handleInlineUpload}
                disabled={uploading || !uploadFile}
                className="self-start text-xs px-3 py-1.5 rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                data-testid="add-pyq-upload-submit"
              >
                {uploading ? "Uploading…" : "Upload PDF"}
              </button>
              {uploadPhase && (
                <p className="text-xs text-gray-500" data-testid="add-pyq-upload-status">
                  {UPLOAD_PHASE_LABEL[uploadPhase] ?? uploadPhase}
                </p>
              )}
              {documentId && uploadedDocs.some((d) => d.id === documentId) && (
                <p className="text-xs text-emerald-600" data-testid="add-pyq-upload-linked">
                  Uploaded document linked — it will be attached on submit.
                </p>
              )}
              {uploadErr && (
                <p className="text-xs text-rose-600" data-testid="add-pyq-upload-error">{uploadErr}</p>
              )}
            </div>
          )}
        </fieldset>

        {/* ── Reason ── */}
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Reason <span className="text-gray-400 font-normal">(required, ≥ 8 chars)</span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none resize-none"
            placeholder="e.g. Added official 2024 paper from commission archive"
            data-testid="add-pyq-reason"
          />
        </label>

        {err && <p className="text-xs text-rose-600" data-testid="add-pyq-error">{err}</p>}

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-700 hover:bg-gray-50">
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-3 py-1.5 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
            data-testid="add-pyq-submit"
          >
            {submitting ? "Adding…" : "Add paper"}
          </button>
        </div>
      </form>
    </div>
  );
}
