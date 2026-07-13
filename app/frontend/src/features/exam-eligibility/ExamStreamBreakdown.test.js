/* eslint-env jest */
import React from "react";
import { render, screen } from "@testing-library/react";
import ExamStreamBreakdown, {
  hasStreamLevelOpportunity,
  streamOpportunity,
  isStreamSpecific,
} from "./ExamStreamBreakdown";

// Streams carrying the optional PR #973 provenance flag.
function flaggedStreams() {
  return [
    { stream_id: "s1", stream_key: "general", name: "General", status: "eligible", reasons: [], missing_fields: [], has_stream_specific_rules: true },
    { stream_id: "s2", stream_key: "research", name: "Research", status: "conditional", reasons: [], missing_fields: ["education_percentage"], has_stream_specific_rules: true },
    { stream_id: "s3", stream_key: "legal", name: "Legal", status: "not_eligible", reasons: ["Requires a law degree."], missing_fields: [], has_stream_specific_rules: true },
    { stream_id: "s4", stream_key: "it", name: "IT", status: "unknown", reasons: [], missing_fields: [], has_stream_specific_rules: true },
    // Inherits the exam-wide baseline — NOT a stream-specific verdict.
    { stream_id: "s5", stream_key: "official-language", name: "Official Language", status: "eligible", reasons: [], missing_fields: [], has_stream_specific_rules: false },
  ];
}

test("finding 5 — a streamless exam gets an explicit no-stream-identity state (not a silent null)", () => {
  const empty = render(<ExamStreamBreakdown streams={[]} examStatus="eligible" />);
  expect(empty.getByTestId("no-stream-identity").textContent).toMatch(/no separate streams/i);
  empty.unmount();
  const undef = render(<ExamStreamBreakdown streams={undefined} examStatus="eligible" />);
  expect(undef.getByTestId("no-stream-identity")).toBeTruthy();
});

test("groups stream-specific verdicts into eligible / conditional / not-eligible (flag present)", () => {
  render(<ExamStreamBreakdown streams={flaggedStreams()} examName="SEBI Grade A" examStatus="eligible" />);
  expect(screen.getByTestId("stream-specific-verdicts")).toBeTruthy();
  expect(screen.getByTestId("stream-group-eligible").textContent).toMatch(/General/);
  expect(screen.getByTestId("stream-group-conditional").textContent).toMatch(/Research/);
  expect(screen.getByTestId("stream-group-not_eligible").textContent).toMatch(/Legal/);
});

test("finding 2 — a same-as-baseline stream is NOT presented as a stream verdict", () => {
  render(<ExamStreamBreakdown streams={flaggedStreams()} examStatus="eligible" />);
  expect(screen.getByTestId("stream-inherited").textContent).toMatch(/Official Language/);
  expect(screen.getByTestId("stream-group-eligible").textContent).not.toMatch(/Official Language/);
});

test("finding 4 — an unknown stream stays visible in a 'Not evaluated' group", () => {
  render(<ExamStreamBreakdown streams={flaggedStreams()} examStatus="eligible" />);
  const notEval = screen.getByTestId("stream-group-unknown");
  expect(notEval.textContent).toMatch(/IT/);
  expect(notEval.textContent).toMatch(/verified rules missing/i);
  expect(screen.getByTestId("stream-group-eligible").textContent).not.toMatch(/\bIT\b/);
});

test("conditional stream shows the missing field; not-eligible shows the reason", () => {
  render(<ExamStreamBreakdown streams={flaggedStreams()} examStatus="eligible" />);
  expect(screen.getByTestId("stream-group-conditional").textContent).toMatch(/marks percentage/);
  expect(screen.getByTestId("stream-group-not_eligible").textContent).toMatch(/law degree/i);
});

test("no flag → divergence from the exam-wide verdict marks a stream specific", () => {
  // Exam-wide unknown; General eligible diverges (specific), IT unknown matches (inherited).
  const streams = [
    { stream_id: "s1", stream_key: "general", name: "General", status: "eligible", reasons: [], missing_fields: [] },
    { stream_id: "s4", stream_key: "it", name: "IT", status: "unknown", reasons: [], missing_fields: [] },
  ];
  render(<ExamStreamBreakdown streams={streams} examStatus="unknown" />);
  expect(screen.getByTestId("stream-group-eligible").textContent).toMatch(/General/);
  expect(screen.getByTestId("stream-inherited").textContent).toMatch(/IT/);
});

test("finding 3 — the cycle band makes NO claim about cycle status", () => {
  render(<ExamStreamBreakdown streams={flaggedStreams()} examStatus="eligible" />);
  const cycle = screen.getByTestId("cycle-band-pending").textContent;
  expect(cycle).toMatch(/isn't evaluated in this view/i);
  expect(cycle).toMatch(/any current cycle/i);
  expect(cycle).not.toMatch(/the open cycle/i);
  expect(cycle).not.toMatch(/published yet/i);
  expect(cycle).not.toMatch(/applies until a cycle opens/i);
});

test("provenance helpers work off the flag when present and divergence otherwise", () => {
  // Flag authoritative.
  expect(isStreamSpecific({ status: "eligible", has_stream_specific_rules: true }, "eligible")).toBe(true);
  expect(isStreamSpecific({ status: "eligible", has_stream_specific_rules: false }, "unknown")).toBe(false);
  // No flag → divergence.
  expect(isStreamSpecific({ status: "eligible" }, "unknown")).toBe(true);
  expect(isStreamSpecific({ status: "unknown" }, "unknown")).toBe(false);

  const opp = streamOpportunity(
    { streams: [
      { status: "eligible", has_stream_specific_rules: true },
      { status: "conditional", has_stream_specific_rules: true },
    ] },
    "unknown",
  );
  expect(opp.eligible).toHaveLength(1);
  expect(opp.conditional).toHaveLength(1);
  expect(hasStreamLevelOpportunity({ streams: [{ status: "eligible" }] }, "unknown")).toBe(true);
  // A stream matching the exam-wide verdict is not an opportunity.
  expect(hasStreamLevelOpportunity({ streams: [{ status: "unknown" }] }, "unknown")).toBe(false);
  expect(hasStreamLevelOpportunity({}, "unknown")).toBe(false);
});
