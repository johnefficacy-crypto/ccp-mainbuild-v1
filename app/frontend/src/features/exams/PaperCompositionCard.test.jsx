import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";

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
import PaperCompositionCard from "./PaperCompositionCard";

// A microtopic-tagged paper: the nine GS-I papers look like this.
const MICROTOPIC_PAPER = {
  paper_id: "p-gs1-2025",
  found: true,
  verified_only: true,
  tag_level: "microtopic",
  total_questions: 100,
  tagged_questions: 100,
  untagged_questions: 0,
  multi_tagged_questions: 0,
  groups: [
    {
      topic_id: "t-polity",
      topic_name: "Polity",
      questions: 24,
      children: [
        { topic_id: "m-fr", topic_name: "Fundamental Rights", questions: 14 },
        { topic_id: "m-parl", topic_name: "Parliament", questions: 10 },
      ],
    },
    {
      topic_id: "t-eco",
      topic_name: "Economy",
      questions: 18,
      children: [{ topic_id: "m-fiscal", topic_name: "Fiscal policy", questions: 18 }],
    },
  ],
};

// 2025 CSAT: eighty tags, every one a TOP-LEVEL topic. Same shape on screen,
// different meaning — which is why the card has to say which it is showing.
const TOPIC_PAPER = {
  paper_id: "p-csat-2025",
  found: true,
  verified_only: true,
  tag_level: "topic",
  total_questions: 80,
  tagged_questions: 80,
  untagged_questions: 0,
  multi_tagged_questions: 0,
  groups: [
    { topic_id: "t-compre", topic_name: "Comprehension", questions: 45, children: [] },
    { topic_id: "t-reason", topic_name: "Reasoning", questions: 35, children: [] },
  ],
};

const UNTAGGED_PAPER = {
  paper_id: "p-mains-2024",
  found: true,
  verified_only: true,
  tag_level: null,
  total_questions: 20,
  tagged_questions: 0,
  untagged_questions: 20,
  multi_tagged_questions: 0,
  groups: [],
};

beforeEach(() => api.get.mockReset());

function mount(body, props = {}) {
  api.get.mockResolvedValue(body);
  return render(<PaperCompositionCard paperId={body.paper_id} {...props} />);
}

describe("tag level is always stated", () => {
  it("says microtopic when the tags sit at microtopic level", async () => {
    mount(MICROTOPIC_PAPER);
    const note = await screen.findByTestId("paper-composition-tag-level");
    expect(note).toHaveTextContent(/microtopic level/i);
    expect(note).toHaveTextContent(/grouped under their parent topic/i);
  });

  it("says top-level, and that the two are not comparable, for CSAT", async () => {
    mount(TOPIC_PAPER);
    const note = await screen.findByTestId("paper-composition-tag-level");
    expect(note).toHaveTextContent(/top-level topic only/i);
    expect(note).toHaveTextContent(/not\s+directly comparable/i);
    // It may mention microtopics to say what this is NOT; it must never
    // claim the tags sit at that level.
    expect(note).not.toHaveTextContent(/tagged at microtopic level/i);
  });

  it("reports the tagged/untagged split", async () => {
    mount({ ...MICROTOPIC_PAPER, tagged_questions: 90, untagged_questions: 10 });
    const counts = await screen.findByTestId("paper-composition-counts");
    expect(counts).toHaveTextContent("90 of 100");
    expect(counts).toHaveTextContent("10 untagged");
  });
});

describe("grouping", () => {
  it("shows the parent breakdown by default, microtopics hidden", async () => {
    mount(MICROTOPIC_PAPER);
    const card = await screen.findByTestId("paper-composition-card");
    expect(within(card).getAllByText("Polity").length).toBeGreaterThan(0);
    expect(within(card).getAllByText("Economy").length).toBeGreaterThan(0);
    expect(within(card).queryByText(/Fundamental Rights/)).toBeNull();
  });

  it("expands a parent to its microtopics, and collapses again", async () => {
    mount(MICROTOPIC_PAPER);
    const toggle = await screen.findByTestId("paper-composition-expand-t-polity");
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const card = screen.getByTestId("paper-composition-card");
    expect(within(card).getAllByText(/Fundamental Rights/).length).toBeGreaterThan(0);
    expect(within(card).getAllByText(/Parliament/).length).toBeGreaterThan(0);
    // The other parent stays collapsed — expansion is per topic.
    expect(within(card).queryByText(/Fiscal policy/)).toBeNull();

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(within(card).queryByText(/Fundamental Rights/)).toBeNull();
  });

  it("expands and collapses every parent at once", async () => {
    mount(MICROTOPIC_PAPER);
    const all = await screen.findByTestId("paper-composition-toggle-all");
    fireEvent.click(all);
    const card = screen.getByTestId("paper-composition-card");
    expect(within(card).getAllByText(/Fundamental Rights/).length).toBeGreaterThan(0);
    expect(within(card).getAllByText(/Fiscal policy/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByTestId("paper-composition-toggle-all"));
    expect(within(card).queryByText(/Fiscal policy/)).toBeNull();
  });

  it("offers no expansion for a top-level-tagged paper", async () => {
    mount(TOPIC_PAPER);
    await screen.findByTestId("paper-composition-card");
    expect(screen.queryByTestId("paper-composition-toggle-all")).toBeNull();
    expect(screen.queryByTestId("paper-composition-expand-t-compre")).toBeNull();
  });
});

describe("bars, not a pie", () => {
  it("draws a horizontal bar chart", async () => {
    mount(MICROTOPIC_PAPER);
    const chart = await screen.findByTestId("paper-composition-chart");
    // A pie would render <path> sectors and no axes. Bars render rects under a
    // category axis.
    expect(chart.querySelectorAll(".recharts-bar-rectangle").length).toBeGreaterThan(0);
    expect(chart.querySelector(".recharts-yAxis")).toBeTruthy();
  });
});

describe("empty states", () => {
  it("renders the empty state for a paper with no tags", async () => {
    mount(UNTAGGED_PAPER, { paperLabel: "2024 · Mains · GS-1" });
    const empty = await screen.findByTestId("paper-composition-empty");
    expect(empty).toHaveTextContent(/no verified topic tags yet/i);
    expect(empty).toHaveTextContent("2024 · Mains · GS-1");
    expect(screen.queryByTestId("paper-composition-chart")).toBeNull();
  });

  it("renders nothing without a paper id", () => {
    const { container } = render(<PaperCompositionCard />);
    expect(container).toBeEmptyDOMElement();
    expect(api.get).not.toHaveBeenCalled();
  });

  it("surfaces a read failure instead of an empty chart", async () => {
    api.get.mockRejectedValue(new Error("boom"));
    render(<PaperCompositionCard paperId="p-1" />);
    expect(await screen.findByTestId("paper-composition-error")).toHaveTextContent(
      "boom"
    );
  });
});
