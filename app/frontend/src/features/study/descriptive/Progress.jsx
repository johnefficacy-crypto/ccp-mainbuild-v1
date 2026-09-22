import React, { useEffect, useState } from "react";

import { api } from "../../../lib/api";
import { Card, Eyebrow, StudyEmptyState } from "../../../shared/ui/studyos";

/**
 * Progress — how the answer writing is going, week by week.
 *
 * EVERY COMPARISON STATES ITS SAMPLE. ~87% of the corpus carries no marks and
 * most questions carry no word limit, so "average time vs target" is an
 * average over the subset that HAS a target. Printing it without saying how
 * many answers it covers would make eight answers and one answer look the
 * same.
 *
 * NOTHING HERE IS MACHINE-SCORED. Every number comes from the aspirant's own
 * rubric judgements and their own clock.
 */

const LABEL = {
  structure: "Structure",
  relevance: "Relevance",
  coverage: "Coverage",
  examples: "Examples",
  conclusion: "Conclusion",
  within_limit: "Within limit",
};

export function minutes(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return null;
  return `${Math.round(seconds / 60)} min`;
}

/** The "vs target" line for a week, or null when nothing in it had a target. */
export function comparisonLine(week) {
  const parts = [];
  if (week.words_sample > 0) {
    parts.push(
      `${Math.round(week.avg_words)} words against a ${Math.round(
        week.avg_word_limit,
      )}-word limit (${week.words_sample} ${
        week.words_sample === 1 ? "answer" : "answers"
      })`,
    );
  }
  if (week.time_sample > 0) {
    parts.push(
      `${minutes(week.avg_seconds)} against ${minutes(
        week.avg_target_seconds,
      )} (${week.time_sample} ${week.time_sample === 1 ? "answer" : "answers"})`,
    );
  }
  return parts.length ? parts.join(" · ") : null;
}

function weekLabel(iso) {
  const at = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(at.getTime())) return iso;
  return at.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

