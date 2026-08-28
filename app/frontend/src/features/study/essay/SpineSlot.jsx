import React, { useState } from "react";
import PropTypes from "prop-types";

import useApiAction from "../../../lib/hooks/useApiAction";
import { wordCount } from "./spineSlots";

/**
 * One slot of the essay spine — e.g. "Hook", "Supporting argument".
 *
 * A slot holds zero or more blocks. Zero is a legitimate, expected state: the
 * aspirant simply hasn't written that part yet, so it renders an explicit
 * "not started" affordance rather than an empty gap that reads as broken.
 *
 * Every write goes through `useApiAction` and is followed by a refresh from the
 * server, so what is on screen is always what the API confirmed. A failed write
 * keeps the editor open with the text intact — nothing the aspirant typed is
 * discarded because a request failed.
 */
export default function SpineSlot({ slot, blocks, onCreate, onUpdate, onDelete, onChanged }) {
  const { run, busy } = useApiAction();
  const [draft, setDraft] = useState("");
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState("");

  const testId = `spine-slot-${slot.blockType}`;

  const submitNew = async () => {
    const text = draft.trim();
    if (!text) return;
    const res = await run({
      action: () => onCreate(slot.blockType, text),
      successMessage: `${slot.label} saved.`,
      errorMessage: `Could not save this ${slot.label.toLowerCase()}.`,
    });
    if (res.ok) {
      setDraft("");
      setAdding(false);
      await onChanged();
    }
  };

  const submitEdit = async (blockId) => {
    const text = editDraft.trim();
    if (!text) return;
    const res = await run({
      action: () => onUpdate(blockId, text),
      successMessage: "Updated.",
      errorMessage: "Could not save your edit.",
    });
    if (res.ok) {
      setEditingId(null);
      setEditDraft("");
      await onChanged();
    }
  };

  const remove = async (blockId) => {
    const res = await run({
      action: () => onDelete(blockId),
      confirm: `Remove this ${slot.label.toLowerCase()} from the spine?`,
      successMessage: "Removed.",
      errorMessage: "Could not remove it.",
    });
    if (res.ok) await onChanged();
  };

  return (
    <section className="soft-card rounded-2xl p-4" data-testid={testId}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-heading text-base font-semibold">{slot.label}</h3>
        <span className="text-xs text-muted-foreground">~{slot.targetWords} words</span>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{slot.helper}</p>

      {blocks.length === 0 && !adding && (
        <div
          className="mt-3 rounded-xl border border-dashed border-clay-300 p-4 text-center"
          data-testid={`${testId}-empty`}
        >
          <p className="text-sm text-muted-foreground">Not started yet.</p>
          <button
            type="button"
            className="btn btn-primary mt-3"
            onClick={() => setAdding(true)}
            data-testid={`${testId}-start`}
          >
            Write the {slot.label.toLowerCase()}
          </button>
        </div>
      )}

      {blocks.length > 0 && (
        <ul className="mt-3 space-y-2">
          {blocks.map((block) => (
            <li key={block.id} className="rounded-xl border border-clay-200 p-3">
              {editingId === block.id ? (
                <div>
                  <label className="sr-only" htmlFor={`edit-${block.id}`}>
                    Edit {slot.label}
                  </label>
                  <textarea
                    id={`edit-${block.id}`}
                    className="w-full rounded-lg border border-clay-300 p-2 text-sm"
                    rows={3}
                    value={editDraft}
                    onChange={(e) => setEditDraft(e.target.value)}
                  />
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={busy || !editDraft.trim()}
                      onClick={() => submitEdit(block.id)}
                      data-testid={`${testId}-save-edit`}
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() => {
                        setEditingId(null);
                        setEditDraft("");
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="whitespace-pre-wrap text-sm">{block.block_text}</p>
                  <div className="mt-2 flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">
                      {wordCount(block.block_text)} words
                    </span>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() => {
                        setEditingId(block.id);
                        setEditDraft(block.block_text || "");
                      }}
                      data-testid={`${testId}-edit`}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={busy}
                      onClick={() => remove(block.id)}
                      data-testid={`${testId}-delete`}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {adding ? (
        <div className="mt-3">
          <label className="sr-only" htmlFor={`new-${slot.blockType}`}>
            New {slot.label}
          </label>
          <textarea
            id={`new-${slot.blockType}`}
            className="w-full rounded-lg border border-clay-300 p-2 text-sm"
            rows={3}
            placeholder={slot.placeholder}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            data-testid={`${testId}-input`}
          />
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy || !draft.trim()}
              onClick={submitNew}
              data-testid={`${testId}-save`}
            >
              Save
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setAdding(false);
                setDraft("");
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        blocks.length > 0 && (
          <button
            type="button"
            className="btn btn-ghost mt-3"
            onClick={() => setAdding(true)}
            data-testid={`${testId}-add`}
          >
            Add another
          </button>
        )
      )}
    </section>
  );
}

SpineSlot.propTypes = {
  slot: PropTypes.shape({
    blockType: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    helper: PropTypes.string.isRequired,
    placeholder: PropTypes.string.isRequired,
    targetWords: PropTypes.number.isRequired,
  }).isRequired,
  blocks: PropTypes.arrayOf(PropTypes.object).isRequired,
  onCreate: PropTypes.func.isRequired,
  onUpdate: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onChanged: PropTypes.func.isRequired,
};
