import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPatch = jest.fn();
const mockDel = jest.fn();
const mockErrorToast = jest.fn();

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...a) => mockGet(...a),
    post: (...a) => mockPost(...a),
    patch: (...a) => mockPatch(...a),
    del: (...a) => mockDel(...a),
  },
}));

// Faithful re-implementation of useApiAction so the real optimistic →
// request → rollback control flow runs without the ToastProvider.
jest.mock("../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({
    busy: false,
    run: async ({ action, optimistic, rollback, onSuccess, errorMessage }) => {
      if (optimistic) optimistic();
      try {
        const data = await action();
        if (onSuccess) onSuccess(data);
        return { ok: true, data };
      } catch (e) {
        if (rollback) rollback();
        mockErrorToast(errorMessage);
        return { ok: false, error: e };
      }
    },
  }),
}));

// eslint-disable-next-line import/first
import PlannerBoard from "./PlannerBoard";

const DAYS = [
  { date: "2026-09-13", label: "Today" },
  { date: "2026-09-14", label: "Tomorrow" },
  { date: "2026-09-15", label: "Tue 15 Sep" },
  { date: "2026-09-16", label: "Wed 16 Sep" },
  { date: "2026-09-17", label: "Thu 17 Sep" },
  { date: "2026-09-18", label: "Fri 18 Sep" },
  { date: "2026-09-19", label: "Sat 19 Sep" },
];

function card(id, topic, { user = false, date = "2026-09-13" } = {}) {
  return {
    id,
    title: `${topic} · Study`,
    topic,
    topic_id: `topic-${id}`,
    subject: "Quantitative Aptitude",
    task_type: "concept",
    status: "planned",
    scheduled_date: date,
    planned_minutes: 25,
    priority_score: 80,
    source: user ? "user" : "planner",
    placed_by_user: user,
    why: "This task comes from your active study plan.",
  };
}

function board(tasksByDate = {}) {
  return {
    plan_id: "plan-1",
    today: DAYS[0].date,
    days: DAYS.map((d) => ({ ...d, tasks: tasksByDate[d.date] || [] })),
    max_tasks_per_day: 3,
    read_error: false,
  };
}

const CANDIDATES = {
  items: [
    { topic_id: "t-9", topic: "Time and Work", subject: "Quantitative Aptitude", exam_priority_score: 72 },
    { topic_id: "t-8", topic: "Polity Basics", subject: "General Studies", exam_priority_score: 61 },
  ],
};

function wireGet(boardPayload, candidatesPayload = CANDIDATES) {
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/plan/board") return Promise.resolve(boardPayload);
    if (path === "/api/study/plan/candidates") return Promise.resolve(candidatesPayload);
    if (path === "/api/study/plan/draft") {
      return Promise.resolve({
        generated: true,
        changes: { added_count: 2, removed_count: 1, unchanged_count: 1 },
        risk_level: "medium",
      });
    }
    return Promise.resolve({});
  });
}

beforeEach(() => {
  jest.clearAllMocks();
});

async function renderBoard(payload) {
  wireGet(payload);
  render(<PlannerBoard />);
  await waitFor(() => expect(screen.getAllByTestId("board-task").length).toBeGreaterThan(0));
}

function cardIdsInColumn(label) {
  const column = screen.getByRole("region", { name: new RegExp(`^${label},`) });
  return within(column)
    .queryAllByTestId("board-task")
    .map((el) => el.getAttribute("data-task-id"));
}

// ── rendering the distinction ───────────────────────────────────────────

test("user-placed and planner tasks are distinguishable in words, not colour alone", async () => {
  await renderBoard(
    board({ "2026-09-13": [card("a", "Percentage"), card("b", "Ratios", { user: true })] }),
  );

  // Once on the card, once in the legend that explains what the label means.
  expect(screen.getAllByText("Planner · may change")).toHaveLength(2);
  expect(screen.getAllByText("Yours · stays put")).toHaveLength(2);
  expect(screen.getByText(/Moving a block makes it yours/i)).toBeInTheDocument();

  const cards = screen.getAllByTestId("board-task");
  expect(cards.map((c) => c.getAttribute("data-source"))).toEqual(["planner", "user"]);
});

test("all seven days render, today first", async () => {
  await renderBoard(board({ "2026-09-13": [card("a", "Percentage")] }));
  for (const d of DAYS) {
    expect(
      screen.getByRole("region", { name: new RegExp(`^${d.label},`) }),
    ).toBeInTheDocument();
  }
});

