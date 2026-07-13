import React from "react";
import PropTypes from "prop-types";
import { Eyebrow, Pill } from "../../shared/ui/studyos";
import { humanFieldList } from "./eligibilityFields";

/* ExamStreamBreakdown — the per-exam streams[] view for the Regulatory Exam
 * Compass (contract §8.1), rendered inside the existing Eligibility area.
 *
 * Provenance without a backend flag (checkpost PR #975). PR #973 makes a stream
 * with no stream-specific rule MIRROR the exam-wide common verdict. So a stream
 * whose verdict DIVERGES from the exam-wide verdict must have its own rules —
 * that is derivable from the payload that exists today (status + the exam-wide
 * status), no `has_stream_specific_rules` field required. When that field is
 * present it is used authoritatively; otherwise divergence decides.
 *   • Divergent stream → a real stream-specific verdict.
 *   • Same-as-exam stream → "matches the exam-wide baseline" (may be inherited);
 *     never asserted as an independent stream verdict.
 *
 * Other trust rules:
 *   • Unknown streams stay visible in a "Not evaluated" group (never hidden).
 *   • The current-cycle band makes no claim about cycle state — the payload has
 *     no cycle data, so it neither asserts an open cycle nor that baseline
 *     applies until one opens.
 *   • Streamless exams get an explicit no-stream-identity state (not a silent
 *     null), so the surface never just disappears.
 */

const STATUS_TONE = { eligible: "sage", conditional: "amber", not_eligible: "rose", unknown: "outline" };
const GROUPS = [
  { status: "eligible", label: "Eligible" },
  { status: "conditional", label: "Conditional" },
  { status: "not_eligible", label: "Not eligible" },
  { status: "unknown", label: "Not evaluated" },
];

function streamLabel(stream) {
  return stream.name || stream.stream_key || "Stream";
}

function streamKey(stream) {
  return stream.stream_id || stream.stream_key || streamLabel(stream);
}

// A stream is stream-specific if the backend says so, else if its verdict
// diverges from the exam-wide verdict (an inherited stream would match it).
export function isStreamSpecific(stream, examStatus) {
  if (typeof stream.has_stream_specific_rules === "boolean") {
    return stream.has_stream_specific_rules;
  }
  return examStatus != null && stream.status !== examStatus;
}

export function specificStreams(exam, examStatus) {
  const streams = Array.isArray(exam?.streams) ? exam.streams : [];
  return streams.filter((s) => isStreamSpecific(s, examStatus));
}

// Finding 1: a stream-specific eligible/conditional verdict that the exam-wide
// bucket would otherwise hide. Split by status so the caller can label honestly
// (an eligible stream and a conditional stream are NOT the same claim).
export function streamOpportunity(exam, examStatus) {
  const specific = specificStreams(exam, examStatus);
  return {
    eligible: specific.filter((s) => s.status === "eligible"),
    conditional: specific.filter((s) => s.status === "conditional"),
  };
}

export function hasStreamLevelOpportunity(exam, examStatus) {
  const { eligible, conditional } = streamOpportunity(exam, examStatus);
  return eligible.length > 0 || conditional.length > 0;
}

function streamNote(stream, status) {
  const missing = Array.isArray(stream.missing_fields) ? stream.missing_fields : [];
  const reason = Array.isArray(stream.reasons) && stream.reasons.length ? stream.reasons[0] : null;
  if (status === "conditional" && missing.length) return `add ${humanFieldList(missing)}`;
  if (status === "not_eligible" && reason) return reason;
  if (status === "unknown") return "verified rules missing";
  return null;
}

