import React, { useEffect, useState } from "react";
import { Compass, Flag, Activity, MessageSquareWarning } from "lucide-react";
import { api } from "../../../lib/api";
import { Eyebrow, Pill, StudyCard } from "../../../shared/ui/studyos";

// ExamJourneyCard — single, pictorial "where am I in the journey" summary
// rendered on /app/study/home above ExamCycleTimeline.
//
// Pulls only fields already emitted by:
//   - /api/study/plan/timeline (exam_context.phase, milestones[],
//     cycle_progress.{planned_progress_pct, actual_progress_pct,
//     gap_pct, status}, exam_context.exam_name, exam_context.days_remaining)
//   - /api/study/mission-control (truth_panel.corrections[0]) — passed in
//     via the `correction` prop so we don't double-fetch what StudyHome
//     already loaded.
//
// No client-side computation of progress / risk: the card renders the
// fields verbatim and uses the backend-provided `status` to colour the
// delta pill.

const STATUS_TONE = {
  ahead: { tone: "sage", label: "Ahead of plan" },
  on_track: { tone: "ink", label: "On track" },
  behind: { tone: "rose", label: "Behind plan" },
  not_connected: { tone: "outline", label: "Not connected" },
};

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

// Pick the soonest upcoming milestone with a real date (skip kind='today'
// and undated phase markers).
function pickNextMilestone(milestones) {
  if (!Array.isArray(milestones)) return null;
  const future = milestones
    .filter((m) => m && m.date && m.kind !== "today" && m.status !== "past")
    .filter((m) => {
      const t = Date.parse(m.date);
      return Number.isFinite(t) && t >= Date.parse(new Date().toISOString().slice(0, 10));
    });
  if (!future.length) return null;
  future.sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
  return future[0];
}

export default function ExamJourneyCard({ correction }) {
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .get("/api/study/plan/timeline")
      .then((d) => {
        if (cancelled) return;
        setTimeline(d || null);
        setError("");
      })
      .catch((e) => {
        if (cancelled) return;
        setError("Journey summary temporarily unavailable.");
        if (process.env.NODE_ENV !== "production") console.error(e);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <StudyCard data-testid="exam-journey-card-loading">
        <div className="h-5 w-40 bg-clay-50 rounded animate-pulse" />
        <div className="mt-3 h-12 bg-clay-50 rounded animate-pulse" />
      </StudyCard>
    );
  }

  if (error) {
    return (
      <StudyCard data-testid="exam-journey-card-error">
        <Eyebrow>Exam journey</Eyebrow>
        <p className="mt-2 text-[13px] text-[#7A3925]">{error}</p>
      </StudyCard>
    );
  }

  const exam = timeline?.exam_context || {};
  const progress = timeline?.cycle_progress || {};
  const milestones = Array.isArray(timeline?.milestones) ? timeline.milestones : [];
  const phaseLabel = exam.phase || "Phase not set";
  const nextMilestone = pickNextMilestone(milestones);
  const status = progress.status || "not_connected";
  const tone = STATUS_TONE[status] || STATUS_TONE.not_connected;
  const planned = Number(progress.planned_progress_pct) || 0;
  const actual = Number(progress.actual_progress_pct) || 0;
  const gap = Number(progress.gap_pct);

  let deltaLabel;
  if (status === "not_connected") {
    deltaLabel = "Cycle not connected";
  } else if (Number.isFinite(gap) && gap !== 0) {
    const sign = gap > 0 ? "+" : "";
    deltaLabel = `Planned ${planned}% · Actual ${actual}% (${sign}${gap}%)`;
  } else {
    deltaLabel = `Planned ${planned}% · Actual ${actual}%`;
  }

  const correctionLabel =
    typeof correction === "string" && correction.trim()
      ? correction
      : "No corrections queued.";

  return (
    <StudyCard data-testid="exam-journey-card">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <Eyebrow>Exam journey</Eyebrow>
          <h2 className="font-heading text-lg font-semibold mt-1">
            {exam.exam_name || "Your exam"}
            {exam.days_remaining != null ? (
              <span className="text-clay-700 text-sm ml-2 num-mono">
                {exam.days_remaining}d to D-day
              </span>
            ) : null}
          </h2>
        </div>
        <Pill tone={tone.tone}>{tone.label}</Pill>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <JourneyCell
          icon={<Compass className="h-4 w-4 text-clay-700" aria-hidden="true" />}
          label="Current phase"
          value={phaseLabel}
          testId="exam-journey-phase"
        />
        <JourneyCell
          icon={<Flag className="h-4 w-4 text-clay-700" aria-hidden="true" />}
          label="Next milestone"
          value={
            nextMilestone
              ? `${nextMilestone.label} · ${fmtDate(nextMilestone.date)}`
              : "No upcoming milestones"
          }
          testId="exam-journey-next-milestone"
        />
        <JourneyCell
          icon={<Activity className="h-4 w-4 text-clay-700" aria-hidden="true" />}
          label="Plan vs actual"
          value={deltaLabel}
          testId="exam-journey-delta"
        />
        <JourneyCell
          icon={
            <MessageSquareWarning
              className="h-4 w-4 text-clay-700"
              aria-hidden="true"
            />
          }
          label="Next correction"
          value={correctionLabel}
          testId="exam-journey-correction"
        />
      </div>
    </StudyCard>
  );
}

function JourneyCell({ icon, label, value, testId }) {
  return (
    <div
      className="rounded-xl border border-[#E7DECB] bg-white/70 p-3"
      data-testid={testId}
    >
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="num-mono text-[10px] uppercase tracking-[0.18em] text-clay-700 font-semibold">
          {label}
        </span>
      </div>
      <p className="text-[13px] text-clay-900 leading-snug">{value}</p>
    </div>
  );
}
