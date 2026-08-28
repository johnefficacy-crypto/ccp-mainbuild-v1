import { useCallback } from "react";

import { api } from "../../../lib/api";
import useApiCollection from "../../../lib/hooks/useApiCollection";

/**
 * Data layer for the Essay Spine screen.
 *
 * One API source of truth: `/api/essay-brainstorm-blocks` (PR #1035), scoped
 * server-side to the authenticated aspirant's own rows.
 *
 * Two reads, deliberately:
 *   - `blocks`  — the selected theme's blocks, the authoritative slot content.
 *   - `themes`  — every theme the aspirant already has a block under, so the
 *                 screen can offer a switcher between essays in progress.
 *
 * Writes never send `lens` or `canvas_x`/`canvas_y`: a Spine block is not on
 * the canvas, and the columns default to null. Sending them would be the one
 * way this screen could corrupt Idea Canvas state.
 */

const BLOCKS_URL = "/api/essay-brainstorm-blocks";
// The endpoint caps `limit` at 500; ask for the ceiling on the switcher read so
// a prolific aspirant's older themes don't silently drop out of the list.
const THEME_SCAN_LIMIT = 500;

export default function useSpineBlocks(themeId) {
  // Server-side filtering, not client-side: the theme scan below is capped, so
  // filtering the scan would silently drop blocks past the cap on a busy theme.
  // With no theme selected this read duplicates the scan — one extra GET on a
  // screen that only renders the theme picker, which is not worth a workaround
  // that would break the rules of hooks.
  const blocks = useApiCollection(BLOCKS_URL, [], {
    params: themeId ? { theme_id: themeId } : undefined,
  });
  const themeScan = useApiCollection(BLOCKS_URL, [], {
    params: { limit: String(THEME_SCAN_LIMIT) },
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

  const refreshAll = useCallback(async () => {
    await Promise.all([blocks.refresh(), themeScan.refresh()]);
  }, [blocks, themeScan]);

  return {
    blocks: blocks.items,
    status: blocks.status,
    refresh: blocks.refresh,
    refreshAll,
    themeScanBlocks: themeScan.items,
    themeScanStatus: themeScan.status,
    createBlock,
    updateBlock,
    deleteBlock,
  };
}
