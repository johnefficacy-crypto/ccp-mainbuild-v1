import React from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ExamListTable from "./ExamListTable";

const UUID = "3f9a1c2e-7b44-4d11-9aaa-0c2b9f8e1234";
const UUID_2 = "4f9a1c2e-7b44-4d11-9aaa-0c2b9f8e5678";

const ITEMS = [
  {
    id: UUID, slug: "ssc-cgl", name: "SSC CGL", exam_type: "recruitment",
    is_active: true, syllabus_verified: 2, syllabus_pending: 1,
    verified_topic_count: 3, coverage_total: 5, high_yield_topic_count: 2,
    readiness_level: "ready", pyq_coverage_status: "covered",
    management_mode: "core", cadence: "annual",
  },
  {
    id: "e2", slug: "ibps-po", name: "IBPS PO", exam_type: "recruitment",
    is_active: false, syllabus_verified: 0, syllabus_pending: 1,
    verified_topic_count: 0, coverage_total: 0, high_yield_topic_count: 0,
    readiness_level: "not_ready", pyq_coverage_status: "none",
    management_mode: null, cadence: null,
  },
];

const SAME_SLUG_OLD = {
  ...ITEMS[0],
  id: "old-id",
  slug: "same-slug",
  name: "Same Slug Old",
};

const SAME_SLUG_NEW = {
  ...ITEMS[0],
  id: "new-id",
  slug: "same-slug",
  name: "Same Slug New",
};

const SLUGLESS_UUID_ITEM = {
  id: UUID,
  slug: null,
  name: null,
  exam_type: "recruitment",
  is_active: true,
  syllabus_verified: 0,
  syllabus_pending: 0,
  verified_topic_count: 0,
  coverage_total: 0,
  high_yield_topic_count: 0,
  readiness_level: "needs_manual_review",
  management_mode: "core",
  cadence: "annual",
};

const FALLBACK_SHARED_NAME_ITEMS = [
  {
    ...ITEMS[0],
    id: "",
    slug: null,
    name: "Shared Name",
    readiness_level: "ready",
  },
  {
    ...ITEMS[1],
    id: null,
    slug: null,
    name: "Shared Name",
    readiness_level: "partial",
  },
];

const ANONYMOUS_ITEMS = [
  { ...SLUGLESS_UUID_ITEM, id: undefined, readiness_level: "ready" },
  { ...SLUGLESS_UUID_ITEM, id: null, readiness_level: "partial" },
];

const SLUGLESS_SAME_NAME_UUID_ITEMS = [
  { ...SLUGLESS_UUID_ITEM, id: UUID, name: "Shared UUID Name", readiness_level: "ready" },
  { ...SLUGLESS_UUID_ITEM, id: UUID_2, name: "Shared UUID Name", readiness_level: "partial" },
];

function readinessFixture(readiness_level) {
  return {
    ...SLUGLESS_UUID_ITEM,
    id: `readiness-${String(readiness_level).replace(/[^a-z0-9]/gi, "-")}`,
    name: "Readiness Guard",
    readiness_level,
  };
}

function wrap(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

function headers() {
  return screen.getAllByRole("columnheader").map((h) => h.textContent);
}

function expand(slug = "ssc-cgl") {
  fireEvent.click(screen.getByTestId(`exam-intel-disclosure-${slug}`));
}

// ── table renders ──────────────────────────────────────────────────────────

test("renders rows for each item with exam name primary and slug secondary", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expect(screen.getByText("SSC CGL")).toBeInTheDocument();
  expect(screen.getByText("ssc-cgl")).toBeInTheDocument();
  expect(screen.getByText("IBPS PO")).toBeInTheDocument();
  expect(document.body.textContent).not.toContain(UUID);
});

test("renders empty state when no items and page is 0", () => {
  wrap(<ExamListTable items={[]} total_count={0} />);
  expect(screen.getByText(/no exams registered yet/i)).toBeInTheDocument();
});

