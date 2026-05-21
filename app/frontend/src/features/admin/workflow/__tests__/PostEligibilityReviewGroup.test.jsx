import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import PostEligibilityReviewGroup from "../PostEligibilityReviewGroup";

function renderGroup(posts, evidenceDetails = [], onFieldAction = jest.fn()) {
  return render(
    <PostEligibilityReviewGroup
      posts={posts}
      evidenceDetails={evidenceDetails}
      onFieldAction={onFieldAction}
    />,
  );
}

const dom = (entity_key, reviewer_status) => ({
  field_name: "requires_domicile",
  entity_type: "post",
  entity_key,
  reviewer_status,
});

// ── BUG 3: accept "verified" AND "corrected" as resolved ────────────────────

test("verified post → Verify button disabled + done check shown", () => {
  renderGroup([{ post_name: "A" }], [dom("A", "verified")]);
  expect(screen.getByTestId("post-verify-0").disabled).toBe(true);
  expect(screen.getByTestId("post-domicile-done-0")).toBeTruthy();
});

test("corrected post → Verify button disabled + done check shown (gate accepts corrected)", () => {
  renderGroup([{ post_name: "A" }], [dom("A", "corrected")]);
  expect(screen.getByTestId("post-verify-0").disabled).toBe(true);
  expect(screen.getByTestId("post-domicile-done-0")).toBeTruthy();
});

test("rejected post → Verify button enabled + no check", () => {
  renderGroup([{ post_name: "A" }], [dom("A", "rejected")]);
  expect(screen.getByTestId("post-verify-0").disabled).toBe(false);
  expect(screen.queryByTestId("post-domicile-done-0")).toBeNull();
});

test("unverified/pending post → Verify button enabled + no check", () => {
  renderGroup([{ post_name: "A" }], []);
  expect(screen.getByTestId("post-verify-0").disabled).toBe(false);
  expect(screen.queryByTestId("post-domicile-done-0")).toBeNull();
});

// ── BUG 4: unnamed post → positional entity_key + dev warning ───────────────

test("unnamed post warns and emits a positional post-N entity_key on correct", () => {
  const warn = jest.spyOn(console, "warn").mockImplementation(() => {});
  const onFieldAction = jest.fn();
  renderGroup([{ post_name: "" }], [], onFieldAction);
  expect(warn).toHaveBeenCalledWith(expect.stringContaining("post-0"));
  fireEvent.click(screen.getByTestId("post-domicile-0"));
  expect(onFieldAction).toHaveBeenCalledWith(
    "requires_domicile",
    "correct",
    true,
    { entity_type: "post", entity_key: "post-0" },
  );
  warn.mockRestore();
});

test("named post does NOT warn and uses post_name as entity_key", () => {
  const warn = jest.spyOn(console, "warn").mockImplementation(() => {});
  const onFieldAction = jest.fn();
  renderGroup([{ post_name: "Constable" }], [], onFieldAction);
  expect(warn).not.toHaveBeenCalled();
  fireEvent.click(screen.getByTestId("post-domicile-0"));
  expect(onFieldAction).toHaveBeenCalledWith(
    "requires_domicile",
    "correct",
    true,
    { entity_type: "post", entity_key: "Constable" },
  );
  warn.mockRestore();
});
