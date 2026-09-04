import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";

// Recharts needs a measured container, which jsdom never gives it. Stub the
// responsive wrapper to a fixed box so the SVG renders; everything asserted
// below is DOM text or a labelled element, never chart geometry.
jest.mock("recharts", () => {
  const actual = jest.requireActual("recharts");
  const mockReact = jest.requireActual("react");
  return {
    ...actual,
    ResponsiveContainer: ({ children }) =>
      mockReact.createElement(
        "div",
        { style: { width: 800, height: 400 } },
        mockReact.cloneElement(children, { width: 800, height: 400 })
      ),
  };
});

jest.mock("../../lib/api", () => ({ api: { get: jest.fn() } }));

import { api } from "../../lib/api";
import CsatCompositionSection from "./CsatCompositionSection";
import { csatAnalysis } from "./csatCompositionConfig";

const UPSC = "upsc-cse";
const QUANT = "55555555-5555-5555-5555-555555555551";
const ENGLISH = "55555555-5555-5555-5555-555555555552";
const REASONING = "55555555-5555-5555-5555-555555555553";

const YEARS = [2023, 2024, 2025, 2026];
const PAPER_ID = {
  2023: "586d515e-2d3d-485d-a944-3983e4569e53",
  2024: "9e191ae4-68b9-47bf-9121-6d9d468a7bc5",
  2025: "505b29a0-0d4d-5230-88aa-3bbc525a6db5",
  2026: "b06305ad-cc93-4c27-b309-1b590f0a3247",
};
// Rejected, superseded by b06305ad…. The endpoint never returns it; a payload
// carrying it would be a bug upstream, and this file asserts its absence.
const REJECTED_2026 = "7b18bf8d-2919-4328-9779-8b0fe9a8b22a";

const SUBJECT_SPLIT = {
  2023: { [QUANT]: 46, [REASONING]: 14, [ENGLISH]: 20 },
  2024: { [QUANT]: 42, [REASONING]: 17, [ENGLISH]: 16 },
  2025: { [QUANT]: 42, [REASONING]: 22, [ENGLISH]: 16 },
  2026: { [QUANT]: 40, [REASONING]: 14, [ENGLISH]: 26 },
};

// Per-year vectors, not totals: LCM/HCF runs 16, 8, 16, 8, and only the vector
// shows that. The aggregate 48 looks identical to a flat 12, 12, 12, 12.
const QUANT_TOPICS = [
  ["LCM/HCF and divisibility", [16, 8, 16, 8]],
  ["Data sufficiency", [7, 6, 6, 6]],
  ["Percentage increase and decrease", [4, 4, 4, 3]],
  ["Permutations and counting", [3, 3, 3, 3]],
  ["Linear equations", [3, 3, 2, 3]],
  ["Number series", [3, 3, 2, 3]],
  ["Area and perimeter", [2, 3, 2, 3]],
  ["Consecutive and patterned numbers", [2, 2, 2, 2]],
  ["Averages", [1, 1, 0, 0]],
  ["Boats and streams", [0, 0, 1, 1]],
  ["Calendars", [1, 0, 1, 0]],
  ["Clocks", [0, 1, 0, 1]],
  ["Profit and loss", [1, 1, 1, 1]],
  ["Ratio and proportion", [1, 1, 1, 1]],
  ["Simple and compound interest", [1, 1, 0, 1]],
  ["Speed, time and distance", [1, 1, 0, 1]],
  ["Probability", [0, 1, 1, 1]],
  ["Mixtures and alligation", [0, 1, 0, 1]],
  ["Pipes and cisterns", [0, 1, 0, 1]],
  ["Surds and indices", [0, 1, 0, 0]],
];

const REASONING_TOPICS = [
  ["Statement and assumption", [8, 8, 9, 8]],
  ["Blood relations", [0, 1, 1, 0]],
  ["Coding and decoding", [0, 1, 1, 0]],
  ["Direction sense", [0, 1, 1, 0]],
  ["Seating arrangement", [0, 1, 1, 0]],
  ["Syllogism", [0, 1, 1, 0]],
  ["Venn diagrams", [0, 1, 1, 0]],
  ["Cubes and dice", [0, 1, 1, 0]],
  ["Analogy", [0, 1, 1, 0]],
  ["Statement and conclusion", [0, 1, 1, 1]],
  ["Course of action", [1, 0, 1, 1]],
  ["Cause and effect", [1, 0, 1, 1]],
  ["Ordering and ranking", [1, 0, 1, 1]],
  ["Series completion", [1, 0, 1, 1]],
  ["Odd one out", [1, 0, 0, 1]],
  ["Input and output", [1, 0, 0, 0]],
];

