import React, { useMemo, useState } from "react";
import {
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, Info } from "lucide-react";
import PropTypes from "prop-types";
import {
  BAND_COLOR,
  BAND_LABEL,
  PROVENANCE_LINE,
  PROVENANCE_SOURCE,
  REACHABILITY_BANDS,
  SHARED_MEASURE_LINE,
  Y_AXIS_LABEL,
  Y_AXIS_MAX,
  reachabilityConfigFor,
} from "./reachabilityConfig";

/**
 * Reachability trend — how reachable each paper's questions were from standard
 * preparation, per band, per year.
 *
 * This is NOT a difficulty curve. No candidate response data exists for this
 * corpus; every question was read and classified against a fixed rubric. The
 * measure line, the band copy and the provenance note all exist to keep that
 * distinction in front of the reader, so none of them is optional and none is
 * behind a disclosure.
 *
 * Bands render as the stored `pyq_questions.observed_difficulty` enum —
 * Easy/Medium/Hard — with no display mapping layer. The Hard copy says
 * "not reachable", never "difficult": that word is what separates this chart
 * from the difficulty curve it would otherwise be mistaken for.
 */

/** Only papers that have been through a judging pass reach this component. */
function toChartRows(papers) {
  return papers.map((p) => ({
    year: p.year,
    easy: p.easy,
    medium: p.medium,
    hard: p.hard,
  }));
}

/**
 * Direct end-label for one series. The categorical palette clears the CVD
 * separation floor but not by a wide margin, so identity carries on the label
 * as well as the hue — never on color alone.
 */
function EndLabel({ x, y, value, index, total, band }) {
  if (index !== total - 1) return null;
  return (
    <text
      x={x + 8}
      y={y}
      dy={4}
      fontSize={11}
      fontWeight={600}
      fill={BAND_COLOR[band]}
      data-testid={`reachability-end-label-${band}`}
    >
      {BAND_LABEL[band]} {value}
    </text>
  );
}

function BandInfo({ band, copy }) {
  const [open, setOpen] = useState(false);
  const label = BAND_LABEL[band];
  return (
    <div className="flex items-start gap-2">
      <span
        aria-hidden="true"
        className="mt-1 h-2.5 w-2.5 rounded-full shrink-0"
        style={{ backgroundColor: BAND_COLOR[band] }}
      />
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold">{label}</span>
          <button
            type="button"
            aria-label={`What ${label} means`}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="text-muted-foreground hover:text-clay-700 rounded"
            data-testid={`reachability-info-${band}`}
          >
            <Info className="h-3.5 w-3.5" />
          </button>
        </div>
        {open ? (
          <p
            className="mt-1 text-[11px] leading-relaxed text-muted-foreground"
            data-testid={`reachability-info-copy-${band}`}
          >
            {copy}
          </p>
        ) : null}
      </div>
    </div>
  );
}

BandInfo.propTypes = {
  band: PropTypes.oneOf(REACHABILITY_BANDS).isRequired,
  copy: PropTypes.string.isRequired,
};

/**
 * The observation beneath the chart.
 *
 * Deliberately an observation about this corpus, never advice. No study plans,
 * no book lists, no second person. A test asserts the absence of imperative
 * study language, because the line between "here is what the corpus shows" and
 * "here is what you should do about it" is exactly what makes this publishable.
 */
function AnalysisProse() {
  return (
    <div
      className="mt-5 space-y-3 text-sm leading-relaxed text-muted-foreground"
      data-testid="reachability-analysis"
    >
      <p>
        Across all eight papers the Medium band barely moves — it sits close to
        53 questions every year. What changed sits either side of it. Easy fell
        from 39 in 2018 to 10 in 2026, while Hard roughly doubled over the same
        span. On this classification those are one movement, not two: questions
        once reachable from a textbook or a newspaper have become questions
        reachable from no standard source at all.
      </p>
      <p>
        The reachable pool — Easy plus Medium together — has averaged about 70
        questions per paper in recent years. Cutoffs have needed roughly 40 to
        45 net correct once negative marking is applied.
      </p>
      <p>
        Placing those two figures side by side, one observation follows from
        this corpus: the reachable pool alone clears the cutoff, and a paper's
        Hard band can be left entirely unanswered without the arithmetic
        failing. That is a property of how these papers were classified, not a
        prediction about any individual attempt.
      </p>
    </div>
  );
}