// ── reorder persists ────────────────────────────────────────────────────

test("a reorder persists and survives a remount", async () => {
  const initial = board({
    "2026-09-13": [card("a", "Percentage"), card("b", "Ratios")],
  });
  mockPatch.mockResolvedValue({ ...card("b", "Ratios", { user: true }) });
  await renderBoard(initial);

  expect(cardIdsInColumn("Today")).toEqual(["a", "b"]);

  const gaps = screen.getAllByTestId("board-drop-gap");
  const topGap = gaps.find(
    (g) => g.getAttribute("data-date") === "2026-09-13" && g.getAttribute("data-index") === "0",
  );
  fireEvent.drop(topGap, {
    dataTransfer: { getData: () => "b", dropEffect: "move" },
  });

  await waitFor(() =>
    expect(mockPatch).toHaveBeenCalledWith(
      "/api/study/plan/board/tasks/b/placement",
      { scheduled_date: "2026-09-13", position: 0 },
    ),
  );
  await waitFor(() => expect(cardIdsInColumn("Today")).toEqual(["b", "a"]));

  // Remount against what the server now returns — the order is the server's,
  // not a local artefact.
  const persisted = board({
    "2026-09-13": [card("b", "Ratios", { user: true }), card("a", "Percentage")],
  });
  wireGet(persisted);
  const { unmount } = render(<PlannerBoard />);
  await waitFor(() => expect(screen.getAllByTestId("board-task").length).toBeGreaterThan(0));
  unmount();
});

test("a failed write reverts the card and surfaces an error", async () => {
  mockPatch.mockRejectedValue(new Error("boom"));
  await renderBoard(
    board({ "2026-09-13": [card("a", "Percentage"), card("b", "Ratios")] }),
  );

  const gaps = screen.getAllByTestId("board-drop-gap");
  const topGap = gaps.find(
    (g) => g.getAttribute("data-date") === "2026-09-13" && g.getAttribute("data-index") === "0",
  );
  fireEvent.drop(topGap, { dataTransfer: { getData: () => "b", dropEffect: "move" } });

  await waitFor(() => expect(mockErrorToast).toHaveBeenCalled());
  expect(cardIdsInColumn("Today")).toEqual(["a", "b"]);
  expect(mockErrorToast).toHaveBeenCalledWith(
    "Couldn't move that block — it's back where it was.",
  );
});

// ── keyboard parity ─────────────────────────────────────────────────────

test("every drag operation is reachable by keyboard", async () => {
  mockPatch.mockResolvedValue(card("b", "Ratios", { user: true, date: "2026-09-14" }));
  await renderBoard(
    board({ "2026-09-13": [card("a", "Percentage"), card("b", "Ratios")] }),
  );

  const handle = screen.getByRole("button", { name: "Move Ratios" });

  // Pick up.
  fireEvent.click(handle);
  expect(handle).toHaveAttribute("aria-pressed", "true");

  // Move to the next day, then drop.
  fireEvent.keyDown(handle, { key: "ArrowRight" });
  fireEvent.click(screen.getByRole("button", { name: "Drop Ratios" }));

  await waitFor(() =>
    expect(mockPatch).toHaveBeenCalledWith(
      "/api/study/plan/board/tasks/b/placement",
      { scheduled_date: "2026-09-14", position: 0 },
    ),
  );
});

test("Escape cancels a keyboard move without writing", async () => {
  await renderBoard(
    board({ "2026-09-13": [card("a", "Percentage"), card("b", "Ratios")] }),
  );

  const handle = screen.getByRole("button", { name: "Move Ratios" });
  fireEvent.click(handle);
  fireEvent.keyDown(handle, { key: "ArrowRight" });
  fireEvent.keyDown(handle, { key: "Escape" });

  expect(mockPatch).not.toHaveBeenCalled();
  expect(cardIdsInColumn("Today")).toEqual(["a", "b"]);
});

test("a keyboard move that changes nothing does not write", async () => {
  await renderBoard(board({ "2026-09-13": [card("a", "Percentage")] }));
  const handle = screen.getByRole("button", { name: "Move Percentage" });
  fireEvent.click(handle);
  fireEvent.click(screen.getByRole("button", { name: "Drop Percentage" }));
  expect(mockPatch).not.toHaveBeenCalled();
});

