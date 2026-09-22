import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";

import ErrorState from "../../../shared/ui/ErrorState";
import LoadingSkeleton from "../../../shared/ui/LoadingSkeleton";
import SpineSlot from "./SpineSlot";
import ThemeSelector from "./ThemeSelector";
import useSpineBlocks from "./useSpineBlocks";
import {
  SPINE_SECTIONS,
  SPINE_SLOTS,
  SPINE_TARGET_WORDS_HIGH,
  SPINE_TARGET_WORDS_LOW,
  blocksForSlot,
  plannedWordCount,
  promotedBlocks,
} from "./spineSlots";

/**
 * Essay Spine — sequence brainstormed content into an essay structure.
 *
 * Reads and writes `/api/essay-brainstorm-blocks` only (PR #1035 / #1036).
 * Spine blocks carry no `lens` and no canvas position: this is a linear
 * sequence, not the spatial Idea Canvas, so nothing here sends those fields.
 *
 * With no theme chosen the screen renders the shared `ThemeSelector`, which
 * reads the real catalogue from `GET /api/essay-themes` (PR #1041). That
 * replaced an earlier stopgap that listed the raw `theme_id`s of blocks the
 * aspirant already had — it could not show theme names and gave a first-time
 * aspirant no way in at all.
 *
 * The `themeId` prop (the `:themeId` route param) still deep-links straight
 * past the picker; the picker is an alternate entry path, not a replacement.
 *
 * Stitching this screen and the Idea Canvas into one navigable flow remains a
 * separate task.
 */
export default function EssaySpineScreen({ themeId: themeIdProp = null }) {
  const [selectedTheme, setSelectedTheme] = useState(themeIdProp || null);
  const themeId = themeIdProp || selectedTheme;

  const {
    blocks,
    status,
    refresh,
    refreshAll,
    createBlock,
    updateBlock,
    deleteBlock,
  } = useSpineBlocks(themeId);

  const planned = useMemo(() => plannedWordCount(blocks), [blocks]);
  const promoted = useMemo(() => promotedBlocks(blocks), [blocks]);

  const header = (
    <header>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">Essay builder</p>
      <h1 className="mt-1 font-heading text-2xl font-semibold">Spine</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Put your material in the order the essay should read — introduction, body, conclusion.
      </p>
    </header>
  );

  if (!themeId) {
    return (
      <div className="mx-auto max-w-3xl p-4" data-testid="essay-spine">
        {header}
        <div className="mt-6" data-testid="essay-spine-theme-picker">
          <ThemeSelector
            onPick={(id) => setSelectedTheme(id)}
            subtitle="Pick the essay theme you want to sequence."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-4" data-testid="essay-spine">
      {header}

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <p className="text-sm text-muted-foreground">
          Planned length: <b>{planned}</b> words
          <span className="text-xs"> · target {SPINE_TARGET_WORDS_LOW}–{SPINE_TARGET_WORDS_HIGH}</span>
        </p>
        {!themeIdProp && (
          <button type="button" className="btn btn-ghost" onClick={() => setSelectedTheme(null)}>
            Switch theme
          </button>
        )}
      </div>

      {status === "loading" && (
        <div className="mt-6" data-testid="essay-spine-loading">
          <LoadingSkeleton variant="card" />
        </div>
      )}

      {status === "error" && (
        <div className="mt-6" data-testid="essay-spine-error">
          <ErrorState
            title="Could not load this essay"
            message="Your spine is safe — we just could not read it back. Try again."
            onRetry={refresh}
          />
        </div>
      )}

      {(status === "live" || status === "empty") && (
        <div className="mt-6 space-y-8" data-testid="essay-spine-slots">
          {SPINE_SECTIONS.map((section) => (
            <div key={section}>
              <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {section}
              </h2>
              <div className="mt-3 space-y-4">
                {SPINE_SLOTS.filter((slot) => slot.section === section).map((slot) => (
                  <SpineSlot
                    key={slot.blockType}
                    slot={slot}
                    blocks={blocksForSlot(blocks, slot.blockType)}
                    onCreate={createBlock}
                    onUpdate={updateBlock}
                    onDelete={deleteBlock}
                    onChanged={refreshAll}
                  />
                ))}
              </div>
            </div>
          ))}

          {promoted.length > 0 && (
            <section data-testid="essay-spine-promoted">
              <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                From your brainstorm
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Material you promoted off the canvas. Work it into the slots above in your own words.
              </p>
              <ul className="mt-3 space-y-2">
                {promoted.map((block) => (
                  <li key={block.id} className="soft-card rounded-xl p-3 text-sm">
                    {block.block_text}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

EssaySpineScreen.propTypes = {
  themeId: PropTypes.string,
};
