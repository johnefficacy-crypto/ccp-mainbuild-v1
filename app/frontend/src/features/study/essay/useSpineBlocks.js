import { useCallback } from "react";

import { api } from "../../../lib/api";
import useApiCollection from "../../../lib/hooks/useApiCollection";

/**
 * Data layer for the Essay Spine screen.
 *
 * One API source of truth: `/api/essay-brainstorm-blocks` (PR #1035), scoped
 * server-side to the authenticated aspirant's own rows.
 *
 * One read: the selected theme's blocks, the authoritative slot content. The
 * theme catalogue itself comes from `GET /api/essay-themes` via the shared
 * `ThemeSelector`, so this hook no longer scans every block the aspirant owns
 * just to recover a list of theme ids.
 *
 * Writes never send `lens` or `canvas_x`/`canvas_y`: a Spine block is not on
 * the canvas, and the columns default to null. Sending them would be the one
 * way this screen could corrupt Idea Canvas state.
 */

const BLOCKS_URL = "/api/essay-brainstorm-blocks";

export default function useSpineBlocks(themeId) {
  // lens_scope=spine — the server returns only lens-null blocks, so the slots
  // cannot receive Idea Canvas content. `isSpineBlock()` still runs downstream;
  // it is now a second line of defence rather than the only one.
  const blocks = useApiCollection(BLOCKS_URL, [], {
    params: themeId
      ? { theme_id: themeId, lens_scope: "spine" }
      : { lens_scope: "spine" },
  });

  const createBlock = useCallback(
    (blockType, text) =>
      api.post(BLOCKS_URL, {
        theme_id: themeId,
        block_type: blockType,
        block_text: text,
      }),
    [themeId],
  );

  const updateBlock = useCallback(
    (blockId, text) => api.patch(`${BLOCKS_URL}/${blockId}`, { block_text: text }),
    [],
  );

  const deleteBlock = useCallback((blockId) => api.delete(`${BLOCKS_URL}/${blockId}`), []);

  // Kept as the single write-completion hook the slots call, so a later
  // second read can be added here without touching every call site.
  const refreshAll = useCallback(async () => {
    await blocks.refresh();
  }, [blocks]);

  return {
    blocks: blocks.items,
    status: blocks.status,
    refresh: blocks.refresh,
    refreshAll,
    createBlock,
    updateBlock,
    deleteBlock,
  };
}
