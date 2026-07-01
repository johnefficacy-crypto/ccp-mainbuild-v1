import React, { useState } from "react";
import PropTypes from "prop-types";

/**
 * Shared, surface-agnostic topic create/edit form (J2 OD-3).
 *
 * Presentational only — it owns local field state and calls `onSubmit` with a
 * plain payload; the consuming surface (Manage Exam Syllabus panel today,
 * Advanced Repair CMS on convergence) wires the actual mutation. Slug is
 * immutable on edit (identity field). A reason is always required.
 */
export const TOPIC_LEVELS = ["topic", "microtopic", "concept"];

export default function TopicEditorForm({ initial = null, busy = false, onSubmit, onCancel }) {
  const isEdit = Boolean(initial?.id);
  const [name, setName] = useState(initial?.name || "");
  const [slug, setSlug] = useState(initial?.slug || "");
  const [level, setLevel] = useState(initial?.level || "topic");
  const [description, setDescription] = useState(initial?.description || "");
  const [reason, setReason] = useState("");

  function submit(e) {
    e.preventDefault();
    onSubmit({ id: initial?.id, name, slug, level, description, reason });
  }

  return (
    <form className="mt-3 bg-white border border-slate-200 rounded p-3 space-y-2" onSubmit={submit} data-testid="ste-form">
      <div className="text-xs font-semibold text-slate-600">{isEdit ? "Edit topic" : "New topic"}</div>
      <div className="flex gap-2 flex-wrap">
        <input
          className="text-sm border rounded px-2 py-1 flex-1" placeholder="name" required
          value={name} onChange={(e) => setName(e.target.value)}
          aria-label="Topic name" data-testid="ste-form-name"
        />
        <input
          className="text-sm border rounded px-2 py-1" placeholder="slug" required disabled={isEdit}
          value={slug} onChange={(e) => setSlug(e.target.value)}
          aria-label="Topic slug" data-testid="ste-form-slug"
        />
        <select
          className="text-sm border rounded px-2 py-1" value={level}
          onChange={(e) => setLevel(e.target.value)} aria-label="Topic level" data-testid="ste-form-level"
        >
          {TOPIC_LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
      </div>
      <textarea
        className="text-sm border rounded px-2 py-1 w-full" placeholder="description (optional)" rows={2}
        value={description} onChange={(e) => setDescription(e.target.value)}
        aria-label="Topic description" data-testid="ste-form-description"
      />
      <input
        className="text-sm border rounded px-2 py-1 w-full" placeholder="reason (min 8 chars, audited)" required
        value={reason} onChange={(e) => setReason(e.target.value)}
        aria-label="Reason" data-testid="ste-form-reason"
      />
      <div className="flex gap-2">
        <button type="submit" className="text-sm px-3 py-1 border rounded bg-slate-800 text-white disabled:opacity-40" disabled={busy} data-testid="ste-form-save">
          {busy ? "Saving…" : "Save"}
        </button>
        <button type="button" className="text-sm px-3 py-1 border rounded" onClick={onCancel} data-testid="ste-form-cancel">
          Cancel
        </button>
      </div>
    </form>
  );
}

TopicEditorForm.propTypes = {
  initial: PropTypes.object,
  busy: PropTypes.bool,
  onSubmit: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
};
