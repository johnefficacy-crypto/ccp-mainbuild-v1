import React, { useState } from "react";
import PropTypes from "prop-types";
import { ChevronRight } from "lucide-react";

import CycleProgressRail from "./CycleProgressRail";
import PhaseBandTimeline from "./PhaseBandTimeline";

/**
 * How long is left, in one line — and the whole cycle behind one click.
 *
 * The plan page used to open with a full-width cycle console: a planned-vs-
 * actual curve, a progress rail, phase bands, per-subject bars, and a metric
 * strip reading "planned 62% · actual 0% · plan v9 · planner_v1". All of it
 * sat above the only thing an aspirant opens this page for, which is today's
 * work. The dates still matter — they are just not what you need on every
 * visit. So: one line, and the rest expands in place.
 *
 * Nothing is fetched here. The line and the ladder come from the same
 * `/api/study/plan/timeline` payload the page already loads, so opening the
 * detail costs no request.
 */
function titleCase(value) {
  const s = String(value || "").replace(/[_-]+/g, " ").trim();
  return s ? s[0].toUpperCase() + s.slice(1) : "";
}

export default function CycleCountdown({ timeline }) {
  const [open, setOpen] = useState(false);

  const exam = timeline?.exam_context || {};
  const days = exam.days_remaining;
  const milestones = Array.isArray(timeline?.milestones) ? timeline.milestones : [];
  const bands = Array.isArray(timeline?.phase_bands) ? timeline.phase_bands : [];

  // No date to count to, no line. A countdown that says "—" is worse than no
  // countdown: it puts a question at the top of the page and answers nothing.
  if (days == null) return null;

  const phase = titleCase(exam.phase) || exam.exam_name || "Your exam";
  const dayWord = Math.abs(days) === 1 ? "day" : "days";
  const headline =
    days > 0
      ? `${phase} · ${days} ${dayWord}`
      : days === 0
        ? `${phase} · today`
        : `${phase} · done`;

  return (
    <div data-testid="cycle-countdown">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        data-testid="cycle-countdown-toggle"
        className="group flex w-full items-baseline gap-2 rounded-lg px-1 py-1 text-left hover:bg-[#F3EADB] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218]"
      >
        <span className="font-heading text-[15px] leading-tight text-[#2E2218]">
          {headline}
        </span>
        <span className="text-[11.5px] text-clay-700">
          {open ? "Hide the dates" : "See the dates"}
        </span>
        <ChevronRight
          aria-hidden="true"
          className={`h-3.5 w-3.5 shrink-0 self-center text-clay-700 transition-transform ${
            open ? "rotate-90" : ""
          }`}
        />
      </button>

      {open && (
        <div
          data-testid="cycle-countdown-detail"
          className="mt-3 rounded-xl border border-[#E7DECB] bg-white/60 px-4 py-4"
        >
          <CycleProgressRail milestones={milestones} phaseBands={bands} />
          <div className="mt-5 border-t border-[#E7DECB] pt-5">
            <PhaseBandTimeline
              bands={bands}
              today={milestones.find((m) => m.kind === "today")?.date}
            />
          </div>
        </div>
      )}
    </div>
  );
}

CycleCountdown.propTypes = {
  timeline: PropTypes.shape({
    exam_context: PropTypes.shape({
      phase: PropTypes.string,
      exam_name: PropTypes.string,
      days_remaining: PropTypes.number,
    }),
    milestones: PropTypes.array,
    phase_bands: PropTypes.array,
  }),
};
