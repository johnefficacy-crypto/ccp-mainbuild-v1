import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useTopicEdit } from "../useTopicEdit";
import TopicEditDrawer from "../TopicEditDrawer";
import TopicTreePanel from "../../TopicTreePanel";

// ---------------------------------------------------------------------------
// Mock api module
// ---------------------------------------------------------------------------
jest.mock("../../../../../../lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  },
}));

const { api } = require("../../../../../../lib/api");

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------
const TOPIC = {
  id: "topic-1",
  subject_id: "subj-1",
  parent_topic_id: null,
  slug: "polity-federalism",
  name: "Federalism",
  level: "topic",
  default_difficulty_level: "medium",
  description: "Constitutional federalism in India",
  is_active: true,
  metadata: {},
};

const SIBLINGS = [
  { id: "topic-2", subject_id: "subj-1", name: "Fundamental Rights", slug: "fundamental-rights", level: "topic" },
];

const ALIASES = [
  { id: "alias-1", topic_id: "topic-1", alias: "Federalism in India", normalized_alias: "federalism in india", source_context: null },
];

function makeTopicsRes(extra = []) {
  return { items: [TOPIC, ...SIBLINGS, ...extra], total: 2 + extra.length, limit: 200, offset: 0 };
}

function makeAliasesRes(items = ALIASES) {
  return { items, total: items.length, limit: 50, offset: 0 };
}

// ---------------------------------------------------------------------------
// Wrapper: renders hook + drawer so we can trigger openForTopic
// ---------------------------------------------------------------------------
function DrawerHarness({ onSaved } = {}) {
  const hook = useTopicEdit();
  return (
    <>
      <button data-testid="open-btn" onClick={() => hook.openForTopic("topic-1")}>
        Open
      </button>
      <TopicEditDrawer hook={hook} onSaved={onSaved} />
    </>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
});

// ---------------------------------------------------------------------------
// 1. Drawer opens and fetches topic + aliases
// ---------------------------------------------------------------------------
test("drawer opens when Edit button clicked, fetches topic + aliases", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));

  await waitFor(() => expect(screen.getByTestId("topic-edit-drawer")).toBeTruthy());

  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/topics?limit=200"));
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/topic-aliases?topic_id=topic-1"));
});

// ---------------------------------------------------------------------------
// 2. Form fields populate from fetched topic
// ---------------------------------------------------------------------------
test("form fields populate from fetched topic", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));

  await waitFor(() => expect(screen.getByDisplayValue("Federalism")).toBeTruthy());
  expect(screen.getByDisplayValue("polity-federalism")).toBeTruthy();
});

// ---------------------------------------------------------------------------
// 3. Changing a field marks it dirty — Save still disabled without reason
// ---------------------------------------------------------------------------
test("changing a field marks it dirty; Save still disabled without reason", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByDisplayValue("Federalism")).toBeTruthy());

  fireEvent.change(screen.getByDisplayValue("Federalism"), { target: { value: "Federalism v2" } });

  // Dirty but no reason → Save disabled
  expect(screen.getByTestId("topic-edit-save").disabled).toBe(true);
});

// ---------------------------------------------------------------------------
// 4. Save button disabled until reason entered AND at least one field dirty
// ---------------------------------------------------------------------------
test("Save button disabled until reason entered AND at least one field dirty", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByTestId("topic-edit-save")).toBeTruthy());

  // Initially disabled (no dirty fields, no reason)
  expect(screen.getByTestId("topic-edit-save").disabled).toBe(true);

  // Enter reason only — still disabled (no dirty field)
  const reasonBox = screen.getByPlaceholderText(/why are you making/i);
  fireEvent.change(reasonBox, { target: { value: "Updating topic name" } });
  expect(screen.getByTestId("topic-edit-save").disabled).toBe(true);

  // Dirty a field — now enabled
  fireEvent.change(screen.getByDisplayValue("Federalism"), { target: { value: "X" } });
  expect(screen.getByTestId("topic-edit-save").disabled).toBe(false);
});

// ---------------------------------------------------------------------------
// 5. Save sends only dirty fields (not the whole row)
// ---------------------------------------------------------------------------
test("Save sends only dirty fields in payload", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());
  api.patch.mockResolvedValueOnce({ ok: true, audit_id: "a1", row: { ...TOPIC, name: "Federalism Updated" } });

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByDisplayValue("Federalism")).toBeTruthy());

  fireEvent.change(screen.getByDisplayValue("Federalism"), { target: { value: "Federalism Updated" } });
  fireEvent.change(screen.getByPlaceholderText(/why are you making/i), { target: { value: "Updating name field" } });
  fireEvent.click(screen.getByTestId("topic-edit-save"));

  await waitFor(() => {
    expect(api.patch).toHaveBeenCalledWith(
      expect.stringContaining("/topics/topic-1"),
      expect.objectContaining({
        reason: "Updating name field",
        payload: { name: "Federalism Updated" },
      }),
    );
  });

  // Payload must contain only the dirty field (name), not the whole row
  const callPayload = api.patch.mock.calls[0][1].payload;
  expect(Object.keys(callPayload)).toEqual(["name"]);
});

