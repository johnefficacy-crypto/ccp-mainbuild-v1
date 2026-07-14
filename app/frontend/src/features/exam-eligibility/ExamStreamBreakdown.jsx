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
const STATUS_LABEL = {
  eligible: "Eligible",
  conditional: "Conditional",
  not_eligible: "Not eligible",
  unknown: "Not evaluated",
};
const GROUPS = [
  { status: "eligible", label: "Eligible" },
  { status: "conditional", label: "Conditional" },
  { status: "not_eligible", label: "Not eligible" },
  { status: "unknown", label: "Not evaluated" },
];

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

// Format an ISO date ("YYYY-MM-DD") or ISO timestamp into a readable "12 Mar
// 2026". Parsed lexically (not via Date) so it is timezone-stable across
// environments and never shifts a date-only value by a day.
function formatDate(iso) {
  if (!iso) return null;
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return String(iso);
  const [, year, month, day] = m;
  const mi = parseInt(month, 10) - 1;
  const name = MONTHS[mi] || month;
  return `${parseInt(day, 10)} ${name} ${year}`;
}

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

// A single verified current-cycle entry. Reads ONLY from the cycle payload —
// never from the baseline streams/examStatus — and groups THIS cycle's streams
// independently via the shared GROUPS/StreamGroup pipeline.
function CycleEntry({ cycle }) {
  const streams = Array.isArray(cycle.streams) ? cycle.streams : [];
  const title = cycle.cycle_name || "Cycle";
  const notified = formatDate(cycle.notification_date);
  const cutoff = formatDate(cycle.cutoff_date);
  const verified = formatDate(cycle.verified_at);
  const tone = STATUS_TONE[cycle.status] || "outline";
  const statusLabel = STATUS_LABEL[cycle.status] || "Not evaluated";

  return (
    <div
      data-testid={`cycle-entry-${cycle.cycle_id}`}
      className="rounded-lg border border-[#E7DECB] bg-white/55 px-3 py-2.5 space-y-1.5"
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-semibold text-[12.5px] text-clay-900">
          {title}
          {cycle.year ? ` ${cycle.year}` : ""}
        </span>
        <Pill tone={tone}>{statusLabel}</Pill>
      </div>

      <div className="text-[11.5px] text-clay-700 flex flex-wrap gap-x-3 gap-y-0.5">
        {notified || cutoff ? (
          <>
            {notified && <span data-testid="cycle-notified">Notified {notified}</span>}
            {cutoff && <span data-testid="cycle-cutoff">Cut-off {cutoff}</span>}
          </>
        ) : (
          <span data-testid="cycle-dates-missing">Cycle dates aren't published yet.</span>
        )}
      </div>

      <div className="text-[11.5px] text-clay-700 flex flex-wrap gap-x-3 gap-y-0.5">
        {cycle.source_url && (
          <a
            href={cycle.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="link-under text-clay-900 font-semibold"
            data-testid="cycle-source-link"
          >
            Official notification
          </a>
        )}
        {verified && <span data-testid="cycle-verified">Verified {verified}</span>}
      </div>

      {streams.length ? (
        <div className="mt-1.5 space-y-2.5" data-testid="cycle-stream-verdicts">
          {GROUPS.map((g) => (
            <StreamGroup
              key={g.status}
              label={g.label}
              status={g.status}
              streams={streams.filter((s) => s.status === g.status)}
            />
          ))}
        </div>
      ) : (
        <p className="text-[11.5px] text-clay-600" data-testid="cycle-no-streams">
          No stream verdicts recorded for this cycle.
        </p>
      )}
    </div>
  );
}

CycleEntry.propTypes = {
  cycle: PropTypes.object.isRequired,
};

// Band 2 — the real current-cycle eligibility band. Renders strictly from the
// `cycle` prop. An absent or empty cycle payload yields an explicit empty state;
// it NEVER substitutes the baseline streams for current-cycle eligibility.
function CycleBand({ cycle }) {
  const cycles = Array.isArray(cycle?.cycles) ? cycle.cycles : [];
  return (
    <section data-testid="provenance-band-cycle" aria-label="Current-cycle stream eligibility">
      <div className="flex items-center gap-2">
        <Eyebrow>Streams · current cycle</Eyebrow>
        <Pill tone="dusk">Per cycle</Pill>
      </div>
      {cycles.length ? (
        <div className="mt-2 space-y-2.5" data-testid="cycle-entries">
          {cycles.map((c) => (
            <CycleEntry key={c.cycle_id} cycle={c} />
          ))}
        </div>
      ) : (
        <p className="text-[11.5px] text-clay-600 mt-1" data-testid="cycle-band-empty">
          No verified cycle eligibility available.
        </p>
      )}
    </section>
  );
}

CycleBand.propTypes = {
  cycle: PropTypes.object,
};

export default function ExamStreamBreakdown({ streams, examName, examStatus, cycle }) {
  const list = Array.isArray(streams) ? streams : [];
  const cycleEntries = Array.isArray(cycle?.cycles) ? cycle.cycles : [];

  // Finding 5 — explicit no-stream-identity state instead of a silent null, so
  // the expanded detail never just vanishes for a streamless exam. Only taken
  // when there is NEITHER a baseline stream NOR any cycle data; a cycle band is
  // never hidden merely because baseline streams are absent (requirement 6).
  if (list.length === 0 && cycleEntries.length === 0) {
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
      {list.length > 0 ? (
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
      ) : (
        <section data-testid="provenance-band-baseline" aria-label="Baseline stream eligibility">
          <div className="flex items-center gap-2">
            <Eyebrow>Streams · baseline</Eyebrow>
            <Pill tone="outline">Baseline</Pill>
          </div>
          <p className="text-[11.5px] text-clay-600 mt-1" data-testid="baseline-no-streams">
            This exam has no separate streams — the exam-wide verdict above applies.
          </p>
        </section>
      )}

      {/* Band 2 — Real current-cycle provenance (reads only from `cycle`) */}
      <CycleBand cycle={cycle} />
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
  // Additive current-cycle eligibility payload (frozen backend contract). Read
  // ONLY by Band 2; never substituted for baseline `streams`.
  cycle: PropTypes.shape({
    status: PropTypes.oneOf(["eligible", "conditional", "not_eligible", "unknown"]),
    cycles: PropTypes.arrayOf(
      PropTypes.shape({
        cycle_id: PropTypes.string,
        cycle_name: PropTypes.string,
        year: PropTypes.number,
        notification_date: PropTypes.string,
        cutoff_date: PropTypes.string,
        source_url: PropTypes.string,
        verified_at: PropTypes.string,
        status: PropTypes.oneOf(["eligible", "conditional", "not_eligible", "unknown"]),
        streams: PropTypes.arrayOf(
          PropTypes.shape({
            stream_id: PropTypes.string,
            stream_key: PropTypes.string,
            name: PropTypes.string,
            status: PropTypes.oneOf(["eligible", "conditional", "not_eligible", "unknown"]),
            reasons: PropTypes.arrayOf(PropTypes.string),
            missing_fields: PropTypes.arrayOf(PropTypes.string),
          }),
        ),
      }),
    ),
  }),
};

ExamStreamBreakdown.defaultProps = {
  streams: [],
  examName: undefined,
  examStatus: undefined,
  cycle: null,
};
