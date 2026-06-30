import React, { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { useAuth } from "../../../../lib/authContext";
import { usePyqWorkbench } from "./usePyqWorkbench";
import { getApiBlockingFields } from "../../../../lib/api";
import BulkImportModal from "./bulk-import/BulkImportModal";
import PyqMockProjectionPanel from "./PyqMockProjectionPanel";
import PyqProvenanceFields from "./PyqProvenanceFields";
import AddPyqPaperModal from "./AddPyqPaperModal";

const PyqPaperWorkspace = lazy(() => import("../../studyos/PyqPaperWorkspace"));

const TRUST_LABEL = {
  verified: "Verified",
  rejected: "Rejected",
  pending: "Pending",
};

export function isPaperProvenanceComplete(paper) {
  const validSourceType = Boolean(paper?.source_type) && paper.source_type !== "unknown";
  const hasExactAnchor = Boolean(paper?.source_document_id) || Boolean(paper?.source_url?.trim());
  return validSourceType && hasExactAnchor;
}

function PaperReviewModal({ paper, targetStatus, onCancel, onSubmit }) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState(null);
  const textareaRef = useRef(null);

  useEffect(() => { textareaRef.current?.focus(); }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (reason.trim().length < 8) { setErr("Reason must be at least 8 characters."); return; }
    setSubmitting(true);
    setErr(null);
    try {
      await onSubmit(paper.id, targetStatus, reason.trim());
    } catch (ex) {
      setErr(ex?.message || "Review failed");
      setSubmitting(false);
    }
  }

  const REVIEW_ACTION = {
    verified: { label: "Verify",   btnClass: "px-3 py-1.5 text-sm rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50" },
    rejected: { label: "Reject",   btnClass: "px-3 py-1.5 text-sm rounded bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50" },
    pending:  { label: "Re-queue", btnClass: "px-3 py-1.5 text-sm rounded bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50" },
  };
  const { label, btnClass } = REVIEW_ACTION[targetStatus] ?? REVIEW_ACTION.rejected;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" data-testid="paper-review-modal">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 flex flex-col gap-4"
      >
        <h2 className="text-base font-semibold text-gray-800">
          {label} paper — {paper.year ?? "—"} {[paper.paper_code, paper.shift].filter(Boolean).join(" · ")}
        </h2>
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Reason <span className="text-gray-400 font-normal">(required, ≥ 8 chars)</span>
          <textarea
            ref={textareaRef}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none resize-none"
            placeholder="e.g. Confirmed against official UPSC 2024 paper PDF"
            data-testid="paper-review-reason"
          />
        </label>
        {err && <p className="text-xs text-rose-600" data-testid="paper-review-error">{err}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-700 hover:bg-gray-50">
            Cancel
          </button>
          <button type="submit" disabled={submitting} className={btnClass} data-testid="paper-review-submit">
            {submitting ? "Saving…" : label}
          </button>
        </div>
      </form>
    </div>
  );
}

// ─── SourceReviewModal ──────────────────────────────────────────────────────
// Reason modal for the PYQ source trust lifecycle (OD-2 / Finding 7). Mirrors
// PaperReviewModal: ≥8-char reason, target-status-styled submit. Calls
// onSubmit(sourceId, targetStatus, reason).
function SourceReviewModal({ source, targetStatus, onCancel, onSubmit }) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState(null);
  const textareaRef = useRef(null);

  useEffect(() => { textareaRef.current?.focus(); }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (reason.trim().length < 8) { setErr("Reason must be at least 8 characters."); return; }
    setSubmitting(true);
    setErr(null);
    try {
      await onSubmit(source.id, targetStatus, reason.trim());
    } catch (ex) {
      const fields = getApiBlockingFields(ex);
      setErr(fields.length > 0 ? `Review blocked — fix: ${fields.join(", ")}` : (ex?.message || "Review failed"));
      setSubmitting(false);
    }
  }

  const REVIEW_ACTION = {
    verified: { label: "Verify",   btnClass: "px-3 py-1.5 text-sm rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50" },
    rejected: { label: "Reject",   btnClass: "px-3 py-1.5 text-sm rounded bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50" },
    pending:  { label: "Re-queue", btnClass: "px-3 py-1.5 text-sm rounded bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50" },
  };
  const { label, btnClass } = REVIEW_ACTION[targetStatus] ?? REVIEW_ACTION.rejected;
  const sourceLabel = source.title || source.source_url || source.id;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" data-testid="source-review-modal">
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 flex flex-col gap-4">
        <h2 className="text-base font-semibold text-gray-800">
          {label} source — {sourceLabel}
        </h2>
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Reason <span className="text-gray-400 font-normal">(required, ≥ 8 chars)</span>
          <textarea
            ref={textareaRef}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none resize-none"
            placeholder="e.g. Confirmed source is the official commission archive"
            data-testid="source-review-reason"
          />
        </label>
        {err && <p className="text-xs text-rose-600" data-testid="source-review-error">{err}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-700 hover:bg-gray-50">
            Cancel
          </button>
          <button type="submit" disabled={submitting} className={btnClass} data-testid="source-review-submit">
            {submitting ? "Saving…" : label}
          </button>
        </div>
      </form>
    </div>
  );
}

