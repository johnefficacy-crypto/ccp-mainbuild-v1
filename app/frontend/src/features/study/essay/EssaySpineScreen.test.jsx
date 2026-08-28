import React from "react";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import "@testing-library/jest-dom";

import EssaySpineScreen from "./EssaySpineScreen";
import ToastProvider from "../../../shared/ui/ToastProvider";
import { api } from "../../../lib/api";
import { SPINE_SLOTS } from "./spineSlots";

// Factory mock so the real client (which pulls in supabase) never loads.
jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn(), delete: jest.fn() },
}));

// `useApiCollection` imports the env config directly, and that module throws
// when REACT_APP_BACKEND_URL is unset — which it is under `react-scripts test`.
// Mocking the config keeps this suite runnable without a real backend URL.
jest.mock("../../../shared/config/env", () => ({
  __esModule: true,
  BACKEND_URL: "http://backend.test",
  API_TIMEOUT_MS: 15000,
  ENABLE_DEMO_DATA: false,
}));

const THEME = "11111111-1111-4111-8111-111111111111";

function block(over = {}) {
  return {
    id: "b1",
    theme_id: THEME,
    block_type: "hook",
    block_text: "An opening line.",
    lens: null,
    linked_gs_topic_id: null,
    canvas_x: null,
    canvas_y: null,
    created_at: "2026-08-01T00:00:00+00:00",
    ...over,
  };
}

/** Serve every GET from one block list, regardless of which read asks. */
function serve(items) {
  api.get.mockImplementation(() => Promise.resolve({ items }));
}

function renderScreen(props = {}) {
  return render(
    <ToastProvider>
      <EssaySpineScreen themeId={THEME} {...props} />
    </ToastProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  api.post.mockResolvedValue({});
  api.patch.mockResolvedValue({});
  api.delete.mockResolvedValue({ ok: true });
});

test("every slot renders a clear not-started state when nothing is written", async () => {
  serve([]);
  renderScreen();

  await screen.findByTestId("essay-spine-slots");
  for (const slot of SPINE_SLOTS) {
    const section = screen.getByTestId(`spine-slot-${slot.blockType}`);
    expect(within(section).getByTestId(`spine-slot-${slot.blockType}-empty`)).toBeInTheDocument();
    expect(within(section).getByText("Not started yet.")).toBeInTheDocument();
  }
});

test("body is two separately labelled slots, not one merged bucket", async () => {
  serve([]);
  renderScreen();

  await screen.findByTestId("essay-spine-slots");
  expect(screen.getByText("Supporting argument")).toBeInTheDocument();
  expect(screen.getByText("Counter-consideration")).toBeInTheDocument();
  expect(screen.queryByText("Body paragraph")).not.toBeInTheDocument();
  // The raw enum names never reach the aspirant.
  expect(screen.queryByText(/argument_for|argument_against/)).not.toBeInTheDocument();
});

test("existing spine blocks populate their matching slots on mount", async () => {
  serve([
    block({ id: "h", block_type: "hook", block_text: "Fuel queues made this a kitchen-table issue." }),
    block({ id: "t", block_type: "thesis", block_text: "Cash beats kind, where banking reaches." }),
    block({ id: "a", block_type: "argument_for", block_text: "Transfers cut the leaking middlemen." }),
    block({ id: "c", block_type: "closing_thought", block_text: "Cash plus last-mile banking." }),
  ]);
  renderScreen();

  await screen.findByTestId("essay-spine-slots");
  expect(
    within(screen.getByTestId("spine-slot-hook")).getByText(/kitchen-table issue/),
  ).toBeInTheDocument();
  expect(
    within(screen.getByTestId("spine-slot-thesis")).getByText(/Cash beats kind/),
  ).toBeInTheDocument();
  expect(
    within(screen.getByTestId("spine-slot-argument_for")).getByText(/leaking middlemen/),
  ).toBeInTheDocument();
  expect(
    within(screen.getByTestId("spine-slot-closing_thought")).getByText(/last-mile banking/),
  ).toBeInTheDocument();
  // Untouched slots still read as not-started, not as broken gaps.
  expect(screen.getByTestId("spine-slot-counter_narrative-empty")).toBeInTheDocument();
});

test("canvas blocks (lens set) never leak into the spine slots", async () => {
  serve([
    block({ id: "canvas", block_type: "quote", block_text: "On the canvas", lens: "economic_efficiency" }),
    block({ id: "h", block_type: "hook", block_text: "On the spine" }),
  ]);
  renderScreen();

  await screen.findByTestId("essay-spine-slots");
  expect(screen.getByText("On the spine")).toBeInTheDocument();
  expect(screen.queryByText("On the canvas")).not.toBeInTheDocument();
});

test("promoted brainstorm material is shown but has no create affordance", async () => {
  serve([block({ id: "q", block_type: "quote", block_text: "Poverty is the worst form of violence." })]);
  renderScreen();

  const promoted = await screen.findByTestId("essay-spine-promoted");
  expect(within(promoted).getByText(/worst form of violence/)).toBeInTheDocument();
  expect(screen.queryByTestId("spine-slot-quote")).not.toBeInTheDocument();
});