// ---------------------------------------------------------------------------
// 6. Save success closes drawer
// ---------------------------------------------------------------------------
test("Save success closes drawer", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());
  api.patch.mockResolvedValueOnce({ ok: true, audit_id: "a1", row: { ...TOPIC, name: "Updated" } });

  const onSaved = jest.fn();
  render(<DrawerHarness onSaved={onSaved} />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByDisplayValue("Federalism")).toBeTruthy());

  fireEvent.change(screen.getByDisplayValue("Federalism"), { target: { value: "Updated" } });
  fireEvent.change(screen.getByPlaceholderText(/why are you making/i), { target: { value: "Rename topic" } });
  fireEvent.click(screen.getByTestId("topic-edit-save"));

  await waitFor(() => expect(screen.queryByTestId("topic-edit-drawer")).toBeFalsy());
  expect(onSaved).toHaveBeenCalledTimes(1);
});

// ---------------------------------------------------------------------------
// 7. Cancel with dirty fields shows confirmation
// ---------------------------------------------------------------------------
test("Cancel with dirty fields shows confirmation dialog", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());

  window.confirm = jest.fn().mockReturnValue(false); // user declines discard

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByDisplayValue("Federalism")).toBeTruthy());

  fireEvent.change(screen.getByDisplayValue("Federalism"), { target: { value: "X" } });
  fireEvent.click(screen.getByText("Cancel"));

  expect(window.confirm).toHaveBeenCalled();
  // Drawer still open (user chose not to discard)
  expect(screen.getByTestId("topic-edit-drawer")).toBeTruthy();
});

// ---------------------------------------------------------------------------
// 8. Escape with dirty fields shows confirmation
// ---------------------------------------------------------------------------
test("Escape with dirty fields shows confirmation", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());

  window.confirm = jest.fn().mockReturnValue(false);

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByDisplayValue("Federalism")).toBeTruthy());

  fireEvent.change(screen.getByDisplayValue("Federalism"), { target: { value: "X" } });
  fireEvent.keyDown(document, { key: "Escape", bubbles: true });

  expect(window.confirm).toHaveBeenCalled();
  expect(screen.getByTestId("topic-edit-drawer")).toBeTruthy();
});

// ---------------------------------------------------------------------------
// 9. Alias add appends to list on success
// ---------------------------------------------------------------------------
test("Alias add appends to list on success", async () => {
  const newAlias = {
    id: "alias-2",
    topic_id: "topic-1",
    alias: "Centre-State Relations",
    normalized_alias: "centre state relations",
    source_context: null,
  };

  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());
  api.post.mockResolvedValueOnce({ ok: true, audit_id: "a2", row: newAlias });

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByDisplayValue("Federalism")).toBeTruthy());

  fireEvent.change(screen.getByPlaceholderText(/why are you making/i), { target: { value: "Adding alias" } });
  fireEvent.change(screen.getByPlaceholderText("New alias"), { target: { value: "Centre-State Relations" } });
  fireEvent.submit(screen.getByPlaceholderText("New alias").closest("form"));

  await waitFor(() => expect(screen.getByText("Centre-State Relations")).toBeTruthy());
});

// ---------------------------------------------------------------------------
// 10. Alias add error surfaces inline error, does not close drawer
// ---------------------------------------------------------------------------
test("Alias add error surfaces inline error, does not close drawer", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());
  api.post.mockRejectedValueOnce(new Error("Duplicate alias"));

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByDisplayValue("Federalism")).toBeTruthy());

  fireEvent.change(screen.getByPlaceholderText(/why are you making/i), { target: { value: "Adding alias" } });
  fireEvent.change(screen.getByPlaceholderText("New alias"), { target: { value: "Duplicate" } });
  fireEvent.submit(screen.getByPlaceholderText("New alias").closest("form"));

  await waitFor(() => {
    const alert = screen.getByRole("alert");
    expect(alert).toBeTruthy();
    expect(alert.textContent).toContain("Duplicate alias");
  });
  expect(screen.getByTestId("topic-edit-drawer")).toBeTruthy();
});