const ENGLISH_TOPICS = [
  ["Inference and implied meaning", [6, 4, 4, 7]],
  ["Explicit detail retrieval", [5, 4, 4, 7]],
  ["Main idea and central point", [5, 4, 4, 7]],
  ["Tone and attitude", [3, 3, 3, 3]],
  ["Vocabulary in context", [1, 0, 0, 0]],
  ["Sentence rearrangement", [0, 1, 0, 0]],
  ["Author's purpose", [0, 0, 1, 0]],
  ["Summary selection", [0, 0, 0, 2]],
];

const BY_SUBJECT = [
  [QUANT, QUANT_TOPICS],
  [REASONING, REASONING_TOPICS],
  [ENGLISH, ENGLISH_TOPICS],
];

function slug(name) {
  return name.toLowerCase().replace(/[ ]/g, "-").replace(/\//g, "-").replace(/,/g, "");
}

function topicRow(subjectId, name, perYear) {
  const byPaper = {};
  YEARS.forEach((y, i) => {
    if (perYear[i]) byPaper[PAPER_ID[y]] = perYear[i];
  });
  return {
    topic_id: slug(name),
    topic_name: name,
    subject_id: subjectId,
    total: perYear.reduce((a, b) => a + b, 0),
    by_paper: byPaper,
  };
}

const TOPICS = BY_SUBJECT.flatMap(([sid, rows]) =>
  rows.map(([name, perYear]) => topicRow(sid, name, perYear))
).sort((a, b) => b.total - a.total || a.topic_name.localeCompare(b.topic_name));

const SUBJECTS = [
  { subject_id: QUANT, name: "Quantitative Aptitude", slug: "quantitative-aptitude" },
  { subject_id: REASONING, name: "General Intelligence & Reasoning", slug: "reasoning" },
  { subject_id: ENGLISH, name: "English Language", slug: "english-language" },
];

const PAPERS = YEARS.map((y) => {
  const split = SUBJECT_SPLIT[y];
  const tagged = Object.values(split).reduce((a, b) => a + b, 0);
  return {
    paper_id: PAPER_ID[y],
    year: y,
    phase_id: y < 2025 ? "phase-a" : y === 2025 ? "phase-b" : "phase-c",
    phase_name: "Prelims",
    paper_code: "CSAT",
    set_label: null,
    total_questions: tagged,
    tagged_questions: tagged,
    untagged_questions: 0,
    multi_tagged_questions: 0,
    by_subject: split,
  };
});

function payload(overrides = {}) {
  return {
    exam_id: "e-upsc",
    exam_slug: UPSC,
    verified_only: true,
    subject_ids: [QUANT, REASONING, ENGLISH],
    subjects: SUBJECTS,
    papers: PAPERS,
    topics: TOPICS,
    papers_considered: 14,
    ...overrides,
  };
}

function mockGet(body) {
  api.get.mockImplementation(() => Promise.resolve(body));
}

beforeEach(() => {
  api.get.mockReset();
});

async function renderSection(body = payload()) {
  mockGet(body);
  render(<CsatCompositionSection examSlug={UPSC} />);
  return screen.findByTestId("csat-composition-section");
}

describe("the four CSAT papers", () => {
  it("renders every paper with its subject split", async () => {
    const section = await renderSection();
    const chart = within(section).getByTestId("csat-subject-split-chart");

    YEARS.forEach((y) => {
      expect(within(chart).getAllByText(String(y)).length).toBeGreaterThan(0);
    });
    SUBJECTS.forEach((s) => {
      expect(within(chart).getAllByText(s.name).length).toBeGreaterThan(0);
    });
    // The split is also stated as text, so the counts do not live only in
    // chart geometry.
    YEARS.forEach((y) => {
      const row = within(section).getByTestId(
        `csat-subject-split-row-${PAPER_ID[y]}`
      );
      expect(row).toHaveTextContent(`Quantitative Aptitude ${SUBJECT_SPLIT[y][QUANT]}`);
      expect(row).toHaveTextContent(
        `General Intelligence & Reasoning ${SUBJECT_SPLIT[y][REASONING]}`
      );
      expect(row).toHaveTextContent(`English Language ${SUBJECT_SPLIT[y][ENGLISH]}`);
    });

    expect(api.get).toHaveBeenCalledWith(
      `/api/exam-intelligence/exams/${UPSC}/csat-composition`
    );
  });

  it("counts four papers and 315 tagged questions", async () => {
    const section = await renderSection();
    const counts = within(section).getByTestId("csat-composition-counts");
    expect(counts).toHaveTextContent("4 papers");
    expect(counts).toHaveTextContent("315");
  });

  it("never shows the rejected 2026 paper the endpoint filtered out", async () => {
    const section = await renderSection();
    // b06305ad… is the verified 2026 paper; 7b18bf8d… is the rejected one it
    // superseded, and no row is keyed on it.
    expect(
      within(section).getByTestId(`csat-subject-split-row-${PAPER_ID[2026]}`)
    ).toBeInTheDocument();
    expect(
      within(section).queryByTestId(`csat-subject-split-row-${REJECTED_2026}`)
    ).toBeNull();
    expect(section.innerHTML).not.toContain(REJECTED_2026);
  });
});

describe("topics within a subject", () => {
  it("opens on Quantitative Aptitude", async () => {
    const section = await renderSection();
    expect(
      within(section).getByTestId(`csat-subject-tab-${QUANT}`)
    ).toHaveAttribute("aria-selected", "true");
  });

  it("renders LCM/HCF at 48 with its per-year counts 16, 8, 16, 8", async () => {
    const section = await renderSection();
    const row = within(section).getByTestId(
      `csat-subject-topic-row-${slug("LCM/HCF and divisibility")}`
    );
    expect(row).toHaveTextContent("LCM/HCF and divisibility");
    expect(row).toHaveTextContent("2023 16");
    expect(row).toHaveTextContent("2024 8");
    expect(row).toHaveTextContent("2025 16");
    expect(row).toHaveTextContent("2026 8");
    expect(row).toHaveTextContent("48");
  });

  it("shows Quant's top twelve, with the rest behind a control", async () => {
    const section = await renderSection();
    const strip = within(section).getByTestId("csat-subject-topic-strip");
    expect(strip.children).toHaveLength(12);

    const toggle = within(section).getByTestId("csat-subject-topics-show-all");
    expect(toggle).toHaveTextContent("Show all 20");
    fireEvent.click(toggle);
    expect(
      within(section).getByTestId("csat-subject-topic-strip").children
    ).toHaveLength(20);
  });

  it("shows Reasoning and English whole, with no truncation control", async () => {
    const section = await renderSection();

    fireEvent.click(within(section).getByTestId(`csat-subject-tab-${REASONING}`));
    expect(
      within(section).getByTestId("csat-subject-topic-strip").children
    ).toHaveLength(16);
    expect(
      within(section).queryByTestId("csat-subject-topics-show-all")
    ).toBeNull();
    const sa = within(section).getByTestId(
      `csat-subject-topic-row-${slug("Statement and assumption")}`
    );
    expect(sa).toHaveTextContent("33");

    fireEvent.click(within(section).getByTestId(`csat-subject-tab-${ENGLISH}`));
    expect(
      within(section).getByTestId("csat-subject-topic-strip").children
    ).toHaveLength(8);
  });
});

describe("most-tested topics overall", () => {
  it("ranks the top twelve across every subject, expandable to all", async () => {
    const section = await renderSection();
    const strip = within(section).getByTestId("csat-overall-topic-strip");
    expect(strip.children).toHaveLength(12);

    const first5 = Array.from(strip.children)
      .slice(0, 5)
      .map((li) => li.textContent);
    expect(first5[0]).toContain("LCM/HCF and divisibility");
    expect(first5[1]).toContain("Statement and assumption");
    expect(first5[2]).toContain("Data sufficiency");
    expect(first5[3]).toContain("Inference and implied meaning");
    expect(first5[4]).toContain("Explicit detail retrieval");

    const toggle = within(section).getByTestId("csat-overall-topics-show-all");
    expect(toggle).toHaveTextContent(`Show all ${TOPICS.length}`);
    fireEvent.click(toggle);
    expect(
      within(section).getByTestId("csat-overall-topic-strip").children
    ).toHaveLength(TOPICS.length);
  });

  it("colours each row by its subject", async () => {
    const section = await renderSection();
    const lcm = within(section).getByTestId(
      `csat-overall-topic-row-${slug("LCM/HCF and divisibility")}`
    );
    const inference = within(section).getByTestId(
      `csat-overall-topic-row-${slug("Inference and implied meaning")}`
    );
    const dotColor = (row) => row.querySelector("span[aria-hidden]").style.backgroundColor;
    expect(dotColor(lcm)).not.toEqual(dotColor(inference));
  });
});

describe("difficulty never appears", () => {
  it("renders no band, scale or difficulty word anywhere in the section", async () => {
    const section = await renderSection();
    const text = section.textContent;

    // "not how hard the questions were" is the provenance line saying what this
    // is NOT, so the check is for a band used as a label, not for the word.
    expect(within(section).queryByText(/^Easy$/)).toBeNull();
    expect(within(section).queryByText(/^Medium$/)).toBeNull();
    expect(within(section).queryByText(/^Hard$/)).toBeNull();
    expect(text).not.toMatch(/difficulty/i);
    expect(text).not.toMatch(/reachab/i);
    expect(text).not.toMatch(/\beasy\b/i);
  });

  it("says what the section shows, and what it does not, whenever it renders", async () => {
    const section = await renderSection();
    const provenance = within(section).getByTestId("csat-composition-provenance");
    expect(provenance).toHaveTextContent(
      "Composition of four CSAT papers (2023-2026), from the primary topic tag on each question."
    );
    expect(provenance).toHaveTextContent(
      "Shows what the paper was made of, not how hard the questions were."
    );
  });
});

describe("eligibility", () => {
  it("gives a paper with no primary tags an empty state, not an empty chart", async () => {
    const untagged = {
      paper_id: "p-csat-2022",
      year: 2022,
      phase_id: "phase-a",
      phase_name: "Prelims",
      paper_code: "CSAT",
      set_label: null,
      total_questions: 80,
      tagged_questions: 0,
      untagged_questions: 80,
      multi_tagged_questions: 0,
      by_subject: { [QUANT]: 0, [REASONING]: 0, [ENGLISH]: 0 },
    };
    const section = await renderSection(payload({ papers: [untagged, ...PAPERS] }));

    const note = within(section).getByTestId("csat-composition-untagged-papers");
    expect(note).toHaveTextContent("2022");
    expect(note).toHaveTextContent(/no primary topic tags yet/);

    // And it is not drawn as a bar with nothing in it.
    const chart = within(section).getByTestId("csat-subject-split-chart");
    expect(within(chart).queryByText("2022")).toBeNull();
  });

  it("renders no section at all when no CSAT paper qualifies", async () => {
    mockGet(payload({ papers: [], topics: [], subjects: [] }));
    const { container } = render(<CsatCompositionSection examSlug={UPSC} />);
    await screen.findByTestId("csat-composition-loading");
    await new Promise((r) => setTimeout(r, 0));
    expect(container.querySelector('[data-testid^="csat-composition-"]')).toBeNull();
  });

  it("renders nothing without an exam slug", () => {
    const { container } = render(<CsatCompositionSection examSlug={null} />);
    expect(container.firstChild).toBeNull();
    expect(api.get).not.toHaveBeenCalled();
  });
});

describe("the written observation", () => {
  const paras = csatAnalysis(payload());
  const prose = paras.join(" ");

  it("is roughly 180 words", () => {
    const words = prose.split(/\s+/).filter(Boolean).length;
    expect(words).toBeGreaterThan(130);
    expect(words).toBeLessThan(230);
  });

  it("quotes figures computed from the payload, not typed into the config", () => {
    expect(prose).toContain("40 and 46");
    expect(prose).toContain("44 distinct topics");
    expect(prose).toContain("315");
    expect(prose).toContain("16, 8, 16, 8");
    expect(prose).toContain("48 of 170");
    expect(prose).toContain("33 of 67");
  });

  it("names the three topics carrying a third of the corpus", () => {
    expect(prose).toContain("LCM/HCF and divisibility (48)");
    expect(prose).toContain("Statement and assumption (33)");
    expect(prose).toContain("Data sufficiency (25)");
  });

  it("observes the corpus without advising anyone about it", () => {
    // No second person, no imperative, no ordering of what to study, and no
    // claim about a future paper. This is the line that makes the section
    // publishable: it reports what four papers contained and stops there.
    expect(prose).not.toMatch(/\b(you|your|candidates should|aspirants should)\b/i);
    expect(prose).not.toMatch(/\b(should|must|focus on|prioriti[sz]e|start with|revise)\b/i);
    expect(prose).not.toMatch(/\b(expect|likely|will be asked|next year|predict)\b/i);
  });

  it("renders under the charts", async () => {
    const section = await renderSection();
    const block = within(section).getByTestId("csat-composition-analysis");
    expect(block).toHaveTextContent("LCM/HCF and divisibility");
  });
});
