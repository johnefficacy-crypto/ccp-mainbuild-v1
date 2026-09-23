// ROADMAP-01 — "Syllabus roadmap" section on the Progress tab.
//
// Reads GET /api/study/progress/roadmap for the user's primary exam (the same
// /api/study/target-exam source the Plan page hydrates from) and renders
// subject → macro topic → microtopic with a state per row. Read-only.
//
// Every threshold shown in the legend comes from the response; nothing here
// hard-codes 50 / 75 / 2 / 14. States are text + icon, never colour alone.
import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { api } from "../../../../lib/api";

const PLAN_PATH = "/app/study/plan";

const STATE_META = {
  mastered: { label: "Mastered", icon: "✓", cls: "border-emerald-300 bg-emerald-50 text-emerald-800" },
  studied: { label: "Studied", icon: "◐", cls: "border-sky-300 bg-sky-50 text-sky-800" },
  not_started: { label: "Not started", icon: "○", cls: "border-neutral-300 bg-white text-neutral-600" },
};

export function StateChip({ state }) {
  const meta = STATE_META[state] || STATE_META.not_started;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${meta.cls}`}
      data-testid="roadmap-state-chip"
      data-state={state}
    >
      <span aria-hidden="true">{meta.icon}</span>
      {meta.label}
    </span>
  );
}
StateChip.propTypes = { state: PropTypes.string };

function Badge({ children, testId }) {
  return (
    <span
      className="inline-flex items-center rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-xs font-medium text-amber-900"
      data-testid={testId}
    >
      {children}
    </span>
  );
}
Badge.propTypes = { children: PropTypes.node, testId: PropTypes.string };

// Inline SVG sparkline — no chart library. Renders nothing without history.
export function Sparkline({ points, width = 72, height = 20 }) {
  const values = (points || []).map((p) => Number(p?.score)).filter((v) => Number.isFinite(v));
  if (values.length === 0) return null;
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  const y = (v) => height - (Math.max(0, Math.min(100, v)) / 100) * height;
  const d = values.map((v, i) => `${i === 0 ? "M" : "L"}${(i * step).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="shrink-0 max-[359px]:hidden"
      role="img"
      aria-label={`Score history, ${values.length} point${values.length === 1 ? "" : "s"}`}
      data-testid="roadmap-sparkline"
    >
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.5" className="text-neutral-500" />
      {values.length === 1 && <circle cx={0} cy={y(values[0])} r="2" className="fill-neutral-500" />}
    </svg>
  );
}
Sparkline.propTypes = { points: PropTypes.array, width: PropTypes.number, height: PropTypes.number };

function Legend({ thresholds }) {
  if (!thresholds) return null;
  const { weak_below: weak, mastered_at: mastered, min_attempts: minAttempts, revise_after_days: days } = thresholds;
  return (
    <p className="text-xs text-neutral-600" data-testid="roadmap-legend">
      <span className="font-medium">Mastered</span>: score {mastered}+ after {minAttempts}+ attempts ·{" "}
      <span className="font-medium">Weak</span>: below {weak} after {minAttempts}+ attempts ·{" "}
      <span className="font-medium">Revise</span>: mastered, not practised for more than {days} days
    </p>
  );
}
Legend.propTypes = { thresholds: PropTypes.object };

function ScheduleLink({ name }) {
  return (
    <Link
      to={PLAN_PATH}
      className="text-xs font-medium text-sky-700 underline-offset-2 hover:underline"
      aria-label={`Schedule ${name || "this topic"} on your plan`}
      data-testid="roadmap-schedule-link"
    >
      Schedule
    </Link>
  );
}
ScheduleLink.propTypes = { name: PropTypes.string };

function MicroRow({ micro }) {
  return (
    <li
      className="flex flex-col gap-1 py-1.5 pl-6 sm:flex-row sm:items-center sm:gap-3"
      data-testid="roadmap-micro-row"
    >
      <span className="min-w-0 flex-1 text-sm text-neutral-800">
        {micro.name}
        {micro.is_high_yield && (
          <span className="ml-2 text-xs font-medium text-violet-700" data-testid="roadmap-high-yield">
            <span aria-hidden="true">★ </span>High-yield
          </span>
        )}
      </span>
      <div className="flex flex-wrap items-center gap-2">
        <StateChip state={micro.state} />
        <span className="text-xs text-neutral-600">
          {micro.completed_tasks} task{micro.completed_tasks === 1 ? "" : "s"} done
        </span>
        <ScheduleLink name={micro.name} />
      </div>
    </li>
  );
}
MicroRow.propTypes = { micro: PropTypes.object.isRequired };

