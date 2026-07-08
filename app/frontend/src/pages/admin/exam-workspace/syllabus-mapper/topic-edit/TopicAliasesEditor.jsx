import React, { useId, useRef, useState } from "react";
import { Trash2 } from "lucide-react";

/**
 * Inline add/delete editor for a topic's aliases.
 *
 * Alias writes are IMMEDIATE — not gated on the topic Save button.
 * Add and delete each produce their own CMS audit entry, using the
 * drawer's shared reason field.
 *
 * Props:
 *   aliases        - current alias list
 *   canWrite       - bool: true when drawer reason is valid (≥ 8 chars)
 *   loadingAdd     - bool
 *   loadingDelete  - bool (we disable all delete buttons while any delete runs)
 *   errorAdd       - string | null
 *   errorDelete    - string | null
 *   onAdd(text)    - callback
 *   onDelete(id)   - callback
 */
export default function TopicAliasesEditor({
  aliases,
  canWrite,
  loadingAdd,
  loadingDelete,
  errorAdd,
  errorDelete,
  onAdd,
  onDelete,
}) {
  const uid = useId();
  const [newAlias, setNewAlias] = useState("");
  const inputRef = useRef(null);

  async function handleAdd(e) {
    e.preventDefault();
    if (!newAlias.trim() || !canWrite || loadingAdd) return;
    await onAdd(newAlias.trim());
    setNewAlias("");
    inputRef.current?.focus();
  }

  return (
    <div>
      <h3 className="text-sm font-medium text-gray-700 mb-1">Aliases</h3>
      {/* M2: this inline editor stays scoped to a topic reached from a mapper proposal.
          A standalone, pre-proposal alias manager also exists — the "Manage topics" bar
          at the top of the Syllabus tab (SyllabusTopicEditorPanel -> Aliases) lets an
          operator pick any subject/topic and manage aliases without running the mapper. */}
      <p className="text-xs text-gray-400 mb-2" data-testid="alias-mapper-only-note">
        Aliases can also be managed without a mapper proposal — use &quot;Manage topics&quot; at the
        top of the Syllabus tab to pick a topic directly.
      </p>

      {aliases.length === 0 ? (
        <p className="text-xs text-gray-400 mb-3">No aliases yet.</p>
      ) : (
        <ul className="divide-y divide-gray-100 mb-3 border border-gray-200 rounded-md overflow-hidden">
          {aliases.map((a) => (
            <li key={a.id} className="flex items-center gap-2 px-3 py-2 bg-white">
              <span className="flex-1 text-sm truncate" title={a.alias}>{a.alias}</span>
              <span
                className="text-xs text-gray-400 truncate max-w-[120px]"
                title={a.normalized_alias}
              >
                {a.normalized_alias}
              </span>
              <button
                type="button"
                onClick={() => onDelete(a.id)}
                disabled={loadingDelete || !canWrite}
                aria-label={`Delete alias ${a.alias}`}
                className="shrink-0 p-1 text-gray-400 hover:text-red-600 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {errorDelete && (
        <p role="alert" className="text-xs text-red-600 mb-2">{errorDelete}</p>
      )}

      {/* Add row */}
      <form onSubmit={handleAdd} className="flex gap-2">
        <input
          ref={inputRef}
          id={`${uid}-new-alias`}
          type="text"
          value={newAlias}
          onChange={(e) => setNewAlias(e.target.value)}
          placeholder="New alias"
          disabled={!canWrite}
          aria-label="New alias text"
          className="flex-1 border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50 disabled:text-gray-400"
        />
        <button
          type="submit"
          disabled={!newAlias.trim() || !canWrite || loadingAdd}
          className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loadingAdd ? "Adding…" : "Add"}
        </button>
      </form>

      {!canWrite && (
        <p className="text-xs text-amber-600 mt-1">
          Enter a reason (≥ 8 characters) above to enable alias changes.
        </p>
      )}

      {errorAdd && (
        <p role="alert" className="text-xs text-red-600 mt-1">{errorAdd}</p>
      )}
    </div>
  );
}
