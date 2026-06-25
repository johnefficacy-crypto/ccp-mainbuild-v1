import React, { useEffect, useRef, useState } from "react";
import { getApiBlockingFields } from "../../../../lib/api";
import PyqProvenanceFields from "./PyqProvenanceFields";

// ─── AddPyqPaperModal ────────────────────────────────────────────────────────
// Guided "Add PYQ paper" form embedded in the PYQ Workbench (no new route).
// Composes the shared PyqProvenanceFields for the source step and the evidence
// (document picker) step. Picker-only (OD-4) and select-only (OD-5): there is
// NO raw-UUID input and NO inline upload. Exam is prefilled+immutable from
// context; a selected cycle prefills exam_cycle_id/exam_phase_id provenance.
//
// On submit it builds the LOCKED /pyq-onboarding contract body and calls
// onboardPaper(body); the returned paper.id is handed to onSuccess.

export default function AddPyqPaperModal({
  examId,
  examName,
  cycleId = null,
  phaseId = null,
  pyqDocuments,
  pyqSources,
  onboardPaper,
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

  // ── Evidence step (reuses the document picker) ──
  const [documentId, setDocumentId] = useState("");

  // ── Audit ──
  const [reason, setReason] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState(null);

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

        {/* Exam is prefilled + immutable from context */}
        <p className="text-xs text-gray-500" data-testid="add-pyq-exam-immutable">
          Exam is set from this workspace and cannot be changed here.
        </p>

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

        {/* ── Evidence step (reuses the document picker; select-only) ── */}
        <fieldset className="flex flex-col gap-3 border border-gray-200 rounded p-3">
          <legend className="px-1 text-xs font-medium text-gray-500">Evidence (uploaded document)</legend>
          <PyqProvenanceFields
            idPrefix="add-pyq-evidence"
            documentId={documentId}
            onDocumentIdChange={setDocumentId}
            pyqDocuments={pyqDocuments}
            show={{ sourceType: false, sourceUrl: false, pyqSource: false }}
          />
          <p className="text-xs text-gray-400">
            Upload the PDF in the Documents tab first; only existing exam documents appear here.
          </p>
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