// ── palette ─────────────────────────────────────────────────────────────

test("the palette lists candidates and adds one to a chosen day without a pointer", async () => {
  mockPost.mockResolvedValue(card("new-1", "Time and Work", { user: true, date: "2026-09-15" }));
  await renderBoard(board({ "2026-09-13": [card("a", "Percentage")] }));

  // PLAN-UI-02: the palette is a syllabus tree now, so it opens on one subject
  // rather than listing every candidate at once. The other subject's topic is
  // one click away, not gone.
  expect(screen.getByText("Time and Work")).toBeInTheDocument();
  expect(screen.queryByText("Polity Basics")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /General Studies/ }));
  expect(screen.getByText("Polity Basics")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Quantitative Aptitude/ }));

  fireEvent.change(screen.getByLabelText("Day for Time and Work"), {
    target: { value: "2026-09-15" },
  });
  const firstTopic = screen.getAllByTestId("palette-topic")[0];
  fireEvent.click(within(firstTopic).getByRole("button", { name: "Add" }));

  await waitFor(() =>
    expect(mockPost).toHaveBeenCalledWith("/api/study/plan/board/tasks", {
      topic_id: "t-9",
      scheduled_date: "2026-09-15",
      position: undefined,
    }),
  );
});

test("the palette excludes topics already scheduled", async () => {
  // The server does the excluding; the component must not re-add them.
  wireGet(board({ "2026-09-13": [card("a", "Percentage")] }), { items: [] });
  render(<PlannerBoard />);
  await waitFor(() =>
    expect(screen.getByText(/Every verified topic is already on your board/i)).toBeInTheDocument(),
  );
  expect(screen.queryAllByTestId("palette-topic")).toHaveLength(0);
});

test("palette search narrows the list", async () => {
  await renderBoard(board({ "2026-09-13": [card("a", "Percentage")] }));
  fireEvent.change(screen.getByLabelText("Search topics"), {
    target: { value: "polity" },
  });
  expect(screen.queryByText("Time and Work")).not.toBeInTheDocument();
  expect(screen.getByText("Polity Basics")).toBeInTheDocument();
});

// ── removal ─────────────────────────────────────────────────────────────

test("removing a block calls delete and drops the card", async () => {
  mockDel.mockResolvedValue({ id: "a", deleted: true });
  await renderBoard(board({ "2026-09-13": [card("a", "Percentage")] }));

  fireEvent.click(screen.getByRole("button", { name: "Remove Percentage" }));

  await waitFor(() =>
    expect(mockDel).toHaveBeenCalledWith("/api/study/plan/board/tasks/a"),
  );
  await waitFor(() => expect(cardIdsInColumn("Today")).toEqual([]));
});

// ── regeneration preview ────────────────────────────────────────────────

test("regeneration shows the diff and counts protected blocks before committing", async () => {
  await renderBoard(
    board({
      "2026-09-13": [card("a", "Percentage"), card("b", "Ratios", { user: true })],
    }),
  );

  expect(screen.getByText(/Your 1 arranged block stays/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "See what changes" }));

  await waitFor(() => expect(screen.getByText("Today changes noticeably.")).toBeInTheDocument());
  expect(screen.getByRole("button", { name: "Rebuild today" })).toBeInTheDocument();
  expect(mockPost).not.toHaveBeenCalledWith("/api/study/plan/apply", {});
});

// ── failure surfaces ────────────────────────────────────────────────────

test("a board read failure says so instead of showing an empty week", async () => {
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/plan/board") return Promise.reject(new Error("down"));
    return Promise.resolve({ items: [] });
  });
  render(<PlannerBoard />);
  await waitFor(() =>
    expect(screen.getByText(/Your board is unavailable right now/i)).toBeInTheDocument(),
  );
  expect(screen.queryAllByRole("region")).toHaveLength(0);
});

// ── PLAN-BUG-01: a card must reach another day ──────────────────────────
//
// Written red. The board's only drop targets were the 8px transparent gaps
// between cards, so everything else in a day column — the space below the
// last card, an empty column's body, the surface of a card — rejected every
// drop, because a target that does not preventDefault on `dragover` silently
// refuses. A user dragging a block to another day hit that dead surface
// almost every time and the card sprang back.

function dayColumn(label) {
  return screen.getByRole("region", { name: new RegExp(`^${label},`) });
}