// ─── SourceTrustSummary ─────────────────────────────────────────────────────
// Shown when the selected paper carries a pyq_source_id (OD-2 / Finding 7).
// Renders the resolved source's title/type/url + a trust_status chip and, when
// the operator canReview, permission-gated Verify / Reject / Re-queue actions
// (legal transitions only). Papers with no source keep the "No reusable source
// record" advisory elsewhere — this block simply does not render for them.
function SourceTrustSummary({ source, canReview, onReview }) {
  const status = source.trust_status || "pending";
  const chip = {
    verified: "bg-emerald-100 text-emerald-700 border-emerald-200",
    rejected: "bg-rose-100 text-rose-700 border-rose-200",
    pending:  "bg-amber-100 text-amber-700 border-amber-200",
  }[status] || "bg-slate-100 text-slate-600 border-slate-200";
  const sourceLabel = source.title || source.source_url || source.id;

  return (
    <div
      className="px-4 py-3 border-b border-gray-200 bg-slate-50 flex-shrink-0"
      data-testid="source-trust-summary"
    >
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700 truncate" title={sourceLabel}>
              {sourceLabel}
            </span>
            <span
              className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${chip}`}
              data-testid="source-trust-chip"
            >
              {TRUST_LABEL[status] ?? status}
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-0.5">
            {source.source_type ? <span data-testid="source-trust-type">{source.source_type}</span> : <span>—</span>}
            {source.source_url && (
              <>
                {" · "}
                <a
                  href={source.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 hover:underline break-all"
                  data-testid="source-trust-url"
                >
                  {source.source_url}
                </a>
              </>
            )}
          </div>
        </div>
        {canReview && (
          <div className="flex items-center gap-1 flex-shrink-0" data-testid="source-trust-actions">
            {/* pending → verified */}
            {status === "pending" && (
              <button
                type="button"
                onClick={() => onReview(source, "verified")}
                className="text-xs px-2 py-0.5 rounded border border-emerald-400 text-emerald-700 hover:bg-emerald-50"
                data-testid="verify-source-btn"
              >
                Verify
              </button>
            )}
            {/* pending → rejected | verified → rejected */}
            {(status === "pending" || status === "verified") && (
              <button
                type="button"
                onClick={() => onReview(source, "rejected")}
                className="text-xs px-2 py-0.5 rounded border border-rose-300 text-rose-600 hover:bg-rose-50"
                data-testid="reject-source-btn"
              >
                Reject
              </button>
            )}
            {/* rejected → pending (re-queue) */}
            {status === "rejected" && (
              <button
                type="button"
                onClick={() => onReview(source, "pending")}
                className="text-xs px-2 py-0.5 rounded border border-amber-400 text-amber-700 hover:bg-amber-50"
                data-testid="requeue-source-btn"
              >
                Re-queue
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── PaperProvenanceModal ───────────────────────────────────────────────────
// Replaces the old raw-UUID AttachDocModal.
// Shows paper identity, infers candidate documents from source_document_id on
// questions (if already fetched), lets admin pick source type / URL / document
// from dropdown of known pyq_paper documents, and source registry entry.

function PaperProvenanceModal({ paper, onCancel, onSubmit, pyqDocuments, pyqSources, docCounts }) {
  const [sourceType, setSourceType]     = useState(paper.source_type || "");
  const [sourceUrl, setSourceUrl]       = useState(paper.source_url || "");
  const [documentId, setDocumentId]     = useState(paper.source_document_id || "");
  const [pyqSourceId, setPyqSourceId]   = useState(paper.pyq_source_id || "");

  // Preselect the document that the most questions already reference,
  // but only when the paper has no existing source_document_id.
  useEffect(() => {
    if (paper.source_document_id) return;
    if (!docCounts || docCounts.size === 0) return;
    if (!pyqDocuments || pyqDocuments.length === 0) return;
    let maxCount = 0;
    let topDocId = null;
    let tied = false;
    for (const [id, count] of docCounts) {
      if (count > maxCount) { maxCount = count; topDocId = id; tied = false; }
      else if (count === maxCount) { tied = true; }
    }
    if (!tied && topDocId && pyqDocuments.some((d) => d.id === topDocId)) {
      setDocumentId(topDocId);
    }
  }, [paper.source_document_id, docCounts, pyqDocuments]);
  const [reason, setReason]             = useState("");
  const [submitting, setSubmitting]     = useState(false);
  const [err, setErr]                   = useState(null);

  const isReplace = Boolean(paper.source_document_id) || Boolean(paper.source_url);
  const paperLabel = [paper.year, paper.paper_code, paper.shift].filter(Boolean).join(" · ");

  async function handleSubmit(e) {
    e.preventDefault();
    if (reason.trim().length < 8) { setErr("Reason must be at least 8 characters."); return; }
    const newSourceType = sourceType || null;
    const newSourceUrl  = sourceUrl.trim() || null;
    const newDocId      = documentId || null;
    const newPyqSrcId   = pyqSourceId || null;
    const payload = {};
    if (newSourceType !== (paper.source_type        || null)) payload.source_type         = newSourceType;
    if (newSourceUrl  !== (paper.source_url         || null)) payload.source_url          = newSourceUrl;
    if (newDocId      !== (paper.source_document_id || null)) payload.source_document_id  = newDocId;
    if (newPyqSrcId   !== (paper.pyq_source_id      || null)) payload.pyq_source_id       = newPyqSrcId;
    if (Object.keys(payload).length === 0) { setErr("No changes to save."); return; }
    setSubmitting(true);
    setErr(null);
    try {
      await onSubmit(paper.id, payload, reason.trim());
    } catch (ex) {
      const fields = getApiBlockingFields(ex);
      if (fields.length > 0) {
        setErr(`Provenance incomplete — fix: ${fields.join(", ")}`);
      } else {
        setErr(ex?.message || "Save failed");
      }
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" data-testid="paper-provenance-modal">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-lg shadow-xl w-full max-w-xl p-6 flex flex-col gap-4"
      >
        <h2 className="text-base font-semibold text-gray-800">
          {isReplace ? "Update" : "Set"} provenance — {paperLabel || "—"}
        </h2>

        <PyqProvenanceFields
          sourceType={sourceType}
          onSourceTypeChange={setSourceType}
          sourceUrl={sourceUrl}
          onSourceUrlChange={setSourceUrl}
          documentId={documentId}
          onDocumentIdChange={setDocumentId}
          pyqSourceId={pyqSourceId}
          onPyqSourceIdChange={setPyqSourceId}
          pyqDocuments={pyqDocuments}
          pyqSources={pyqSources}
          docCounts={docCounts}
        />

        {/* Reason */}
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Reason <span className="text-gray-400 font-normal">(required, ≥ 8 chars)</span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none resize-none"
            placeholder="e.g. Linked official UPSC PDF uploaded 2024-06-20"
            data-testid="provenance-reason"
          />
        </label>

        {err && <p className="text-xs text-rose-600" data-testid="provenance-error">{err}</p>}

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-700 hover:bg-gray-50">
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-3 py-1.5 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
            data-testid="provenance-submit"
          >
            {submitting ? "Saving…" : "Save provenance"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function PyqWorkbenchPanel({ paperId = null, rowId = null, status = null }) {
  const { exam, cycle } = useExamWorkspace();
  const examId = exam?.id;
  const cycleId = cycle?.id ?? null;
  // exam_cycles has no exam_phase_id column; phase is always null for this panel.
  const cycleLabel = cycle?.cycle_name ?? null;
  const cycleYear = cycle?.year ?? null;

  const { user } = useAuth();
  const canReview = user?.role === "super_admin" ||
    (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.review"));
  const canEdit = user?.role === "super_admin" ||
    (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.cms"));

  const {
    papers, selectedPaperId, setSelectedPaperId, loading, loaded, error,
    reviewPaper, saveProvenance, onboardPaper, getPaperSignedPdf,
    fetchPyqDocuments, fetchPyqSources, fetchPaperQuestions,
    uploadPyqDocument, reviewPyqSource,
  } = usePyqWorkbench(examId, cycleId);

  const [showBulkImport, setShowBulkImport] = useState(false);
  const [showAddPaper, setShowAddPaper] = useState(false);
  const [paperNotFound, setPaperNotFound] = useState(false);
  const [reviewTarget, setReviewTarget] = useState(null); // { paper, targetStatus }
  const [provenanceTarget, setProvenanceTarget] = useState(null); // { paper }
  const [pdfError, setPdfError] = useState(null);
  const [sourceReviewTarget, setSourceReviewTarget] = useState(null); // { source, targetStatus }
  // Sources resolved for the selected paper's trust summary (OD-2 / Finding 7).
  const [selectedPaperSources, setSelectedPaperSources] = useState([]);

  // Lazy-loaded lists for the PaperProvenanceModal
  const [pyqDocuments, setPyqDocuments] = useState([]);
  const [pyqSources, setPyqSources]     = useState([]);
  // question-count keyed by source_document_id (Map<string, number>)
  const [pyqDocCounts, setPyqDocCounts] = useState(() => new Map());

  // Auto-select paperId once papers have loaded
  useEffect(() => {
    if (!paperId || loading || papers.length === 0) return;
    const found = papers.some((p) => p.id === paperId);
    if (found) {
      setSelectedPaperId(paperId);
      setPaperNotFound(false);
    } else {
      setPaperNotFound(true);
    }
  }, [paperId, papers, loading, setSelectedPaperId]);

  const openProvenanceModal = useCallback(async (paper) => {
    setProvenanceTarget({ paper });
    setPyqDocuments([]);
    setPyqSources([]);
    setPyqDocCounts(new Map());
    // Fetch independently so a failure on one optional list (e.g. pyq-sources)
    // does not discard the results of the others.
    fetchPyqDocuments().then(setPyqDocuments).catch(() => {});
    fetchPyqSources().then(setPyqSources).catch(() => {});
    fetchPaperQuestions(paper.id).then((questions) => {
      const counts = new Map();
      for (const q of questions) {
        if (q.source_document_id) {
          counts.set(q.source_document_id, (counts.get(q.source_document_id) || 0) + 1);
        }
      }
      setPyqDocCounts(counts);
    }).catch(() => {});
  }, [fetchPyqDocuments, fetchPyqSources, fetchPaperQuestions]);

  const openAddPaperModal = useCallback(() => {
    setShowAddPaper(true);
    setPyqDocuments([]);
    setPyqSources([]);
    setPyqDocCounts(new Map());
    // Load the exam-scoped picker lists the modal reuses. Independent fetches
    // so a failure on one optional list does not discard the other.
    fetchPyqDocuments().then(setPyqDocuments).catch(() => {});
    fetchPyqSources().then(setPyqSources).catch(() => {});
  }, [fetchPyqDocuments, fetchPyqSources]);

  // Resolve the selected paper and, when it carries a pyq_source_id, load the
  // exam-scoped sources so the trust summary can render the matching record.
  const selectedPaper = papers.find((p) => p.id === selectedPaperId) || null;
  const selectedSourceId = selectedPaper?.pyq_source_id || null;

  useEffect(() => {
    if (!selectedSourceId) { setSelectedPaperSources([]); return; }
    let cancelled = false;
    // Background read — fetch the source list to resolve the linked record.
    fetchPyqSources()
      .then((list) => { if (!cancelled) setSelectedPaperSources(list || []); })
      .catch(() => { if (!cancelled) setSelectedPaperSources([]); });
    return () => { cancelled = true; };
  }, [selectedSourceId, fetchPyqSources]);

  const selectedSource = selectedSourceId
    ? selectedPaperSources.find((s) => s.id === selectedSourceId) || null
    : null;

  async function handleReviewSubmit(pid, targetStatus, reason) {
    await reviewPaper(pid, targetStatus, reason);
    setReviewTarget(null);
  }

  async function handleSourceReviewSubmit(sourceId, targetStatus, reason) {
    await reviewPyqSource(sourceId, targetStatus, reason);
    // Refresh the resolved source list so the summary chip reflects the change.
    fetchPyqSources().then(setSelectedPaperSources).catch(() => {});
    setSourceReviewTarget(null);
  }

  async function handleProvenanceSubmit(pid, payload, reason) {
    await saveProvenance(pid, payload, reason);
    setProvenanceTarget(null);
  }

  async function handleVerifyClick(paper) {
    if (!isPaperProvenanceComplete(paper)) {
      // Provenance is incomplete — open modal instead of review modal
      await openProvenanceModal(paper);
      return;
    }
    setReviewTarget({ paper, targetStatus: "verified" });
  }

  async function handleViewPdf(paper) {
    setPdfError(null);
    try {
      const url = await getPaperSignedPdf(paper.id, paper.source_document_id);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (ex) {
      setPdfError(ex?.message || "Failed to get signed URL");
    }
  }

  return (
    <div className="flex flex-col h-full" data-testid="pyq-workbench-panel">
      {/* Paper overview table */}
      <div className="px-4 py-3 border-b border-gray-200 bg-white flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">PYQ Papers</span>
          <div className="flex items-center gap-2 flex-shrink-0">
            {canEdit && (
              <button
                type="button"
                onClick={openAddPaperModal}
                className="text-sm px-3 py-1.5 rounded bg-indigo-600 text-white hover:bg-indigo-700 whitespace-nowrap"
                data-testid="add-pyq-paper-btn"
              >
                Add PYQ paper
              </button>
            )}
            <button
              type="button"
              onClick={() => setShowBulkImport(true)}
              className="text-sm px-3 py-1.5 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 whitespace-nowrap"
              data-testid="bulk-import-btn"
            >
              Bulk import questions
            </button>
          </div>
        </div>
        {loading && <span className="text-sm text-gray-400">Loading papers…</span>}
        {error && <span className="text-sm text-rose-600" data-testid="pyq-papers-error">{error}</span>}
        {paperNotFound && (
          <span className="text-sm text-rose-600" data-testid="pyq-paper-not-found">
            Paper {paperId} was not found in this exam.
          </span>
        )}
        {loaded && !loading && !error && papers.length === 0 && (
          <div className="text-sm text-gray-500 flex flex-col items-start gap-2" data-testid="pyq-empty-state">
            <span>No PYQ papers for this exam yet.</span>
            {canEdit && (
              <button
                type="button"
                onClick={openAddPaperModal}
                className="text-sm px-3 py-1.5 rounded bg-indigo-600 text-white hover:bg-indigo-700"
                data-testid="add-first-pyq-paper-btn"
              >
                Add the first PYQ paper
              </button>
            )}
          </div>
        )}
        {pdfError && (
          <p className="text-xs text-rose-600 mt-1" data-testid="pdf-error">{pdfError}</p>
        )}
        {!loading && papers.length > 0 && (
          <table
            className="w-full text-sm border-collapse"
            data-testid="pyq-paper-table"
          >
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                <th className="pb-1 pr-4 font-medium">Year</th>
                <th className="pb-1 pr-4 font-medium">Section</th>
                <th className="pb-1 pr-4 font-medium">Questions</th>
                <th className="pb-1 pr-4 font-medium">Readiness</th>
                <th className="pb-1 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {papers.map((p) => {
                const isSelected = p.id === selectedPaperId;
                const expectedCount = p.metadata?.expected_question_count ?? "—";
                const readiness = TRUST_LABEL[p.trust_status] ?? p.trust_status ?? "—";
                const section = [p.paper_code, p.shift].filter(Boolean).join(" · ") || "—";
                const provenanceComplete = isPaperProvenanceComplete(p);
                // OD-3: complete provenance but no reusable source record is an
                // ADVISORY, not a blocker. Distinct from isPaperProvenanceComplete.
                const noReusableSource = provenanceComplete && !p.pyq_source_id;
                return (
                  <tr
                    key={p.id}
                    onClick={() => setSelectedPaperId(p.id)}
                    style={{
                      cursor: "pointer",
                      fontWeight: isSelected ? "bold" : "normal",
                      background: isSelected ? "#eef2ff" : "transparent",
                    }}
                    className="border-b border-gray-100 hover:bg-indigo-50 transition-colors"
                  >
                    <td className="py-1.5 pr-4" data-testid={`pyq-paper-row-${p.id}`}>{p.year ?? "—"}</td>
                    <td className="py-1.5 pr-4">{section}</td>
                    <td className="py-1.5 pr-4">{expectedCount}</td>
                    <td className="py-1.5 pr-4">
                      {readiness}
                      {noReusableSource && (
                        <span
                          className="ml-2 inline-block text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 align-middle"
                          data-testid={`no-source-record-advisory-${p.id}`}
                          title="This paper has complete provenance but is not linked to a reusable source record."
                        >
                          No reusable source record
                        </span>
                      )}
                    </td>
                    <td className="py-1.5" onClick={(e) => e.stopPropagation()}>
                      {canReview && (
                        <>
                          {/* pending → verified: show "Confirm provenance" when provenance is incomplete */}
                          {p.trust_status === "pending" && (
                            provenanceComplete ? (
                              <button
                                type="button"
                                onClick={() => setReviewTarget({ paper: p, targetStatus: "verified" })}
                                className="text-xs px-2 py-0.5 rounded border border-emerald-400 text-emerald-700 hover:bg-emerald-50 mr-1"
                                data-testid={`verify-paper-btn-${p.id}`}
                              >
                                Verify
                              </button>
                            ) : canEdit ? (
                              <button
                                type="button"
                                onClick={() => handleVerifyClick(p)}
                                className="text-xs px-2 py-0.5 rounded border border-amber-400 text-amber-700 hover:bg-amber-50 mr-1"
                                data-testid={`confirm-provenance-btn-${p.id}`}
                              >
                                Confirm provenance
                              </button>
                            ) : (
                              <span
                                className="text-xs text-amber-600 mr-1"
                                data-testid={`provenance-needed-${p.id}`}
                              >
                                CMS provenance confirmation required
                              </span>
                            )
                          )}
                          {/* pending → rejected  |  verified → rejected */}
                          {(p.trust_status === "pending" || p.trust_status === "verified") && (
                            <button
                              type="button"
                              onClick={() => setReviewTarget({ paper: p, targetStatus: "rejected" })}
                              className="text-xs px-2 py-0.5 rounded border border-rose-300 text-rose-600 hover:bg-rose-50"
                              data-testid={`reject-paper-btn-${p.id}`}
                            >
                              Reject
                            </button>
                          )}
                          {/* rejected → pending (re-queue for review) */}
                          {p.trust_status === "rejected" && (
                            <button
                              type="button"
                              onClick={() => setReviewTarget({ paper: p, targetStatus: "pending" })}
                              className="text-xs px-2 py-0.5 rounded border border-amber-400 text-amber-700 hover:bg-amber-50"
                              data-testid={`requeue-paper-btn-${p.id}`}
                            >
                              Re-queue
                            </button>
                          )}
                        </>
                      )}
                      {/* Source document actions — available to CMS editors */}
                      {canEdit && (
                        <>
                          {p.source_document_id ? (
                            <>
                              <button
                                type="button"
                                onClick={() => handleViewPdf(p)}
                                className="text-xs px-2 py-0.5 rounded border border-sky-300 text-sky-700 hover:bg-sky-50 mr-1"
                                data-testid={`view-pdf-btn-${p.id}`}
                                title="View source PDF"
                              >
                                PDF
                              </button>
                              <button
                                type="button"
                                onClick={() => openProvenanceModal(p)}
                                className="text-xs px-2 py-0.5 rounded border border-gray-300 text-gray-600 hover:bg-gray-50"
                                data-testid={`replace-doc-btn-${p.id}`}
                                title="Update provenance"
                              >
                                Edit Provenance
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              onClick={() => openProvenanceModal(p)}
                              className="text-xs px-2 py-0.5 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50"
                              data-testid={`attach-doc-btn-${p.id}`}
                              title="Set provenance"
                            >
                              Set Provenance
                            </button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Source trust summary — only for a selected paper with a linked source */}
      {selectedSource && (
        <SourceTrustSummary
          source={selectedSource}
          canReview={canReview}
          onReview={(source, targetStatus) => setSourceReviewTarget({ source, targetStatus })}
        />
      )}

      {/* Workspace area */}
      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <div className="flex-1 min-h-0">
          {selectedPaperId ? (
            <Suspense fallback={<div className="p-8 text-gray-400">Loading…</div>}>
              {/*
               * E4 — Dual entry points for PyqPaperWorkspace:
               *
               * 1. EMBEDDED (here, embedded prop = true): rendered inside ExamWorkspace via this
               *    panel. Receives full exam context from ExamWorkspaceContext (exam, cycle, phase).
               *    The paper list and review actions above operate within that exam scope.
               *
               * 2. STANDALONE ROUTE (/admin/exam-intelligence/pyq-papers/:id/workspace): rendered
               *    directly via adminRoutes. Has NO ExamWorkspaceContext — exam context must be
               *    derived solely from the paper's own exam_id field. Use this path for deep-links
               *    or when navigating to a specific paper outside of ExamWorkspace.
               */}
              <PyqPaperWorkspace paperId={selectedPaperId} embedded rowId={rowId} status={status} />
            </Suspense>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400 text-sm" data-testid="pyq-no-paper-selected">
              Select a paper to begin reviewing.
            </div>
          )}
        </div>
        {/* Embedded mock projection section — not a new route */}
        {selectedPaperId && (
          <PyqMockProjectionPanel paperId={selectedPaperId} />
        )}
      </div>
      {showBulkImport && (
        <BulkImportModal
          papers={papers}
          initialPaperId={selectedPaperId}
          onClose={() => setShowBulkImport(false)}
          onSuccess={(pid) => {
            setSelectedPaperId(pid);
            setShowBulkImport(false);
          }}
        />
      )}
      {showAddPaper && (
        <AddPyqPaperModal
          examId={examId}
          examName={exam?.name}
          cycleId={cycleId}
          cycleLabel={cycleLabel}
          cycleYear={cycleYear}
          pyqDocuments={pyqDocuments}
          pyqSources={pyqSources}
          onboardPaper={onboardPaper}
          uploadPyqDocument={uploadPyqDocument}
          onCancel={() => setShowAddPaper(false)}
          onSuccess={(newPaperId) => {
            setShowAddPaper(false);
            if (newPaperId) setSelectedPaperId(newPaperId);
          }}
        />
      )}
      {reviewTarget && (
        <PaperReviewModal
          paper={reviewTarget.paper}
          targetStatus={reviewTarget.targetStatus}
          onCancel={() => setReviewTarget(null)}
          onSubmit={handleReviewSubmit}
        />
      )}
      {provenanceTarget && (
        <PaperProvenanceModal
          paper={provenanceTarget.paper}
          pyqDocuments={pyqDocuments}
          pyqSources={pyqSources}
          docCounts={pyqDocCounts}
          onCancel={() => setProvenanceTarget(null)}
          onSubmit={handleProvenanceSubmit}
        />
      )}
      {sourceReviewTarget && (
        <SourceReviewModal
          source={sourceReviewTarget.source}
          targetStatus={sourceReviewTarget.targetStatus}
          onCancel={() => setSourceReviewTarget(null)}
          onSubmit={handleSourceReviewSubmit}
        />
      )}
    </div>
  );
}
