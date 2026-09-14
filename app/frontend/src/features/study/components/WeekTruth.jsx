import React from "react";
import PropTypes from "prop-types";

/**
 * What actually happened this week — only where a real number exists.
 *
 * This replaces the dark "Truth panel · week" card, which listed four fixed
 * rows whatever the data said. Two of them could never be true: it read
 * `completed_tasks` / `planned_tasks` and `backlog_count`, and
 * `/api/study/weekly-review` returns `tasks_completed`, `tasks_planned` and
 * `backlog_end` — so every user saw "0 / 0" and "No backlog telemetry"
 * regardless of their week. A third called `.join()` on `mock_trend`, which is
 * a list of objects, and printed "[object Object]".
 *
 * The rule here is the opposite of that panel's: a row exists only when its
 * value is real. A missing value is an absent row, never a zero and never
 * "Not available yet" — and when every row is missing, the whole section
 * renders nothing rather than an empty frame.
 */
function pct(value) {
  return `${Math.round(value * 100)}%`;
}

export const NO_MOCK_SCORES = "No mocks yet";

/**
 * Mock percentages as a plain list, or ``NO_MOCK_SCORES``.
 *
 * `mock_trend` rows are `{id, name, percentage}` from
 * `weekly_review._mock_trend_history`. Joining them printed
 * "[object Object] · [object Object]" (PLAN-BUG-02 F1); this reads the one
 * field an aspirant can use, and names the gap rather than rendering it.
 */
export function mockTrendLabel(trend) {
  const scores = (Array.isArray(trend) ? trend : [])
    .map((m) => (typeof m === "number" ? m : m && m.percentage))
    .filter((v) => typeof v === "number" && Number.isFinite(v));
  return scores.length ? scores.map((v) => `${v}%`).join(" · ") : NO_MOCK_SCORES;
}

export function weekTruthLines(review) {
  const r = review || {};
  const lines = [];

  const planned = Number(r.tasks_planned || 0);
  if (planned > 0) {
    lines.push({
      key: "blocks",
      text: `You finished ${Number(r.tasks_completed || 0)} of ${planned} blocks this week.`,
    });
  }

  const mocks = Number(r.mocks_taken || 0);
  if (mocks > 0) {
    // `mock_trend` is a list of {id, name, percentage} rows — never strings.
    // `mockTrendLabel` reads the one field that means something and says so
    // plainly when none of them carries a score (PLAN-BUG-02 F1).
    const scores = mockTrendLabel(r.mock_trend);
    lines.push({
      key: "mocks",
      text:
        scores === NO_MOCK_SCORES
          ? `You took ${mocks} mock${mocks === 1 ? "" : "s"}.`
          : `You took ${mocks} mock${mocks === 1 ? "" : "s"}: ${scores}.`,
    });
  }

  if (r.backlog_end != null) {
    const n = Number(r.backlog_end);
    lines.push({
      key: "backlog",
      text:
        n === 0
          ? "Nothing is left over from earlier days."
          : `${n} block${n === 1 ? "" : "s"} from earlier days ${n === 1 ? "is" : "are"} still waiting.`,
    });
  }

  if (r.revision_coverage != null) {
    lines.push({
      key: "revision",
      text: `You got through ${pct(r.revision_coverage)} of the revision you had scheduled.`,
    });
  }

  const correction = (Array.isArray(r.corrections) ? r.corrections : [])[0];
  if (correction) lines.push({ key: "correction", text: correction });

  return lines;
}

export default function WeekTruth({ review }) {
  const lines = weekTruthLines(review);
  if (!lines.length) return null;

  return (
    <section
      data-testid="week-truth"
      className="rounded-xl border border-[#E7DECB] bg-white/60 px-6 py-5"
    >
      <h2 className="font-heading text-[18px] leading-tight text-[#2E2218]">
        How this week went
      </h2>
      <ul className="mt-3 space-y-2">
        {lines.map((l) => (
          <li
            key={l.key}
            data-testid={`week-truth-${l.key}`}
            className="text-[13px] leading-relaxed text-[#2E2218]"
          >
            {l.text}
          </li>
        ))}
      </ul>
    </section>
  );
}

WeekTruth.propTypes = {
  review: PropTypes.shape({
    tasks_completed: PropTypes.number,
    tasks_planned: PropTypes.number,
    mocks_taken: PropTypes.number,
    mock_trend: PropTypes.array,
    backlog_end: PropTypes.number,
    revision_coverage: PropTypes.number,
    corrections: PropTypes.array,
  }),
};