test("collapsed table has exactly six column headers and removes old dense headers", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expect(headers()).toEqual(["Exam", "Purpose", "Syllabus", "Topic coverage", "Readiness", "Actions"]);
  expect(headers()).toHaveLength(6);
  [
    ["Exam", "key"].join(" "),
    "Business priority",
    "Syllabus ✓",
    "Syllabus ⏳",
    ["Planner-ready", "topics"].join(" "),
    ["Locked", "high-yield topics"].join(" "),
    "User-facing readiness",
  ].forEach((oldHeader) => {
    expect(screen.queryByRole("columnheader", { name: oldHeader })).not.toBeInTheDocument();
  });
});

// ── expansion ──────────────────────────────────────────────────────────────

test("detail is absent initially and disclosure starts collapsed", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  const button = screen.getByTestId("exam-intel-disclosure-ssc-cgl");
  expect(button).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByTestId("exam-intel-details-ssc-cgl")).not.toBeInTheDocument();
});

test("click renders controlled detail row, flips aria-expanded, and wires aria-controls", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  const button = screen.getByTestId("exam-intel-disclosure-ssc-cgl");
  expand();
  const detail = screen.getByTestId("exam-intel-details-ssc-cgl");
  expect(button).toHaveAttribute("aria-expanded", "true");
  expect(button.getAttribute("aria-controls")).toBe(detail.getAttribute("id"));
  expect(within(detail).getByRole("cell")).toHaveAttribute("colspan", "6");
  expect(document.body.textContent).not.toContain(UUID);
});

test("second click closes the detail row", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expand();
  expect(screen.getByTestId("exam-intel-details-ssc-cgl")).toBeInTheDocument();
  expand();
  expect(screen.queryByTestId("exam-intel-details-ssc-cgl")).not.toBeInTheDocument();
  expect(screen.getByTestId("exam-intel-disclosure-ssc-cgl")).toHaveAttribute("aria-expanded", "false");
});

test("multiple rows expand independently", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expand("ssc-cgl");
  expand("ibps-po");
  expect(screen.getByTestId("exam-intel-details-ssc-cgl")).toBeInTheDocument();
  expect(screen.getByTestId("exam-intel-details-ibps-po")).toBeInTheDocument();
});

test("replacing items clears stale expanded details for absent exams", () => {
  const { rerender } = wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expand("ssc-cgl");
  expect(screen.getByTestId("exam-intel-details-ssc-cgl")).toBeInTheDocument();
  rerender(
    <MemoryRouter>
      <ExamListTable items={[ITEMS[1]]} total_count={1} />
    </MemoryRouter>
  );
  expect(screen.queryByTestId("exam-intel-details-ssc-cgl")).not.toBeInTheDocument();
});

test("same-slug replacement with a new id does not inherit expansion", () => {
  const { rerender } = wrap(<ExamListTable items={[SAME_SLUG_OLD]} total_count={1} />);
  expand("same-slug");
  expect(screen.getByTestId("exam-intel-details-same-slug")).toBeInTheDocument();
  expect(screen.getByText("Same Slug Old")).toBeInTheDocument();

  rerender(
    <MemoryRouter>
      <ExamListTable items={[SAME_SLUG_NEW]} total_count={1} />
    </MemoryRouter>
  );

  expect(screen.getByText("Same Slug New")).toBeInTheDocument();
  expect(screen.queryByText("Same Slug Old")).not.toBeInTheDocument();
  expect(screen.queryByTestId("exam-intel-details-same-slug")).not.toBeInTheDocument();
  expect(screen.getByTestId("exam-intel-disclosure-same-slug")).toHaveAttribute("aria-expanded", "false");
});

test("slugless UUID row keeps UUID out of visible text and controlled DOM handles", () => {
  wrap(<ExamListTable items={[SLUGLESS_UUID_ITEM]} total_count={1} />);
  expect(screen.getByText("Unnamed exam")).toBeInTheDocument();
  const button = screen.getByTestId("exam-intel-disclosure-row-0");
  expect(button).toHaveAccessibleName("Show details for Unnamed exam");
  expect(button.getAttribute("aria-controls")).not.toContain(UUID);
  expect(document.body.textContent).not.toContain(UUID);

  fireEvent.click(button);
  const detail = screen.getByTestId("exam-intel-details-row-0");
  expect(detail.getAttribute("id")).not.toContain(UUID);
  expect(within(detail).getByText("Exam key")).toBeInTheDocument();
  expect(within(detail).getByText("—")).toBeInTheDocument();
  expect(document.body.textContent).not.toContain(UUID);
});

