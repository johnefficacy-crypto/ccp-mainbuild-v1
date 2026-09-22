/**
 * The catalogue navigator: subject → paper tab → lens.
 *
 * WHAT THIS REPLACES. With no subject chosen the picker rendered all 140
 * papers as chips labelled "2025 · P1" — a label six subjects share. The wall
 * was unreadable and every chip in it was ambiguous, both for the same reason:
 * a paper only means something inside a subject.
 *
 * So the first thing these hold is that nothing renders before a subject.
 */
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import CatalogPicker, { countLabel } from "../CatalogPicker";

const PSIR = "Political Science and International Relations";

const SUBJECTS = [
  { subject: PSIR, question_count: 140 },
  { subject: "Anthropology", question_count: 96 },
  { subject: "General Studies", question_count: 1351 },
];

const OPT_SLOTS = [
  { paper_number: 1, label: "Paper I", slot: "P1", question_count: 76, attempted_count: 4 },
  { paper_number: 2, label: "Paper II", slot: "P2", question_count: 64, attempted_count: 0 },
];

const CATALOG = {
  exam_id: "exam-1",
  subject: PSIR,
  subject_short: "PSIR",
  subjects: SUBJECTS,
  paper_slots: OPT_SLOTS,
  papers: [
    { id: "p1", label: "2025 · P1", subject: PSIR, subject_short: "PSIR",
      year: 2025, paper_slot: "P1", question_count: 10 },
  ],
  themes: [
    {
      paper_id: "opt-psir-p1",
      paper_label: "P1",
      paper_number: 1,
      question_count: 20,
      attempted_count: 3,
      sections: [
        {
          section: "Political Theory",
          part: "Part A",
          line: "Political theory: meaning and approaches.",
          question_count: 12,
          attempted_count: 3,
          themes: [
            { theme: "Sovereignty", question_count: 7, attempted_count: 3 },
            { theme: "Justice", question_count: 5, attempted_count: 0 },
          ],
        },
        {
          section: "Indian Government",
          part: null,
          line: null,
          question_count: 8,
          attempted_count: 0,
          themes: [{ theme: "Federalism", question_count: 8, attempted_count: 0 }],
        },
      ],
    },
  ],
  years: [
    { year: 2025, question_count: 28, attempted_count: 5, paper_ids: ["p1"] },
    { year: 2024, question_count: 24, attempted_count: 0, paper_ids: ["p3"] },
    { year: 2023, question_count: 20, attempted_count: 20, paper_ids: ["p5"] },
  ],
  total_questions: 140,
};

const NO_FILTERS = { unattempted: false, hasMarks: false, yearFrom: "", yearTo: "" };

function renderPicker(props = {}) {
  const onSelect = jest.fn();
  const onLensChange = jest.fn();
  const onFilterChange = jest.fn();
  render(
    <CatalogPicker
      catalog={CATALOG}
      selection={{ subject: PSIR, paper: null, paper_id: null, paper_number: null, theme: null, year: null }}
      onSelect={onSelect}
      lens="syllabus"
      onLensChange={onLensChange}
      filters={NO_FILTERS}
      onFilterChange={onFilterChange}
      {...props}
    />,
  );
  return { onSelect, onLensChange, onFilterChange };
}

// ── 1. no subject → the picker, and nothing else ───────────────────────────

test("with no subject it shows the subject picker only", () => {
  renderPicker({ selection: { subject: null } });

  expect(screen.getByTestId("descriptive-subject-picker")).toBeInTheDocument();
  expect(screen.getAllByTestId("descriptive-subject")).toHaveLength(3);
  // The chip wall, gone: no papers, no tabs, no lens, no themes, no years.
  expect(screen.queryByTestId("descriptive-paper-tab")).not.toBeInTheDocument();
  expect(screen.queryByTestId("descriptive-syllabus-lens")).not.toBeInTheDocument();
  expect(screen.queryByTestId("descriptive-year-lens")).not.toBeInTheDocument();
  expect(screen.queryByTestId("descriptive-lens-syllabus")).not.toBeInTheDocument();
});

test("the picker says why it is asking", () => {
  renderPicker({ selection: { subject: null } });
  expect(screen.getByText(/means a different paper in each subject/i)).toBeInTheDocument();
});

