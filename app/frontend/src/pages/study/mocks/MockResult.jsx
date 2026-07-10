import React, { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api";
import AttemptSummaryCard from "../components/reports/AttemptSummaryCard";
import SectionBreakdownBars from "../components/reports/SectionBreakdownBars";
import { getAttemptReturnContext } from "./attemptReturnContext";
import { errorTypeLabel } from "./errorTypeLabels";
const AccuracyHeatmap = lazy(() => import("../components/reports/AccuracyHeatmap"));
const TimeDistributionChart = lazy(() => import("../components/reports/TimeDistributionChart"));
const ErrorTypeDonut = lazy(() => import("../components/reports/ErrorTypeDonut"));

const TABS = ["overview", "topic", "time", "error"];
const TAB_LABELS = { overview: "Overview", topic: "Topic", time: "Time", error: "Error" };

function fmtDuration(sec) {
  const s = Math.max(0, Math.round(Number(sec) || 0));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return m > 0 ? `${m}m ${r}s` : `${r}s`;
}

function StatTile({ label, value, testId }) {
  return (
    <div className="rounded-xl bg-clay-50/70 border border-clay-100 p-3" data-testid={testId}>
      <div className="text-[10px] uppercase tracking-wider text-clay-700">{label}</div>
      <div className="font-heading text-2xl font-semibold mt-1">{value}</div>
    </div>
  );
}

export default function MockResult() {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const returnCtx = useMemo(() => getAttemptReturnContext(attemptId), [attemptId]);
  const [result, setResult] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    api.get(`/api/study/mocks/attempts/${attemptId}/result`).then(setResult);
  }, [attemptId]);
  useEffect(() => {
    if (tab !== "overview") {
      api.get(`/api/study/mocks/attempts/${attemptId}/analytics`).then(setAnalytics).catch(() => setAnalytics({}));
    }
  }, [attemptId, tab]);

  // Aggregate by raw classifier code, then map to a learner-friendly label for
  // display — raw codes (silly_mistake, …) must never reach the chart/tooltip.
  const donut = useMemo(
    () =>
      Object.entries(
        (analytics?.response_classification || []).reduce((a, r) => {
          a[r.error_type] = (a[r.error_type] || 0) + 1;
          return a;
        }, {}),
      ).map(([code, value]) => ({ label: errorTypeLabel(code), code, value })),
    [analytics],
  );

  if (!result) return <div data-testid="result-loading">Loading…</div>;

  const timeUsed = Number(result.time_used_sec || 0);
  const avgPerQ = Number(result.avg_time_per_q_sec || 0);
  const hasTiming = timeUsed > 0;

  return (
    <div className="p-4 space-y-4" data-testid="result-page">
      {returnCtx ? (
        <Link
          to={returnCtx.return_to}
          data-testid="result-back-source"
          className="inline-flex items-center gap-1 text-sm text-clay-700 hover:underline"
        >
          ← {returnCtx.source_label}
        </Link>
      ) : null}

      <div data-testid="result-summary" data-score={result.score_percentage ?? ""}>
        <AttemptSummaryCard
          scorePct={result.score_percentage}
          accuracyPct={
            ((result.total_correct || 0) /
              Math.max((result.total_correct || 0) + (result.total_wrong || 0), 1)) *
            100
          }
          timeUsed={hasTiming ? fmtDuration(timeUsed) : "—"}
        />
      </div>

      <SectionBreakdownBars
        data={(result.section_breakdown || []).map((s) => ({
          section: s.section_name || `Section ${s.section_index + 1}`,
          correct: s.correct,
          wrong: s.wrong,
          unattempted: s.unattempted,
        }))}
      />

      {/* Segmented control (title-case labels). */}
      <div
        className="inline-flex rounded-lg border border-border bg-white p-1"
        role="tablist"
        data-testid="result-tabs"
      >
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            data-testid={`result-tab-${t}`}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-sm rounded-md transition ${
              tab === t ? "bg-clay-900 text-white" : "text-clay-700 hover:bg-clay-100"
            }`}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {tab === "topic" && (
        <Suspense fallback={<div data-testid="chart-loading">Loading chart…</div>}>
          <div data-testid="result-chart-topic">
            <AccuracyHeatmap
              topics={(analytics?.topic_breakdown || []).map((t, i) => ({
                topic_id: t.topic_id || `t${i}`,
                topic_name: t.topic_id || "General",
              }))}
              cells={[]}
            />
          </div>
        </Suspense>
      )}

      {tab === "time" &&
        (hasTiming ? (
          <div data-testid="result-time-panel" className="space-y-3">
            <div className="grid grid-cols-2 gap-3 sm:max-w-md">
              <StatTile label="Total time used" value={fmtDuration(timeUsed)} testId="result-time-total" />
              <StatTile label="Avg per question" value={fmtDuration(avgPerQ)} testId="result-time-avg" />
            </div>
            {(analytics?.topic_breakdown || []).length > 0 ? (
              <Suspense fallback={<div data-testid="chart-loading">Loading chart…</div>}>
                <div data-testid="result-chart-time">
                  <TimeDistributionChart data={[]} />
                </div>
              </Suspense>
            ) : null}
          </div>
        ) : (
          <div
            data-testid="result-time-unavailable"
            className="rounded-xl border border-dashed border-clay-200 bg-clay-50/50 p-6 text-sm text-muted-foreground"
          >
            Time tracking unavailable for this attempt. Start a new attempt after the latest timing
            update to see dwell analysis.
          </div>
        ))}

      {tab === "error" && (
        <Suspense fallback={<div data-testid="chart-loading">Loading chart…</div>}>
          <div data-testid="result-chart-error">
            <ErrorTypeDonut data={donut} />
          </div>
        </Suspense>
      )}

      <button
        data-testid="result-review-btn"
        className="btn btn-primary"
        onClick={() => navigate(`/app/study/mocks/attempts/${attemptId}/review`)}
      >
        Review Questions
      </button>
    </div>
  );
}