test.each(SPINE_SLOTS.map((s) => [s.blockType, s.label]))(
  "the %s slot creates a block with that type and never sends lens or canvas position",
  async (blockType) => {
    serve([]);
    renderScreen();
    await screen.findByTestId("essay-spine-slots");

    fireEvent.click(screen.getByTestId(`spine-slot-${blockType}-start`));
    fireEvent.change(screen.getByTestId(`spine-slot-${blockType}-input`), {
      target: { value: "  Written by the aspirant.  " },
    });
    fireEvent.click(screen.getByTestId(`spine-slot-${blockType}-save`));

    await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
    const [url, body] = api.post.mock.calls[0];
    expect(url).toBe("/api/essay-brainstorm-blocks");
    expect(body).toEqual({
      theme_id: THEME,
      block_type: blockType,
      block_text: "Written by the aspirant.",
    });
    // lens / canvas_x / canvas_y are Idea Canvas state. A Spine write must not
    // mention them at all — sending null would still be sending them.
    expect(Object.keys(body)).toEqual(["theme_id", "block_type", "block_text"]);
  },
);

test("saving re-reads from the server so the slot is never left stale", async () => {
  serve([]);
  renderScreen();
  await screen.findByTestId("essay-spine-slots");
  const readsBefore = api.get.mock.calls.length;

  fireEvent.click(screen.getByTestId("spine-slot-hook-start"));
  fireEvent.change(screen.getByTestId("spine-slot-hook-input"), { target: { value: "New hook" } });

  serve([block({ id: "h", block_text: "New hook" })]);
  fireEvent.click(screen.getByTestId("spine-slot-hook-save"));

  await waitFor(() => expect(api.get.mock.calls.length).toBeGreaterThan(readsBefore));
  expect(await screen.findByText("New hook")).toBeInTheDocument();
});

test("editing a block patches only its text and reflects the confirmed value", async () => {
  serve([block({ id: "h", block_text: "Original hook" })]);
  renderScreen();
  await screen.findByText("Original hook");

  fireEvent.click(screen.getByTestId("spine-slot-hook-edit"));
  fireEvent.change(screen.getByLabelText("Edit Hook"), { target: { value: "Sharper hook" } });

  serve([block({ id: "h", block_text: "Sharper hook" })]);
  fireEvent.click(screen.getByTestId("spine-slot-hook-save-edit"));

  await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
  expect(api.patch).toHaveBeenCalledWith("/api/essay-brainstorm-blocks/h", {
    block_text: "Sharper hook",
  });
  // The editor closes only once the write is confirmed; assert on the rendered
  // block afterwards so the textarea's own text can't satisfy the query.
  await waitFor(() => expect(screen.queryByLabelText("Edit Hook")).not.toBeInTheDocument());
  const slot = screen.getByTestId("spine-slot-hook");
  expect(within(slot).getByText("Sharper hook")).toBeInTheDocument();
  expect(within(slot).queryByText("Original hook")).not.toBeInTheDocument();
});

test("deleting a block removes it from the slot after the server confirms", async () => {
  const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
  serve([block({ id: "h", block_text: "Doomed hook" })]);
  renderScreen();
  await screen.findByText("Doomed hook");

  serve([]);
  fireEvent.click(screen.getByTestId("spine-slot-hook-delete"));

  await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/api/essay-brainstorm-blocks/h"));
  await waitFor(() => expect(screen.queryByText("Doomed hook")).not.toBeInTheDocument());
  expect(screen.getByTestId("spine-slot-hook-empty")).toBeInTheDocument();
  confirmSpy.mockRestore();
});

test("a failed save keeps the aspirant's text instead of discarding it", async () => {
  serve([]);
  api.post.mockRejectedValue(new Error("network"));
  renderScreen();
  await screen.findByTestId("essay-spine-slots");

  fireEvent.click(screen.getByTestId("spine-slot-thesis-start"));
  fireEvent.change(screen.getByTestId("spine-slot-thesis-input"), {
    target: { value: "Hard-won thesis" },
  });
  fireEvent.click(screen.getByTestId("spine-slot-thesis-save"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  expect(screen.getByTestId("spine-slot-thesis-input")).toHaveValue("Hard-won thesis");
});

test("a failed read shows the error state with a retry, not an empty spine", async () => {
  api.get.mockRejectedValue(new Error("boom"));
  renderScreen();

  const errorBox = await screen.findByTestId("essay-spine-error");
  expect(within(errorBox).getByText("Could not load this essay")).toBeInTheDocument();
  expect(screen.queryByTestId("essay-spine-slots")).not.toBeInTheDocument();

  serve([]);
  fireEvent.click(within(errorBox).getByRole("button", { name: "Retry" }));
  await screen.findByTestId("essay-spine-slots");
});

test("with no theme it offers the aspirant's in-progress themes", async () => {
  serve([block({ theme_id: THEME }), block({ id: "b2", theme_id: "22222222-2222-4222-8222-222222222222" })]);
  render(
    <ToastProvider>
      <EssaySpineScreen />
    </ToastProvider>,
  );

  const picker = await screen.findByTestId("essay-spine-theme-picker");
  expect(within(picker).getByText(THEME)).toBeInTheDocument();

  fireEvent.click(within(picker).getByText(THEME));
  await screen.findByTestId("essay-spine-slots");
});

test("with no theme and nothing brainstormed it explains where to start", async () => {
  serve([]);
  render(
    <ToastProvider>
      <EssaySpineScreen />
    </ToastProvider>,
  );

  expect(await screen.findByText("No essay theme yet")).toBeInTheDocument();
  expect(screen.queryByTestId("essay-spine-slots")).not.toBeInTheDocument();
});
