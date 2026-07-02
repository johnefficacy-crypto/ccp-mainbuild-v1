/**
 * Prompt Bank — operator-facing admin panel for managing English writing prompts.
 *
 * Embedded as a tab inside Exam Workspace (no new sidebar destination).
 * Entry point: /admin/exam-intelligence/exams/:exam_id?tab=prompts
 *
 * Sections:
 * 1. Readiness summary (by exercise type)
 * 2. Search/filter bar
 * 3. Prompt table with lifecycle actions
 * 4. Create/edit drawer
 * 5. Preview modal
 * 6. Bulk import flow
 */
import React, { useCallback, useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { useAuth } from "../../../../lib/authContext";
import useApiCollection from "../../../../lib/hooks/useApiCollection";
import useApiAction from "../../../../lib/hooks/useApiAction";
import PromptBankTable from "./PromptBankTable";
import PromptReadinessSummary from "./PromptReadinessSummary";
import PromptEditor from "./PromptEditor";
import PromptPreview from "./PromptPreview";
import PromptFilters from "./PromptFilters";
import PromptBulkImport from "./PromptBulkImport";
import { promptBankApi } from "./promptBankApi";
import ErrorState from "../../../../shared/ui/ErrorState";

export default function PromptBankPanel() {
  const { exam, cycle } = useExamWorkspace();
  const { user } = useAuth();

  // Permission checks
  const hasCmsPermission =
    user?.role === "super_admin" ||
    user?.permissions?.includes("exam_intelligence.cms");
  const hasReviewPermission =
    user?.role === "super_admin" ||
    user?.permissions?.includes("exam_intelligence.review");

  // UI state
  const [filters, setFilters] = useState({
    exam_id: exam?.id,
    q: "",
    exercise_type: "",
    reviewer_status: "",
    is_active: "",
    difficulty_level: "",
    topic_id: "",
    microtopic_id: "",
    offset: 0,
    limit: 25,
  });
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [showEditor, setShowEditor] = useState(false);
  const [previewPrompt, setPreviewPrompt] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showBulkImport, setShowBulkImport] = useState(false);

  // Fetch prompts with filters
  const { items: prompts, status, setItems } = useApiCollection(
    "/api/admin/exam-intelligence-cms/writing-prompts",
    [],
    { params: filters }
  );

  // Extract summary from the last response
  // Note: useApiCollection doesn't expose full response, so we'll need to track it
  const [summary, setSummary] = useState(null);

  // Refresh with summary capture
  const loadPrompts = useCallback(async () => {
    try {
      const data = await promptBankApi.listPrompts(filters);
      setItems(data?.items || []);
      setSummary(data?.summary);
    } catch (e) {
      // useApiCollection handles error state
    }
  }, [filters, setItems]);

  // Sync external refresh calls
  React.useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const { run: runCreateOrUpdate } = useApiAction();
  const { run: runReview } = useApiAction();
  const { run: runActivation } = useApiAction();
  const { run: runBulkImport } = useApiAction();

  const handleCreatePrompt = useCallback(() => {
    setEditingPrompt(null);
    setShowEditor(true);
  }, []);

  const handleEditPrompt = useCallback((prompt) => {
    setEditingPrompt(prompt);
    setShowEditor(true);
  }, []);

  const handleSavePrompt = useCallback(async (formData) => {
    const isCreate = !editingPrompt;
    await runCreateOrUpdate({
      action: () =>
        isCreate
          ? promptBankApi.createPrompt(formData)
          : promptBankApi.updatePrompt(editingPrompt.id, formData),
      successMessage: isCreate ? "Prompt created." : "Prompt updated.",
      errorMessage: isCreate ? "Failed to create prompt." : "Failed to update prompt.",
      onSuccess: () => {
        setShowEditor(false);
        setEditingPrompt(null);
        loadPrompts();
      },
    });
  }, [editingPrompt, runCreateOrUpdate, loadPrompts]);

  const handleReviewPrompt = useCallback(
    async (promptId, status, notes) => {
      await runReview({
        action: () =>
          promptBankApi.reviewPrompt(promptId, {
            reviewer_status: status,
            reviewer_notes: notes,
          }),
        successMessage: `Prompt marked as ${status}.`,
        errorMessage: "Review failed.",
        onSuccess: () => loadPrompts(),
      });
    },
    [runReview, loadPrompts]
  );

  const handleActivatePrompt = useCallback(
    async (promptId, isActive) => {
      await runActivation({
        action: () => promptBankApi.setActivation(promptId, isActive),
        successMessage: isActive ? "Prompt activated." : "Prompt deactivated.",
        errorMessage: "Activation failed.",
        onSuccess: () => loadPrompts(),
      });
    },
    [runActivation, loadPrompts]
  );

  const handleClonePrompt = useCallback(
    async (promptId) => {
      await runCreateOrUpdate({
        action: () => promptBankApi.clonePrompt(promptId),
        successMessage: "Prompt cloned.",
        errorMessage: "Clone failed.",
        onSuccess: () => loadPrompts(),
      });
    },
    [runCreateOrUpdate, loadPrompts]
  );

  const handleBulkImport = useCallback(
    async (rows) => {
      await runBulkImport({
        action: () =>
          promptBankApi.bulkImportPrompts({
            rows,
            override_duplicates: false,
          }),
        successMessage: "Import completed.",
        errorMessage: "Import failed.",
        onSuccess: () => {
          setShowBulkImport(false);
          loadPrompts();
        },
      });
    },
    [runBulkImport, loadPrompts]
  );

  const handleFilterChange = useCallback((newFilters) => {
    setFilters({ ...filters, ...newFilters, offset: 0 });
  }, [filters]);

  if (status === "error") {
    return (
      <div style={{ padding: "2rem" }}>
        <ErrorState>
          <button className="btn primary" onClick={loadPrompts}>
            Retry
          </button>
        </ErrorState>
      </div>
    );
  }

  if (!exam?.id) {
    return (
      <div style={{ padding: "2rem", color: "var(--ink-mute)" }}>
        Select an exam to view prompts.
      </div>
    );
  }

  return (
    <div className="panel-body">
      {/* Readiness summary */}
      <PromptReadinessSummary summary={summary} />

      {/* Action buttons */}
      {hasCmsPermission && (
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button className="btn primary" onClick={handleCreatePrompt}>
            + New Prompt
          </button>
          <button className="btn" onClick={() => setShowBulkImport(true)}>
            ⬆ Bulk Import
          </button>
        </div>
      )}

      {/* Filters */}
      <PromptFilters filters={filters} onChange={handleFilterChange} />

      {/* Table */}
      {status === "loading" && (
        <div style={{ padding: "2rem", textAlign: "center", color: "var(--ink-mute)" }}>
          Loading prompts…
        </div>
      )}
      {status === "empty" && (
        <div style={{ padding: "2rem", textAlign: "center", color: "var(--ink-mute)" }}>
          No prompts found.
        </div>
      )}
      {status === "live" && (
        <PromptBankTable
          prompts={prompts}
          onEdit={handleEditPrompt}
          onPreview={setPreviewPrompt}
          onReview={handleReviewPrompt}
          onActivate={handleActivatePrompt}
          onClone={handleClonePrompt}
          hasCmsPermission={hasCmsPermission}
          hasReviewPermission={hasReviewPermission}
        />
      )}

      {/* Editor drawer */}
      {showEditor && (
        <PromptEditor
          prompt={editingPrompt}
          examId={exam.id}
          examCycleId={cycle?.id}
          onSave={handleSavePrompt}
          onClose={() => {
            setShowEditor(false);
            setEditingPrompt(null);
          }}
        />
      )}

      {/* Preview modal */}
      {showPreview && previewPrompt && (
        <PromptPreview
          prompt={previewPrompt}
          onClose={() => {
            setShowPreview(false);
            setPreviewPrompt(null);
          }}
        />
      )}

      {/* Bulk import flow */}
      {showBulkImport && (
        <PromptBulkImport
          examId={exam.id}
          onImport={handleBulkImport}
          onClose={() => setShowBulkImport(false)}
        />
      )}
    </div>
  );
}
