import React, { useState } from "react";
import PropTypes from "prop-types";

/**
 * Shared, surface-agnostic topic alias editor (J2 OD-3).
 *
 * Presentational only — the consuming surface supplies the alias list and the
 * add/remove handlers (each wired through its own `useApiAction`). `disabled`
 * carries the fail-closed / busy state from the parent.
 */
export default function TopicAliasEditor({
  topicName,
  aliases = [],
  loading = false,
  disabled = false,
  onAdd,
  onRemove,
}) {
  const [value, setValue] = useState("");

  function add() {
    const v = value.trim();
    if (!v || disabled) return;
    onAdd(v);
    setValue("");
  }

  return (
    <div className="mt-3 bg-white border border-slate-200 rounded p-3" data-testid="ste-alias-editor">
      <div className="text-xs font-semibold text-slate-600 mb-2">Aliases · {topicName}</div>
      {loading ? (
        <div className="text-sm text-slate-400">Loading…</div>
      ) : (
        <ul className="text-sm divide-y divide-slate-100 mb-2" data-testid="ste-alias-list">
          {aliases.length === 0 && <li className="py-1 text-slate-400">No aliases.</li>}
          {aliases.map((a) => (
            <li key={a.id} className="py-1 flex items-center gap-2" data-testid={`ste-alias-${a.id}`}>
              <span className="flex-1">{a.alias}</span>
              <button
                type="button"
                className="text-xs px-2 py-0.5 border rounded text-rose-600 disabled:opacity-40"
                onClick={() => onRemove(a)}
                disabled={disabled}
                data-testid={`ste-alias-remove-${a.id}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <input
          className="text-sm border rounded px-2 py-1 flex-1"
          placeholder="new alias"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-label="New alias"
          data-testid="ste-alias-input"
        />
        <button
          type="button"
          className="text-sm px-3 py-1 border rounded disabled:opacity-40"
          onClick={add}
          disabled={disabled || !value.trim()}
          data-testid="ste-alias-add"
        >
          Add
        </button>
      </div>
    </div>
  );
}

TopicAliasEditor.propTypes = {
  topicName: PropTypes.string,
  aliases: PropTypes.array,
  loading: PropTypes.bool,
  disabled: PropTypes.bool,
  onAdd: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
};