function StreamGroup({ label, status, streams }) {
  if (!streams.length) return null;
  const tone = STATUS_TONE[status] || "outline";
  return (
    <div data-testid={`stream-group-${status}`} className="space-y-1.5">
      <div className="num-mono uppercase text-[9.5px] tracking-[0.18em] text-clay-700">{label}</div>
      <ul className="space-y-1">
        {streams.map((s) => {
          const note = streamNote(s, status);
          return (
            <li
              key={streamKey(s)}
              data-testid={`stream-${status}-${streamKey(s)}`}
              className="flex items-center gap-2 flex-wrap"
            >
              <Pill tone={tone}>{streamLabel(s)}</Pill>
              {note && <span className="text-[11.5px] text-clay-700">{note}</span>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

StreamGroup.propTypes = {
  label: PropTypes.string.isRequired,
  status: PropTypes.oneOf(["eligible", "conditional", "not_eligible", "unknown"]).isRequired,
  streams: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default function ExamStreamBreakdown({ streams, examName, examStatus }) {
  const list = Array.isArray(streams) ? streams : [];

  // Finding 5 — explicit no-stream-identity state instead of a silent null, so
  // the expanded detail never just vanishes for a streamless exam.
  if (list.length === 0) {
    return (
      <div
        data-testid="no-stream-identity"
        className="mt-3 pt-3 border-t border-[#E7DECB] text-[11.5px] text-clay-600"
      >
        This exam has no separate streams — the exam-wide verdict above applies.
      </div>
    );
  }

  const specific = list.filter((s) => isStreamSpecific(s, examStatus));
  const matchesBaseline = list.filter((s) => !isStreamSpecific(s, examStatus));

  return (
    <div
      data-testid="exam-stream-breakdown"
      className="mt-3 pt-3 border-t border-[#E7DECB] space-y-3"
    >
      {/* Band 1 — Baseline provenance */}
      <section data-testid="provenance-band-baseline" aria-label="Baseline stream eligibility">
        <div className="flex items-center gap-2">
          <Eyebrow>Streams · baseline</Eyebrow>
          <Pill tone="outline">Baseline</Pill>
        </div>
        <p className="text-[11.5px] text-clay-700 mt-1">
          Verdicts below are from each stream's own rules
          {examName ? ` for ${examName}` : ""}. Not confirmed against any cycle.
        </p>

        {specific.length ? (
          <div className="mt-2 space-y-2.5" data-testid="stream-specific-verdicts">
            {GROUPS.map((g) => (
              <StreamGroup
                key={g.status}
                label={g.label}
                status={g.status}
                streams={specific.filter((s) => s.status === g.status)}
              />
            ))}
          </div>
        ) : (
          <p className="text-[11.5px] text-clay-600 mt-2" data-testid="stream-no-specific">
            No stream diverges from the exam-wide verdict yet.
          </p>
        )}

        {matchesBaseline.length > 0 && (
          <div className="mt-2.5" data-testid="stream-inherited">
            <div className="num-mono uppercase text-[9.5px] tracking-[0.18em] text-clay-700">
              Matches the exam-wide baseline
            </div>
            <p className="text-[11.5px] text-clay-600 mt-1">
              Same as the exam-level verdict (no divergent stream rule):{" "}
              {matchesBaseline.map(streamLabel).join(", ")}.
            </p>
          </div>
        )}
      </section>

      {/* Band 2 — Current-cycle provenance (makes no claim about cycle state) */}
      <section data-testid="provenance-band-cycle" aria-label="Current-cycle stream eligibility">
        <div className="flex items-center gap-2">
          <Eyebrow>Streams · current cycle</Eyebrow>
          <Pill tone="dusk">Per cycle</Pill>
        </div>
        <p className="text-[11.5px] text-clay-700 mt-1" data-testid="cycle-band-pending">
          Current-cycle eligibility isn't evaluated in this view. Check the official notification
          for any current cycle, if available, to confirm.
        </p>
      </section>
    </div>
  );
}

ExamStreamBreakdown.propTypes = {
  streams: PropTypes.arrayOf(
    PropTypes.shape({
      stream_id: PropTypes.string,
      stream_key: PropTypes.string,
      name: PropTypes.string,
      status: PropTypes.oneOf(["eligible", "conditional", "not_eligible", "unknown"]),
      reasons: PropTypes.arrayOf(PropTypes.string),
      missing_fields: PropTypes.arrayOf(PropTypes.string),
      has_stream_specific_rules: PropTypes.bool,
    }),
  ),
  examName: PropTypes.string,
  // The exam-wide verdict, used to detect stream divergence when the backend
  // omits `has_stream_specific_rules`.
  examStatus: PropTypes.oneOf(["eligible", "conditional", "not_eligible", "unknown"]),
};

ExamStreamBreakdown.defaultProps = {
  streams: [],
  examName: undefined,
  examStatus: undefined,
};
