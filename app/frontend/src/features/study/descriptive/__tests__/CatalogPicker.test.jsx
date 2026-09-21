/**
 * The catalogue picker, against the payload the fixed API returns.
 *
 * What broke was visible here and caused elsewhere: thematic compilations
 * arrived in `papers` and were rendered under "Sat papers, in question order",
 * a claim the thematic half cannot keep — its question_number is NULL by
 * design. These pin the rendering half of that contract.
 */
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import CatalogPicker from "../CatalogPicker";

const PSIR = "Political Science and International Relations";

const CATALOG = {
  exam_id: "exam-1",
  subject: PSIR,
  subjects: [
    { subject: PSIR, question_count: 140 },
    { subject: "Anthropology", question_count: 96 },
    { subject: "General Studies", question_count: 1 },
  ],
  papers: [
    { id: "p1", label: "2025 · P1", year: 2025, paper_slot: "P1", question_count: 10 },
    { id: "p2", label: "2025 · P2", year: 2025, paper_slot: "P2", question_count: 8 },
    { id: "p3", label: "2024 · P1", year: 2024, paper_slot: "P1", question_count: 9 },
  ],
  theme_papers: [
    { paper_id: "opt-psir-p1", paper_label: "P1", paper_number: 1, question_count: 20 },
    { paper_id: "opt-psir-p2", paper_label: "P2", paper_number: 2, question_count: 9 },
    { paper_id: null, paper_label: "Other", paper_number: null, question_count: 3 },
  ],
  themes: [
    {
      paper_id: "opt-psir-p1",
      paper_label: "P1",
      paper_number: 1,
      question_count: 20,
      sections: [
        {
          section: "1. Political Theory: meaning and approaches",
          part: "Section A",
          line: "Political Theory: meaning and approaches to the study of political theory.",
          question_count: 12,
          themes: [
            { theme: "The State", question_count: 12 },
          ],
        },
        {
          section: "2. Theories of the state",
          part: "Section A",
          question_count: 8,
          themes: [{ theme: "Liberal", question_count: 8 }],
        },
      ],
    },
    {
      paper_id: "opt-psir-p2",
      paper_label: "P2",
      paper_number: 2,
      question_count: 9,
      sections: [
        {
          section: "1. Comparative Politics",
          part: null,
          question_count: 9,
          themes: [{ theme: "Nature and approaches", question_count: 9 }],
        },
      ],
    },
    {
      paper_id: null,
      paper_label: "Other",
      paper_number: null,
      question_count: 3,
      sections: [
        {
          section: "Other",
          part: null,
          question_count: 3,
          themes: [{ theme: "Untagged", question_count: 3 }],
        },
      ],
    },
  ],
  years: [{ year: 2025, question_count: 18 }],
  total_questions: 27,
};

const SELECTION = {
  subject: PSIR,
  paper_id: null,
  paper_number: null,
  theme: null,
  year: null,
};

const renderPicker = (props = {}) =>
  render(
    <CatalogPicker
      catalog={CATALOG}
      selection={SELECTION}
      onSelect={jest.fn()}
      {...props}
    />,
  );

test("papers are labelled year then paper number, in that order", () => {
  renderPicker();
  // The trailing count lives in its own span; the label is the text before it.
  const labels = screen
    .getAllByTestId("descriptive-paper")
    .map((b) => Array.from(b.childNodes)
      .filter((n) => n.nodeType === Node.TEXT_NODE)
      .map((n) => n.textContent)
      .join("")
      .trim());
  expect(labels).toEqual(["2025 · P1", "2025 · P2", "2024 · P1"]);
});

test("the question-order claim is made only when there are papers", () => {
  renderPicker();
  expect(screen.getByTestId("descriptive-papers-hint")).toHaveTextContent(
    "Sat papers, in question order.",
  );
});

test("no question-order claim when the papers list is empty", () => {
  // A subject with only thematic questions. The old picker still printed
  // "Sat papers, in question order." over whatever had leaked into the list.
  renderPicker({ catalog: { ...CATALOG, papers: [] } });
  expect(screen.queryByTestId("descriptive-papers-hint")).not.toBeInTheDocument();
  expect(screen.getByText("No papers for this subject yet.")).toBeInTheDocument();
});

test("themes always keep their own no-order wording", () => {
  renderPicker();
  expect(
    screen.getByText(/No\s+paper order, no year\./),
  ).toBeInTheDocument();
});

test("every count says what it counts", () => {
  renderPicker();
  const subject = screen
    .getAllByTestId("descriptive-subject")
    .find((b) => b.textContent.startsWith(PSIR));
  expect(subject).toHaveAttribute("title", "140 questions");
  expect(screen.getAllByTestId("descriptive-paper")[0]).toHaveAttribute(
    "title",
    "10 questions",
  );
  expect(screen.getAllByTestId("descriptive-theme")[0]).toHaveAttribute(
    "title",
    "12 questions",
  );
});

