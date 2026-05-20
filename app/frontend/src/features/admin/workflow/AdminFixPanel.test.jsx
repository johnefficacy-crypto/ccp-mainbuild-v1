import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";

// Spy holder so each test can read what useToast was asked to show.
const mockToastSpies = { info: jest.fn(), error: jest.fn(), success: jest.fn() };
jest.mock("../../../shared/ui", () => ({ useToast: () => mockToastSpies }));

// PromotionPreviewPanel: record every mount + the refreshKey it renders with,
// so tests can assert lazy-mount (Task 4) and bump-after-write (Task 3).
const mockPreviewMounts = [];
jest.mock("./PromotionPreviewPanel", () => (props) => {
  const React2 = require("react");
  React2.useEffect(() => {
    mockPreviewMounts.push(props.refreshKey);
    return undefined;
  }, []);
  return React2.createElement("div", {
    "data-testid": "ppp",
    "data-refresh-key": String(props.refreshKey),
  });
});

// FieldReviewGroup: a button that invokes the field action and stashes the
// returned promise so the test can await/inspect it.
const mockFieldAction = { lastPromise: null };
jest.mock("./FieldReviewGroup", () => (props) =>
  require("react").createElement(
    "button",
    {
      "data-testid": "fire-field",
      onClick: () => {
        mockFieldAction.lastPromise = props.onFieldAction("requires_domicile", "verify", null, null);
      },
    },
    "fire"
  )
);
jest.mock("./PostEligibilityReviewGroup", () => () => null);
jest.mock("./BlockerList", () => () => null);
jest.mock("./ConflictResolver", () => () => null);
jest.mock("./OfficialSourceQuickResolver", () => () => null);
jest.mock("../recruitments/RecruitmentCriteriaPanel", () => () => null);
jest.mock("../recruitments/RecruitmentBlockerFixForm", () => () => null);

import AdminFixPanel from "./AdminFixPanel";

const QUEUE_ITEM = { id: "q1", unverified_fields: ["requires_domicile"], promotable: false };

function renderPanel(onQueueFieldAction) {
  return render(<AdminFixPanel queueItem={QUEUE_ITEM} onQueueFieldAction={onQueueFieldAction} />);
}

function openPreview() {
  const details = screen.getByTestId("fx-promotion-preview");
  details.open = true;
  fireEvent(details, new Event("toggle", { bubbles: true }));
}

function closePreview() {
  const details = screen.getByTestId("fx-promotion-preview");
  details.open = false;
  fireEvent(details, new Event("toggle", { bubbles: true }));
}

beforeEach(() => {
  mockToastSpies.info.mockReset();
  mockToastSpies.error.mockReset();
  mockToastSpies.success.mockReset();
  mockPreviewMounts.length = 0;
  mockFieldAction.lastPromise = null;
});

// ── Task 4 — preview is mounted only when the disclosure is open ──────────

test("does not mount PromotionPreviewPanel while the disclosure is collapsed", () => {
  renderPanel(jest.fn());
  expect(screen.queryByTestId("ppp")).toBeNull();
});

test("mounts the preview when the disclosure is toggled open, unmounts on close", () => {
  renderPanel(jest.fn());
  act(() => openPreview());
  expect(screen.queryByTestId("ppp")).not.toBeNull();
  expect(mockPreviewMounts.length).toBe(1);

  act(() => closePreview());
  expect(screen.queryByTestId("ppp")).toBeNull();

  act(() => openPreview());
  expect(screen.queryByTestId("ppp")).not.toBeNull();
  expect(mockPreviewMounts.length).toBe(2); // a fresh fetch each open
});

// ── Task 3 — bumpPreview only fires after the write resolves ──────────────

test("bumps the preview only AFTER the write resolves", async () => {
  let resolveWrite;
  const onQueueFieldAction = jest.fn(() => new Promise((res) => { resolveWrite = res; }));
  renderPanel(onQueueFieldAction);
  act(() => openPreview());
  expect(screen.getByTestId("ppp").getAttribute("data-refresh-key")).toBe("0");

  act(() => {
    fireEvent.click(screen.getAllByTestId("fire-field")[0]);
  });
  // Write still pending → no bump yet.
  await act(async () => { await Promise.resolve(); });
  expect(screen.getByTestId("ppp").getAttribute("data-refresh-key")).toBe("0");

  await act(async () => {
    resolveWrite({ ok: true });
    await mockFieldAction.lastPromise;
  });
  expect(screen.getByTestId("ppp").getAttribute("data-refresh-key")).toBe("1");
});

test("does NOT bump the preview when the write fails, and the error propagates", async () => {
  const err = { status: 400, message: "bad request" };
  const onQueueFieldAction = jest.fn(() => Promise.reject(err));
  renderPanel(onQueueFieldAction);
  act(() => openPreview());
  expect(screen.getByTestId("ppp").getAttribute("data-refresh-key")).toBe("0");

  act(() => {
    fireEvent.click(screen.getAllByTestId("fire-field")[0]);
  });
  await expect(mockFieldAction.lastPromise).rejects.toBe(err);
  expect(screen.getByTestId("ppp").getAttribute("data-refresh-key")).toBe("0");
});

// ── Task 5 (frontend) — auto-retry once on a 503, then bump ───────────────

test("on a 503 it retries once after 2s, toasts, and bumps on the retry success", async () => {
  jest.useFakeTimers();
  try {
    const onQueueFieldAction = jest
      .fn()
      .mockRejectedValueOnce({ status: 503 })
      .mockResolvedValueOnce({ ok: true });
    renderPanel(onQueueFieldAction);
    act(() => openPreview());

    act(() => {
      fireEvent.click(screen.getAllByTestId("fire-field")[0]);
    });
    // First attempt rejected with 503 → "retrying" toast, no bump yet.
    await act(async () => { await Promise.resolve(); });
    expect(mockToastSpies.info).toHaveBeenCalledWith("Temporary database hiccup — retrying");
    expect(screen.getByTestId("ppp").getAttribute("data-refresh-key")).toBe("0");

    await act(async () => {
      jest.advanceTimersByTime(2000);
      await mockFieldAction.lastPromise;
    });
    expect(onQueueFieldAction).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId("ppp").getAttribute("data-refresh-key")).toBe("1");
  } finally {
    jest.useRealTimers();
  }
});

test("on a persistent 503 it surfaces the retry-failed toast and does not bump", async () => {
  jest.useFakeTimers();
  try {
    const onQueueFieldAction = jest
      .fn()
      .mockRejectedValueOnce({ status: 503 })
      .mockRejectedValueOnce({ status: 503 });
    renderPanel(onQueueFieldAction);
    act(() => openPreview());

    act(() => {
      fireEvent.click(screen.getAllByTestId("fire-field")[0]);
    });
    await act(async () => { await Promise.resolve(); });

    const settled = mockFieldAction.lastPromise.catch((e) => e);
    await act(async () => {
      jest.advanceTimersByTime(2000);
      await settled;
    });
    expect(mockToastSpies.error).toHaveBeenCalledWith("Please try again in a moment");
    expect(screen.getByTestId("ppp").getAttribute("data-refresh-key")).toBe("0");
  } finally {
    jest.useRealTimers();
  }
});
