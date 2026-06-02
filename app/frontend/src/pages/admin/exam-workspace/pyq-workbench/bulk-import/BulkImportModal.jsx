import React, { useEffect, useRef, useState } from "react";
import BulkImportSteps from "./BulkImportSteps";
import CsvUploadStep from "./CsvUploadStep";
import CommitConfirmation from "./CommitConfirmation";
import CommitResult from "./CommitResult";
import PreflightPreview from "./PreflightPreview";
import { useBulkImport } from "./useBulkImport";

export default function BulkImportModal({ papers, initialPaperId, onClose }) {
  const {
    state,
    selectPaper,
    selectFile,
    runPreflight,
    setOverride,
    setReason,
    runCommit,
    reset,
    goToStep,
  } = useBulkImport(initialPaperId);

  const dialogRef = useRef(null);
  const [escapeConfirm, setEscapeConfirm] = useState(false);

  // Focus trap + Escape handling
  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    el.focus();

    function handleKey(e) {
      if (e.key !== "Escape") return;
      if (state.step === "upload") {
        onClose();
        return;
      }
      // Preview/committing/result — ask for confirmation
      setEscapeConfirm(true);
    }
    el.addEventListener("keydown", handleKey);
    return () => el.removeEventListener("keydown", handleKey);
  }, [state.step, onClose]);

  function handleEscapeConfirmClose() {
    setEscapeConfirm(false);
    onClose();
  }

  function handleContinuePreflight() {
    runPreflight(state.selected_paper_id, state.csv_text);
  }

  function handleCommit() {
    runCommit(
      state.selected_paper_id,
      state.preflight?.import_token,
      state.override_errors,
      state.reason,
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      data-testid="bulk-import-modal-backdrop"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="PYQ bulk import"
        tabIndex={-1}
        className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[85vh] flex flex-col outline-none"
        data-testid="bulk-import-modal"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-gray-200 flex-shrink-0">
          <div>
            <h2 className="text-base font-semibold text-gray-900 mb-2">Bulk import questions</h2>
            <BulkImportSteps current={state.step} />
          </div>
          <button
            type="button"
            onClick={() => {
              if (state.step === "upload") onClose();
              else setEscapeConfirm(true);
            }}
            className="text-gray-400 hover:text-gray-700 text-xl leading-none"
            aria-label="Close"
            data-testid="modal-close-btn"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-hidden px-6 py-5 min-h-0">
          {state.step === "upload" && (
            <CsvUploadStep
              papers={papers}
              selectedPaperId={state.selected_paper_id}
              onSelectPaper={selectPaper}
              csvFilename={state.csv_filename}
              onSelectFile={selectFile}
              onRunPreflight={handleContinuePreflight}
              loading={state.loading.preflight}
              error={state.error.preflight}
            />
          )}
          {state.step === "preview" && (
            <PreflightPreview
              preflight={state.preflight}
              onBack={() => goToStep("upload")}
              onContinue={() => goToStep("committing")}
            />
          )}
          {state.step === "committing" && (
            <CommitConfirmation
              overrideErrors={state.override_errors}
              onSetOverride={setOverride}
              reason={state.reason}
              onSetReason={setReason}
              onBack={() => goToStep("preview")}
              onCommit={handleCommit}
              loading={state.loading.commit}
              error={state.error.commit}
            />
          )}
          {state.step === "result" && (
            <CommitResult
              commitResult={state.commit_result}
              onImportAnother={() => reset(state.selected_paper_id)}
              onClose={onClose}
            />
          )}
        </div>
      </div>

      {/* Escape confirmation overlay */}
      {escapeConfirm && (
        <div
          className="absolute inset-0 z-10 flex items-center justify-center bg-black/30"
          data-testid="escape-confirm-overlay"
        >
          <div className="bg-white rounded-lg shadow-lg p-6 w-80 space-y-4">
            <p className="text-sm font-medium text-gray-800">
              Close the import wizard? Your current progress will be lost.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="text-sm px-3 py-1.5 border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
                onClick={() => setEscapeConfirm(false)}
                data-testid="escape-cancel-btn"
              >
                Keep editing
              </button>
              <button
                type="button"
                className="text-sm px-3 py-1.5 bg-rose-600 text-white rounded hover:bg-rose-700"
                onClick={handleEscapeConfirmClose}
                data-testid="escape-confirm-btn"
              >
                Close anyway
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