test("picking a subject clears every selection below it", () => {
  const { onSelect } = renderPicker({ selection: { subject: null } });
  fireEvent.click(screen.getAllByTestId("descriptive-subject")[0]);
  expect(onSelect).toHaveBeenCalledWith({
    subject: PSIR, paper: null, paper_id: null, paper_number: null, theme: null, year: null,
  });
});

test("an exam with no descriptive questions says so rather than showing a picker", () => {
  renderPicker({ catalog: { subjects: [] }, selection: { subject: null } });
  expect(screen.getByTestId("descriptive-catalog-empty")).toBeInTheDocument();
});

// ── 2. subject header and paper tabs ───────────────────────────────────────

test("the subject is named in a header once chosen", () => {
  renderPicker();
  expect(screen.getByTestId("descriptive-subject-header")).toHaveTextContent(PSIR);
  expect(screen.getByTestId("descriptive-change-subject")).toBeInTheDocument();
});

test("an optional gets Paper I and Paper II tabs", () => {
  renderPicker();
  const tabs = screen.getAllByTestId("descriptive-paper-tab");
  expect(tabs.map((t) => t.textContent)).toEqual([
    expect.stringContaining("Paper I"),
    expect.stringContaining("Paper II"),
  ]);
});

test("General Studies gets GS1..GS4 and Essay", () => {
  renderPicker({
    catalog: {
      ...CATALOG,
      subject: "General Studies",
      paper_slots: [
        { slot: "GS1", paper_number: 1, label: "GS1", question_count: 300, attempted_count: 0 },
        { slot: "GS2", paper_number: 2, label: "GS2", question_count: 300, attempted_count: 0 },
        { slot: "GS3", paper_number: 3, label: "GS3", question_count: 300, attempted_count: 0 },
        { slot: "GS4", paper_number: 4, label: "GS4", question_count: 280, attempted_count: 0 },
        { slot: "ESSAY", paper_number: 99, label: "Essay", question_count: 84, attempted_count: 0 },
      ],
    },
    selection: { subject: "General Studies" },
  });
  expect(screen.getAllByTestId("descriptive-paper-tab").map((t) => t.textContent.trim()))
    .toEqual([
      expect.stringContaining("GS1"), expect.stringContaining("GS2"),
      expect.stringContaining("GS3"), expect.stringContaining("GS4"),
      expect.stringContaining("Essay"),
    ]);
});

test("a tab with nothing in it is still a tab, and says which", () => {
  /* A missing tab reads as "this paper does not exist", which is false. */
  renderPicker({
    catalog: {
      ...CATALOG,
      paper_slots: [
        OPT_SLOTS[0],
        { slot: "P2", paper_number: 2, label: "Paper II", question_count: 0, attempted_count: 0 },
      ],
    },
    selection: { subject: PSIR, paper: "P2" },
  });
  expect(screen.getAllByTestId("descriptive-paper-tab")).toHaveLength(2);
  expect(screen.getByTestId("descriptive-slot-empty")).toHaveTextContent(
    "Paper II — not available yet.",
  );
  // ...and the lens is not offered for a paper with nothing behind it.
  expect(screen.queryByTestId("descriptive-syllabus-lens")).not.toBeInTheDocument();
});

test("selecting a tab clears the selections below it", () => {
  const { onSelect } = renderPicker();
  fireEvent.click(screen.getAllByTestId("descriptive-paper-tab")[1]);
  expect(onSelect).toHaveBeenCalledWith(
    expect.objectContaining({ paper: "P2", paper_number: null, paper_id: null, theme: null, year: null }),
  );
});

test("the selected tab is the one marked selected", () => {
  renderPicker({ selection: { subject: PSIR, paper: "P1" } });
  const tabs = screen.getAllByTestId("descriptive-paper-tab");
  expect(tabs[0]).toHaveAttribute("aria-selected", "true");
  expect(tabs[1]).toHaveAttribute("aria-selected", "false");
});

// ── 3. the two lenses ──────────────────────────────────────────────────────

test("by syllabus is the default and shows sections in syllabus order", () => {
  renderPicker();
  expect(screen.getByTestId("descriptive-lens-syllabus")).toHaveAttribute("aria-checked", "true");
  const sections = screen.getAllByTestId("descriptive-theme-section");
  expect(sections.map((s) => s.textContent)).toEqual([
    expect.stringContaining("Political Theory"),
    expect.stringContaining("Indian Government"),
  ]);
});

