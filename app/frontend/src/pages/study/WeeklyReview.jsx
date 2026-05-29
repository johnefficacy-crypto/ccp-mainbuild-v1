import React, { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../../lib/api";
import { Eyebrow, PageHeader, StatusDot, StudyCard } from "../../shared/ui/studyos";

const PERIODS = ["daily", "weekly", "monthly"];

// Resolve the initial period from `?period=` on first mount.
// Invalid / missing values fall back to the existing "weekly" default.
// Deliberately read once on mount — switching the query string later
// shouldn't yank the user out of a period they manually selected.
function resolveInitialPeriod(search) {
  try {
    const params = new URLSearchParams(search || "");
    const requested = (params.get("period") || "").toLowerCase();
    if (PERIODS.includes(requested)) return requested;
  } catch {
    // URLSearchParams is well supported in target browsers; this catch is
    // defensive in case `search` is exotic.
  }
  return "weekly";
}

function fmtPct(v) {
  if (v === null || v === undefined) return "—";
  return `${Math.round(Number(v) * 100)}%`;
}

function readTone(score) {
  if (score === null || score === undefined) return "bg-[#F3EEE8] text-[#6E5A4A] border-[#DDCFBE]";
  const p = Number(score) * 100;
  if (p >= 90) return "bg-[#E7F6EA] text-[#1E5A33] border-[#B5DDBF]";
  if (p >= 75) return "bg-[#EEF7FF] text-[#164A7A] border-[#BCD9F4]";
  if (p >= 60) return "bg-[#FFF8E8] text-[#6A4A09] border-[#F1DEAF]";
  if (p >= 40) return "bg-[#FFF0E8] text-[#7A3A1D] border-[#EDC6B1]";
  return "bg-[#FCEBEC] text-[#7A1D2C] border-[#E8B9C1]";
}

export default function WeeklyReview() {
  const location = useLocation();
  const [period, setPeriod] = useState(() => resolveInitialPeriod(location.search));
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const title = period === "daily" ? "Today's Report Card" : period === "weekly" ? "Weekly Report Card" : "Monthly Report Card";

  const load = async (p = period) => {
    try {
      const r = await api.get(`/api/study/report-card?period=${p}`);
      setData(r || null);
      setErr("");
    } catch (e) {
      setErr("Report card unavailable right now.");
      if (process.env.NODE_ENV !== "production") console.error(e);
    }
  };

  const recompute = async () => {
    setBusy(true);
    try {
      const r = await api.post(`/api/study/report-card/compute?period=${period}`);
      setData(r || null);
      setErr("");
    } catch (e) {
      setErr("Could not recompute report card.");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    load(period);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period]);

  const scoreCards = useMemo(() => {
    const s = data?.scores || {};
    return [
      { k: "Adherence", v: fmtPct(s.plan_adherence_score), hint: s.label || "No evidence" },
      { k: "Completion", v: fmtPct(s.plan_completion_score), hint: "Completed minutes / planned minutes" },
      { k: "Focus adherence", v: fmtPct(s.focus_adherence_score), hint: "Focus minutes / planned minutes" },
      { k: "Consistency", v: fmtPct(s.consistency_score), hint: "Active days / planned days" },
      { k: "Revision", v: fmtPct(s.revision_completion_score), hint: "Revision tasks completed" },
      { k: "Mock review", v: fmtPct(s.mock_review_score), hint: `Trust: ${data?.evidence_summary?.mock_score_block?.trust_label || "platform_verified"}` },
      { k: "Corrections", v: fmtPct(s.correction_completion_score), hint: "Correction tasks closed" },
      { k: "Backlog Δ", v: `${s.backlog_delta ?? "—"}`, hint: "Backlog movement" },
    ];
  }, [data]);

  return (
    <div className="space-y-6" data-testid="weekly-review-page">
      {err && <div className="rounded-xl bg-clay-50 text-clay-800 text-xs px-3 py-2">{err}</div>}

      <PageHeader
        eyebrow="Report Card"
        title={title}
        sub="Deterministic progress analytics from tracked study behavior. No AI judgement, only evidence."
        right={
          <div className="flex gap-2 items-center">
            <StatusDot state="live" label="" />
            <button type="button" onClick={recompute} disabled={busy} className="text-[12px] px-3 py-1.5 rounded-full bg-[#2E2218] text-[#F3EADB] font-semibold disabled:opacity-50">
              {busy ? "Recomputing…" : "Recompute"}
            </button>
          </div>
        }
      />

      <div className="soft-card rounded-2xl p-2 inline-flex gap-2">
        {PERIODS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPeriod(p)}
            className={`px-4 py-2 rounded-xl text-sm font-semibold ${period === p ? "bg-[#2E2218] text-[#F3EADB]" : "bg-transparent text-[#5D4B3F]"}`}
          >
            {p[0].toUpperCase() + p.slice(1)}
          </button>
        ))}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {scoreCards.map((c) => {
          const scores = data?.scores || {};
          const toneScore =
            c.k === "Adherence"
              ? scores.plan_adherence_score
              : c.k === "Completion"
                ? scores.plan_completion_score
                : c.k === "Focus adherence"
                  ? scores.focus_adherence_score
                  : c.k === "Consistency"
                    ? scores.consistency_score
                    : null;
          return (
            <div key={c.k} className={`rounded-2xl border p-4 ${readTone(toneScore)}`}>
              <Eyebrow>{c.k}</Eyebrow>
              <div className="font-heading text-[28px] mt-1 leading-none">{c.v}</div>
              <div className="text-[11px] mt-2 opacity-90">{c.hint}</div>
            </div>
          );
        })}
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <StudyCard className="!bg-[#F8FBFF] !border-[#C9DCF2]">
          <Eyebrow>Task execution</Eyebrow>
          <div className="text-sm mt-2">Planned: <b>{data?.planned_tasks ?? 0}</b></div>
          <div className="text-sm">Completed: <b>{data?.completed_tasks ?? 0}</b></div>
          <div className="text-sm">Missed / Skipped / Carried: <b>{data?.missed_tasks ?? 0}</b> / <b>{data?.skipped_tasks ?? 0}</b> / <b>{data?.carried_forward_tasks ?? 0}</b></div>
        </StudyCard>
        <StudyCard className="!bg-[#F4FBF2] !border-[#C9E8C3]">
          <Eyebrow>Time evidence</Eyebrow>
          <div className="text-sm mt-2">Planned minutes: <b>{data?.planned_minutes ?? 0}</b></div>
          <div className="text-sm">Completed minutes: <b>{data?.completed_minutes ?? 0}</b></div>
          <div className="text-sm">Focus minutes: <b>{data?.focus_minutes ?? 0}</b></div>
        </StudyCard>
        <StudyCard className="!bg-[#FFF8F1] !border-[#F0D7B8]">
          <Eyebrow>Mocks and corrections</Eyebrow>
          <div className="text-sm mt-2">Mocks taken / reviewed: <b>{data?.mocks_taken ?? 0}</b> / <b>{data?.mocks_reviewed ?? 0}</b></div>
          <div className="text-sm">Correction tasks created / completed: <b>{data?.correction_tasks_created ?? 0}</b> / <b>{data?.correction_tasks_completed ?? 0}</b></div>
          <div className="text-xs text-muted-foreground mt-2">Source: platform tracked</div>
        </StudyCard>
      </div>

      <ReportInsights data={data} />
      <HighYieldCoverageCard coverage={data?.high_yield_coverage} />
      <BacklogHeatmapCard heatmap={data?.backlog_heatmap} />
    </div>
  );
}