// ---------------------------------------------------------------------------
// 11. Alias delete removes from list on success
// ---------------------------------------------------------------------------
test("Alias delete removes from list on success", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());
  api.delete.mockResolvedValueOnce({ ok: true, audit_id: "a3", id: "alias-1" });

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByText("Federalism in India")).toBeTruthy());

  fireEvent.change(screen.getByPlaceholderText(/why are you making/i), { target: { value: "Remove old alias" } });
  fireEvent.click(screen.getByRole("button", { name: /delete alias federalism in india/i }));

  await waitFor(() => expect(screen.queryByText("Federalism in India")).toBeFalsy());
});

// ---------------------------------------------------------------------------
// 12. Alias write happens immediately, not gated on topic Save
// ---------------------------------------------------------------------------
test("Alias write happens immediately, not gated on topic Save", async () => {
  const newAlias = {
    id: "alias-2",
    topic_id: "topic-1",
    alias: "Federal Structure",
    normalized_alias: "federal structure",
    source_context: null,
  };

  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());
  api.post.mockResolvedValueOnce({ ok: true, audit_id: "a4", row: newAlias });

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByDisplayValue("Federalism")).toBeTruthy());

  fireEvent.change(screen.getByPlaceholderText(/why are you making/i), { target: { value: "Add alias now" } });
  fireEvent.change(screen.getByPlaceholderText("New alias"), { target: { value: "Federal Structure" } });
  fireEvent.submit(screen.getByPlaceholderText("New alias").closest("form"));

  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  // Topic Save (PATCH) should NOT have been called
  expect(api.patch).not.toHaveBeenCalled();
});

// ---------------------------------------------------------------------------
// 13. Save error keeps drawer open with error message
// ---------------------------------------------------------------------------
test("Save error keeps drawer open with error message", async () => {
  api.get
    .mockResolvedValueOnce(makeTopicsRes())
    .mockResolvedValueOnce(makeAliasesRes());
  api.patch.mockRejectedValueOnce(new Error("Slug conflict"));

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));
  await waitFor(() => expect(screen.getByDisplayValue("Federalism")).toBeTruthy());

  fireEvent.change(screen.getByDisplayValue("Federalism"), { target: { value: "Conflict" } });
  fireEvent.change(screen.getByPlaceholderText(/why are you making/i), { target: { value: "Trigger conflict" } });
  fireEvent.click(screen.getByTestId("topic-edit-save"));

  await waitFor(() => {
    const alert = screen.getByRole("alert");
    expect(alert).toBeTruthy();
    expect(alert.textContent).toContain("Slug conflict");
  });
  expect(screen.getByTestId("topic-edit-drawer")).toBeTruthy();
});

// ---------------------------------------------------------------------------
// 14. Permission 403 from backend surfaces gracefully
// ---------------------------------------------------------------------------
test("403 from backend surfaces as an error message, not a crash", async () => {
  const err = new Error("Forbidden");
  err.status = 403;
  api.get.mockRejectedValue(err);

  render(<DrawerHarness />);
  fireEvent.click(screen.getByTestId("open-btn"));

  await waitFor(() => {
    const alert = screen.queryByRole("alert");
    expect(alert).toBeTruthy();
  });
  expect(screen.getByTestId("topic-edit-drawer")).toBeTruthy();
});

// ---------------------------------------------------------------------------
// 15. Edit button has correct aria-label
// ---------------------------------------------------------------------------
test("Edit button has aria-label with topic name", () => {
  const proposals = [
    { topic_id: "topic-1", matched_alias: "Federalism", client_proposal_key: "k1", source_page: 1, confidence_score: 0.9 },
  ];

  render(
    <TopicTreePanel
      proposals={proposals}
      selectedKeys={new Set()}
      onToggle={() => {}}
      onEditTopic={jest.fn()}
      currentPage={1}
    />,
  );

  expect(screen.getByRole("button", { name: /edit topic federalism/i })).toBeTruthy();
});

// ---------------------------------------------------------------------------
// 16. TopicTreePanel: existing proposal counts unchanged (regression)
// ---------------------------------------------------------------------------
test("TopicTreePanel renders proposal counts correctly (regression)", () => {
  const proposals = [
    { topic_id: "t1", matched_alias: "Economy", client_proposal_key: "k1", source_page: 1, confidence_score: 0.8 },
    { topic_id: "t1", matched_alias: "Economy", client_proposal_key: "k2", source_page: 1, confidence_score: 0.7 },
    { topic_id: "t2", matched_alias: "Polity", client_proposal_key: "k3", source_page: 1, confidence_score: 0.9 },
  ];

  render(
    <TopicTreePanel
      proposals={proposals}
      selectedKeys={new Set()}
      onToggle={() => {}}
      currentPage={1}
    />,
  );

  const tree = screen.getByTestId("topic-tree-panel");
  expect(tree.textContent).toContain("Economy");
  expect(tree.textContent).toContain("Polity");
});
