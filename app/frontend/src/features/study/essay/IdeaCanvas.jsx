import React, { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import useEssayBlocks from "./useEssayBlocks";
import PyqTagsSidebar from "./PyqTagsSidebar";
import {
  LENSES,
  LENS_LABEL,
  LENS_ANCHOR,
  RESOURCE_TYPES,
  BRANCH_IDEA_BLOCK_TYPE,
  NEW_BLOCK_OFFSET,
} from "./essayConstants";

// Resolve a block's on-canvas position: its persisted point, or — when it has
// no position yet (both null) — a sensible spot near its lens branch so it is
// visible and grouped, never stacked at 0,0 or hidden.
function positionFor(block, seed = 0) {
  if (block.canvas_x != null && block.canvas_y != null) {
    return { x: Number(block.canvas_x), y: Number(block.canvas_y) };
  }
  const anchor = LENS_ANCHOR[block.lens] || { x: 480, y: 420 };
  const jitter = (seed % 5) * NEW_BLOCK_OFFSET;
  return { x: anchor.x + jitter, y: anchor.y + jitter };
}

// A single draggable sticky. Drag updates only LOCAL position during the move;
// exactly one PATCH fires on drag-end (mouseup), never per pointer-move.
function Sticky({ block, pos, hue, onMoveEnd, onDelete }) {
  const [drag, setDrag] = useState(null); // { startX, startY, originX, originY } while dragging
  const [local, setLocal] = useState(pos);
  const posRef = useRef(pos);

  // Keep in sync with persisted position when not actively dragging.
  useEffect(() => {
    if (!drag) { setLocal(pos); posRef.current = pos; }
  }, [pos, drag]);

  const onMouseMove = useCallback((e) => {
    setDrag((d) => {
      if (!d) return d;
      const next = { x: d.originX + (e.clientX - d.startX), y: d.originY + (e.clientY - d.startY) };
      posRef.current = next;
      setLocal(next);
      return d;
    });
  }, []);

  const onMouseUp = useCallback(() => {
    setDrag((d) => {
      if (d) {
        const { x, y } = posRef.current;
        // Single PATCH per completed drag.
        onMoveEnd(Math.round(x * 100) / 100, Math.round(y * 100) / 100);
      }
      return null;
    });
  }, [onMoveEnd]);

  useEffect(() => {
    if (!drag) return undefined;
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [drag, onMouseMove, onMouseUp]);

  const p = drag ? local : pos;

  return (
    <div
      data-testid={`sticky-${block.id}`}
      onMouseDown={(e) => {
        e.preventDefault();
        setDrag({ startX: e.clientX, startY: e.clientY, originX: p.x, originY: p.y });
      }}
      className="absolute select-none rounded-md border bg-white px-2 py-1.5 text-xs shadow-sm cursor-grab"
      style={{
        left: p.x,
        top: p.y,
        width: 180,
        borderColor: `oklch(60% 0.12 ${hue})`,
        borderLeftWidth: 3,
      }}
    >
      <div className="flex items-start justify-between gap-1">
        <span className="text-[9px] uppercase tracking-wide text-slate-400">
          {block.block_type.replace(/_/g, " ")}
        </span>
        <button
          type="button"
          onMouseDown={(e) => e.stopPropagation()}
          onClick={() => onDelete(block.id)}
          aria-label="Delete block"
          data-testid={`sticky-delete-${block.id}`}
          className="text-slate-400 hover:text-rose-600 leading-none"
        >
          ×
        </button>
      </div>
      <div className="text-slate-800">{block.block_text}</div>
    </div>
  );
}

Sticky.propTypes = {
  block: PropTypes.object.isRequired,
  pos: PropTypes.shape({ x: PropTypes.number, y: PropTypes.number }).isRequired,
  hue: PropTypes.number.isRequired,
  onMoveEnd: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
};

export default function IdeaCanvas({ themeId, themeLabel }) {
  const { blocks, status, mutError, reload, createBlock, moveBlock, deleteBlock } =
    useEssayBlocks(themeId);
  const [activeLens, setActiveLens] = useState(LENSES[0].key);

  const addFreeIdea = async (lensKey) => {
    setActiveLens(lensKey);
    const text = window.prompt(`New idea for ${LENS_LABEL[lensKey]}`);
    if (!text || !text.trim()) return;
    await createBlock({ block_type: BRANCH_IDEA_BLOCK_TYPE, block_text: text.trim(), lens: lensKey });
  };

  const addHelper = async (resType) => {
    // Helper block enters the currently-active branch (target lens), matching
    // "adding one creates a block with that block_type and the target lens".
    await createBlock({
      block_type: resType.type,
      block_text: resType.label,
      lens: activeLens,
    });
  };

  return (
    <div className="flex flex-col gap-3 lg:flex-row" data-testid="idea-canvas">
      {/* Canvas + branches */}
      <div className="flex-1 min-w-0">
        <div className="mb-2 flex items-center justify-between">
          <div className="text-sm text-slate-600" data-testid="idea-canvas-theme">
            Theme: <span className="font-medium">{themeLabel || themeId}</span>
          </div>
          <div className="text-[11px] text-slate-400">
            Drag stickies anywhere. Active branch: <strong>{LENS_LABEL[activeLens]}</strong>
          </div>
        </div>

        {mutError ? (
          <p className="mb-2 text-xs text-clay-700" role="alert" data-testid="idea-canvas-mut-error">
            {mutError}
          </p>
        ) : null}

        <div
          className="relative overflow-auto rounded border bg-[oklch(98%_0.005_85)]"
          style={{ height: 560 }}
          data-testid="idea-canvas-surface"
        >
          {/* central theme node */}
          <div
            className="absolute -translate-x-1/2 -translate-y-1/2 rounded-2xl border-2 bg-white px-4 py-3 text-center text-sm font-medium"
            style={{ left: 510, top: 430, width: 220, borderColor: "oklch(58% 0.14 75)" }}
          >
            {themeLabel || "This theme"}
          </div>

          {/* six branch labels + add-idea affordances */}
          {LENSES.map((lens) => {
            const a = LENS_ANCHOR[lens.key];
            const active = activeLens === lens.key;
            return (
              <div
                key={lens.key}
                className="absolute text-center"
                style={{ left: a.x - 30, top: a.y - 44, width: 200 }}
                data-testid={`branch-${lens.key}`}
              >
                <button
                  type="button"
                  onClick={() => setActiveLens(lens.key)}
                  className={
                    "rounded px-2 py-0.5 text-[12px] font-semibold " +
                    (active ? "ring-1 ring-slate-400" : "")
                  }
                  style={{ color: `oklch(45% 0.13 ${lens.hue})` }}
                  data-testid={`branch-select-${lens.key}`}
                  aria-pressed={active}
                >
                  {lens.label}
                </button>
                <div>
                  <button
                    type="button"
                    onClick={() => addFreeIdea(lens.key)}
                    className="text-[11px] text-slate-500 hover:text-slate-800"
                    data-testid={`branch-add-${lens.key}`}
                  >
                    + add idea
                  </button>
                </div>
              </div>
            );
          })}

          {/* stickies */}
          {status === "ready"
            ? blocks.map((b, i) => (
                <Sticky
                  key={b.id}
                  block={b}
                  pos={positionFor(b, i)}
                  hue={(LENSES.find((l) => l.key === b.lens) || {}).hue || 60}
                  onMoveEnd={(x, y) => moveBlock(b.id, x, y)}
                  onDelete={deleteBlock}
                />
              ))
            : null}

          {status === "loading" ? (
            <p className="p-4 text-sm text-slate-500" role="status" data-testid="idea-canvas-loading">
              Loading your canvas…
            </p>
          ) : null}
          {status === "error" ? (
            <div className="p-4 text-sm text-clay-700" role="alert" data-testid="idea-canvas-error">
              Couldn&apos;t load your canvas.{" "}
              <button type="button" onClick={reload} className="underline" data-testid="idea-canvas-retry">
                Retry
              </button>
            </div>
          ) : null}
        </div>
      </div>

      {/* Right rail: helpers + real questions */}
      <div className="w-full shrink-0 space-y-3 lg:w-64">
        <div className="rounded border p-3" data-testid="helper-rail">
          <div className="mb-2 text-[10.5px] uppercase tracking-wide text-slate-500">
            Helpers → {LENS_LABEL[activeLens]}
          </div>
          {RESOURCE_TYPES.map((r) => (
            <button
              key={r.type}
              type="button"
              onClick={() => addHelper(r)}
              className="mb-1 flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-xs hover:bg-slate-50"
              data-testid={`helper-add-${r.type}`}
            >
              <span>{r.label}</span>
              <span className="text-slate-400">+</span>
            </button>
          ))}
        </div>

        <PyqTagsSidebar themeId={themeId} />
      </div>
    </div>
  );
}

IdeaCanvas.propTypes = {
  themeId: PropTypes.string.isRequired,
  themeLabel: PropTypes.string,
};
