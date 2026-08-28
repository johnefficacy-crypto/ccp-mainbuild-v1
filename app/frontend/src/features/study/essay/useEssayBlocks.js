import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../../lib/api";

const BLOCKS_BASE = "/api/essay-brainstorm-blocks";

// useEssayBlocks — load + mutate the caller's own brainstorm blocks for one
// theme against the real /essay-brainstorm-blocks endpoints. All rows are
// owned by the aspirant (backend 404s on anything not theirs).
//
// status: "loading" | "ready" | "error". Mutations optimistically/confirmed
// update local state so the canvas never silently goes stale after a write;
// a failed write restores prior state and surfaces an error string.
export default function useEssayBlocks(themeId) {
  const [blocks, setBlocks] = useState([]);
  const [status, setStatus] = useState("loading");
  const [mutError, setMutError] = useState("");
  const gen = useRef(0);

  const load = useCallback(async () => {
    if (!themeId) return;
    const my = ++gen.current;
    setStatus("loading");
    try {
      const res = await api.get(
        `${BLOCKS_BASE}?theme_id=${encodeURIComponent(themeId)}`,
      );
      if (my !== gen.current) return;
      setBlocks(Array.isArray(res?.items) ? res.items : []);
      setStatus("ready");
    } catch {
      if (my !== gen.current) return;
      setStatus("error");
    }
  }, [themeId]);

  useEffect(() => { load(); }, [load]);

  // Create a block. Returns the created row (or null on failure). New block is
  // appended to local state so it appears immediately.
  const createBlock = useCallback(async (payload) => {
    setMutError("");
    try {
      const row = await api.post(BLOCKS_BASE, { theme_id: themeId, ...payload });
      setBlocks((prev) => [row, ...prev]);
      return row;
    } catch (e) {
      setMutError(e?.message || "Couldn't add that block.");
      return null;
    }
  }, [themeId]);

  // Move a block: exactly one PATCH carrying BOTH coordinates (the backend
  // rejects a single-axis update). Optimistic; reverts on failure.
  const moveBlock = useCallback(async (id, x, y) => {
    setMutError("");
    let prevPos = null;
    setBlocks((prev) =>
      prev.map((b) => {
        if (b.id !== id) return b;
        prevPos = { canvas_x: b.canvas_x, canvas_y: b.canvas_y };
        return { ...b, canvas_x: x, canvas_y: y };
      }),
    );
    try {
      const row = await api.patch(`${BLOCKS_BASE}/${encodeURIComponent(id)}`, {
        canvas_x: x,
        canvas_y: y,
      });
      setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, ...row } : b)));
      return true;
    } catch (e) {
      if (prevPos) {
        setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, ...prevPos } : b)));
      }
      setMutError(e?.message || "Couldn't save that move.");
      return false;
    }
  }, []);

  const deleteBlock = useCallback(async (id) => {
    setMutError("");
    const snapshot = blocks;
    setBlocks((prev) => prev.filter((b) => b.id !== id));
    try {
      await api.delete(`${BLOCKS_BASE}/${encodeURIComponent(id)}`);
      return true;
    } catch (e) {
      setBlocks(snapshot); // restore — never leave the UI stale on a failed delete
      setMutError(e?.message || "Couldn't delete that block.");
      return false;
    }
  }, [blocks]);

  return { blocks, status, mutError, reload: load, createBlock, moveBlock, deleteBlock };
}
