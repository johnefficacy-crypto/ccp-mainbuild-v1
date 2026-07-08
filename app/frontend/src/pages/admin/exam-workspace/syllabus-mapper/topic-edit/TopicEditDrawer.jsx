import React, { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";
import TopicAliasesEditor from "./TopicAliasesEditor";
import TopicFieldsForm from "./TopicFieldsForm";

/**
 * Right-side slide-over drawer for editing a topic and its aliases.
 *
 * Props: hook return value from useTopicEdit + onSaved(row) callback.
 *
 * Accessibility:
 *   - role="dialog" aria-modal="true" aria-labelledby="topic-edit-drawer-title"
 *   - Focus lands on close button on open
 *   - Tab focus trapped inside
 *   - Escape with dirty-check confirmation
 *   - Body scroll locked while open
 */
export default function TopicEditDrawer({ hook, onSaved }) {
  const {
    open,
    topic,
    siblings,
    aliases,
    dirtyFields,
    reason,
    loading,
    error,
    isDirty,
    canSave,
    canAliasWrite,
    setField,
    setReason,
    save,
    addAlias,
    deleteAlias,
    close,
  } = hook;

  const uid = useId();
  const titleId = `${uid}-title`;
  const reasonId = `${uid}-reason`;
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);

  // Body scroll lock
  useEffect(() => {
    if (!open) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [open]);

  // Initial focus
  useEffect(() => {
    if (open) closeButtonRef.current?.focus?.();
  }, [open, topic?.id]);

  // Escape + focus trap
  useEffect(() => {
    if (!open) return undefined;
    function onKey(e) {
      if (e.key === "Escape") {
        e.stopPropagation();
        handleClose();
        return;
      }
      if (e.key !== "Tab" || !dialogRef.current) return;
      const focusables = dialogRef.current.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKey, true);
    return () => document.removeEventListener("keydown", onKey, true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, isDirty]);

  if (!open) return null;

  function handleClose() {
    if (isDirty) {
      if (!window.confirm("You have unsaved changes. Discard them?")) return;
    }
    close();
  }

  function handleSave() {
    save((result) => {
      onSaved?.(result);
      close();
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex" data-testid="topic-edit-drawer-root">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={handleClose}
        aria-hidden="true"
        data-testid="topic-edit-backdrop"
      />

      {/* Drawer panel */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-label="Edit topic"
        className="relative ml-auto h-full w-full max-w-[480px] bg-white shadow-2xl flex flex-col animate-slide-in-right"
        data-testid="topic-edit-drawer"
      >
        {/* Header */}
        <header className="flex items-start justify-between gap-4 px-6 py-5 border-b border-gray-200 shrink-0">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-gray-400 font-semibold">
              Syllabus Mapper
            </div>
            <h2
              id={titleId}
              className="text-xl font-semibold text-gray-900 mt-0.5"
              data-testid="topic-edit-drawer-title"
            >
              {loading.fetch || !topic ? "Loading…" : topic.name}
            </h2>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={handleClose}
            aria-label="Close drawer"
            data-testid="topic-edit-close"
            className="h-9 w-9 grid place-items-center rounded-lg border border-gray-200 bg-white hover:bg-gray-50 shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {loading.fetch && (
            <p className="text-sm text-gray-500">Loading topic…</p>
          )}

          {error.fetch && (
            <p role="alert" className="text-sm text-red-600">{error.fetch}</p>
          )}

          {!loading.fetch && topic && (
            <>
              <TopicFieldsForm
                topic={topic}
                siblings={siblings}
                dirtyFields={dirtyFields}
                onFieldChange={setField}
              />

              <hr className="border-gray-100" />

              {/* M2: this drawer's alias editor is reached via a mapper proposal (TopicTreePanel
                  onEditTopic). A standalone, pre-proposal path also exists: SyllabusTopicEditorPanel
                  (mounted above the mapper in SyllabusMapperPanel) lets an operator pick a subject and
                  topic directly and manage aliases without running a mapper proposal first. */}
              <TopicAliasesEditor
                aliases={aliases}
                canWrite={canAliasWrite}
                loadingAdd={loading.alias_add}
                loadingDelete={loading.alias_delete}
                errorAdd={error.alias_add}
                errorDelete={error.alias_delete}
                onAdd={addAlias}
                onDelete={deleteAlias}
              />
            </>
          )}
        </div>

        {/* Footer */}
        {!loading.fetch && topic && (
          <footer className="px-6 py-4 border-t border-gray-200 space-y-3 shrink-0 bg-gray-50">
            {/* Reason textarea */}
            <div>
              <label
                htmlFor={reasonId}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Reason <span aria-hidden="true" className="text-red-500">*</span>
              </label>
              <textarea
                id={reasonId}
                rows={2}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Why are you making this change? (8+ characters)"
                aria-required="true"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {error.save && (
              <p role="alert" className="text-sm text-red-600">{error.save}</p>
            )}

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={!canSave}
                aria-disabled={!canSave}
                data-testid="topic-edit-save"
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {loading.save ? "Saving…" : "Save"}
              </button>
            </div>
          </footer>
        )}
      </div>
    </div>
  );
}