export default function ReachabilityTrendCard({ examId = null, phaseId = null }) {
  const config = useMemo(
    () => reachabilityConfigFor(examId, phaseId),
    [examId, phaseId]
  );
  const rows = useMemo(
    () => (config ? toChartRows(config.papers) : []),
    [config]
  );

  // No judged papers for this exam. The corpus almost certainly HAS rows for
  // it — bulk-defaulted to 'medium' at import — and charting those would be a
  // chart of the import default dressed as a finding. Empty state instead.
  if (!config || rows.length === 0) {
    return (
      <div
        className="soft-card rounded-2xl p-5"
        data-testid="reachability-trend-empty"
      >
        <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">
          Question reachability · by paper
        </div>
        <div className="font-heading text-lg font-semibold mt-0.5">
          Reachability trend
        </div>
        <div className="mt-4 flex items-start gap-3">
          <BarChart3 className="h-5 w-5 text-clay-500 shrink-0" />
          <p className="text-sm text-muted-foreground">
            Difficulty assessment is pending for this exam. Its papers have not
            yet been read against the reachability rubric, so there is nothing
            to plot. {SHARED_MEASURE_LINE}
          </p>
        </div>
      </div>
    );
  }

  const lastIndex = rows.length - 1;

  return (
    <div className="soft-card rounded-2xl p-5" data-testid="reachability-trend-card">
      <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">
        Question reachability · {config.seriesLabel} · {rows.length} judged papers
      </div>
      <div className="font-heading text-lg font-semibold mt-0.5">
        Reachability trend
      </div>

      <div className="mt-4 grid lg:grid-cols-[minmax(0,1fr)_15rem] gap-4">
        <div className="h-72" data-testid="reachability-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 8, right: 78, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E8DFD3" vertical={false} />
              <XAxis
                dataKey="year"
                stroke="#7A6A55"
                fontSize={11}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[0, Y_AXIS_MAX]}
                stroke="#7A6A55"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                label={{
                  value: Y_AXIS_LABEL,
                  angle: -90,
                  position: "insideLeft",
                  style: { fontSize: 11, fill: "#7A6A55" },
                }}
              />
              <Tooltip
                formatter={(value, key) => [value, BAND_LABEL[key] || key]}
                labelFormatter={(y) => `${y} paper`}
              />
              <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              {REACHABILITY_BANDS.map((band) => (
                <Line
                  key={band}
                  type="monotone"
                  dataKey={band}
                  name={BAND_LABEL[band]}
                  stroke={BAND_COLOR[band]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                >
                  <LabelList
                    dataKey={band}
                    content={(props) => (
                      <EndLabel {...props} total={lastIndex + 1} band={band} />
                    )}
                  />
                </Line>
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="space-y-3">
          <p
            className="text-xs leading-relaxed text-muted-foreground"
            data-testid="reachability-measure-line"
          >
            {SHARED_MEASURE_LINE}
          </p>
          <div className="space-y-2.5 pt-1">
            {REACHABILITY_BANDS.map((band) => (
              <BandInfo key={band} band={band} copy={config.bandCopy[band]} />
            ))}
          </div>
        </div>
      </div>

      <AnalysisProse />

      <p
        className="mt-4 text-xs leading-relaxed text-clay-700 bg-clay-50/70 border border-clay-100 rounded-lg px-3 py-2"
        data-testid="reachability-caveat"
      >
        {config.caveat}
      </p>

      <p
        className="mt-3 text-[11px] leading-relaxed text-muted-foreground"
        data-testid="reachability-provenance"
      >
        {PROVENANCE_LINE}{" "}
        <span className="font-mono text-[10px]">{PROVENANCE_SOURCE}</span>
      </p>
    </div>
  );
}

ReachabilityTrendCard.propTypes = {
  /** Exam id or slug. Resolved against the per-exam reachability config. */
  examId: PropTypes.string,
  /**
   * Optional narrowing filter. Read the phase-scoping note in
   * reachabilityConfig.js first — `exam_phases` has no unique constraint and
   * UPSC's eight judged papers span two phase ids, so passing one here splits
   * a continuous series.
   */
  phaseId: PropTypes.string,
};