function MacroRow({ macro }) {
  const [open, setOpen] = useState(false);
  const micros = macro.micros || [];
  const score = macro.score == null ? "—" : Math.round(macro.score);
  return (
    <li className="border-t border-neutral-100 py-2" data-testid="roadmap-macro-row">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
        <div className="min-w-0 flex-1">
          {micros.length > 0 ? (
            <button
              type="button"
              className="text-left text-sm font-medium text-neutral-900"
              aria-expanded={open}
              onClick={() => setOpen((v) => !v)}
            >
              <span aria-hidden="true">{open ? "▾ " : "▸ "}</span>
              {macro.name}
            </button>
          ) : (
            <span className="text-sm font-medium text-neutral-900">{macro.name}</span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StateChip state={macro.state} />
          {macro.weak && <Badge testId="roadmap-weak-badge">Weak</Badge>}
          {macro.revise && <Badge testId="roadmap-revise-badge">Revise</Badge>}
          <span className="text-xs text-neutral-700" data-testid="roadmap-score">Score {score}</span>
          <span className="text-xs text-neutral-600">
            {macro.attempts} attempt{macro.attempts === 1 ? "" : "s"}
          </span>
          <Sparkline points={macro.history} />
          <ScheduleLink name={macro.name} />
        </div>
      </div>
      {open && micros.length > 0 && (
        <ul className="mt-1" aria-label={`${macro.name} microtopics`}>
          {micros.map((m) => (
            <MicroRow key={m.topic_id} micro={m} />
          ))}
        </ul>
      )}
    </li>
  );
}
MacroRow.propTypes = { macro: PropTypes.object.isRequired };

function SubjectBlock({ subject }) {
  const [open, setOpen] = useState(false);
  const r = subject.rollup || {};
  const total = (r.not_started || 0) + (r.studied || 0) + (r.mastered || 0);
  return (
    <div className="rounded-lg border border-neutral-200 bg-white" data-testid="roadmap-subject">
      <button
        type="button"
        className="flex w-full flex-col gap-1 px-3 py-2 text-left sm:flex-row sm:items-center sm:justify-between"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="font-medium text-neutral-900">
          <span aria-hidden="true">{open ? "▾ " : "▸ "}</span>
          {subject.name}
        </span>
        <span className="text-xs text-neutral-600">
          {r.mastered || 0} of {total} mastered · {r.studied || 0} studied · {r.not_started || 0} not started
          {r.weak_count ? ` · ${r.weak_count} weak` : ""}
          {r.revise_count ? ` · ${r.revise_count} to revise` : ""}
        </span>
      </button>
      {open && (
        <ul className="px-3 pb-2">
          {(subject.macros || []).map((m) => (
            <MacroRow key={m.topic_id} macro={m} />
          ))}
        </ul>
      )}
    </div>
  );
}
SubjectBlock.propTypes = { subject: PropTypes.object.isRequired };

function hasAnyEvidence(subjects) {
  return subjects.some((s) =>
    (s.macros || []).some(
      (m) => m.state !== "not_started" || (m.micros || []).some((x) => x.state !== "not_started"),
    ),
  );
}

// Presentational: renders a loaded roadmap payload.
export function SyllabusRoadmapView({ data }) {
  const subjects = Array.isArray(data?.subjects) ? data.subjects : [];
  return (
    <div className="space-y-3">
      <Legend thresholds={data?.thresholds} />
      {!hasAnyEvidence(subjects) && (
        <p className="text-sm text-neutral-700" data-testid="roadmap-empty">
          Nothing practised yet — mocks and completed plan tasks fill this in as you go.
        </p>
      )}
      {subjects.map((s) => (
        <SubjectBlock key={s.subject_id} subject={s} />
      ))}
    </div>
  );
}
SyllabusRoadmapView.propTypes = { data: PropTypes.object };

// Container: primary exam → roadmap, with loading / 409 / error / retry states.
export default function SyllabusRoadmap() {
  const [status, setStatus] = useState("loading"); // loading | ready | no_exam | not_ready | error
  const [data, setData] = useState(null);
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    (async () => {
      try {
        const target = await api.get("/api/study/target-exam");
        const examId = target?.selected_exam?.id;
        if (!examId) {
          if (!cancelled) setStatus("no_exam");
          return;
        }
        const body = await api.get(`/api/study/progress/roadmap?exam_id=${encodeURIComponent(examId)}`);
        if (cancelled) return;
        setData(body);
        setStatus("ready");
      } catch (e) {
        if (cancelled) return;
        setStatus(e?.status === 409 ? "not_ready" : "error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  return (
    <section className="space-y-3" aria-labelledby="roadmap-heading" data-testid="syllabus-roadmap">
      <h3 id="roadmap-heading" className="font-heading text-lg font-semibold">
        Syllabus roadmap
      </h3>
      {status === "loading" && (
        <p role="status" className="text-sm text-neutral-600">
          Loading your roadmap…
        </p>
      )}
      {status === "no_exam" && (
        <p className="text-sm text-neutral-700" data-testid="roadmap-no-exam">
          Choose your exam on the <Link to={PLAN_PATH} className="underline">Plan page</Link> to see your roadmap.
        </p>
      )}
      {status === "not_ready" && (
        <p className="text-sm text-neutral-700" data-testid="roadmap-not-ready">
          This exam&apos;s syllabus isn&apos;t ready for planning yet, so there&apos;s no roadmap to show.
        </p>
      )}
      {status === "error" && (
        <div className="flex flex-wrap items-center gap-3" role="alert" data-testid="roadmap-error">
          <p className="text-sm text-neutral-700">Your roadmap didn&apos;t load.</p>
          <button
            type="button"
            className="rounded border px-2 py-1 text-sm"
            onClick={retry}
            data-testid="roadmap-retry"
          >
            Try again
          </button>
        </div>
      )}
      {status === "ready" && <SyllabusRoadmapView data={data} />}
    </section>
  );
}