test("a count of one is singular", () => {
  renderPicker();
  const gs = screen
    .getAllByTestId("descriptive-subject")
    .find((b) => b.textContent.startsWith("General Studies"));
  expect(gs).toHaveAttribute("title", "1 question");
});

test("choosing a subject clears the paper and theme below it", () => {
  const onSelect = jest.fn();
  renderPicker({
    onSelect,
    selection: { ...SELECTION, subject: "Anthropology", paper_id: "p9" },
  });
  const psir = screen
    .getAllByTestId("descriptive-subject")
    .find((b) => b.textContent.startsWith(PSIR));
  fireEvent.click(psir);

  expect(onSelect).toHaveBeenCalledWith({
    subject: PSIR,
    paper_id: null,
    theme: null,
    year: null,
  });
});

test("with no subject chosen the lists say why they are empty", () => {
  renderPicker({
    catalog: { ...CATALOG, subject: null, papers: [], themes: [], theme_papers: [] },
    selection: { subject: null, paper_id: null, paper_number: null, theme: null, year: null },
  });
  expect(screen.getByText("Pick a subject to see its papers.")).toBeInTheDocument();
  expect(screen.getByText("Pick a subject to see its themes.")).toBeInTheDocument();
});


// ── the syllabus tree ────────────────────────────────────────────────────


test("themes are grouped into syllabus sections, in the order given", () => {
  renderPicker();
  const sections = screen
    .getAllByTestId("descriptive-theme-section")
    .map((el) => el.querySelector("summary").textContent);

  // Section 1 before section 2, and P2's section after both of P1's.
  expect(sections[0]).toMatch(/^1\. Political Theory/);
  expect(sections[1]).toMatch(/^2\. Theories of the state/);
  expect(sections[2]).toMatch(/^1\. Comparative Politics/);
});

test("a section carries its syllabus part when the paper has parts", () => {
  renderPicker();
  const first = screen.getAllByTestId("descriptive-theme-section")[0];
  expect(first.querySelector("summary").textContent).toContain("Section A");
  // Comparative Politics has no part — eight of the twelve papers have none.
  const third = screen.getAllByTestId("descriptive-theme-section")[2];
  expect(third.querySelector("summary").textContent).not.toContain("Section");
});

test("sections are collapsible and carry their own count", () => {
  renderPicker();
  const first = screen.getAllByTestId("descriptive-theme-section")[0];
  expect(first.tagName).toBe("DETAILS");
  expect(first.querySelector("summary").textContent).toContain("12");
});

test("paper tabs are rendered for each paper with themes", () => {
  renderPicker();
  // The trailing count lives in its own span; the label is the text before it.
  const labels = screen
    .getAllByTestId("descriptive-theme-paper-tab")
    .map((t) =>
      Array.from(t.childNodes)
        .filter((n) => n.nodeType === Node.TEXT_NODE)
        .map((n) => n.textContent)
        .join("")
        .trim(),
    );
  expect(labels).toEqual(["P1", "P2", "Other"]);
});

test("choosing a paper tab sets paper_number and clears the theme and sitting", () => {
  const onSelect = jest.fn();
  renderPicker({ onSelect });
  fireEvent.click(screen.getAllByTestId("descriptive-theme-paper-tab")[0]);

  expect(onSelect).toHaveBeenCalledWith(
    expect.objectContaining({ paper_number: "1", theme: null, paper_id: null }),
  );
});

test("the Other tab cannot be selected — it is a label, not a paper", () => {
  renderPicker();
  const tabs = screen.getAllByTestId("descriptive-theme-paper-tab");
  expect(tabs[2]).toBeDisabled();
});

test("clicking the selected paper tab again clears the filter", () => {
  const onSelect = jest.fn();
  renderPicker({ onSelect, selection: { ...SELECTION, paper_number: "1" } });
  fireEvent.click(screen.getAllByTestId("descriptive-theme-paper-tab")[0]);
  expect(onSelect).toHaveBeenCalledWith(
    expect.objectContaining({ paper_number: null }),
  );
});

test("an unplaced theme is visible in its own Other group", () => {
  renderPicker();
  const papers = screen.getAllByTestId("descriptive-theme-paper");
  expect(papers[papers.length - 1].textContent).toContain("Untagged");
});

test("no paper tabs when there is only one paper of themes", () => {
  renderPicker({
    catalog: {
      ...CATALOG,
      theme_papers: [CATALOG.theme_papers[0]],
      themes: [CATALOG.themes[0]],
    },
  });
  expect(screen.queryByTestId("descriptive-theme-paper-tab")).not.toBeInTheDocument();
});


test("a section shows its official syllabus line as a subtitle", () => {
  renderPicker();
  expect(screen.getAllByTestId("descriptive-section-line")[0]).toHaveTextContent(
    "Political Theory: meaning and approaches to the study of political theory.",
  );
});

test("a section with no recorded syllabus line shows no subtitle", () => {
  renderPicker();
  // Only the first section carries `line` in the fixture.
  expect(screen.getAllByTestId("descriptive-section-line")).toHaveLength(1);
});
