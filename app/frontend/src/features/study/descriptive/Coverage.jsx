import PropTypes from "prop-types";
import React, { useEffect, useState } from "react";

import { api } from "../../../lib/api";
import { Card, Eyebrow, StudyEmptyState } from "../../../shared/ui/studyos";

/**
 * Coverage — what has been written, and what is still waiting.
 *
 * COUNTS ARE FRACTIONS, NEVER BARE PERCENTAGES. "18 of 1,351" is honest about
 * the size of what is left in a way "1%" is not, and an aspirant deciding what
 * to write tonight needs the size.
 *
 * ONLY SUBMITTED ATTEMPTS COUNT. An open draft is a question they are in the
 * middle of, not one they have covered — otherwise coverage goes up by opening
 * questions and closing the tab.
 *
 * An average over nothing is shown as absent, not as 0: "0.0 average" reads as
 * "everything they wrote scored zero", which is the opposite of "they have not
 * scored anything yet".
 */

function Meter({ attempted, available }) {
  const pct = available ? Math.round((attempted / available) * 100) : 0;
  return (
    <div className="mt-1 h-1.5 w-full rounded-full bg-[#E7DECB]" aria-hidden="true">
      <div
        className="h-1.5 rounded-full bg-[#8A7A5C]"
        style={{ width: `${Math.min(100, pct)}%` }}
      />
    </div>
  );
}

Meter.propTypes = { attempted: PropTypes.number, available: PropTypes.number };

export function scoreLine(group) {
  if (group.avg_self_score === null || group.avg_self_score === undefined) return null;
  return `${group.avg_self_score}/12 average over ${group.scored_attempts} ${
    group.scored_attempts === 1 ? "answer" : "answers"
  }`;
}

export default function Coverage({ examId, onPickQuestion }) {
  const [data, setData] = useState(null);
  const [state, setState] = useState("idle");
  const [open, setOpen] = useState({});

  useEffect(() => {
    if (!examId) {
      setState("idle");
      return undefined;
    }
    let live = true;
    setState("loading");
    api
      .get(`/api/study/descriptive/coverage?exam_id=${encodeURIComponent(examId)}`)
      .then((d) => {
        if (!live) return;
        setData(d);
        setState("ready");
      })
      .catch(() => live && setState("error"));
    return () => {
      live = false;
    };
  }, [examId]);

  if (!examId) {
    return (
      <Card>
        <p className="text-sm text-clay-700">
          Pick your target exam on the Study Plan first, and this fills with its
          coverage.
        </p>
      </Card>
    );
  }
  if (state === "error") {
    return (
      <Card>
        <p role="status" className="text-sm text-rose-700">
          Couldn&apos;t load your coverage. Reload the page.
        </p>
      </Card>
    );
  }
  if (state === "loading") {
    return (
      <Card>
        <p role="status" className="text-sm text-clay-700">
          Working out what you&apos;ve covered…
        </p>
      </Card>
    );
  }

  const totals = data?.totals || {};
  const subjects = data?.subjects || [];

  if (!subjects.length) {
    return (
      <StudyEmptyState
        icon="◔"
        title="Nothing to cover yet."
        body="There are no descriptive questions for this exam in the corpus."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <Eyebrow>Overall</Eyebrow>
        <h2 className="font-heading mt-1 text-[22px] leading-tight" data-testid="coverage-total">
          {totals.attempted} of {totals.available} written
        </h2>
        <Meter attempted={totals.attempted} available={totals.available} />
        <p className="mt-2 text-[12px] text-clay-700">
          {totals.unattempted} still waiting
          {totals.avg_self_score !== null && totals.avg_self_score !== undefined
            ? ` · ${totals.avg_self_score}/12 average self-score`
            : " · no self-scores yet"}
        </p>
      </Card>

      {subjects.map((subject) => (
        <Card key={subject.subject} padded={false}>
          <div className="px-7 pt-6 pb-3">
            <Eyebrow>{subject.subject}</Eyebrow>
            <h3 className="font-heading mt-1 text-[18px] leading-tight">
              {subject.attempted} of {subject.available} written
            </h3>
            <Meter attempted={subject.attempted} available={subject.available} />
          </div>
          <div className="hairline mx-7" />
          <ul className="px-7 pb-6 pt-2">
            {subject.groups.map((group) => {
              const key = `${subject.subject}::${group.label}`;
              const expanded = Boolean(open[key]);
              return (
                <li key={key} className="border-b border-[#E7DECB] py-3 last:border-0">
                  <button
                    type="button"
                    className="w-full text-left"
                    aria-expanded={expanded}
                    onClick={() => setOpen((o) => ({ ...o, [key]: !o[key] }))}
                    data-testid="coverage-group"
                  >
                    <span className="text-[13px] leading-snug">{group.label}</span>
                    <span className="num-mono mt-1 block text-[10.5px] text-clay-700">
                      {[
                        `${group.attempted} of ${group.available} written`,
                        scoreLine(group),
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  </button>

                  {expanded && group.unattempted_total > 0 && (
                    <div className="mt-2" data-testid="coverage-unattempted">
                      <p className="text-[11px] text-clay-700">
                        Not yet attempted
                        {group.unattempted_total > group.unattempted.length
                          ? ` — showing ${group.unattempted.length} of ${group.unattempted_total}`
                          : ""}
                      </p>
                      <ul className="mt-1">
                        {group.unattempted.map((q) => (
                          <li key={q.id} className="py-1">
                            <button
                              type="button"
                              className="link-under text-left text-[12px]"
                              onClick={() => onPickQuestion && onPickQuestion(q)}
                              data-testid="coverage-unattempted-row"
                            >
                              {q.excerpt}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {expanded && group.unattempted_total === 0 && (
                    <p className="mt-2 text-[11px] text-clay-700">
                      Every question in this group is written.
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </Card>
      ))}
    </div>
  );
}

Coverage.propTypes = {
  examId: PropTypes.string,
  onPickQuestion: PropTypes.func,
};