test("a section shows its syllabus line and its microtopics with counts", () => {
  renderPicker();
  expect(screen.getByTestId("descriptive-section-line")).toHaveTextContent(
    "Political theory: meaning and approaches.",
  );
  const themes = screen.getAllByTestId("descriptive-theme");
  expect(themes[0]).toHaveTextContent("Sovereignty");
  expect(themes[0]).toHaveTextContent("3/7");   // attempted / available
  expect(themes[1]).toHaveTextContent("Justice");
  expect(themes[1]).toHaveTextContent("5");
});

test("by year shows one row per year, newest first — not a chip wall", () => {
  renderPicker({ lens: "year" });
  const rows = screen.getAllByTestId("descriptive-year-row");
  expect(rows).toHaveLength(3);
  expect(rows.map((r) => r.textContent)).toEqual([
    expect.stringContaining("2025"),
    expect.stringContaining("2024"),
    expect.stringContaining("2023"),
  ]);
  expect(rows[0]).toHaveTextContent("28 questions · 5 done");
  expect(screen.queryByTestId("descriptive-syllabus-lens")).not.toBeInTheDocument();
});

test("a year with nothing done shows the plain count", () => {
  renderPicker({ lens: "year" });
  expect(screen.getAllByTestId("descriptive-year-row")[1]).toHaveTextContent("24 questions");
  expect(screen.getAllByTestId("descriptive-year-row")[1]).not.toHaveTextContent("done");
});

test("picking a year clears the theme and the paper", () => {
  const { onSelect } = renderPicker({ lens: "year" });
  fireEvent.click(screen.getAllByTestId("descriptive-year-row")[0]);
  expect(onSelect).toHaveBeenCalledWith(
    expect.objectContaining({ year: "2025", theme: null, paper_id: null }),
  );
});

test("the lens toggle reports the change rather than holding it itself", () => {
  const { onLensChange } = renderPicker();
  fireEvent.click(screen.getByTestId("descriptive-lens-year"));
  expect(onLensChange).toHaveBeenCalledWith("year");
});

test("an empty lens says so instead of rendering nothing", () => {
  renderPicker({ catalog: { ...CATALOG, themes: [] } });
  expect(screen.getByTestId("descriptive-syllabus-empty")).toBeInTheDocument();
  renderPicker({ catalog: { ...CATALOG, years: [] }, lens: "year" });
  expect(screen.getByTestId("descriptive-year-empty")).toBeInTheDocument();
});

// ── 4. filters ─────────────────────────────────────────────────────────────

test("the filters report their changes by name", () => {
  const { onFilterChange } = renderPicker();
  fireEvent.click(screen.getByTestId("descriptive-filter-unattempted"));
  expect(onFilterChange).toHaveBeenCalledWith("unattempted", true);
  fireEvent.click(screen.getByTestId("descriptive-filter-has-marks"));
  expect(onFilterChange).toHaveBeenCalledWith("hasMarks", true);
});

test("the year range belongs to the by-year lens alone", () => {
  /* A year range is a question about sittings. The syllabus lens has none. */
  renderPicker();
  expect(screen.queryByTestId("descriptive-filter-year-from")).not.toBeInTheDocument();

  renderPicker({ lens: "year" });
  expect(screen.getByTestId("descriptive-filter-year-from")).toBeInTheDocument();
  expect(screen.getByTestId("descriptive-filter-year-to")).toBeInTheDocument();
});

test("the year range inputs are labelled for a screen reader", () => {
  renderPicker({ lens: "year" });
  expect(screen.getByLabelText("Year from")).toBeInTheDocument();
  expect(screen.getByLabelText("Year to")).toBeInTheDocument();
});

test("a filter renders the value it was given rather than its own", () => {
  renderPicker({ filters: { ...NO_FILTERS, unattempted: true, yearFrom: "2019" }, lens: "year" });
  expect(screen.getByTestId("descriptive-filter-unattempted")).toBeChecked();
  expect(screen.getByTestId("descriptive-filter-year-from")).toHaveValue(2019);
});

// ── countLabel ─────────────────────────────────────────────────────────────

describe("countLabel", () => {
  test("omits the done count when nothing is done", () => {
    expect(countLabel(28, 0)).toBe("28 questions");
    expect(countLabel(1, 0)).toBe("1 question");
  });

  test("states it when there is one", () => {
    expect(countLabel(28, 5)).toBe("28 questions · 5 done");
  });

  test("treats missing counts as zero rather than as NaN", () => {
    expect(countLabel(undefined, undefined)).toBe("0 questions");
  });
});