// HighYieldCoverageCard renders the deterministic backend metric — covered
// vs total locked high-yield topics for the user's target exam, plus the
// trust_status the backend returns. No client-side computation: the bar
// uses the ratio as-is.
function HighYieldCoverageCard({ coverage }) {
  if (!coverage || typeof coverage !== "object") return null;
  const total = Number(coverage.total) || 0;
  const covered = Number(coverage.covered) || 0;
  const pct = total > 0 ? Math.round((covered / total) * 100) : 0;
  const trust = coverage.trust_status || "preview";
  return (
    <StudyCard className="!bg-white !border-[#E7DECB]" data-testid="report-high-yield">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <Eyebrow>High-yield coverage</Eyebrow>
          <div className="font-heading text-[22px] mt-1 leading-none">
            {covered} / {total}
            <span className="text-clay-700 text-base ml-2">topics mastered</span>
          </div>
        </div>
        <span className="num-mono text-[10px] uppercase tracking-[0.18em] text-clay-700">
          trust · {trust}
        </span>
      </div>
      <div className="mt-3 h-2 bg-[#EFE2C9] rounded-full overflow-hidden">
        <div
          className="h-full bg-sage-500"
          style={{ width: `${pct}%` }}
          data-testid="report-high-yield-bar"
        />
      </div>
      <p className="text-[11px] text-clay-700 mt-2">
        Mastered = mastery score ≥ {Number(coverage.mastered_threshold) || 75} on locked, admin-reviewed high-yield topics.
      </p>
      {total === 0 ? (
        <p className="text-[11px] text-amber-700 mt-1">
          No locked high-yield topics yet — ask an admin to lock topics in /admin/exam-intelligence.
        </p>
      ) : null}
    </StudyCard>
  );
}