test("anonymous fallback rows do not emit duplicate-key warnings", () => {
  const errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
  try {
    wrap(<ExamListTable items={ANONYMOUS_ITEMS} total_count={2} />);
    const keyWarnings = errorSpy.mock.calls.filter((call) =>
      String(call[0]).includes("Encountered two children with the same key")
    );
    expect(keyWarnings).toHaveLength(0);
  } finally {
    errorSpy.mockRestore();
  }
});

test("fallback rows sharing a name expand independently", () => {
  wrap(<ExamListTable items={FALLBACK_SHARED_NAME_ITEMS} total_count={2} />);
  fireEvent.click(screen.getByTestId("exam-intel-disclosure-Shared-Name-0"));
  expect(screen.getByTestId("exam-intel-details-Shared-Name-0")).toBeInTheDocument();
  expect(screen.queryByTestId("exam-intel-details-Shared-Name-1")).not.toBeInTheDocument();

  fireEvent.click(screen.getByTestId("exam-intel-disclosure-Shared-Name-1"));
  expect(screen.getByTestId("exam-intel-details-Shared-Name-0")).toBeInTheDocument();
  expect(screen.getByTestId("exam-intel-details-Shared-Name-1")).toBeInTheDocument();
});

test("expanded fallback row stays expanded across rerender with same rows", () => {
  const { rerender } = wrap(<ExamListTable items={ANONYMOUS_ITEMS} total_count={2} />);
  fireEvent.click(screen.getByTestId("exam-intel-disclosure-row-1"));
  expect(screen.getByTestId("exam-intel-details-row-1")).toBeInTheDocument();

  rerender(
    <MemoryRouter>
      <ExamListTable items={ANONYMOUS_ITEMS} total_count={2} />
    </MemoryRouter>
  );

  expect(screen.getByTestId("exam-intel-details-row-1")).toBeInTheDocument();
  expect(screen.queryByTestId("exam-intel-details-row-0")).not.toBeInTheDocument();
});

test("slugless same-name UUID rows get unique DOM handles and action testids", () => {
  wrap(<ExamListTable items={SLUGLESS_SAME_NAME_UUID_ITEMS} total_count={2} />);
  const first = screen.getByTestId("exam-intel-disclosure-Shared-UUID-Name-0");
  const second = screen.getByTestId("exam-intel-disclosure-Shared-UUID-Name-1");
  expect(first).toBeInTheDocument();
  expect(second).toBeInTheDocument();
  expect(first.getAttribute("aria-controls")).not.toBe(second.getAttribute("aria-controls"));
  expect(first.getAttribute("aria-controls")).not.toContain(UUID);
  expect(second.getAttribute("aria-controls")).not.toContain(UUID_2);
  expect(screen.getByTestId("exam-intel-console-Shared-UUID-Name-0")).toBeInTheDocument();
  expect(screen.getByTestId("exam-intel-workspace-Shared-UUID-Name-0")).toBeInTheDocument();
  expect(screen.getByTestId("exam-intel-console-Shared-UUID-Name-1")).toBeInTheDocument();
  expect(screen.getByTestId("exam-intel-workspace-Shared-UUID-Name-1")).toBeInTheDocument();

  fireEvent.click(first);
  fireEvent.click(second);
  const firstDetail = screen.getByTestId("exam-intel-details-Shared-UUID-Name-0");
  const secondDetail = screen.getByTestId("exam-intel-details-Shared-UUID-Name-1");
  expect(firstDetail).toBeInTheDocument();
  expect(secondDetail).toBeInTheDocument();
  expect(firstDetail.getAttribute("id")).not.toBe(secondDetail.getAttribute("id"));
  expect(firstDetail.getAttribute("id")).not.toContain(UUID);
  expect(secondDetail.getAttribute("id")).not.toContain(UUID_2);
  expect(document.body.textContent).not.toContain(UUID);
  expect(document.body.textContent).not.toContain(UUID_2);
});

// ── collapsed metrics and readiness ───────────────────────────────────────

