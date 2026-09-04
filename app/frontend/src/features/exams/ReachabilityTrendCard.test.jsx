import React from "react";
import { render, screen, within } from "@testing-library/react";

// Recharts needs a measured container, which jsdom never gives it. Stub the
// responsive wrapper to a fixed box so the SVG actually renders; everything
// asserted below is either DOM text or a labelled element, never chart geometry.
jest.mock("recharts", () => {
  const actual = jest.requireActual("recharts");
  const mockReact = jest.requireActual("react");
  return {
    ...actual,
    ResponsiveContainer: ({ children }) =>
      mockReact.createElement(
        "div",
        { style: { width: 800, height: 288 } },
        mockReact.cloneElement(children, { width: 800, height: 288 })
      ),
  };
});

jest.mock("../../lib/api", () => ({ api: { get: jest.fn() } }));

import { api } from "../../lib/api";
import ReachabilityTrendCard from "./ReachabilityTrendCard";
import { reachabilityCopyFor } from "./reachabilityConfig";

const UPSC = "upsc-cse";

// The nine assessed UPSC Prelims GS Paper I papers, as the endpoint returns
// them: eight from phase 715de35f… plus 2026 from 6566d50e…, and 2025 — the
// paper tagged on 2026-09-04 that the old hardcoded config never showed.
const NINE_PAPERS = [
  { year: 2018, easy: 39, medium: 45, hard: 16 },
  { year: 2019, easy: 22, medium: 59, hard: 19 },
  { year: 2020, easy: 18, medium: 50, hard: 32 },
  { year: 2021, easy: 18, medium: 54, hard: 28 },
  { year: 2022, easy: 21, medium: 53, hard: 26 },
  { year: 2023, easy: 17, medium: 55, hard: 28 },
  { year: 2024, easy: 23, medium: 50, hard: 27 },
  { year: 2025, easy: 16, medium: 58, hard: 26 },
  { year: 2026, easy: 10, medium: 56, hard: 34 },
].map((p, i) => ({
  ...p,
  paper_id: `paper-${p.year}`,
  total: p.easy + p.medium + p.hard,
  phase_id: p.year === 2026 ? "6566d50e" : "715de35f",
  phase_name: "Prelims",
  paper_code: "GS-1",
  set_label: i === 7 ? "Set A" : null,
}));

function payload(papers, excluded = {}) {
  return {
    exam_id: "e-upsc",
    exam_slug: UPSC,
    verified_only: true,
    bands: ["easy", "medium", "hard"],
    papers,
    excluded: { not_assessed: 0, uniform: 0, unrecognised: 0, ...excluded },
    papers_considered: papers.length,
  };
}

function mockGet(body) {
  api.get.mockImplementation(() => Promise.resolve(body));
}

beforeEach(() => {
  api.get.mockReset();
});