// BacklogHeatmapCard renders the per-subject backlog grid. Columns = age
// buckets in the order the backend supplies. Cell shade scales to the max
// cell value in the grid (purely display; the numbers themselves are not
// recomputed).
function BacklogHeatmapCard({ heatmap }) {
  if (!heatmap || typeof heatmap !== "object") return null;
  const buckets = Array.isArray(heatmap.buckets) ? heatmap.buckets : [];
  const subjects = Array.isArray(heatmap.subjects) ? heatmap.subjects : [];
  const grandTotal = Number(heatmap.total) || 0;
  if (!buckets.length) return null;
  const maxCell = subjects.reduce((m, row) => {
    const local = buckets.reduce((mm, b) => Math.max(mm, Number(row?.buckets?.[b]) || 0), 0);
    return Math.max(m, local);
  }, 0);
  const shadeFor = (n) => {
    if (!n) return "bg-[#FBF8F2] text-clay-700";
    const ratio = maxCell ? n / maxCell : 0;
    if (ratio >= 0.75) return "bg-[#7A1D2C] text-white";
    if (ratio >= 0.5) return "bg-[#C75D44] text-white";
    if (ratio >= 0.25) return "bg-[#F1B97E] text-clay-900";
    return "bg-[#F7E2C4] text-clay-900";
  };
  return (
    <StudyCard className="!bg-white !border-[#E7DECB]" data-testid="report-backlog-heatmap">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <Eyebrow>Backlog heatmap</Eyebrow>
          <div className="font-heading text-[22px] mt-1 leading-none">
            {grandTotal}
            <span className="text-clay-700 text-base ml-2">open tasks</span>
          </div>
        </div>
        <span className="num-mono text-[10px] uppercase tracking-[0.18em] text-clay-700">
          by subject · age
        </span>
      </div>
      {subjects.length ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-[12px]" data-testid="report-backlog-heatmap-grid">
            <thead>
              <tr className="text-clay-700 num-mono text-[10px] uppercase tracking-[0.18em]">
                <th className="text-left py-1 pr-3">Subject</th>
                {buckets.map((b) => (
                  <th key={b} className="text-center py-1 px-2">{b}</th>
                ))}
                <th className="text-right py-1 pl-3">Total</th>
              </tr>
            </thead>
            <tbody>
              {subjects.map((row) => (
                <tr key={row.subject} className="border-t border-[#EFE2C9]">
                  <td className="py-1.5 pr-3 text-clay-800">{row.subject}</td>
                  {buckets.map((b) => {
                    const n = Number(row?.buckets?.[b]) || 0;
                    return (
                      <td key={b} className="py-1 px-2 text-center">
                        <span
                          className={`inline-block min-w-[28px] px-2 py-0.5 rounded-md num-mono ${shadeFor(n)}`}
                        >
                          {n}
                        </span>
                      </td>
                    );
                  })}
                  <td className="py-1.5 pl-3 text-right num-mono font-semibold text-clay-900">
                    {row.total}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-[11px] text-clay-700 mt-2">No open backlog tasks.</p>
      )}
    </StudyCard>
  );
}

// ReportInsights renders the deterministic highlights / corrections /
// next_actions lists the backend computes in study_os/report_cards.py. Each
// list is rendered exactly as-returned — no client-side ranking, scoring or
// copy generation.
function ReportInsights({ data }) {
  const highlights = Array.isArray(data?.highlights) ? data.highlights : [];
  const corrections = Array.isArray(data?.corrections) ? data.corrections : [];
  const nextActions = Array.isArray(data?.next_actions) ? data.next_actions : [];
  if (!highlights.length && !corrections.length && !nextActions.length) {
    return null;
  }
  return (
    <div className="grid lg:grid-cols-3 gap-4" data-testid="report-insights">
      <StudyCard className="!bg-[#F4FBF2] !border-[#C9E8C3]" data-testid="report-highlights">
        <Eyebrow>Highlights · this period</Eyebrow>
        {highlights.length ? (
          <ul className="mt-2 space-y-1.5 text-sm text-clay-800">
            {highlights.map((h, i) => (
              <li key={`${h.kind || "h"}-${i}`}>{h.label}</li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted-foreground mt-2">No standout wins yet — close more planned tasks to surface them.</p>
        )}
      </StudyCard>
      <StudyCard className="!bg-[#FCEBEC] !border-[#E8B9C1]" data-testid="report-corrections">
        <Eyebrow>Corrections · top misses</Eyebrow>
        {corrections.length ? (
          <ul className="mt-2 space-y-1.5 text-sm text-clay-800">
            {corrections.map((c, i) => {
              const key = `${c.kind || "c"}-${i}`;
              const linkId = c.task_id || c.mock_id || c.correction_id;
              return (
                <li key={key} className="flex items-baseline gap-2">
                  <span>{c.label}</span>
                  {linkId ? (
                    <span className="num-mono text-[10px] text-clay-700">#{String(linkId).slice(0, 8)}</span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="text-xs text-muted-foreground mt-2">No corrections logged this period.</p>
        )}
      </StudyCard>
      <StudyCard className="!bg-[#F8FBFF] !border-[#C9DCF2]" data-testid="report-next-actions">
        <Eyebrow>Next actions</Eyebrow>
        {nextActions.length ? (
          <ul className="mt-2 space-y-1.5 text-sm text-clay-800">
            {nextActions.map((a, i) => (
              <li key={`${a.kind || "a"}-${i}`}>{a.label}</li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted-foreground mt-2">No suggested next actions yet.</p>
        )}
      </StudyCard>
    </div>
  );
}

