import React, { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { useAuth } from "../../../../lib/authContext";
import { usePyqWorkbench } from "./usePyqWorkbench";
import BulkImportModal from "./bulk-import/BulkImportModal";
import PyqMockProjectionPanel from "./PyqMockProjectionPanel";

const PyqPaperWorkspace = lazy(() => import("../../studyos/PyqPaperWorkspace"));

const TRUST_LABEL = {
  verified: "Verified",
  rejected: "Rejected",
  pending: "Pending",
};

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

export default function PyqWorkbenchPanel({ paperId = null, rowId = null, status = null }) {
  const { exam, cycle } = useExamWorkspace();
  const examId = exam?.id;
  const cycleId = cycle?.id ?? null;

  const { user } = useAuth();
  const canReview = user?.role === "super_admin" ||
    (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.review"));

  const { papers, selectedPaperId, setSelectedPaperId, loading, error, reviewPaper } = usePyqWorkbench(
    examId,
    cycleId,
  );

  const [showBulkImport, setShowBulkImport] = useState(false);
  const [paperNotFound, setPaperNotFound] = useState(false);
  const [reviewTarget, setReviewTarget] = useState(null); // { paper, targetStatus }

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

  async function handleReviewSubmit(pid, targetStatus, reason) {
    await reviewPaper(pid, targetStatus, reason);
    setReviewTarget(null);
  }

  return (
    <div className="flex flex-col h-full" data-testid="pyq-workbench-panel">
      {/* Paper overview table */}
      <div className="px-4 py-3 border-b border-gray-200 bg-white flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">PYQ Papers</span>
          <button
            type="button"
            onClick={() => setShowBulkImport(true)}
            className="text-sm px-3 py-1.5 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 whitespace-nowrap flex-shrink-0"
            data-testid="bulk-import-btn"
          >
            Bulk import questions
          </button>
        </div>
        {loading && <span className="text-sm text-gray-400">Loading papers…</span>}
        {error && <span className="text-sm text-rose-600" data-testid="pyq-papers-error">{error}</span>}
        {paperNotFound && (
          <span className="text-sm text-rose-600" data-testid="pyq-paper-not-found">
            Paper {paperId} was not found in this exam/cycle.
          </span>
        )}
        {!loading && !error && papers.length === 0 && (
          <span className="text-sm text-gray-500" data-testid="pyq-empty-state">
            No PYQ papers for this exam/cycle. Create one in the CMS.
          </span>
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
                return (
                  <tr
                    key={p.id}
                    data-testid={`pyq-paper-row-${p.id}`}
                    onClick={() => setSelectedPaperId(p.id)}
                    style={{
                      cursor: "pointer",
                      fontWeight: isSelected ? "bold" : "normal",
                      background: isSelected ? "#eef2ff" : "transparent",
                    }}
                    className="border-b border-gray-100 hover:bg-indigo-50 transition-colors"
                  >
                    <td className="py-1.5 pr-4">{p.year ?? "—"}</td>
                    <td className="py-1.5 pr-4">{section}</td>
                    <td className="py-1.5 pr-4">{expectedCount}</td>
                    <td className="py-1.5 pr-4">{readiness}</td>
                    <td className="py-1.5" onClick={(e) => e.stopPropagation()}>
                      {canReview && (
                        <>
                          {/* pending → verified */}
                          {p.trust_status === "pending" && (
                            <button
                              type="button"
                              onClick={() => setReviewTarget({ paper: p, targetStatus: "verified" })}
                              className="text-xs px-2 py-0.5 rounded border border-emerald-400 text-emerald-700 hover:bg-emerald-50 mr-1"
                              data-testid={`verify-paper-btn-${p.id}`}
                            >
                              Verify
                            </button>
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
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Workspace area */}
      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <div className="flex-1 min-h-0">
          {selectedPaperId ? (
            <Suspense fallback={<div className="p-8 text-gray-400">Loading…</div>}>
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
          onSuccess={(paperId) => {
            setSelectedPaperId(paperId);
            setShowBulkImport(false);
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
    </div>
  );
}
