/* eslint-env jest */
import React from "react";
import { render, screen, within } from "@testing-library/react";
import ExamStreamBreakdown, {
  hasStreamLevelOpportunity,
  streamOpportunity,
  isStreamSpecific,
} from "./ExamStreamBreakdown";

// A verified current-cycle payload matching the frozen backend contract.
function cyclePayload() {
  return {
    status: "conditional",
    cycles: [
      {
        cycle_id: "c1",
        cycle_name: "SEBI Grade A 2026",
        year: 2026,
        notification_date: "2026-03-12",
        cutoff_date: "2026-04-01",
        source_url: "https://sebi.gov.in/notification.pdf",
        verified_at: "2026-03-15T10:30:00Z",
        status: "conditional",
        streams: [
          { stream_id: "cs1", stream_key: "general", name: "General", status: "eligible", reasons: [], missing_fields: [] },
          { stream_id: "cs2", stream_key: "research", name: "Research", status: "conditional", reasons: [], missing_fields: ["education_percentage"] },
          { stream_id: "cs3", stream_key: "legal", name: "Legal", status: "not_eligible", reasons: ["Requires a law degree."], missing_fields: [] },
          { stream_id: "cs4", stream_key: "it", name: "IT", status: "unknown", reasons: [], missing_fields: [] },
        ],
      },
    ],
  };
}

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

test("A2 — the cycle band renders name+year, notification/cut-off dates, source link, verified date", () => {
  render(
    <ExamStreamBreakdown streams={flaggedStreams()} examStatus="eligible" cycle={cyclePayload()} />,
  );
  const entry = screen.getByTestId("cycle-entry-c1");
  const scoped = within(entry);
  expect(entry.textContent).toMatch(/SEBI Grade A 2026/);
  expect(entry.textContent).toMatch(/2026/);
  expect(scoped.getByTestId("cycle-notified").textContent).toMatch(/Notified 12 Mar 2026/);
  expect(scoped.getByTestId("cycle-cutoff").textContent).toMatch(/Cut-off 1 Apr 2026/);
  const link = scoped.getByTestId("cycle-source-link");
  expect(link.getAttribute("href")).toBe("https://sebi.gov.in/notification.pdf");
  expect(link.getAttribute("rel")).toBe("noopener noreferrer");
  expect(link.getAttribute("target")).toBe("_blank");
  expect(link.textContent).toMatch(/Official notification/i);
  expect(scoped.getByTestId("cycle-verified").textContent).toMatch(/Verified 15 Mar 2026/);
});

test("A2 — each cycle's streams are grouped by all four statuses, independently of baseline", () => {
  render(<ExamStreamBreakdown streams={[]} examStatus="unknown" cycle={cyclePayload()} />);
  // Scope to the cycle entry so the baseline band (absent here anyway) can never
  // be mistaken for the current-cycle grouping.
  const scoped = within(screen.getByTestId("cycle-entry-c1"));
  expect(scoped.getByTestId("stream-group-eligible").textContent).toMatch(/General/);
  const conditional = scoped.getByTestId("stream-group-conditional");
  expect(conditional.textContent).toMatch(/Research/);
  expect(conditional.textContent).toMatch(/marks percentage/); // missing_fields surfaced
  const notEligible = scoped.getByTestId("stream-group-not_eligible");
  expect(notEligible.textContent).toMatch(/Legal/);
  expect(notEligible.textContent).toMatch(/law degree/i); // reason surfaced
  expect(scoped.getByTestId("stream-group-unknown").textContent).toMatch(/IT/);
});

test("A2 — cycle band never substitutes baseline eligibility for current-cycle eligibility", () => {
  // Baseline says General is eligible; the cycle says General is NOT eligible.
  const cycle = {
    status: "not_eligible",
    cycles: [
      {
        cycle_id: "cx",
        cycle_name: "2027 Cycle",
        year: 2027,
        notification_date: null,
        cutoff_date: null,
        source_url: null,
        verified_at: null,
        status: "not_eligible",
        streams: [
          { stream_id: "g", stream_key: "general", name: "General", status: "not_eligible", reasons: ["Cycle-specific bar."], missing_fields: [] },
        ],
      },
    ],
  };
  render(<ExamStreamBreakdown streams={flaggedStreams()} examStatus="eligible" cycle={cycle} />);
  const scoped = within(screen.getByTestId("cycle-entry-cx"));
  expect(scoped.getByTestId("stream-group-not_eligible").textContent).toMatch(/General/);
  expect(scoped.queryByTestId("stream-group-eligible")).toBeNull();
  // Dates unpublished → explicit note; no source link.
  expect(scoped.getByTestId("cycle-dates-missing").textContent).toMatch(/aren't published/i);
  expect(scoped.queryByTestId("cycle-source-link")).toBeNull();
});

test("A2 — cycle=null renders the explicit empty state and NO baseline substitution", () => {
  const { getByTestId, queryByTestId } = render(
    <ExamStreamBreakdown streams={flaggedStreams()} examStatus="eligible" cycle={null} />,
  );
  expect(getByTestId("cycle-band-empty").textContent).toMatch(/No verified cycle eligibility available/i);
  expect(queryByTestId("cycle-entries")).toBeNull();
  // The baseline eligible stream must NOT leak into the cycle band.
  expect(within(getByTestId("provenance-band-cycle")).queryByTestId("stream-group-eligible")).toBeNull();
});

test("A2 — an empty cycles array is treated as the empty state, not a baseline fallback", () => {
  render(
    <ExamStreamBreakdown streams={flaggedStreams()} examStatus="eligible" cycle={{ status: "unknown", cycles: [] }} />,
  );
  expect(screen.getByTestId("cycle-band-empty")).toBeTruthy();
  expect(screen.queryByTestId("cycle-entries")).toBeNull();
});

test("A2 — streamless baseline still shows the cycle band when cycle is present", () => {
  render(<ExamStreamBreakdown streams={[]} examStatus="unknown" cycle={cyclePayload()} />);
  // Not the streamless early-return — the cycle band is rendered.
  expect(screen.queryByTestId("no-stream-identity")).toBeNull();
  expect(screen.getByTestId("cycle-entry-c1")).toBeTruthy();
  expect(screen.getByTestId("baseline-no-streams")).toBeTruthy();
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