describe("assessed papers", () => {
  it("renders all nine UPSC points, including the 2025 paper", async () => {
    mockGet(payload(NINE_PAPERS));
    render(<ReachabilityTrendCard examSlug={UPSC} />);

    const card = await screen.findByTestId("reachability-trend-card");
    expect(screen.queryByTestId("reachability-trend-empty")).toBeNull();
    expect(within(card).getByText(/9 assessed papers/)).toBeInTheDocument();

    // Every year has an axis tick, 2025 included — the point the old
    // eight-paper config was missing.
    NINE_PAPERS.forEach((p) => {
      expect(within(card).getAllByText(String(p.year)).length).toBeGreaterThan(0);
    });

    expect(api.get).toHaveBeenCalledWith(
      `/api/exam-intelligence/exams/${UPSC}/reachability`
    );
  });

  it("draws exactly nine points, 2018-2026, with no CSAT paper among them", async () => {
    // The defect this replaced: CSAT acquired non-uniform observed_difficulty,
    // three of its papers passed reachability eligibility, and the card read
    // "12 assessed papers" while plotting two papers at the same x-position —
    // so the line jumped vertically at 2023 and 2024. The endpoint now pins the
    // series to GS Paper I and reports what it left out.
    mockGet(payload(NINE_PAPERS, { off_subject: 3 }));
    render(<ReachabilityTrendCard examSlug={UPSC} />);
    const card = await screen.findByTestId("reachability-trend-card");

    expect(within(card).getByText(/9 assessed papers/)).toBeInTheDocument();
    expect(within(card).queryByText(/12 assessed papers/)).toBeNull();

    // The x axis carries one tick per plotted paper, so a twelfth paper shows
    // up here — as a twelfth tick, and as a duplicate of a year already on the
    // axis. Nine ticks, 2018 through 2026, no repeats.
    const ticks = Array.from(
      card.querySelectorAll(".recharts-xAxis .recharts-cartesian-axis-tick-value")
    ).map((t) => t.textContent);
    expect(ticks).toEqual([
      "2018",
      "2019",
      "2020",
      "2021",
      "2022",
      "2023",
      "2024",
      "2025",
      "2026",
    ]);
    expect(new Set(ticks).size).toBe(ticks.length);
    // One line per band, no more.
    expect(card.querySelectorAll(".recharts-line-curve")).toHaveLength(3);
    expect(within(card).queryByText(/CSAT/i)).toBeNull();
  });

  it("plots the years in ascending order, so the chart reads as a trend", async () => {
    mockGet(payload(NINE_PAPERS));
    render(<ReachabilityTrendCard examSlug={UPSC} />);
    await screen.findByTestId("reachability-trend-card");

    const years = NINE_PAPERS.map((p) => p.year);
    expect(years).toEqual([...years].sort((a, b) => a - b));
  });

  it("holds no counts in the frontend config", () => {
    const copy = reachabilityCopyFor(UPSC);
    expect(copy.papers).toBeUndefined();
    const serialised = JSON.stringify(copy);
    // The band counts used to live here. If any reappears, this notices.
    expect(serialised).not.toMatch(/"easy":\s*\d/);
    expect(serialised).not.toMatch(/"hard":\s*\d/);
  });

  it("labels the bands with the stored enum, not a display mapping", async () => {
    mockGet(payload(NINE_PAPERS));
    render(<ReachabilityTrendCard examSlug={UPSC} />);
    const card = await screen.findByTestId("reachability-trend-card");
    ["Easy", "Medium", "Hard"].forEach((label) => {
      expect(within(card).getAllByText(label).length).toBeGreaterThan(0);
    });
  });

  it("keeps the measure line and provenance visible whenever a chart renders", async () => {
    mockGet(payload(NINE_PAPERS));
    render(<ReachabilityTrendCard examSlug={UPSC} />);
    await screen.findByTestId("reachability-trend-card");
    expect(screen.getByTestId("reachability-measure-line")).toBeInTheDocument();
    expect(screen.getByTestId("reachability-provenance")).toBeInTheDocument();
  });

  it("flags prose written against a different number of papers", async () => {
    // The prose is editorial and quotes figures. If a tenth paper lands, the
    // sentences under the chart are stale and the card must say so rather than
    // sit quietly under fresh counts.
    mockGet(payload(NINE_PAPERS.slice(0, 8)));
    const stale = render(<ReachabilityTrendCard examSlug={UPSC} />);
    await screen.findByTestId("reachability-trend-card");
    expect(screen.getByTestId("reachability-analysis-stale")).toBeInTheDocument();
    stale.unmount();

    api.get.mockReset();
    mockGet(payload(NINE_PAPERS));
    render(<ReachabilityTrendCard examSlug={UPSC} />);
    await screen.findByTestId("reachability-trend-card");
    expect(screen.queryByTestId("reachability-analysis-stale")).toBeNull();
  });
});