export default function Progress() {
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading");

  useEffect(() => {
    let live = true;
    api
      .get("/api/study/descriptive/analytics")
      .then((d) => {
        if (!live) return;
        setData(d);
        setState("ready");
      })
      .catch(() => live && setState("error"));
    return () => {
      live = false;
    };
  }, []);

  if (state === "error") {
    return (
      <Card>
        <p role="status" className="text-sm text-rose-700">
          Couldn&apos;t load your progress. Reload the page.
        </p>
      </Card>
    );
  }
  if (state === "loading") {
    return (
      <Card>
        <p role="status" className="text-sm text-clay-700">
          Adding up your answers…
        </p>
      </Card>
    );
  }
  if (!data?.submitted_total) {
    return (
      <StudyEmptyState
        icon="↗"
        title="Nothing to measure yet."
        body="Submit an answer and this fills with your own numbers — words against the limit, time against the target, and how you scored yourself."
      />
    );
  }

  const rubric = data.rubric || {};
  const weakest = data.weakest_dimensions || [];

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <Eyebrow>So far</Eyebrow>
        <h2 className="font-heading mt-1 text-[22px] leading-tight" data-testid="progress-total">
          {data.submitted_total} {data.submitted_total === 1 ? "answer" : "answers"} written
        </h2>
        <p className="mt-1 text-[12px] text-clay-700" data-testid="progress-streak">
          {data.streak_weeks > 0
            ? `${data.streak_weeks} ${
                data.streak_weeks === 1 ? "week" : "weeks"
              } in a row with at least one answer`
            : "No streak yet — one answer this week starts it."}
        </p>
      </Card>

      <Card padded={false}>
        <div className="px-7 pt-6 pb-3">
          <Eyebrow>By week</Eyebrow>
        </div>
        <div className="hairline mx-7" />
        <ul className="px-7 pb-6 pt-2">
          {data.weeks.map((week) => (
            <li key={week.week} className="border-b border-[#E7DECB] py-3 last:border-0"
                data-testid="progress-week">
              <p className="text-[13px]">
                Week of {weekLabel(week.week)} — {week.submitted}{" "}
                {week.submitted === 1 ? "answer" : "answers"}
                {week.avg_self_total !== null && week.avg_self_total !== undefined
                  ? ` · ${week.avg_self_total}/12 average`
                  : ""}
                {week.points_sample > 0
                  ? ` · ${week.avg_points_covered_pct}% points covered`
                  : ""}
              </p>
              {/* Absent, not zeroed: a week whose questions carried no marks
                  and no word limit has nothing to compare, and saying "0 min
                  against 0 min" would invent a target. */}
              {comparisonLine(week) ? (
                <p className="num-mono mt-1 text-[10.5px] text-clay-700"
                   data-testid="progress-week-comparison">
                  {comparisonLine(week)}
                </p>
              ) : (
                <p className="mt-1 text-[10.5px] text-clay-700">
                  No word limit or marks on these questions, so nothing to compare.
                </p>
              )}
            </li>
          ))}
        </ul>
      </Card>

      {data.points_covered?.sample > 0 && (
        <Card>
          <Eyebrow>Answer-structure points covered</Eyebrow>
          <h2 className="font-heading mt-1 text-[22px] leading-tight" data-testid="progress-points-covered">
            {data.points_covered.avg_pct}% on average
          </h2>
          <p className="mt-1 text-[11px] text-clay-700" data-testid="progress-points-sample">
            Based on {data.points_covered.sample}{" "}
            {data.points_covered.sample === 1 ? "answer" : "answers"} you compared.
          </p>
        </Card>
      )}

      <Card>
        <Eyebrow>Your rubric, on average</Eyebrow>
        <ul className="mt-3 flex flex-col gap-2">
          {Object.keys(LABEL).map((key) => {
            const value = rubric[key];
            return (
              <li key={key} className="flex items-center gap-3" data-testid="progress-rubric-row">
                <span className="w-28 shrink-0 text-[12px]">{LABEL[key]}</span>
                <span className="h-1.5 flex-1 rounded-full bg-[#E7DECB]" aria-hidden="true">
                  <span
                    className="block h-1.5 rounded-full bg-[#8A7A5C]"
                    style={{ width: value === null || value === undefined ? 0 : `${(value / 2) * 100}%` }}
                  />
                </span>
                <span className="num-mono w-16 shrink-0 text-right text-[11px] text-clay-700">
                  {value === null || value === undefined ? "not scored" : `${value}/2`}
                </span>
              </li>
            );
          })}
        </ul>
        {weakest.length > 0 && (
          <p className="mt-3 text-[12px] text-clay-700" data-testid="progress-weakest">
            {weakest.length === 1
              ? `Your lowest-scoring criterion is ${LABEL[weakest[0]].toLowerCase()}.`
              : `Your lowest-scoring criteria are ${weakest
                  .map((k) => LABEL[k].toLowerCase())
                  .join(" and ")}.`}
          </p>
        )}
      </Card>

      <Card>
        <Eyebrow>By topic</Eyebrow>
        {data.strongest_topics.length === 0 ? (
          <p className="mt-2 text-[12px] text-clay-700" data-testid="progress-topics-empty">
            No topic has {data.min_attempts_per_topic} answers yet
            {data.topics_below_threshold > 0
              ? ` — ${data.topics_below_threshold} ${
                  data.topics_below_threshold === 1 ? "topic is" : "topics are"
                } close.`
              : "."}{" "}
            Fewer than that is too little to call a topic strong or weak.
          </p>
        ) : (
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-[11px] text-clay-700">Strongest</p>
              <ul className="mt-1">
                {data.strongest_topics.map((t) => (
                  <li key={t.topic} className="py-0.5 text-[12px]" data-testid="progress-topic-strong">
                    {t.topic} — {t.avg_self_total}/12 over {t.attempts}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[11px] text-clay-700">Weakest</p>
              <ul className="mt-1">
                {data.weakest_topics.map((t) => (
                  <li key={t.topic} className="py-0.5 text-[12px]" data-testid="progress-topic-weak">
                    {t.topic} — {t.avg_self_total}/12 over {t.attempts}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
