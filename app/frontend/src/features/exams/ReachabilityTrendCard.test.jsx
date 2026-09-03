import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";

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

import ReachabilityTrendCard from "./ReachabilityTrendCard";
import { reachabilityConfigFor } from "./reachabilityConfig";

const UPSC = "upsc-cse";

// The 2026-09-02 tagging pass over UPSC Prelims GS Paper I. Duplicated here on
// purpose: if the config drifts, this fixture is what notices.
const EXPECTED = [
  { year: 2018, easy: 39, medium: 45, hard: 16 },
  { year: 2019, easy: 22, medium: 59, hard: 19 },
  { year: 2020, easy: 18, medium: 50, hard: 32 },
  { year: 2021, easy: 18, medium: 54, hard: 28 },
  { year: 2022, easy: 21, medium: 53, hard: 26 },
  { year: 2023, easy: 17, medium: 55, hard: 28 },
  { year: 2024, easy: 23, medium: 50, hard: 27 },
  { year: 2026, easy: 10, medium: 56, hard: 34 },
];

describe("eligible papers", () => {
  it("renders the eight judged UPSC papers with their counts", () => {
    const config = reachabilityConfigFor(UPSC);
    expect(config).not.toBeNull();
    expect(config.papers).toEqual(EXPECTED);

    // Ascending left to right — the chart reads as a trend, not a scatter.
    const years = config.papers.map((p) => p.year);
    expect(years).toEqual([...years].sort((a, b) => a - b));

    render(<ReachabilityTrendCard examId={UPSC} />);
    expect(screen.getByTestId("reachability-trend-card")).toBeInTheDocument();
    expect(screen.queryByTestId("reachability-trend-empty")).toBeNull();
    expect(screen.getByText(/8 judged papers/)).toBeInTheDocument();
  });

  it("labels the bands with the stored enum, not a display mapping", () => {
    render(<ReachabilityTrendCard examId={UPSC} />);
    const bands = screen.getByTestId("reachability-trend-card");
    ["Easy", "Medium", "Hard"].forEach((label) => {
      expect(within(bands).getAllByText(label).length).toBeGreaterThan(0);
    });
  });

  it("keeps the measure line visible beside the chart", () => {
    render(<ReachabilityTrendCard examId={UPSC} />);
    expect(screen.getByTestId("reachability-measure-line")).toHaveTextContent(
      /not how many candidates answered it correctly/i
    );
  });

  it("always shows provenance when a chart renders", () => {
    render(<ReachabilityTrendCard examId={UPSC} />);
    const prov = screen.getByTestId("reachability-provenance");
    expect(prov).toHaveTextContent(/fixed rubric/i);
    expect(prov).toHaveTextContent(
      "docs/operator-validation/2026-08-31-upsc-prelims-corpus-findings.md"
    );
  });

  it("shows the 2018 reliability caveat", () => {
    render(<ReachabilityTrendCard examId={UPSC} />);
    expect(screen.getByTestId("reachability-caveat")).toHaveTextContent(
      /2018.*least reliable/i
    );
  });
});

describe("empty state", () => {
  it("renders the pending state for an exam with no judged papers", () => {
    render(<ReachabilityTrendCard examId="ssc-cgl" />);
    const empty = screen.getByTestId("reachability-trend-empty");
    expect(empty).toHaveTextContent(/difficulty assessment is pending/i);
    // Never a chart of bulk-defaulted rows.
    expect(screen.queryByTestId("reachability-trend-card")).toBeNull();
    expect(screen.queryByTestId("reachability-chart")).toBeNull();
  });

  it("renders the pending state when no exam is supplied", () => {
    render(<ReachabilityTrendCard />);
    expect(screen.getByTestId("reachability-trend-empty")).toBeInTheDocument();
  });
});

describe("band info copy", () => {
  it("describes Hard as unreachable, never as difficult", () => {
    render(<ReachabilityTrendCard examId={UPSC} />);
    fireEvent.click(screen.getByTestId("reachability-info-hard"));
    const copy = screen.getByTestId("reachability-info-copy-hard");
    // The whole point of the chart: Hard means no standard source reaches it,
    // not that the question is intrinsically harder.
    expect(copy).toHaveTextContent(/not reachable/i);
    expect(copy.textContent).not.toMatch(/difficult/i);
  });

  it("carries the reachability meaning for each band", () => {
    render(<ReachabilityTrendCard examId={UPSC} />);

    fireEvent.click(screen.getByTestId("reachability-info-easy"));
    expect(screen.getByTestId("reachability-info-copy-easy")).toHaveTextContent(
      /NCERT textbook/i
    );

    fireEvent.click(screen.getByTestId("reachability-info-medium"));
    expect(
      screen.getByTestId("reachability-info-copy-medium")
    ).toHaveTextContent(/reference books/i);
  });

  it("gives every info button an accessible name", () => {
    render(<ReachabilityTrendCard examId={UPSC} />);
    ["Easy", "Medium", "Hard"].forEach((label) => {
      expect(
        screen.getByRole("button", { name: `What ${label} means` })
      ).toBeInTheDocument();
    });
  });
});

describe("analysis prose", () => {
  it("reports the corpus movement", () => {
    render(<ReachabilityTrendCard examId={UPSC} />);
    const prose = screen.getByTestId("reachability-analysis");
    expect(prose).toHaveTextContent(/Medium band barely moves/i);
    expect(prose).toHaveTextContent(/40 to 45 net correct/i);
  });

  it("contains no imperative study advice", () => {
    render(<ReachabilityTrendCard examId={UPSC} />);
    const text = screen.getByTestId("reachability-analysis").textContent;

    // Second person and prescription: the prose is an observation about a
    // corpus, and must never become a study plan.
    [
      /\byou should\b/i,
      /\byou must\b/i,
      /\byou need to\b/i,
      /\bfocus on\b/i,
      /\bskip\b/i,
      /\bprioriti[sz]e\b/i,
      /\bstudy\b/i,
      /\brecommend/i,
      /\bwe advise\b/i,
      /\byour\b/i,
    ].forEach((pattern) => {
      expect(text).not.toMatch(pattern);
    });
  });
});

describe("phase scoping", () => {
  it("returns nothing rather than a partial series when scoped by phase", () => {
    // exam_phases has no unique constraint and UPSC's judged papers span two
    // phase ids, so a phase-scoped read is a silent series split. The config
    // refuses instead of returning seven of eight papers.
    expect(reachabilityConfigFor(UPSC, "715de35f")).toBeNull();
  });
});
