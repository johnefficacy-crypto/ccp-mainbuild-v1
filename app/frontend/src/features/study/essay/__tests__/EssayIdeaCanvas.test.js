import React from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPatch = jest.fn();
const mockDelete = jest.fn();
jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...a) => mockGet(...a),
    post: (...a) => mockPost(...a),
    patch: (...a) => mockPatch(...a),
    delete: (...a) => mockDelete(...a),
  },
}));

import EssayIdeaCanvas from "../../../../pages/study/EssayIdeaCanvas";

const THEME = "11111111-1111-1111-1111-111111111111";

// api.get is routed by URL: blocks list vs pyq-tags vs themes.
function routeGet({ blocks = [], tags = [], themes = null } = {}) {
  mockGet.mockImplementation((url) => {
    if (url.includes("/essay-brainstorm-blocks")) return Promise.resolve({ items: blocks, count: blocks.length });
    if (url.includes("/essay-pyq-tags")) return Promise.resolve({ items: tags, count: tags.length });
    if (url.includes("/essay-themes")) {
      return themes ? Promise.resolve({ items: themes }) : Promise.reject(new Error("404"));
    }
    return Promise.resolve({ items: [] });
  });
}

function renderCanvas(theme = THEME) {
  return render(
    <MemoryRouter initialEntries={[`/app/study/essay?theme=${theme}`]}>
      <EssayIdeaCanvas />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockGet.mockReset();
  mockPost.mockReset();
  mockPatch.mockReset();
  mockDelete.mockReset();
  mockPost.mockResolvedValue({
    id: "new-block", theme_id: THEME, block_type: "vocab_term",
    block_text: "Vocab term", lens: "economic_efficiency", canvas_x: null, canvas_y: null,
  });
  mockPatch.mockResolvedValue({ id: "b1", canvas_x: 260, canvas_y: 180 });
  mockDelete.mockResolvedValue({ ok: true, id: "b1" });
});

// ─── Resource-type affordances send the right block_type + lens ─────────────

test("a helper resource-type add POSTs the correct block_type and active lens", async () => {
  routeGet();
  renderCanvas();
  await screen.findByTestId("helper-rail");

  fireEvent.click(screen.getByTestId("helper-add-quote"));
  await waitFor(() => expect(mockPost).toHaveBeenCalled());
  const [url, body] = mockPost.mock.calls[0];
  expect(url).toBe("/api/essay-brainstorm-blocks");
  expect(body).toMatchObject({
    theme_id: THEME,
    block_type: "quote",
    lens: "economic_efficiency", // default active branch
  });
});

test("switching the active branch routes the next helper add to that lens", async () => {
  routeGet();
  renderCanvas();
  await screen.findByTestId("helper-rail");

  fireEvent.click(screen.getByTestId("branch-select-social_equity_access"));
  fireEvent.click(screen.getByTestId("helper-add-stat_to_verify"));

  await waitFor(() => expect(mockPost).toHaveBeenCalled());
  expect(mockPost.mock.calls[0][1]).toMatchObject({
    block_type: "stat_to_verify",
    lens: "social_equity_access",
  });
});

test("a per-branch '+ add idea' POSTs a free-text block in that lens", async () => {
  routeGet();
  const promptSpy = jest.spyOn(window, "prompt").mockReturnValue("DBT beats PDS on leakage");
  renderCanvas();
  await screen.findByTestId("idea-canvas");

  fireEvent.click(screen.getByTestId("branch-add-governance_implementation"));
  await waitFor(() => expect(mockPost).toHaveBeenCalled());
  expect(mockPost.mock.calls[0][1]).toMatchObject({
    block_type: "argument_for",
    block_text: "DBT beats PDS on leakage",
    lens: "governance_implementation",
  });
  promptSpy.mockRestore();
});

// ─── Drag: one PATCH on drag-end, with both coordinates ─────────────────────

test("dragging a sticky fires exactly ONE PATCH on drag-end carrying both coords", async () => {
  routeGet({
    blocks: [{
      id: "b1", theme_id: THEME, block_type: "quote", block_text: "Gandhi on trusteeship",
      lens: "economic_efficiency", canvas_x: 200, canvas_y: 150,
    }],
  });
  renderCanvas();
  const sticky = await screen.findByTestId("sticky-b1");

  fireEvent.mouseDown(sticky, { clientX: 100, clientY: 100 });
  fireEvent.mouseMove(window, { clientX: 130, clientY: 125 }); // mid-drag: no request
  fireEvent.mouseMove(window, { clientX: 160, clientY: 130 });
  expect(mockPatch).not.toHaveBeenCalled();

  fireEvent.mouseUp(window);
  await waitFor(() => expect(mockPatch).toHaveBeenCalledTimes(1));
  const [url, body] = mockPatch.mock.calls[0];
  expect(url).toBe("/api/essay-brainstorm-blocks/b1");
  // origin (200,150) + delta (60,30) = (260,180); both axes present.
  expect(body).toEqual({ canvas_x: 260, canvas_y: 180 });
});

// ─── Load renders persisted + null positions ────────────────────────────────

test("blocks load at persisted positions; a null-position block still renders near its lens", async () => {
  routeGet({
    blocks: [{
      id: "b-null", theme_id: THEME, block_type: "example", block_text: "no position yet",
      lens: "historical_precedent", canvas_x: null, canvas_y: null,
    }],
  });
  renderCanvas();
  const sticky = await screen.findByTestId("sticky-b-null");
  // historical_precedent anchor is (200,300); first block → 0 jitter.
  expect(sticky.style.left).toBe("200px");
  expect(sticky.style.top).toBe("300px");
});

// ─── PYQ tags empty state ───────────────────────────────────────────────────

test("empty essay-pyq-tags renders a clear, non-broken empty state", async () => {
  routeGet({ tags: [] });
  renderCanvas();
  expect(await screen.findByTestId("essay-pyq-tags-empty")).toHaveTextContent(
    /No verified past-paper questions/i,
  );
});

test("essay-pyq-tags renders real tagged questions when present", async () => {
  routeGet({ tags: [{ id: "t1", question_text: "Forests are the best case for conservation", year: 2019 }] });
  renderCanvas();
  expect(await screen.findByTestId("essay-pyq-tag-t1")).toHaveTextContent(/Forests are the best case/);
});

// ─── Theme selector: active vs reserved ─────────────────────────────────────

function renderSelector() {
  return render(
    <MemoryRouter initialEntries={["/app/study/essay"]}>
      <EssayIdeaCanvas />
    </MemoryRouter>,
  );
}

test("theme selector makes active themes selectable and reserved themes disabled", async () => {
  routeGet({
    themes: [
      { id: "th-active", theme_code: "T1", theme_name: "Justice", status: "active" },
      { id: "th-reserved", theme_code: "T2", theme_name: "Ethics", status: "reserved" },
    ],
  });
  renderSelector();
  await screen.findByTestId("theme-list");
  expect(screen.getByTestId("theme-option-th-active")).not.toBeDisabled();
  expect(screen.getByTestId("theme-option-th-reserved")).toBeDisabled();
});

test("theme selector falls back to manual entry when no themes endpoint exists", async () => {
  routeGet({ themes: null }); // /essay-themes rejects (404) — the real state today
  renderSelector();
  await screen.findByTestId("theme-unavailable");
  fireEvent.change(screen.getByTestId("theme-manual-input"), { target: { value: THEME } });
  fireEvent.click(screen.getByTestId("theme-manual-open"));
  // Canvas opens for the entered theme.
  await screen.findByTestId("idea-canvas");
});