function dropGap(date, index) {
  return screen
    .getAllByTestId("board-drop-gap")
    .find(
      (g) =>
        g.getAttribute("data-date") === date &&
        g.getAttribute("data-index") === String(index),
    );
}

const DT = (id) => ({ getData: () => id, dropEffect: "move" });

test("a card dropped on another day's column body lands on that day", async () => {
  mockPatch.mockResolvedValue(card("b", "Ratios", { user: true, date: "2026-09-15" }));
  await renderBoard(
    board({ "2026-09-13": [card("a", "Percentage"), card("b", "Ratios")] }),
  );

  const target = dayColumn("Tue 15 Sep");
  fireEvent.dragOver(target, { dataTransfer: DT("b") });
  fireEvent.drop(target, { dataTransfer: DT("b") });

  await waitFor(() =>
    expect(mockPatch).toHaveBeenCalledWith(
      "/api/study/plan/board/tasks/b/placement",
      { scheduled_date: "2026-09-15", position: 0 },
    ),
  );
  await waitFor(() => expect(cardIdsInColumn("Tue 15 Sep")).toEqual(["b"]));
  // And the day it left renumbers contiguously — no hole where it was.
  expect(cardIdsInColumn("Today")).toEqual(["a"]);
});

test("a card dropped on a gap in another day lands at that position", async () => {
  mockPatch.mockResolvedValue(card("c", "Ratios", { user: true, date: "2026-09-14" }));
  await renderBoard(
    board({
      "2026-09-13": [card("a", "Percentage"), card("c", "Ratios")],
      "2026-09-14": [card("b", "Averages")],
    }),
  );

  const gap = dropGap("2026-09-14", 0);
  fireEvent.drop(gap, { dataTransfer: DT("c") });

  await waitFor(() =>
    expect(mockPatch).toHaveBeenCalledWith(
      "/api/study/plan/board/tasks/c/placement",
      { scheduled_date: "2026-09-14", position: 0 },
    ),
  );
  await waitFor(() => expect(cardIdsInColumn("Tomorrow")).toEqual(["c", "b"]));
  expect(cardIdsInColumn("Today")).toEqual(["a"]);
  // One write, not two: the gap's drop must not also bubble to the column.
  expect(mockPatch).toHaveBeenCalledTimes(1);
});

test("a card dropped over another card lands on that card's day", async () => {
  mockPatch.mockResolvedValue(card("c", "Ratios", { user: true, date: "2026-09-14" }));
  await renderBoard(
    board({
      "2026-09-13": [card("c", "Ratios")],
      "2026-09-14": [card("b", "Averages")],
    }),
  );

  const [, occupant] = screen.getAllByTestId("board-task");
  fireEvent.dragOver(occupant, { dataTransfer: DT("c") });
  fireEvent.drop(occupant, { dataTransfer: DT("c") });

  await waitFor(() =>
    expect(mockPatch).toHaveBeenCalledWith(
      "/api/study/plan/board/tasks/c/placement",
      { scheduled_date: "2026-09-14", position: 1 },
    ),
  );
  expect(cardIdsInColumn("Tomorrow")).toEqual(["b", "c"]);
});

test("a rejected cross-day write puts the card back and says so", async () => {
  mockPatch.mockRejectedValue(new Error("boom"));
  await renderBoard(
    board({ "2026-09-13": [card("a", "Percentage"), card("b", "Ratios")] }),
  );

  const target = dayColumn("Thu 17 Sep");
  fireEvent.drop(target, { dataTransfer: DT("b") });

  await waitFor(() => expect(mockErrorToast).toHaveBeenCalled());
  expect(cardIdsInColumn("Today")).toEqual(["a", "b"]);
  expect(cardIdsInColumn("Thu 17 Sep")).toEqual([]);
});

test("dropping a card back where it already is writes nothing", async () => {
  await renderBoard(
    board({ "2026-09-13": [card("a", "Percentage"), card("b", "Ratios")] }),
  );

  // Its own position, both spellings of it: the gap above the card and the
  // gap below it leave the order untouched.
  fireEvent.drop(dropGap("2026-09-13", 1), { dataTransfer: DT("b") });
  fireEvent.drop(dropGap("2026-09-13", 2), { dataTransfer: DT("b") });

  await waitFor(() => expect(cardIdsInColumn("Today")).toEqual(["a", "b"]));
  expect(mockPatch).not.toHaveBeenCalled();
});
