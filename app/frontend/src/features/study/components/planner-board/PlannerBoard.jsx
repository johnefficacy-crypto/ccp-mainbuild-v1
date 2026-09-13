import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../../../lib/api";
import useApiAction from "../../../../lib/hooks/useApiAction";
import DayColumn from "./DayColumn";
import TopicPalette from "./TopicPalette";
import RegeneratePreview from "./RegeneratePreview";
import {
  applyMove,
  describePlacement,
  findTask,
  insertCard,
  nextKeyboardPlacement,
  removeTask,
} from "./boardModel";

/**
 * The drag-and-drop planner: seven day columns plus a palette of topics.
 *
 * Every action writes immediately — there is no save button. Each write is
 * optimistic with an explicit rollback, so a failed request puts the card back
 * where it was AND says so; the board never drifts from the server while
 * looking like it succeeded.
 *
 * Keyboard parity is not an afterthought. Native HTML5 drag-and-drop is
 * pointer-only, so every move is also reachable as a command: focus a card's
 * move handle, press Enter or Space to pick it up, arrow keys to choose a day
 * and a position, Enter to drop, Escape to cancel. The pointer path and the
 * keyboard path both end in the same `commitMove`.
 */
export default function PlannerBoard() {
  const [board, setBoard] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [paletteError, setPaletteError] = useState("");
  const [announcement, setAnnouncement] = useState("");

  // Keyboard grab state: which card is picked up, and where it currently sits.
  const [grabbedId, setGrabbedId] = useState(null);
  const [grabbedPlacement, setGrabbedPlacement] = useState(null);
  const grabOriginRef = useRef(null);

  const [draft, setDraft] = useState(null);
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftError, setDraftError] = useState("");
  const [applying, setApplying] = useState(false);

  const { run, busy } = useApiAction();

  const loadBoard = useCallback(async () => {
    const data = await api.get("/api/study/plan/board");
    setBoard(data);
    return data;
  }, []);

  const loadCandidates = useCallback(async () => {
    try {
      const data = await api.get("/api/study/plan/candidates");
      setCandidates(Array.isArray(data?.items) ? data.items : []);
      setPaletteError("");
    } catch {
      setCandidates([]);
      setPaletteError("Topics are unavailable right now. Your board still works.");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadBoard()
      .then(() => {
        if (!cancelled) setError("");
      })
      .catch(() => {
        if (!cancelled) setError("Your board is unavailable right now. Try again shortly.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    loadCandidates();
    return () => {
      cancelled = true;
    };
  }, [loadBoard, loadCandidates]);

  /** One move, whatever started it. Optimistic, with a real rollback. */
  const commitMove = useCallback(
    async (taskId, toDate, toIndex) => {
      const previous = board;
      const optimistic = applyMove(board, taskId, toDate, toIndex);
      const result = await run({
        optimistic: () => setBoard(optimistic),
        action: () =>
          api.patch(`/api/study/plan/board/tasks/${taskId}/placement`, {
            scheduled_date: toDate,
            position: toIndex,
          }),
        rollback: () => setBoard(previous),
        errorMessage: "Couldn't move that block — it's back where it was.",
      });
      if (result.ok) {
        setAnnouncement(describePlacement(optimistic, taskId));
        loadCandidates();
      } else {
        setAnnouncement("Move failed. The block is back where it was.");
      }
      return result;
    },
    [board, run, loadCandidates],
  );

  const commitRemove = useCallback(
    async (task) => {
      const previous = board;
      const result = await run({
        optimistic: () => setBoard(removeTask(board, task.id)),
        action: () => api.del(`/api/study/plan/board/tasks/${task.id}`),
        rollback: () => setBoard(previous),
        successMessage: "Block removed.",
        errorMessage: "Couldn't remove that block — it's still there.",
      });
      if (result.ok) loadCandidates();
      return result;
    },
    [board, run, loadCandidates],
  );

  const commitAdd = useCallback(
    async (item, toDate, toIndex) => {
      const previous = board;
      const placeholder = {
        id: `pending-${item.topic_id}`,
        title: item.topic,
        topic: item.topic,
        topic_id: item.topic_id,
        subject: item.subject,
        task_type: "concept",
        status: "planned",
        scheduled_date: toDate,
        priority_score: item.exam_priority_score,
        source: "user",
        placed_by_user: true,
      };
      const result = await run({
        optimistic: () => setBoard(insertCard(board, placeholder, toDate, toIndex)),
        action: () =>
          api.post("/api/study/plan/board/tasks", {
            topic_id: item.topic_id,
            scheduled_date: toDate,
            position: toIndex,
          }),
        rollback: () => setBoard(previous),
        successMessage: "Added to your plan.",
        errorMessage: "Couldn't add that topic — nothing was changed.",
      });
      if (result.ok) {
        await loadBoard().catch(() => {});
        loadCandidates();
        setAnnouncement(`${item.topic} added.`);
      }
      return result;
    },
    [board, run, loadBoard, loadCandidates],
  );

  /** Pointer drop: a board card by id, or a palette topic by `topic:<id>`. */
  const handleDropAt = useCallback(
    (payload, toDate, toIndex) => {
      if (payload.startsWith("topic:")) {
        const topicId = payload.slice("topic:".length);
        const item = candidates.find((c) => c.topic_id === topicId);
        if (item) commitAdd(item, toDate, toIndex);
        return;
      }
      commitMove(payload, toDate, toIndex);
    },
    [candidates, commitAdd, commitMove],
  );

  const toggleGrab = useCallback(
    (task) => {
      if (grabbedId === task.id) {
        const placement = grabbedPlacement;
        setGrabbedId(null);
        setGrabbedPlacement(null);
        const origin = grabOriginRef.current;
        if (
          placement &&
          origin &&
          (placement.date !== origin.date || placement.index !== origin.index)
        ) {
          commitMove(task.id, placement.date, placement.index);
        } else {
          setAnnouncement("Move cancelled.");
        }
        return;
      }
      const found = findTask(board, task.id);
      if (!found) return;
      const placement = { date: found.day.date, index: found.index };
      grabOriginRef.current = placement;
      setGrabbedId(task.id);
      setGrabbedPlacement(placement);
      setAnnouncement(
        `${task.topic || task.title} picked up. Arrow keys to move, Enter to drop, Escape to cancel.`,
      );
    },
    [board, grabbedId, grabbedPlacement, commitMove],
  );

  const handleCardKeyDown = useCallback(
    (event) => {
      if (!grabbedId) return;
      if (event.key === "Escape") {
        event.preventDefault();
        setGrabbedId(null);
        setGrabbedPlacement(null);
        setAnnouncement("Move cancelled.");
        return;
      }
      const next = nextKeyboardPlacement(board, grabbedPlacement, event.key);
      if (!next) return;
      event.preventDefault();
      setGrabbedPlacement(next);
      const day = (board?.days || []).find((d) => d.date === next.date);
      setAnnouncement(`${day ? day.label : next.date}, position ${next.index + 1}.`);
    },
    [board, grabbedId, grabbedPlacement],
  );

  async function previewRegeneration() {
    setDraftLoading(true);
    setDraftError("");
    try {
      const data = await api.get("/api/study/plan/draft");
      setDraft(data);
      if (data?.generated === false) {
        setDraftError("A new plan can't be built right now.");
      }
    } catch {
      setDraftError("Couldn't check what would change. Try again shortly.");
    } finally {
      setDraftLoading(false);
    }
  }

  async function applyRegeneration() {
    setApplying(true);
    const result = await run({
      action: () => api.post("/api/study/plan/apply", {}),
      successMessage: "Today rebuilt.",
      errorMessage: "Couldn't rebuild today — nothing was changed.",
    });
    setApplying(false);
    if (result.ok) {
      setDraft(null);
      await loadBoard().catch(() => {});
      loadCandidates();
    }
  }

  if (loading) {
    return (
      <p role="status" className="py-8 text-sm text-clay-700">
        Loading your board…
      </p>
    );
  }

  if (error) {
    return (
      <div className="py-8">
        <p role="status" className="text-sm text-rose-700">
          {error}
        </p>
      </div>
    );
  }

  const days = board?.days || [];
  const today = board?.today;
  const todayColumn = days.find((d) => d.date === today);
  const protectedCount = (todayColumn?.tasks || []).filter((t) => t.placed_by_user)
    .length;

  return (
    <div className="mt-6 flex flex-col gap-6">
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>

      <div className="rounded-xl border border-[#E7DECB] bg-[#FBF6EF] px-4 py-3">
        <p className="text-[12.5px] leading-relaxed text-[#2E2218]">
          Blocks marked <strong>Yours · stays put</strong> are ones you arranged.
          The planner leaves them alone. Blocks marked{" "}
          <strong>Planner · may change</strong> can be replaced when today is
          rebuilt. Moving a block makes it yours.
        </p>
        <p className="mt-1.5 text-[11.5px] text-clay-700">
          To move a block without a mouse: focus its move handle, press Enter to
          pick it up, arrow keys to choose a day and position, Enter to drop,
          Escape to cancel.
        </p>
      </div>

      <RegeneratePreview
        draft={draft}
        protectedCount={protectedCount}
        loading={draftLoading}
        error={draftError}
        onPreview={previewRegeneration}
        onApply={applyRegeneration}
        applying={applying}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_320px] lg:items-start">
        <div className="flex gap-3 overflow-x-auto pb-2">
          {days.map((day) => (
            <DayColumn
              key={day.date}
              day={day}
              isToday={day.date === today}
              grabbedId={grabbedId}
              grabbedPlacement={grabbedPlacement}
              onGrabToggle={toggleGrab}
              onCardKeyDown={handleCardKeyDown}
              onRemove={commitRemove}
              onDropAt={handleDropAt}
              busy={busy}
              maxTasks={board?.max_tasks_per_day ?? undefined}
            />
          ))}
        </div>

        <TopicPalette
          items={candidates}
          days={days}
          onAdd={(item, date) => commitAdd(item, date, undefined)}
          busy={busy}
          error={paletteError}
        />
      </div>
    </div>
  );
}