test("collapsed syllabus combines verified and pending without bare zeroes", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expect(screen.getByText("2 verified · 1 pending")).toBeInTheDocument();
  expect(screen.getByText("1 pending")).toBeInTheDocument();
});

test("topic coverage uses reviewed-or-locked wording and zero coverage fallback", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  const coverageCell = screen.getByText("3 of 5 reviewed or locked");
  expect(coverageCell).toBeInTheDocument();
  expect(screen.getByText("No topic coverage")).toBeInTheDocument();
  expect(coverageCell.textContent).not.toMatch(/verified/i);
});

test("readiness badge renders for each row", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expect(screen.getByText("ready")).toBeInTheDocument();
  expect(screen.getByText("not ready")).toBeInTheDocument();
});

// Defensive guards: backend readiness_level is a closed enum, but unknown values
// should still render neutral/human labels rather than raw identifiers.
test.each([
  ["needs_manual_review", "Needs manual review"],
  [UUID, "Needs review"],
  ["/api/study/internal", "Needs review"],
  ["https://internal.example/path", "Needs review"],
])("unknown readiness value %p renders a safe label", (raw, label) => {
  wrap(<ExamListTable items={[readinessFixture(raw)]} total_count={1} />);
  expect(screen.getByText(label)).toBeInTheDocument();
  expect(document.body.textContent).not.toContain(raw);
});

// ── detail glossary and safe labels ────────────────────────────────────────

test("detail renders management lane glossary label, helper, and cadence label", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expand("ssc-cgl");
  const detail = screen.getByTestId("exam-intel-details-ssc-cgl");
  expect(within(detail).getByText("Core")).toBeInTheDocument();
  expect(within(detail).getByText("Lane guidance")).toBeInTheDocument();
  expect(within(detail).getByText("Full readiness expected.")).toBeInTheDocument();
  expect(within(detail).getByText("Annual")).toBeInTheDocument();
});

test("null management mode and cadence render Unclassified and Unknown without null helper", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expand("ibps-po");
  const detail = screen.getByTestId("exam-intel-details-ibps-po");
  expect(within(detail).getByText("Unclassified")).toBeInTheDocument();
  expect(within(detail).getByText("Unknown")).toBeInTheDocument();
  expect(within(detail).queryByText("Lane guidance")).not.toBeInTheDocument();
  expect(detail.textContent).not.toContain("null");
});

test("detail renders visibility, syllabus counts, reviewed-or-locked coverage counts, high-yield topics, and planner note", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expand("ssc-cgl");
  expand("ibps-po");
  expect(within(screen.getByTestId("exam-intel-details-ssc-cgl")).getByText("Active")).toBeInTheDocument();
  expect(within(screen.getByTestId("exam-intel-details-ibps-po")).getByText("Inactive")).toBeInTheDocument();
  expect(screen.getAllByText("Syllabus verified count")).toHaveLength(2);
  expect(screen.getAllByText("Syllabus pending count")).toHaveLength(2);
  expect(screen.getAllByText("Reviewed or locked topic count")).toHaveLength(2);
  expect(document.body.textContent).not.toContain(["Verified", "topic count"].join(" "));
  expect(screen.getAllByText("Total topic coverage count")).toHaveLength(2);
  expect(screen.getAllByText("High-yield topics")).toHaveLength(2);
  expect(document.body.textContent).toContain("Reviewed or locked rows feed the planner; locked preferred.");
  expect(document.body.textContent).not.toMatch(/\btrue\b|\bfalse\b/);
  expect(document.body.textContent).not.toContain(["Locked", "high-yield"].join(" "));
});

test("pyq_coverage_status values and PYQ column are not rendered", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expand("ssc-cgl");
  expect(headers()).not.toContain("PYQ");
  expect(document.body.textContent).not.toMatch(/\bcovered\b/);
  expect(document.body.textContent).not.toMatch(/\bnone\b/);
});

// ── pagination footer ──────────────────────────────────────────────────────

test("renders pagination footer with range", () => {
  wrap(<ExamListTable items={ITEMS} page={0} pageSize={25} total_count={30} has_next offset={0} />);
  expect(screen.getByTestId("exam-intel-pagination")).toBeInTheDocument();
  expect(screen.getByTestId("exam-intel-range")).toHaveTextContent("1–2 of 30");
});

