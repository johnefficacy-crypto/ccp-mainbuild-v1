import React from "react";
import { render, screen, fireEvent, act, within } from "@testing-library/react";

import FieldReviewGroup from "../FieldReviewGroup";

// This repo's CRA setup has no @testing-library/jest-dom, so assertions use
// plain Jest matchers (textContent / queryBy*-toBeNull) only.

// Build an "other"-scoped evidence detail row the way the backend surfaces it
// on GET /admin/scrape/queue (includes reviewer_notes).
function detail(field, status, extra = {}) {
  return {
    field_name: field,
    entity_type: "other",
    entity_key: null,
    reviewer_status: status,
    ...extra,
  };
}

function renderGroup(props) {
  const onFieldAction = jest.fn(() => Promise.resolve());
  const utils = render(
    <FieldReviewGroup
      extracted={props.extracted}
      evidence={props.evidence || {}}
      evidenceDetails={props.evidenceDetails || []}
      requiredFields={props.requiredFields || []}
      recommendedFields={props.recommendedFields || []}
      onFieldAction={onFieldAction}
    />,
  );
  return { onFieldAction, ...utils };
}

describe("FieldReviewGroup — flagged ('rejected') is non-terminal", () => {
  const extracted = {
    apply_end_date: "2026-01-01",
    apply_start_date: "2025-12-01",
    total_vacancies: 10,
  };

  test("rejected counts as unresolved in the header summary, not as reviewed", () => {
    renderGroup({
      extracted,
      requiredFields: ["apply_end_date", "apply_start_date", "total_vacancies"],
      evidenceDetails: [
        detail("apply_end_date", "rejected", { reviewer_notes: "Date is wrong" }),
        detail("apply_start_date", "verified"),
      ],
      // total_vacancies has no review row -> pending.
    });

    const summary = screen.getByTestId("field-review-summary");
    // 1 verified = reviewed; flagged + pending are NOT counted as reviewed.
    expect(summary.textContent).toContain("1/3 reviewed");
    expect(screen.getByTestId("field-review-flagged-count").textContent).toContain("1 flagged");
    expect(summary.textContent).toContain("1 pending");
    expect(summary.textContent).not.toContain("all verified");
  });

  test("flagged field renders the action-owed label, not a muted 'flagged'", () => {
    renderGroup({
      extracted,
      requiredFields: ["apply_end_date"],
      evidenceDetails: [detail("apply_end_date", "rejected", { reviewer_notes: "wrong" })],
    });

    const row = document.querySelector('[data-field="apply_end_date"]');
    expect(within(row).queryByText("Flagged — correction required")).not.toBeNull();
    expect(within(row).queryByText("flagged")).toBeNull();
  });

  test("flag reason (reviewer_notes) is shown inline on the flagged field", () => {
    renderGroup({
      extracted,
      requiredFields: ["apply_end_date"],
      evidenceDetails: [detail("apply_end_date", "rejected", { reviewer_notes: "Source PDF was superseded" })],
    });

    expect(screen.getByTestId("field-flag-reason-apply_end_date").textContent).toContain(
      "Source PDF was superseded",
    );
  });

  test("'Verify all' excludes flagged fields (never bulk-overrides the admin's flag)", async () => {
    const { onFieldAction } = renderGroup({
      extracted,
      requiredFields: ["apply_end_date", "apply_start_date", "total_vacancies"],
      evidenceDetails: [
        detail("apply_end_date", "rejected", { reviewer_notes: "wrong" }),
        detail("apply_start_date", "verified"),
      ],
    });

    // Only the untouched (pending, non-blank) field is verifiable.
    const verifyAll = screen.getByTestId("field-verify-all");
    expect(verifyAll.textContent).toContain("Verify all (1)");

    await act(async () => {
      fireEvent.click(verifyAll);
    });

    expect(onFieldAction).toHaveBeenCalledTimes(1);
    expect(onFieldAction).toHaveBeenCalledWith("total_vacancies", "verify", null, {
      entity_type: "other",
      entity_key: null,
    });
    // Crucially, the flagged field was never re-verified.
    expect(onFieldAction).not.toHaveBeenCalledWith(
      "apply_end_date",
      "verify",
      expect.anything(),
      expect.anything(),
    );
  });

  test("when only flagged fields remain, header shows promotion is blocked (not 'all verified')", () => {
    renderGroup({
      extracted,
      requiredFields: ["apply_end_date", "apply_start_date"],
      evidenceDetails: [
        detail("apply_end_date", "rejected", { reviewer_notes: "wrong" }),
        detail("apply_start_date", "verified"),
      ],
    });

    expect(screen.queryByTestId("field-review-flagged-block")).not.toBeNull();
    expect(screen.queryByText("all verified")).toBeNull();
    expect(screen.queryByTestId("field-verify-all")).toBeNull();
  });

  test("inline 'Correct value' transitions rejected -> corrected in one flow", () => {
    const { onFieldAction } = renderGroup({
      extracted,
      requiredFields: ["apply_end_date"],
      evidenceDetails: [detail("apply_end_date", "rejected", { reviewer_notes: "wrong" })],
    });

    // One click opens the inline correction editor on the same row.
    fireEvent.click(screen.getByTestId("field-correct-apply_end_date"));

    const input = screen.getByLabelText("Corrected value for Apply end date");
    fireEvent.change(input, { target: { value: "2026-02-02" } });
    fireEvent.click(screen.getByText("Save"));

    expect(onFieldAction).toHaveBeenCalledWith("apply_end_date", "correct", "2026-02-02", {
      entity_type: "other",
      entity_key: null,
    });
  });
});

describe("FieldReviewGroup — corrected is terminal (gate-pass)", () => {
  const extracted = { total_vacancies: 10, min_age: 18 };

  test("corrected field is excluded from 'Verify all' and counts as reviewed", () => {
    renderGroup({
      extracted,
      requiredFields: ["total_vacancies", "min_age"],
      evidenceDetails: [
        detail("total_vacancies", "corrected", { corrected_value: 12 }),
        detail("min_age", "verified"),
      ],
    });

    // Both are terminal gate-pass -> nothing left to verify, all reviewed.
    expect(screen.queryByTestId("field-verify-all")).toBeNull();
    expect(screen.queryByText("all verified")).not.toBeNull();
    expect(screen.getByTestId("field-review-summary").textContent).toContain("2/2 reviewed");
    expect(screen.getByTestId("field-review-flagged-count").textContent).toContain("0 flagged");
  });
});