describe("ineligible corpora render the empty state, never a chart", () => {
  it("renders the empty state when every paper is unassessed", async () => {
    mockGet(payload([], { not_assessed: 4 }));
    render(<ReachabilityTrendCard examSlug="upsc-cse-mains" />);

    const empty = await screen.findByTestId("reachability-trend-empty");
    expect(screen.queryByTestId("reachability-trend-card")).toBeNull();
    expect(screen.queryByTestId("reachability-chart")).toBeNull();
    expect(empty).toHaveTextContent(/not yet been read against the reachability rubric/i);
  });

  it("says so specifically when the papers are assessed-looking but uniform", async () => {
    // The CSAT archive: 221 questions, every one 'medium' — the August 2026
    // bulk-import default, not a judgement. Charting it would show a flat
    // Medium line at 100 and read as a finding.
    mockGet(payload([], { uniform: 3 }));
    render(<ReachabilityTrendCard examSlug="upsc-cse-csat" />);

    const empty = await screen.findByTestId("reachability-trend-empty");
    expect(screen.queryByTestId("reachability-chart")).toBeNull();
    expect(empty).toHaveTextContent(/single difficulty value/i);
  });

  it("renders nothing at all without an exam slug", () => {
    const { container } = render(<ReachabilityTrendCard />);
    expect(container).toBeEmptyDOMElement();
    expect(api.get).not.toHaveBeenCalled();
  });
});

describe("band copy", () => {
  it("says Hard is NOT REACHABLE, never 'difficult'", () => {
    const copy = reachabilityCopyFor(UPSC);
    expect(copy.bandCopy.hard.toLowerCase()).toContain("not reachable");
    expect(copy.bandCopy.hard.toLowerCase()).not.toContain("difficult");
  });

  it("gives an exam with no editorial the same guarantee", () => {
    // Eligibility is computed now, so an exam can become eligible before
    // anyone writes copy for it. It must not fall back to bare labels.
    const copy = reachabilityCopyFor("some-exam-nobody-has-written-copy-for");
    expect(copy.bandCopy.hard.toLowerCase()).toContain("not reachable");
    expect(copy.bandCopy.easy).toBeTruthy();
    expect(copy.bandCopy.medium).toBeTruthy();
  });

  it("carries every band's meaning behind an info button", async () => {
    mockGet(payload(NINE_PAPERS));
    render(<ReachabilityTrendCard examSlug={UPSC} />);
    await screen.findByTestId("reachability-trend-card");
    ["easy", "medium", "hard"].forEach((band) => {
      expect(screen.getByTestId(`reachability-info-${band}`)).toBeInTheDocument();
    });
  });
});

describe("analysis prose", () => {
  const paragraphs = reachabilityCopyFor(UPSC).analysis.join(" ");

  it("describes all nine papers", () => {
    expect(paragraphs).toMatch(/nine papers/i);
    expect(reachabilityCopyFor(UPSC).analysisPaperCount).toBe(9);
  });

  it("states the movement as Easy converting into Hard", () => {
    expect(paragraphs).toMatch(/39 in 2018/);
    expect(paragraphs).toMatch(/10 in 2026/);
    expect(paragraphs).toMatch(/roughly doubled/i);
    expect(paragraphs).toMatch(/40 to 45 net/i);
    expect(paragraphs).toMatch(/about 72/i);
  });

  it("contains no imperative study advice", () => {
    // The line between "here is what the corpus shows" and "here is what you
    // should do about it" is what makes this publishable at all.
    const banned = [
      /\byou\b/i,
      /\byour\b/i,
      /\bshould\b/i,
      /\bmust\b/i,
      /\bfocus on\b/i,
      /\bskip\b/i,
      /\bprioriti[sz]e\b/i,
      /\battempt\s+(?:all|only|the)\b/i,
      /\bstudy\b/i,
      /\brevise\b/i,
      /\brecommend/i,
      /\bstrategy\b/i,
      /\bmake sure\b/i,
      /\bavoid\b/i,
      /\bpractice\b/i,
      /\bread\s+(?:the|more)\b/i,
      /\bNCERT\b/,
    ];
    banned.forEach((re) => expect(paragraphs).not.toMatch(re));
  });

  it("renders that prose under the chart", async () => {
    mockGet(payload(NINE_PAPERS));
    render(<ReachabilityTrendCard examSlug={UPSC} />);
    await screen.findByTestId("reachability-trend-card");
    expect(screen.getByTestId("reachability-analysis")).toBeInTheDocument();
  });
});