test("prev button disabled on first page", () => {
  wrap(<ExamListTable items={ITEMS} page={0} pageSize={25} total_count={30} has_next offset={0} />);
  expect(screen.getByTestId("exam-intel-prev")).toBeDisabled();
});

test("next button enabled when has_next is true", () => {
  wrap(<ExamListTable items={ITEMS} page={0} pageSize={25} total_count={30} has_next={true} offset={0} />);
  expect(screen.getByTestId("exam-intel-next")).not.toBeDisabled();
});

test("next button disabled when has_next is false", () => {
  wrap(<ExamListTable items={ITEMS} page={0} pageSize={25} total_count={2} has_next={false} offset={0} />);
  expect(screen.getByTestId("exam-intel-next")).toBeDisabled();
});

test("prev button enabled on page > 0", () => {
  wrap(<ExamListTable items={ITEMS} page={1} pageSize={25} total_count={30} has_next={false} offset={25} />);
  expect(screen.getByTestId("exam-intel-prev")).not.toBeDisabled();
});

test("clicking next calls onPageChange with page + 1", () => {
  const onChange = jest.fn();
  wrap(
    <ExamListTable
      items={ITEMS} page={0} pageSize={25} total_count={30}
      has_next={true} offset={0} onPageChange={onChange}
    />
  );
  fireEvent.click(screen.getByTestId("exam-intel-next"));
  expect(onChange).toHaveBeenCalledWith(1);
});

test("clicking prev calls onPageChange with page - 1", () => {
  const onChange = jest.fn();
  wrap(
    <ExamListTable
      items={ITEMS} page={2} pageSize={25} total_count={75}
      has_next={false} offset={50} onPageChange={onChange}
    />
  );
  fireEvent.click(screen.getByTestId("exam-intel-prev"));
  expect(onChange).toHaveBeenCalledWith(1);
});

// ── range label never inverted ─────────────────────────────────────────────

test("range label is never inverted when rows is empty on a non-first page", () => {
  wrap(
    <ExamListTable
      items={[]} page={1} pageSize={25} total_count={30}
      has_next={false} offset={25}
    />
  );
  const range = screen.getByTestId("exam-intel-range");
  const text = range.textContent;
  if (text !== "No results") {
    const match = text.match(/(\d+)–(\d+)/);
    if (match) {
      expect(Number(match[2])).toBeGreaterThanOrEqual(Number(match[1]));
    }
  }
});

test("disclosure expansion does not paginate and leaves action hrefs unchanged", () => {
  const onChange = jest.fn();
  wrap(<ExamListTable items={ITEMS} total_count={2} onPageChange={onChange} />);
  const primary = screen.getByTestId("exam-intel-console-ssc-cgl");
  const secondary = screen.getByTestId("exam-intel-workspace-ssc-cgl");
  const primaryHref = primary.getAttribute("href");
  const secondaryHref = secondary.getAttribute("href");

  expand("ssc-cgl");

  expect(screen.getByTestId("exam-intel-details-ssc-cgl")).toBeInTheDocument();
  expect(onChange).not.toHaveBeenCalled();
  expect(primary.getAttribute("href")).toBe(primaryHref);
  expect(secondary.getAttribute("href")).toBe(secondaryHref);
});

// ── 4.6F: row action routes the primary path to the console ────────────────

test("primary row action 'Open console' targets /console/:exam_id", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  const primary = screen.getByTestId("exam-intel-console-ssc-cgl");
  expect(primary.textContent).toContain("Open console");
  expect(primary.getAttribute("href")).toBe(`/admin/exam-intelligence/console/${UUID}`);
});

test("secondary 'Advanced workspace' still routes to /workspace/:exam_id and is demoted", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  const secondary = screen.getByTestId("exam-intel-workspace-ssc-cgl");
  expect(secondary.textContent).toContain("Advanced workspace");
  expect(secondary.getAttribute("href")).toBe(`/admin/exam-intelligence/workspace/${UUID}`);
  expect(secondary.className).not.toContain("border-indigo-300");
});
